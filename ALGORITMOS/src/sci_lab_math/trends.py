"""Modulo de tendencias temporales.

Incluye regresion lineal (pendiente, R^2, p-valor), prueba de Mann-Kendall
y pendiente de Sen (Sen's Slope).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
import pymannkendall as mk


def _to_series(series) -> pd.Series:
    if isinstance(series, pd.Series):
        s = series.copy()
    elif isinstance(series, (list, tuple, np.ndarray)):
        s = pd.Series(series)
    else:
        s = pd.Series(series)
    s = pd.to_numeric(s, errors="coerce")
    return s


def linear_regression(series) -> dict:
    """Regresion lineal simple sobre una serie temporal.

    Calcula pendiente, intercepto, R^2, p-valor y error estandar de la pendiente.

    Parametros
    ----------
    series : array-like
        Serie temporal (se ignoran NaN).

    Retorna
    -------
    dict con keys: n, slope, intercept, r_squared, p_value, std_err, trend.
    """
    s = _to_series(series).dropna()
    if len(s) < 3:
        return {"n": len(s), "error": "Se requieren al menos 3 observaciones."}
    x = np.arange(len(s), dtype=float)
    y = s.to_numpy(dtype=float)
    res = stats.linregress(x, y)
    trend = "creciente" if res.slope > 0 else ("decreciente" if res.slope < 0 else "sin tendencia")
    # serie estandarizada
    mu = np.mean(y)
    sd = np.std(y, ddof=0)
    if sd and sd != 0:
        yz = (y - mu) / sd
        res_z = stats.linregress(x, yz)
        normalized_slope = float(res_z.slope)
    else:
        normalized_slope = 0.0
    mean = float(np.mean(y)) if len(y) else 0.0
    percent_change_per_step = float((res.slope / mean) * 100.0) if mean != 0 else 0.0
    fitted_line = [float(res.slope * xi + res.intercept) for xi in x]
    return {
        "n": int(len(s)),
        "slope": float(res.slope),
        "intercept": float(res.intercept),
        "r_squared": float(res.rvalue ** 2),
        "p_value": float(res.pvalue),
        "std_err": float(res.stderr),
        "trend": trend,
        "significant": bool(res.pvalue < 0.05),
        "normalized_slope": normalized_slope,
        "percent_change_per_step": percent_change_per_step,
        "fitted_line": fitted_line,
    }


def mann_kendall(series) -> dict:
    """Prueba de Mann-Kendall para tendencias monotonicas.

    No asume normalidad. Devuelve tendencia, p-valor, Z, Tau y pendiente de Sen.

    Parametros
    ----------
    series : array-like

    Retorna
    -------
    dict con keys: trend, h, p_value, z, tau, s, var_s, sens_slope, intercept.
    """
    s = _to_series(series).dropna()
    if len(s) < 4:
        return {"error": "Se requieren al menos 4 observaciones."}
    try:
        res = mk.original_test(s.to_list())
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}
    return {
        "trend": str(res.trend),
        "h": bool(res.h),
        "p_value": float(res.p),
        "z": float(res.z),
        "tau": float(res.Tau),
        "s": float(res.s),
        "var_s": float(res.var_s),
        "sens_slope": float(res.slope),
        "intercept": float(res.intercept),
    }


def sens_slope(series) -> dict:
    """Pendiente de Sen (mediana de pendientes entre pares).

    Util para estimar la magnitud del cambio monotónico por unidad de tiempo.

    Parametros
    ----------
    series : array-like

    Retorna
    -------
    dict con keys: slope, intercept.
    """
    s = _to_series(series).dropna()
    if len(s) < 2:
        return {"error": "Se requieren al menos 2 observaciones."}
    x = np.arange(len(s), dtype=float)
    y = s.to_numpy(dtype=float)
    slopes = []
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = x[j] - x[i]
            if dx != 0:
                slopes.append((y[j] - y[i]) / dx)
    slope = float(np.median(slopes)) if slopes else 0.0
    intercept = float(np.median(y - slope * x))
    return {"slope": slope, "intercept": intercept}