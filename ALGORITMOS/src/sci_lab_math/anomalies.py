"""Modulo de deteccion de anomalias.

Incluye Z-score, desviacion absoluta y desviacion porcentual respecto al
promedio historico.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _to_series(series) -> pd.Series:
    if isinstance(series, pd.Series):
        s = series.copy()
    else:
        s = pd.Series(series)
    return pd.to_numeric(s, errors="coerce")


def z_score(series, ddof: int = 0) -> pd.Series:
    """Z-score de cada observacion respecto a la media y desviacion estandar.

    z = (x - media) / std. Valores con |z| > 2 (o 3) suelen considerarse
    anomalias.

    Parametros
    ----------
    series : array-like
    ddof : int
        Grados de libertad para la desviacion estandar (0 poblacional, 1 muestral).

    Retorna
    -------
    pd.Series de Z-scores (NaN donde la entrada es NaN).
    """
    s = _to_series(series)
    mu = s.mean(skipna=True)
    sd = s.std(skipna=True, ddof=ddof)
    if sd == 0 or pd.isna(sd):
        return pd.Series(np.nan, index=s.index)
    return (s - mu) / sd


def absolute_deviation(series) -> pd.Series:
    """Desviacion absoluta respecto a la mediana (MAD-based robusta).

    Devuelve |x - mediana| para cada observacion.
    """
    s = _to_series(series)
    med = s.median(skipna=True)
    return (s - med).abs()


def percent_deviation(series, baseline=None) -> pd.Series:
    """Desviacion porcentual respecto al promedio historico (o baseline).

    percent = (x - baseline) / baseline * 100.

    Parametros
    ----------
    series : array-like
    baseline : float | None
        Valor de referencia. Si None se usa la media de la serie.

    Retorna
    -------
    pd.Series de porcentajes.
    """
    s = _to_series(series)
    if baseline is None:
        baseline = s.mean(skipna=True)
    if baseline == 0 or pd.isna(baseline):
        return pd.Series(np.nan, index=s.index)
    return (s - baseline) / baseline * 100.0


def detect_anomalies(series, threshold: float = 2.0, method: str = "zscore") -> pd.DataFrame:
    """Detecta anomalias en una serie temporal.

    Parametros
    ----------
    series : array-like
    threshold : float
        Umbral (en unidades de z o desviacion).
    method : str
        'zscore' o 'mad' (mediana + MAD).

    Retorna
    -------
    DataFrame con columnas: value, score, is_anomaly.
    """
    s = _to_series(series)
    if method == "mad":
        med = s.median(skipna=True)
        mad = (s - med).abs().median(skipna=True)
        scale = 1.4826 * mad if mad and mad != 0 else 1.0
        score = (s - med) / scale
    else:
        score = z_score(s)
    out = pd.DataFrame({"value": s, "score": score})
    out["is_anomaly"] = score.abs() > threshold
    return out
