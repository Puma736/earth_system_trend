"""Tendencias y relaciones.

- Mann-Kendall con la corrección de Hamed-Rao (tiene en cuenta la autocorrelación).
- Pendiente de Sen, expresada por década, con su rango del 95 %.
- Regresión lineal + t-test, solo como control (avisa si no coincide).
- Corrección por pruebas múltiples con Benjamini-Hochberg (FDR).
- Correlación de Spearman para el puente sequía-focos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymannkendall as mk
from scipy import stats

from app.stats.changepoint import ChangePoint, pettitt

ALPHA = 0.05
MIN_YEARS = 10
# Con menos años, Hamed-Rao no alcanza a corregir bien una autocorrelación fuerte:
# en una simulación sin tendencia dio 23-26 % de falsas tendencias (docs/comparacion-algoritmos.md).
SHORT_SERIES_YEARS = 30


@dataclass(frozen=True)
class TrendResult:
    n_years: int
    slope_per_decade: float
    # Rango del 95 % de la pendiente de Sen, también por década.
    slope_low_per_decade: float
    slope_high_per_decade: float
    # Cambio en todo el período según la recta de Sen (pendiente × años).
    total_change: float
    intercept: float
    p_value: float
    # Control: regresión lineal por mínimos cuadrados + t-test.
    ols_slope_per_decade: float
    ols_p_value: float
    notes: tuple[str, ...] = ()
    method: str = "Mann-Kendall (Hamed-Rao) + Sen slope"
    # Año de cambio de nivel (Pettitt). None si no se pudo calcular.
    change: ChangePoint | None = None

    @property
    def direction(self) -> int:
        """+1 sube, -1 baja, 0 plano."""
        return int(np.sign(self.slope_per_decade))


def _consistency_notes(sen_low: float, sen_high: float, p_value: float, sen_slope: float,
                       ols_slope: float, ols_p: float) -> tuple[str, ...]:
    """Avisos en inglés cuando los métodos no cuentan la misma historia."""
    notes = []
    range_excludes_zero = sen_low > 0 or sen_high < 0
    if range_excludes_zero != (p_value < ALPHA):
        notes.append(
            "The 95% range of the Sen slope and the p-value disagree: treat this result with caution."
        )
    if np.sign(sen_slope) != np.sign(ols_slope) and ols_p < ALPHA:
        notes.append("Linear regression points the other way: the trend may depend on a few extreme years.")
    return tuple(notes)


def lag1_autocorrelation(residuals: np.ndarray) -> float | None:
    """Autocorrelación entre años consecutivos. None si la serie casi no varía."""
    r = residuals - residuals.mean()
    denom = float(np.sum(r * r))
    scale = float(np.max(np.abs(residuals))) if residuals.size else 0.0
    if denom <= (1e-9 * max(scale, 1.0)) ** 2 * residuals.size:
        return None
    return float(np.sum(r[1:] * r[:-1]) / denom)


def _memory_note(residuals: np.ndarray, p_value: float) -> tuple[str, ...]:
    """Aviso cuando la serie es corta, tiene memoria fuerte y el resultado sale significativo."""
    n = residuals.size
    if n >= SHORT_SERIES_YEARS or p_value >= ALPHA:
        return ()
    r1 = lag1_autocorrelation(residuals)
    # Autocorrelación positiva significativa al 5 % (límite aproximado 1.96 / raíz de n).
    if r1 is None or r1 <= 1.96 / np.sqrt(n):
        return ()
    return (
        f"Consecutive years are strongly linked (lag-1 autocorrelation {r1:.2f}) and the series is short: "
        "the p-value may be too optimistic.",
    )


def trend(years: list[int], values: list[float]) -> TrendResult:
    if len(years) != len(values):
        raise ValueError("years and values must have the same length")
    if len(years) < MIN_YEARS:
        raise ValueError(f"Need at least {MIN_YEARS} years, got {len(years)}")

    order = np.argsort(years)
    x = np.asarray(years, dtype=float)[order]
    y = np.asarray(values, dtype=float)[order]

    # Pendiente de Sen sobre los años reales (funciona aunque falte algún año).
    sen = stats.theilslopes(y, x)
    # Significancia: Mann-Kendall con corrección de Hamed-Rao por autocorrelación.
    with np.errstate(invalid="ignore", divide="ignore"):
        p_value = float(mk.hamed_rao_modification_test(y).p)
        if not np.isfinite(p_value):
            # Hamed-Rao no se puede calcular si los residuos no varían (serie constante
            # o recta perfecta). En ese caso usamos el Mann-Kendall original.
            p_value = float(mk.original_test(y).p)
            if not np.isfinite(p_value):
                p_value = 1.0

    # Control: regresión lineal clásica.
    with np.errstate(invalid="ignore", divide="ignore"):
        ols = stats.linregress(x, y)
    ols_slope = float(ols.slope) if np.isfinite(ols.slope) else 0.0
    ols_p = float(ols.pvalue) if np.isfinite(ols.pvalue) else 1.0

    slope, low, high = float(sen.slope), float(sen.low_slope), float(sen.high_slope)
    return TrendResult(
        n_years=len(y),
        slope_per_decade=slope * 10,
        slope_low_per_decade=low * 10,
        slope_high_per_decade=high * 10,
        total_change=float(slope * (x[-1] - x[0])),
        # Valor de la recta de Sen en el primer año, útil para dibujarla.
        intercept=float(sen.intercept + sen.slope * x[0]),
        p_value=p_value,
        ols_slope_per_decade=ols_slope * 10,
        ols_p_value=ols_p,
        notes=_consistency_notes(low, high, p_value, slope, ols_slope, ols_p)
        # Residuos respecto de la recta de Sen: la memoria que queda después de quitar la tendencia.
        + _memory_note(y - (sen.intercept + sen.slope * x), p_value),
        change=pettitt([int(v) for v in x], list(y)),
    )


def fdr(p_values: list[float]) -> list[float]:
    """q-valores de Benjamini-Hochberg, en el mismo orden de entrada."""
    if not p_values:
        return []
    return [float(q) for q in stats.false_discovery_control(p_values, method="bh")]


@dataclass(frozen=True)
class CorrelationResult:
    n_years: int
    rho: float
    p_value: float
    method: str = "Spearman rank correlation"


def spearman(x: list[float], y: list[float]) -> CorrelationResult:
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("Need two series of equal length (at least 3 values)")
    res = stats.spearmanr(x, y)
    return CorrelationResult(n_years=len(x), rho=float(res.statistic), p_value=float(res.pvalue))
