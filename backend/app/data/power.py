"""MERRA-2 vía NASA POWER (API mensual).

- El endpoint regional admite 1 variable por consulta y 10° por lado como máximo;
  las regiones más grandes se parten en mosaicos.
- El valor de la región es el promedio de sus celdas ponderado por cos(latitud).
- Las respuestas se guardan en disco (settings.cache_dir) para no repetir consultas.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import get_settings
from app.data.errors import DataSourceError
from app.regions import POWER_MAX_SPAN_DEG, BBox

FILL_VALUE = -999.0

# Monthly[año][mes] = valor
Monthly = dict[int, dict[int, float]]


@dataclass(frozen=True)
class Indicator:
    param: str
    label: str
    unit: str
    # -1: baja cuando hay sequía. +1: sube cuando hay sequía.
    drying_sign: int
    definition: str


DROUGHT_INDICATORS: dict[str, Indicator] = {
    i.param: i
    for i in [
        Indicator("PRECTOTCORR", "Rainfall", "mm/day", -1, "Average daily rainfall, bias-corrected."),
        Indicator("GWETTOP", "Surface soil moisture", "0-1", -1, "Wetness of the top 5 cm of soil (0 dry, 1 saturated)."),
        Indicator("GWETROOT", "Root-zone soil moisture", "0-1", -1, "Wetness of the soil where roots take water (top ~1 m)."),
        Indicator("EVPTRNS", "Evapotranspiration", "MJ/m²/day", -1, "Energy used to evaporate water from soil and plants; drops when there is less water."),
        Indicator("T2M_MAX", "Maximum temperature", "°C", +1, "Daily maximum air temperature at 2 m."),
        Indicator("RH2M", "Air humidity", "%", -1, "Relative humidity of the air at 2 m."),
    ]
}


# ---------------------------------------------------------------------------
# Descarga y caché
# ---------------------------------------------------------------------------

def _cache_path(kind: str, key: dict) -> Path:
    settings = get_settings()
    digest = hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]
    folder = settings.cache_dir / "power"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{kind}_{key.get('parameters', 'x')}_{digest}.json"


def _get_json(url: str, params: dict, kind: str) -> dict:
    path = _cache_path(kind, {"url": url, **params})
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    settings = get_settings()
    try:
        resp = httpx.get(url, params=params, timeout=settings.power_timeout_s)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise DataSourceError(f"NASA POWER request failed: {exc}") from exc

    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _tiles(bbox: BBox) -> list[BBox]:
    """Parte un rectángulo en mosaicos de 10° x 10° como máximo."""

    def splits(lo: float, hi: float) -> list[tuple[float, float]]:
        n = max(1, math.ceil((hi - lo) / POWER_MAX_SPAN_DEG))
        step = (hi - lo) / n
        return [(round(lo + i * step, 4), round(lo + (i + 1) * step, 4)) for i in range(n)]

    return [
        BBox(west=w, south=s, east=e, north=n)
        for s, n in splits(bbox.south, bbox.north)
        for w, e in splits(bbox.west, bbox.east)
    ]


def _parse_series(raw: dict[str, float]) -> Monthly:
    """{"AAAAMM": valor} -> {año: {mes: valor}}. Descarta el mes 13 y los -999."""
    out: Monthly = defaultdict(dict)
    for key, value in raw.items():
        year, month = int(key[:4]), int(key[4:])
        if month == 13 or value is None or value == FILL_VALUE:
            continue
        out[year][month] = float(value)
    return dict(out)


def fetch_point(param: str, lat: float, lon: float, start: int, end: int) -> Monthly:
    settings = get_settings()
    params = {
        "parameters": param,
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    payload = _get_json(f"{settings.power_base_url}/point", params, "point")
    try:
        return _parse_series(payload["properties"]["parameter"][param])
    except (KeyError, TypeError) as exc:
        raise DataSourceError(f"Unexpected POWER point response for {param}") from exc


def fetch_regional(param: str, bbox: BBox, start: int, end: int) -> Monthly:
    """Serie mensual de la región: promedio de celdas ponderado por cos(latitud)."""
    settings = get_settings()
    cells: dict[tuple[float, float], Monthly] = {}

    for tile in _tiles(bbox):
        params = {
            "parameters": param,
            "community": "AG",
            "latitude-min": tile.south,
            "latitude-max": tile.north,
            "longitude-min": tile.west,
            "longitude-max": tile.east,
            "start": start,
            "end": end,
            "format": "JSON",
        }
        payload = _get_json(f"{settings.power_base_url}/regional", params, "regional")
        try:
            for feature in payload["features"]:
                lon, lat = feature["geometry"]["coordinates"][:2]
                cells[(round(lat, 4), round(lon, 4))] = _parse_series(
                    feature["properties"]["parameter"][param]
                )
        except (KeyError, TypeError) as exc:
            raise DataSourceError(f"Unexpected POWER regional response for {param}") from exc

    if not cells:
        raise DataSourceError(f"POWER returned no cells for {param}")
    return weighted_mean(cells)


def weighted_mean(cells: dict[tuple[float, float], Monthly]) -> Monthly:
    sums: dict[tuple[int, int], float] = defaultdict(float)
    weights: dict[tuple[int, int], float] = defaultdict(float)
    for (lat, _lon), series in cells.items():
        w = math.cos(math.radians(lat))
        for year, months in series.items():
            for month, value in months.items():
                sums[(year, month)] += w * value
                weights[(year, month)] += w

    out: Monthly = defaultdict(dict)
    for (year, month), total in sums.items():
        out[year][month] = total / weights[(year, month)]
    return dict(out)


# ---------------------------------------------------------------------------
# Agregar por época
# ---------------------------------------------------------------------------

def seasonal_series(monthly: Monthly, months: tuple[int, ...]) -> dict[int, float]:
    """Promedio de los meses de la época para cada año. Solo años con todos los meses."""
    out: dict[int, float] = {}
    for year in sorted(monthly):
        values = [monthly[year][m] for m in months if m in monthly[year]]
        if len(values) == len(months):
            out[year] = sum(values) / len(values)
    return out
