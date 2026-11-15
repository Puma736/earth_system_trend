"""Regiones predefinidas y épocas del año.

Los rectángulos son los propuestos en ALCANCE-SEQUIA-FUEGO.md (sección 5).
Los meses de las épocas todavía están "a confirmar" por el equipo.
"""

from dataclasses import dataclass


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


@dataclass(frozen=True)
class Season:
    id: str
    name: str
    months: tuple[int, ...]


REGIONS: dict[str, Region] = {
    r.id: r
    for r in [
        Region(
            id="santa_cruz",
            name="Santa Cruz department",
            bbox=BBox(west=-64.8, south=-20.5, east=-57.4, north=-13.4),
            note="Approximate rectangle: also includes parts of Beni, Chuquisaca, Brazil and Paraguay.",
        ),
        Region(
            id="chiquitania",
            name="Chiquitania",
            bbox=BBox(west=-62.0, south=-19.0, east=-58.0, north=-15.0),
            note="Approximate rectangle, sub-region of Santa Cruz.",
        ),
        Region(
            id="bolivia",
            name="Bolivia",
            bbox=BBox(west=-69.7, south=-22.9, east=-57.4, north=-9.6),
            note="Context only. Wider than 10 degrees, so POWER regional requests must be split.",
        ),
    ]
}

SEASONS: dict[str, Season] = {
    s.id: s
    for s in [
        Season(id="ANN", name="Full year", months=tuple(range(1, 13))),
        Season(id="DRY", name="Dry season (Jun-Oct, to confirm)", months=(6, 7, 8, 9, 10)),
        Season(id="FIRE", name="Burning peak (Aug-Sep, to confirm)", months=(8, 9)),
    ]
}

# POWER regional acepta como máximo 10° por lado.
POWER_MAX_SPAN_DEG = 10.0
