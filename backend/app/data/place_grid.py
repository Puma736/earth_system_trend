"""Focos de Warnes y Montero en una grilla fina, con el centro de cada celda dentro del municipio.

Los municipios salen de geoBoundaries (GeoBolivia, dominio público). FIRMS se consulta
una vez por año y época y el agregado queda en data/firms_places/.
"""

from __future__ import annotations

import csv
import io
import json
import math
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

from app.config import get_settings
from app.data.errors import DataNotAvailable, DataSourceError
from app.regions import BBox

CELL_DEG = 0.05
API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MIN_CONFIDENCE = 30
PAUSE_S = 0.4
_LOCK = threading.Lock()


def snap_center(value: float, step: float = CELL_DEG) -> float:
    """Centro de la celda de `step` grados que contiene el valor. Vale para longitudes negativas."""
    return math.floor(value / step) * step + step / 2


def ring_contains(ring: list, lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def geometry_contains(geometry: dict, lon: float, lat: float) -> bool:
    if geometry["type"] == "Polygon":
        rings = geometry["coordinates"]
        return ring_contains(rings[0], lon, lat) and not any(
            ring_contains(hole, lon, lat) for hole in rings[1:]
        )
    return any(geometry_contains({"type": "Polygon", "coordinates": polygon}, lon, lat) for polygon in geometry["coordinates"])


def load_places(path: Path | None = None) -> list[dict]:
    path = path or get_settings().data_dir / "warnes-montero.geojson"
    if not path.exists():
        raise DataNotAvailable(f"{path.name} is missing.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["features"]


def bounds_of(features: list[dict], pad: float = 0.02) -> BBox:
    lons: list[float] = []
    lats: list[float] = []
    for feature in features:
        _collect(feature["geometry"], lons, lats)
    return BBox(
        west=min(lons) - pad,
        south=min(lats) - pad,
        east=max(lons) + pad,
        north=max(lats) + pad,
    )


def bin_points(points: list[tuple[float, float]], features: list[dict], step: float = CELL_DEG) -> list[dict]:
    """Cuenta detecciones cuya celda tiene el centro dentro de Warnes o de Montero."""
    counts: dict[tuple[float, float], int] = {}
    for lat, lon in points:
        center_lat = round(snap_center(lat, step), 6)
        center_lon = round(snap_center(lon, step), 6)
        if any(geometry_contains(feature["geometry"], center_lon, center_lat) for feature in features):
            key = (center_lat, center_lon)
            counts[key] = counts.get(key, 0) + 1
    return [{"lat": lat, "lon": lon, "count": n} for (lat, lon), n in sorted(counts.items())]


def grid_for_places(year: int, months: tuple[int, ...]) -> tuple[list[dict], float]:
    features = load_places()
    cache = _cache_path(year, months)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), CELL_DEG
    with _LOCK:
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8")), CELL_DEG
        points = _download_points(bounds_of(features), year, months)
        cells = bin_points(points, features)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(cells), encoding="utf-8")
        return cells, CELL_DEG


def _cache_path(year: int, months: tuple[int, ...]) -> Path:
    tag = "".join(f"{month:02d}" for month in months)
    return get_settings().data_dir / "firms_places" / f"warnes-montero_{year}_{tag}.json"


def _collect(geometry: dict, lons: list[float], lats: list[float]) -> None:
    coords = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        for ring in coords:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)
        return
    for polygon in coords:
        for ring in polygon:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)


def _download_points(bbox: BBox, year: int, months: tuple[int, ...]) -> list[tuple[float, float]]:
    key = get_settings().firms_map_key
    if not key:
        raise DataNotAvailable("FIRMS_MAP_KEY is not set. Put it in backend/.env.")
    raw_dir = get_settings().data_dir / "firms_places" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    points: list[tuple[float, float]] = []
    with httpx.Client() as client:
        for day, days in _windows(year, months):
            text = _fetch_chunk(client, key, bbox, day, days, raw_dir)
            points.extend(_detections(text))
    return points


def _windows(year: int, months: tuple[int, ...]):
    day = date(year, 1, 1)
    end = date(year, 12, 31)
    pending: date | None = None
    count = 0
    while day <= end:
        if day.month in months:
            if pending is None:
                pending = day
                count = 1
            elif count < 5:
                count += 1
            else:
                yield pending, count
                pending = day
                count = 1
        elif pending is not None:
            yield pending, count
            pending = None
            count = 0
        day += timedelta(days=1)
    if pending is not None:
        yield pending, count


def _fetch_chunk(client: httpx.Client, key: str, bbox: BBox, day: date, days: int, raw_dir: Path) -> str:
    path = raw_dir / f"{day.isoformat()}_{days}.csv"
    if path.exists():
        return path.read_text(encoding="utf-8")
    url = f"{API}/{key}/MODIS_SP/{bbox.as_firms()}/{days}/{day.isoformat()}"
    errors = waits = 0
    while True:
        try:
            response = client.get(url, timeout=120)
        except httpx.HTTPError as exc:
            errors += 1
            if errors >= 5:
                raise DataSourceError(f"FIRMS did not respond for {day.isoformat()}.") from exc
            time.sleep(2 * errors)
            continue
        text = response.text
        if response.status_code == 429 or "exceeding allowed transaction limit" in text.lower():
            waits += 1
            if waits > 8:
                raise DataSourceError("FIRMS transaction limit did not clear. Try again in a few minutes.")
            time.sleep(60)
            continue
        if response.status_code != 200 or not text.lower().startswith("latitude"):
            body = text.replace(key, "<MAP_KEY>")[:180]
            raise DataSourceError(f"FIRMS rejected {day.isoformat()}: {body}")
        path.write_text(text, encoding="utf-8")
        time.sleep(PAUSE_S)
        return text


def _detections(text: str) -> list[tuple[float, float]]:
    reader = csv.DictReader(io.StringIO(text))
    points: list[tuple[float, float]] = []
    for row in reader:
        try:
            if int(float(row["confidence"])) < MIN_CONFIDENCE:
                continue
            if "type" in row and row["type"] not in ("", "0"):
                continue
            points.append((float(row["latitude"]), float(row["longitude"])))
        except (KeyError, TypeError, ValueError):
            continue
    return points
