"""Modulo de relaciones entre variables.

Correlacion de Pearson, Spearman y correlaciones cruzadas con desfases
temporales (lags).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _to_series(series) -> pd.Series:
    if isinstance(series, pd.Series):
        s = series.copy()
    else:
        s = pd.Series(series)
    return pd.to_numeric(s, errors="coerce")


def pearson(x, y) -> dict:
    """Correlacion de Pearson (lineal) entre dos series.

    Retorna r, p_value, n.
    """
    a = _to_series(x)
    b = _to_series(y)
    df = pd.concat([a, b], axis=1).dropna()
    if len(df) < 3:
        return {"r": None, "p_value": None, "n": len(df), "error": "datos insuficientes"}
    r, p = stats.pearsonr(df.iloc[:, 0], df.iloc[:, 1])
    return {"r": float(r), "p_value": float(p), "n": int(len(df))}


def spearman(x, y) -> dict:
    """Correlacion de Spearman (monotonica por rangos) entre dos series."""
    a = _to_series(x)
    b = _to_series(y)
    df = pd.concat([a, b], axis=1).dropna()
    if len(df) < 3:
        return {"rho": None, "p_value": None, "n": len(df), "error": "datos insuficientes"}
    rho, p = stats.spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return {"rho": float(rho), "p_value": float(p), "n": int(len(df))}


def cross_correlation(x, y, max_lag: int = 12) -> pd.DataFrame:
    """Correlacion cruzada con desfases temporales (lags).

    Calcula Pearson entre x[t] e y[t+lag] para lag en [-max_lag, max_lag].

    Retorna DataFrame con columnas: lag, correlation, p_value.
    """
    a = _to_series(x).reset_index(drop=True)
    b = _to_series(y).reset_index(drop=True)
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            xx = a.iloc[: len(a) - lag] if lag > 0 else a
            yy = b.iloc[lag:] if lag > 0 else b
        else:
            l = -lag
            xx = a.iloc[l:]
            yy = b.iloc[: len(b) - l]
        df = pd.concat([xx.reset_index(drop=True), yy.reset_index(drop=True)], axis=1).dropna()
        if len(df) < 3:
            rows.append({"lag": lag, "correlation": None, "p_value": None, "n": len(df)})
            continue
        r, p = stats.pearsonr(df.iloc[:, 0], df.iloc[:, 1])
        rows.append({"lag": lag, "correlation": float(r), "p_value": float(p), "n": int(len(df))})
    return pd.DataFrame(rows)


def best_lag(x, y, max_lag: int = 12) -> dict:
    """Devuelve el lag con mayor correlacion absoluta."""
    cc = cross_correlation(x, y, max_lag=max_lag)
    valid = cc.dropna(subset=["correlation"])
    if valid.empty:
        return {"lag": None, "correlation": None}
    idx = valid["correlation"].abs().idxmax()
    row = valid.loc[idx]
    return {"lag": int(row["lag"]), "correlation": float(row["correlation"]), "p_value": float(row["p_value"])}
