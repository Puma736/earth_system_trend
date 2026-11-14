"""Async NASA POWER (MERRA-2) client with a 24 h TTL cache.

Cache layers: in-memory dict -> /tmp/nasa_cache.json -> live HTTP fetch.
If every live/cached source fails, a deterministic synthetic series is
returned (flagged via ``source="synthetic_fallback"``) so the API keeps
answering during a hackathon demo.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

import httpx
import numpy as np

POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
CACHE_TTL_S = 24 * 3600
CACHE_PATH = os.environ.get("NASA_CACHE_PATH", "/tmp/nasa_cache.json")

_memory_cache: dict[str, dict] = {}
_stats = {"hits": 0, "misses": 0, "disk_hits": 0, "fetches": 0, "fallbacks": 0}
_disk_loaded = False

# Plausible annual baselines per NASA parameter for the synthetic fallback.
_BASELINES = {
    "T2M": 25.0,
    "T2M_MAX": 32.0,
    "PRECTOTCORR": 4.0,
    "GWETTOP": 0.45,
    "GWETROOT": 0.50,
    "GWETPROF": 0.55,
    "EVPTRNS": 4.5,
    "RH2M": 70.0,
    "WS2M": 3.0,
    "ALLSKY_SFC_PAR_TOT": 200.0,
}


def _load_disk() -> None:
    global _disk_loaded
    if _disk_loaded:
        return
    _disk_loaded = True
    try:
        with open(CACHE_PATH) as fh:
            _memory_cache.update(json.load(fh))
    except (OSError, json.JSONDecodeError):
        pass


def _save_disk() -> None:
    try:
        with open(CACHE_PATH, "w") as fh:
            json.dump(_memory_cache, fh)
    except OSError:
        pass


def cache_stats() -> dict:
    return {**_stats, "entries": len(_memory_cache), "ttl_seconds": CACHE_TTL_S}


def _key(lat: float, lon: float, params: tuple[str, ...], start: int, end: int) -> str:
    raw = f"{lat:.4f},{lon:.4f},{','.join(params)},{start},{end}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _is_valid(v: float) -> bool:
    return v is not None and v > -900  # NASA missing sentinel is -999


def _parse(payload: dict, params: list[str]) -> dict[str, dict]:
    """Turn a POWER monthly response into annual + monthly series."""
    raw = payload.get("properties", {}).get("parameter", {})
    out: dict[str, dict] = {}
    for param in params:
        entries = raw.get(param)
        if not entries:
            continue
        monthly: dict[int, list[float | None]] = {}
        ann_from_api: dict[int, float] = {}
        for k, v in entries.items():
            if not _is_valid(v):
                continue
            if k == "ANN":  # whole-period annual mean
                continue
            year, month = int(k[:4]), int(k[4:])
            if month == 13:  # per-year annual mean key
                ann_from_api[year] = float(v)
            elif 1 <= month <= 12:
                monthly.setdefault(year, [None] * 12)[month - 1] = float(v)
        years = sorted(monthly)
        annual = []
        for y in years:
            if y in ann_from_api:
                annual.append(ann_from_api[y])
            else:
                vals = [v for v in monthly[y] if v is not None]
                annual.append(float(np.mean(vals)) if vals else np.nan)
        out[param] = {
            "years": years,
            "annual": annual,
            "monthly": {str(y): monthly[y] for y in years},
        }
    return out


def _synthetic(lat: float, lon: float, params: list[str],
               start_year: int, end_year: int) -> dict[str, dict]:
    """Deterministic stand-in series when NASA POWER is unreachable."""
    out: dict[str, dict] = {}
    years = list(range(start_year, end_year + 1))
    for param in params:
        seed = int(hashlib.sha256(f"{param}:{lat}:{lon}".encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        base = _BASELINES.get(param, 10.0)
        n = len(years)
        trend = (0.015 * base / 10.0) * np.arange(n)  # gentle warming-like drift
        seasonal = rng.normal(0, base * 0.06, n)
        annual = (base + trend + seasonal).round(4).tolist()
        monthly = {
            str(y): [
                round(float(annual[i] + rng.normal(0, base * 0.08)), 4)
                for _ in range(12)
            ]
            for i, y in enumerate(years)
        }
        out[param] = {"years": years, "annual": annual, "monthly": monthly}
    return out


async def fetch_monthly(
    lat: float,
    lon: float,
    params: list[str],
    start_year: int,
    end_year: int,
) -> dict:
    """Fetch monthly POWER data. Returns {series, source, cache}."""
    _load_disk()
    key = _key(lat, lon, tuple(params), start_year, end_year)
    now = time.time()

    hit = _memory_cache.get(key)
    if hit and now - hit["ts"] < CACHE_TTL_S:
        _stats["hits"] += 1
        return {"series": hit["series"], "source": "nasa_power", "cache": "hit"}
    stale = hit  # keep stale entry as offline fallback

    _stats["misses"] += 1
    query = {
        "parameters": ",".join(params),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(POWER_URL, params=query)
                resp.raise_for_status()
            series = _parse(resp.json(), params)
            if series:
                _stats["fetches"] += 1
                _memory_cache[key] = {"ts": now, "series": series}
                _save_disk()
                return {"series": series, "source": "nasa_power", "cache": "miss"}
        except (httpx.HTTPError, ValueError, KeyError):
            if attempt == 1:
                continue
            break

    if stale:
        _stats["disk_hits"] += 1
        return {"series": stale["series"], "source": "nasa_power", "cache": "stale"}

    _stats["fallbacks"] += 1
    return {
        "series": _synthetic(lat, lon, params, start_year, end_year),
        "source": "synthetic_fallback",
        "cache": "none",
    }
