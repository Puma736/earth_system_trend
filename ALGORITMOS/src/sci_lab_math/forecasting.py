"""Modulo de pronostico de series temporales.

Modelos ARIMA y SARIMA con intervalos de confianza.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX


def _to_series(series) -> pd.Series:
    if isinstance(series, pd.Series):
        s = series.copy()
    else:
        s = pd.Series(series)
    s = pd.to_numeric(s, errors="coerce")
    # rellenar NaN con interpolacion lineal para el modelo
    s = s.interpolate(limit_direction="both")
    return s


def arima_forecast(series, order=(1, 1, 1), steps: int = 12, alpha: float = 0.05,
                   non_negative: bool = False) -> dict:
    """Pronostico con modelo ARIMA.

    Parametros
    ----------
    series : array-like
    order : tuple (p, d, q)
    steps : int, horizonte de pronostico
    alpha : float, nivel de significancia para intervalos de confianza

    Retorna
    -------
    dict con forecast, lower, upper, aic, bic.
    """
    s = _to_series(series).dropna()
    if len(s) < 10:
        return {"error": "Se requieren al menos 10 observaciones."}
    try:
        model = ARIMA(s, order=order)
        fit = model.fit()
        fc = fit.get_forecast(steps=steps)
        mean = fc.predicted_mean
        ci = fc.conf_int(alpha=alpha)
    except Exception as e:
        return {"error": str(e)}
    fc_vals = [float(v) for v in mean.to_numpy()]
    lo_vals = [float(v) for v in ci.iloc[:, 0].to_numpy()]
    up_vals = [float(v) for v in ci.iloc[:, 1].to_numpy()]
    if non_negative:
        fc_vals = [max(0.0, v) for v in fc_vals]
        lo_vals = [max(0.0, v) for v in lo_vals]
    return {
        "order": list(order),
        "steps": int(steps),
        "forecast": fc_vals,
        "lower": lo_vals,
        "upper": up_vals,
        "aic": float(fit.aic),
        "bic": float(fit.bic),
    }


def sarima_forecast(series, order=(1, 1, 1), seasonal_order=None, steps: int = 12,
                    alpha: float = 0.05, s: int = 0, non_negative: bool = False) -> dict:
    """Pronostico con modelo SARIMA (estacional)."""
    series_clean = _to_series(series).dropna()
    n = len(series_clean)
    if n < 10:
        return {"error": "Se requieren al menos 10 observaciones."}
    # determinar periodo estacional
    if seasonal_order is None:
        if s and s >= 2 and n >= 2 * s:
            seasonal_order = (1, 1, 1, s)
        else:
            seasonal_order = (0, 0, 0, 0)
    # si no hay estacionalidad, usar ARIMA
    if seasonal_order == (0, 0, 0, 0) or (isinstance(seasonal_order, (list, tuple)) and seasonal_order[-1] in (0, 1)):
        return arima_forecast(series_clean, order=order, steps=steps, alpha=alpha, non_negative=non_negative)
    try:
        model = SARIMAX(series_clean, order=order, seasonal_order=tuple(seasonal_order),
                        enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False)
        fc = fit.get_forecast(steps=steps)
        mean = fc.predicted_mean
        ci = fc.conf_int(alpha=alpha)
    except Exception as e:
        # fallback a ARIMA
        return arima_forecast(series_clean, order=order, steps=steps, alpha=alpha, non_negative=non_negative)
    fc_vals = [float(v) for v in mean.to_numpy()]
    lo_vals = [float(v) for v in ci.iloc[:, 0].to_numpy()]
    up_vals = [float(v) for v in ci.iloc[:, 1].to_numpy()]
    if non_negative:
        fc_vals = [max(0.0, v) for v in fc_vals]
        lo_vals = [max(0.0, v) for v in lo_vals]
    return {
        "order": list(order),
        "seasonal_order": list(seasonal_order),
        "steps": int(steps),
        "forecast": fc_vals,
        "lower": lo_vals,
        "upper": up_vals,
        "aic": float(fit.aic),
        "bic": float(fit.bic),
    }
