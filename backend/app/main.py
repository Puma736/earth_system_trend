"""Earth System Trend Detective — FastAPI backend (NASA Space Apps).

Endpoints consumed by the Next.js frontend on http://localhost:3000.
"""

from __future__ import annotations

import time

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import math_engine as me
from . import nasa_client
from .models import (
    CompareRegionsRequest,
    CorrelationRequest,
    InvestigateRequest,
    LocationSpec,
)
from .regions import REGIONS, VARIABLES

app = FastAPI(title="Earth System Trend Detective", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALGORITHMS = [
    "linear_regression",
    "mann_kendall",
    "sens_slope",
    "z_score",
    "historical_deviation",
    "pearson",
    "spearman",
    "cross_correlation",
    "cusum_change_point",
    "decade_comparison",
    "fft_cycles",
    "forecast",
    "pca",
    "kmeans",
]

_place_cache: dict[str, tuple[float, float, str]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return (
        s.lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        .strip()
    )


async def _resolve_location(spec: LocationSpec) -> dict:
    """Resolve a LocationSpec to {lat, lon, name, region_id?}."""
    if spec.region_id:
        region = REGIONS.get(spec.region_id)
        if not region:
            raise HTTPException(404, f"Unknown region_id '{spec.region_id}'")
        return {"lat": region["lat"], "lon": region["lon"],
                "name": region["name"], "region_id": spec.region_id}

    if spec.lat is not None and spec.lon is not None:
        return {"lat": spec.lat, "lon": spec.lon,
                "name": spec.place or f"{spec.lat:.3f}, {spec.lon:.3f}"}

    if spec.place:
        norm = _norm(spec.place)
        for rid, r in REGIONS.items():
            if norm in _norm(r["name"]) or norm == rid:
                return {"lat": r["lat"], "lon": r["lon"],
                        "name": r["name"], "region_id": rid}
        if norm in _place_cache:
            lat, lon, disp = _place_cache[norm]
            return {"lat": lat, "lon": lon, "name": disp}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": spec.place, "format": "json", "limit": 1},
                    headers={"User-Agent": "trend-detective/0.1"},
                )
                hits = resp.json()
            if hits:
                lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
                _place_cache[norm] = (lat, lon, hits[0]["display_name"])
                return {"lat": lat, "lon": lon, "name": hits[0]["display_name"]}
        except httpx.HTTPError:
            pass
        raise HTTPException(404, f"Could not geocode place '{spec.place}'")

    raise HTTPException(
        422, "Provide region_id, place, or lat+lon to locate the investigation."
    )


async def _variable_series(lat: float, lon: float, variable: str,
                           start_year: int, end_year: int) -> dict:
    """Fetch the first available NASA parameter for a variable."""
    if variable not in VARIABLES:
        raise HTTPException(404, f"Unknown variable '{variable}'")
    meta = VARIABLES[variable]
    fetched = await nasa_client.fetch_monthly(
        lat, lon, meta["nasa_params"], start_year, end_year
    )
    for param in meta["nasa_params"]:
        if param in fetched["series"]:
            s = fetched["series"][param]
            pairs = [(y, v) for y, v in zip(s["years"], s["annual"])
                     if not np.isnan(v)]
            if len(pairs) >= 5:
                return {
                    "variable": variable,
                    "meta": meta,
                    "nasa_param": param,
                    "years": [p[0] for p in pairs],
                    "annual": [float(p[1]) for p in pairs],
                    "monthly": s["monthly"],
                    "source": fetched["source"],
                    "cache": fetched["cache"],
                }
    raise HTTPException(
        502, f"NASA POWER returned no usable data for '{variable}' at "
        f"({lat}, {lon})."
    )


def _monthly_climatology(monthly: dict) -> dict:
    """Mean per calendar month across the fetched years."""
    buckets: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for year_vals in monthly.values():
        for m, v in enumerate(year_vals, 1):
            if v is not None:
                buckets[m].append(v)
    return {str(m): round(float(np.mean(v)), 4) if v else None
            for m, v in buckets.items()}


def _analyze(series: dict, place_name: str, lang: str) -> dict:
    """Run the full detective pipeline on an annual series."""
    years, annual = series["years"], series["annual"]
    linear = me.linear_regression(years, annual)
    mk = me.mann_kendall(annual)
    sen = me.sens_slope(years, annual)
    z = me.z_scores(annual, years)
    dev = me.historical_deviation(annual)
    cusum = me.cusum_change_point(years, annual)
    decade = me.decade_comparison(years, annual)
    cycles = me.fft_cycles(annual)
    fc = me.forecast(years, annual, n_ahead=10)
    narrative = me.detective_verdict(
        place=place_name,
        variable_label=series["meta"]["label"] if lang == "es"
        else series["meta"]["label_en"],
        lang=lang,
        linear=linear, mk=mk, sen=sen, cusum=cusum, z=z, decade=decade,
    )
    return {
        "trends": {"linear": linear, "mann_kendall": mk, "sen_slope": sen},
        "anomalies": {"z_scores": z, "historical_deviation": dev},
        "change_point": cusum,
        "decade_comparison": decade,
        "cycles": cycles,
        "forecast": fc,
        "narrative": narrative,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/status")
def api_status() -> dict:
    return {
        "name": "Earth System Trend Detective API",
        "version": "0.1.0",
        "data_source": "NASA POWER (MERRA-2) monthly",
        "algorithms": ALGORITHMS,
        "cache": nasa_client.cache_stats(),
        "server_time": int(time.time()),
    }


@app.get("/api/catalog")
def api_catalog() -> dict:
    return {"regions": REGIONS, "variables": VARIABLES}


@app.post("/api/investigate")
async def investigate(req: InvestigateRequest) -> dict:
    end_year = req.end_year or (time.gmtime().tm_year - 1)
    loc = await _resolve_location(req)
    series = await _variable_series(
        loc["lat"], loc["lon"], req.variable, req.start_year, end_year
    )
    analysis = _analyze(series, loc["name"], req.lang)
    return {
        "location": loc,
        "variable": {
            "id": req.variable,
            "nasa_param": series["nasa_param"],
            "unit": series["meta"]["unit"],
            "label": series["meta"]["label"],
            "label_en": series["meta"]["label_en"],
        },
        "range": {"start_year": req.start_year, "end_year": end_year},
        "series": {
            "years": series["years"],
            "annual": series["annual"],
            "monthly_climatology": _monthly_climatology(series["monthly"]),
        },
        **analysis,
        "meta": {"source": series["source"], "cache": series["cache"]},
    }


@app.post("/api/correlations")
async def correlations(req: CorrelationRequest) -> dict:
    end_year = req.end_year or (time.gmtime().tm_year - 1)
    loc = await _resolve_location(req)
    sx = await _variable_series(loc["lat"], loc["lon"], req.var_x,
                                req.start_year, end_year)
    sy = await _variable_series(loc["lat"], loc["lon"], req.var_y,
                                req.start_year, end_year)

    common = sorted(set(sx["years"]) & set(sy["years"]))
    ix = {y: i for i, y in enumerate(sx["years"])}
    iy = {y: i for i, y in enumerate(sy["years"])}
    x = np.array([sx["annual"][ix[y]] for y in common])
    y = np.array([sy["annual"][iy[y]] for y in common])

    pearson = me.pearson(x, y)
    spearman = me.spearman(x, y)
    xcorr = me.cross_correlation(x, y, max_lag=req.max_lag)
    matrix = np.column_stack([x, y])
    pca = me.pca_summary(matrix)
    km = me.kmeans(matrix, k=3)

    regimes = [
        {"cluster": c, "years": [int(common[i]) for i in range(len(common))
                                 if km["labels"][i] == c],
         "center": {"x": km["centers"][c][0], "y": km["centers"][c][1]}}
        for c in range(km["k"])
    ]
    return {
        "location": loc,
        "var_x": {"id": req.var_x, "nasa_param": sx["nasa_param"],
                  "unit": sx["meta"]["unit"]},
        "var_y": {"id": req.var_y, "nasa_param": sy["nasa_param"],
                  "unit": sy["meta"]["unit"]},
        "range": {"start_year": req.start_year, "end_year": end_year},
        "years": [int(v) for v in common],
        "series": {"x": x.tolist(), "y": y.tolist()},
        "pearson": pearson,
        "spearman": spearman,
        "cross_correlation": xcorr,
        "pca": pca,
        "kmeans": {"k": km["k"], "labels": km["labels"], "regimes": regimes},
        "meta": {"source_x": sx["source"], "source_y": sy["source"]},
    }


@app.post("/api/compare-regions")
async def compare_regions(req: CompareRegionsRequest) -> dict:
    end_year = req.end_year or (time.gmtime().tm_year - 1)

    async def one(spec: LocationSpec):
        loc = await _resolve_location(spec)
        series = await _variable_series(
            loc["lat"], loc["lon"], req.variable, req.start_year, end_year
        )
        return {"location": loc,
                "years": series["years"],
                "annual": series["annual"],
                **_analyze(series, loc["name"], req.lang),
                "meta": {"source": series["source"],
                         "nasa_param": series["nasa_param"]}}

    ra, rb = await one(req.a), await one(req.b)
    delta = {
        "mean_diff": round(
            float(np.mean(ra["annual"])) - float(np.mean(rb["annual"])), 4),
        "sen_slope_decade_diff": round(
            ra["trends"]["sen_slope"]["per_decade"]
            - rb["trends"]["sen_slope"]["per_decade"], 4),
    }
    return {
        "variable": {"id": req.variable, **VARIABLES[req.variable]},
        "range": {"start_year": req.start_year, "end_year": end_year},
        "a": ra,
        "b": rb,
        "delta": delta,
    }
