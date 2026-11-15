"""Provincias de Bolivia para acotar el cálculo al lugar elegido.

La sequía usa el rectángulo de las provincias cuando mide al menos 2° por lado
(el mínimo de NASA POWER regional). Si es más chico, usa la celda MERRA-2 del
punto interior. Los focos solo cuentan celdas cuyo centro cae dentro del polígono.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.regions import POWER_MIN_SPAN_DEG, BBox, Region

_GEOJSON = Path(__file__).resolve().parents[3] / "front" / "data" / "bolivia-admin.json"


@lru_cache(maxsize=1)
def _provinces() -> dict[str, dict]:
    payload = json.loads(_GEOJSON.read_text(encoding="utf-8"))
    found: dict[str, dict] = {}
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        if props.get("level") != "province" or not props.get("id"):
            continue
        found[str(props["id"])] = feature
    return found


@lru_cache(maxsize=1)
def _departments() -> dict[str, dict]:
    payload = json.loads(_GEOJSON.read_text(encoding="utf-8"))
    found: dict[str, dict] = {}
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        if props.get("level") != "department" or not props.get("id"):
            continue
        found[str(props["id"])] = feature
    return found


def covers_department(region_id: str, lat: float, lon: float) -> bool:
    """True si el centro de la celda cae dentro del departamento."""
    feature = _departments().get(region_id)
    if feature is None:
        return True
    return _covers(feature, lon, lat)


def focus(region: Region, raw_ids: list[str]) -> tuple[Region, object]:
    """Devuelve la región acotada y un predicado (lat, lon) -> bool.

    Sin ids, la región no cambia y el predicado es None.
    """
    ids = [item.strip() for item in raw_ids if item.strip()]
    if not ids:
        return region, None
    catalog = _provinces()
    missing = [item for item in ids if item not in catalog]
    if missing:
        raise KeyError(", ".join(missing))
    features = [catalog[item] for item in ids]
    box = _union_bbox(features)
    label = _label(features)
    point = None
    if (box.north - box.south) < POWER_MIN_SPAN_DEG or (box.east - box.west) < POWER_MIN_SPAN_DEG:
        point = _interior_point(features, box)
        drought = (
            f"MERRA-2 cell at the center of {label} ({point[0]:.3f}°, {point[1]:.3f}°). "
            "The selected area is smaller than 2°, so the series is the cell that contains that point."
        )
    else:
        drought = f"MERRA-2 average of the rectangle around {label}."
    note = (
        f"Drought uses the {drought} Hotspot counts, the drought-versus-fire comparison, "
        f"and the season-ahead test keep only cells whose center is inside {label}."
    )
    narrowed = Region(id=region.id, name=label, bbox=box, note=note, point=point, clip=False)

    def inside(lat: float, lon: float) -> bool:
        return any(_covers(feature, lon, lat) for feature in features)

    return narrowed, inside


def _label(features: list[dict]) -> str:
    names = [str((feature.get("properties") or {}).get("name") or "province") for feature in features]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    if len(names) == 3:
        return f"{names[0]}, {names[1]} and {names[2]}"
    return f"{len(names)} provinces"


def _interior_point(features: list[dict], box: BBox) -> tuple[float, float]:
    """Un punto que cae dentro de alguna provincia elegida."""
    candidates: list[tuple[float, float]] = [((box.south + box.north) / 2, (box.west + box.east) / 2)]
    for feature in features:
        ring = _outer_ring(feature)
        if not ring:
            continue
        candidates.append((sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring)))
    for step in (8, 16):
        for i in range(1, step):
            for j in range(1, step):
                candidates.append(
                    (
                        box.south + (box.north - box.south) * i / step,
                        box.west + (box.east - box.west) * j / step,
                    )
                )
    for lat, lon in candidates:
        if any(_covers(feature, lon, lat) for feature in features):
            return (round(lat, 4), round(lon, 4))
    return (round(candidates[0][0], 4), round(candidates[0][1], 4))


def _union_bbox(features: list[dict]) -> BBox:
    west = south = float("inf")
    east = north = float("-inf")
    for feature in features:
        box = _feature_bbox(feature)
        west, south = min(west, box.west), min(south, box.south)
        east, north = max(east, box.east), max(north, box.north)
    return BBox(west=west, south=south, east=east, north=north)


def _feature_bbox(feature: dict) -> BBox:
    west = south = float("inf")
    east = north = float("-inf")

    def visit(pair: object) -> None:
        nonlocal west, south, east, north
        if not isinstance(pair, list):
            return
        if len(pair) >= 2 and isinstance(pair[0], (int, float)) and isinstance(pair[1], (int, float)):
            west, east = min(west, float(pair[0])), max(east, float(pair[0]))
            south, north = min(south, float(pair[1])), max(north, float(pair[1]))
            return
        for item in pair:
            visit(item)

    visit((feature.get("geometry") or {}).get("coordinates"))
    return BBox(west=west, south=south, east=east, north=north)


def _outer_ring(feature: dict) -> list:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        return coordinates[0] if coordinates else []
    if geometry.get("type") == "MultiPolygon" and coordinates and coordinates[0]:
        return coordinates[0][0]
    return []


def _covers(feature: dict, lon: float, lat: float) -> bool:
    box = _feature_bbox(feature)
    if lon < box.west or lon > box.east or lat < box.south or lat > box.north:
        return False
    geometry = feature.get("geometry") or {}
    polygons = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        polygons = [polygons]
    return any(_polygon_covers(rings, lon, lat) for rings in polygons)


def _polygon_covers(rings: list, lon: float, lat: float) -> bool:
    if not rings or not _ring_covers(rings[0], lon, lat):
        return False
    return not any(_ring_covers(hole, lon, lat) for hole in rings[1:])


def _ring_covers(ring: list, lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
