"""Focos de calor MODIS (NASA FIRMS), ya agregados por mes y por celda de 0,5°.

El CSV lo genera scripts/download_firms.py. Columnas:
    year,month,lat,lon,count
donde lat/lon son el centro de la celda de 0,5°.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.data.errors import DataNotAvailable
from app.regions import BBox

CELL_DEG = 0.5
FIRST_YEAR = 2001  # primer año de MODIS en FIRMS (2001-2002 solo Terra)
FIRST_COMPARABLE_YEAR = 2003  # Aqua + Terra completos
LAST_YEAR = 2025


@dataclass(frozen=True)
class CellCount:
    year: int
    month: int
    lat: float
    lon: float
    count: int


def cell_center(value: float) -> float:
    """Centro de la celda de 0,5° que contiene el valor."""
    return (value // CELL_DEG) * CELL_DEG + CELL_DEG / 2


def load_cells(path: Path | None = None) -> tuple[CellCount, ...]:
    path = path or get_settings().firms_csv
    if not path.exists():
        raise DataNotAvailable(
            f"{path.name} not found. Run scripts/download_firms.py first (needs FIRMS_MAP_KEY)."
        )
    # Se lee una vez por versión del archivo: si se regenera, cambia su mtime y se vuelve a leer.
    return _read_cells(path, path.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _read_cells(path: Path, _mtime_ns: int) -> tuple[CellCount, ...]:
    with path.open(newline="", encoding="utf-8") as fh:
        return tuple(
            CellCount(
                year=int(row["year"]),
                month=int(row["month"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                count=int(row["count"]),
            )
            for row in csv.DictReader(fh)
        )


def yearly_counts(
    bbox: BBox,
    months: tuple[int, ...],
    start: int,
    end: int,
    cells: Sequence[CellCount] | None = None,
) -> dict[int, int]:
    """Total de focos por año dentro del rectángulo y de los meses de la época.

    Los años sin ningún foco aparecen con 0 (son datos, no faltantes).
    """
    cells = cells if cells is not None else load_cells()
    totals: dict[int, int] = {year: 0 for year in range(start, end + 1)}
    for c in cells:
        if start <= c.year <= end and c.month in months and bbox.contains(c.lat, c.lon):
            totals[c.year] += c.count
    return totals


def grid_for_year(
    bbox: BBox, months: tuple[int, ...], year: int, cells: Sequence[CellCount] | None = None
) -> list[dict]:
    """Densidad por celda de un año, para el mapa."""
    cells = cells if cells is not None else load_cells()
    grid: dict[tuple[float, float], int] = defaultdict(int)
    for c in cells:
        if c.year == year and c.month in months and bbox.contains(c.lat, c.lon):
            grid[(c.lat, c.lon)] += c.count
    return [{"lat": lat, "lon": lon, "count": n} for (lat, lon), n in sorted(grid.items())]
