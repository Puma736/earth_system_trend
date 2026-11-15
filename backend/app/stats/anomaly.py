"""Anomalía y puesto de cada año frente a un período normal.

- Anomalía: valor menos la media del período base, en la unidad del indicador.
- z: esa anomalía en desviaciones estándar del período base (muestral).
- % de lo normal: valor / media del período base. Se usa sobre todo para la lluvia.
- Puesto: 1 es el año más extremo de todo el registro (el más seco, o el de más focos).

El período base es fijo (no depende de los años elegidos), así 2019 tiene siempre la
misma anomalía. Para la sequía es 1991-2020, la norma climatológica de la OMM.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, stdev

BASELINE_START = 1991
BASELINE_END = 2020
MIN_BASELINE_YEARS = 10


@dataclass(frozen=True)
class Baseline:
    start: int
    end: int
    mean: float
    sd: float


@dataclass(frozen=True)
class Anomaly:
    year: int
    anomaly: float
    z: float | None
    percent_of_normal: float | None
    rank: int


def baseline(record: dict[int, float], start: int, end: int) -> Baseline | None:
    values = [v for y, v in record.items() if start <= y <= end]
    if len(values) < MIN_BASELINE_YEARS:
        return None
    return Baseline(start=start, end=end, mean=mean(values), sd=stdev(values))


def ranks(record: dict[int, float], extreme_sign: int) -> dict[int, int]:
    """Puesto de cada año: extreme_sign -1 pone primero el más bajo, +1 el más alto.

    Los empates comparten el mejor puesto (1, 2, 2, 4).
    """
    ordered = sorted(record.values(), reverse=extreme_sign > 0)
    first = {}
    for position, value in enumerate(ordered, start=1):
        first.setdefault(value, position)
    return {year: first[value] for year, value in record.items()}


def anomalies(
    record: dict[int, float], years: list[int], base: Baseline, extreme_sign: int
) -> list[Anomaly]:
    """Anomalías de los años pedidos. El puesto se calcula sobre todo el registro."""
    rank = ranks(record, extreme_sign)
    out = []
    for year in years:
        value = record[year]
        diff = value - base.mean
        out.append(
            Anomaly(
                year=year,
                anomaly=diff,
                z=diff / base.sd if base.sd > 0 else None,
                percent_of_normal=100 * value / base.mean if base.mean > 0 else None,
                rank=rank[year],
            )
        )
    return out
