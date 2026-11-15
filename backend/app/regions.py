"""Departamentos de Bolivia y épocas del año.

Cada región es un departamento de GeoBolivia. El rectángulo es el de su polígono.
Los meses de las épocas todavía están "a confirmar" por el equipo.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    def as_firms(self) -> str:
        """Formato que pide la API de área de FIRMS: oeste,sur,este,norte."""
        return f"{self.west},{self.south},{self.east},{self.north}"


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    bbox: BBox
    note: str
    # (lat, lon) cuando el área es menor de 2° y POWER no acepta el promedio regional.
    point: tuple[float, float] | None = None
    # True: la sequía y los focos usan solo celdas cuyo centro cae en el polígono.
    clip: bool = False


@dataclass(frozen=True)
class Season:
    id: str
    name: str
    months: tuple[int, ...]


# Rectángulo del país, solo para descargar FIRMS de una vez. No aparece en el tablero.
BOLIVIA_BBOX = BBox(west=-69.7, south=-22.9, east=-57.4, north=-9.6)

_ADMIN = Path(__file__).resolve().parents[2] / "front" / "data" / "bolivia-admin.json"


def _feature_bounds(feature: dict) -> BBox:
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
    return BBox(west=round(west, 4), south=round(south, 4), east=round(east, 4), north=round(north, 4))


def _departments() -> list[Region]:
    payload = json.loads(_ADMIN.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    provinces: dict[str, int] = {}
    departments: list[dict] = []
    for feature in features:
        props = feature.get("properties") or {}
        if props.get("level") == "province" and props.get("department_id"):
            provinces[str(props["department_id"])] = provinces.get(str(props["department_id"]), 0) + 1
        elif props.get("level") == "department" and props.get("id") and props.get("name"):
            departments.append(feature)
    built: list[Region] = []
    for feature in departments:
        props = feature["properties"]
        name = str(props["name"])
        count = provinces.get(str(props["id"]), 0)
        built.append(
            Region(
                id=str(props["id"]),
                name=name,
                bbox=_feature_bounds(feature),
                note=(
                    f"MERRA-2 average of the cells whose center is inside {name}. "
                    f"Hotspot counts use the same area, across its {count} provinces."
                ),
                clip=True,
            )
        )
    rest = sorted((item for item in built if item.id != "santa-cruz"), key=lambda item: item.name)
    first = [item for item in built if item.id == "santa-cruz"]
    return first + rest


REGIONS: dict[str, Region] = {region.id: region for region in _departments()}

SEASONS: dict[str, Season] = {
    s.id: s
    for s in [
        Season(id="ANN", name="Full year", months=tuple(range(1, 13))),
        Season(id="DRY", name="Dry season (Jun-Oct, to confirm)", months=(6, 7, 8, 9, 10)),
        Season(id="FIRE", name="Burning peak (Aug-Sep, to confirm)", months=(8, 9)),
    ]
}

# POWER regional acepta como máximo 10° por lado y exige al menos 2° por lado.
POWER_MAX_SPAN_DEG = 10.0
POWER_MIN_SPAN_DEG = 2.0
