"""Modulo de deteccion de puntos de cambio.

PELT (ruptures) y CUSUM para identificar el indice/fecha exacta de ruptura
estadistica.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import ruptures as rpt


def _to_array(series) -> np.ndarray:
    if isinstance(series, pd.Series):
        arr = series.to_numpy(dtype=float)
    elif isinstance(series, pd.DataFrame):
        arr = series.iloc[:, 0].to_numpy(dtype=float)
    else:
        arr = np.asarray(series, dtype=float)
    return arr


def pelt(series, model: str = "rbf", pen: float = None, min_size: int = 2) -> dict:
    """Deteccion de puntos de cambio con PELT (ruptures).

    Parametros
    ----------
    series : array-like
    model : str
        Modelo de coste: 'l1', 'l2', 'rbf', 'normal', 'ar', etc.
    pen : float | None
        Penalizacion. Si None se usa una heuristica (log(n)*std).
    min_size : int
        Tamano minimo de segmento.

    Retorna
    -------
    dict con keys: breakpoints (indices), segments.
    """
    arr = _to_array(series)
    mask = ~np.isnan(arr)
    if mask.sum() < 4:
        return {"breakpoints": [], "segments": [], "error": "datos insuficientes"}
    # Trabajar solo sobre no-NaN manteniendo indices originales
    idx = np.where(mask)[0]
    clean = arr[mask]
    if pen is None:
        pen = np.log(len(clean)) * np.std(clean) if np.std(clean) > 0 else 1.0
    algo = rpt.Pelt(model=model, min_size=min_size).fit(clean)
    bks = algo.predict(pen=pen)
    # bks incluye len(clean) al final; convertir a indices originales
    orig_bks = [int(idx[b - 1]) + 1 for b in bks if b < len(clean)]
    # segmentos
    segments = []
    prev = 0
    for b in orig_bks + [len(arr)]:
        segments.append({"start": int(prev), "end": int(b)})
        prev = int(b)
    return {"breakpoints": orig_bks, "segments": segments, "penalty": float(pen)}


def cusum(series, threshold: float = None) -> dict:
    """Deteccion de punto de cambio con CUSUM (cambio de media).

    Detecta el indice donde la suma acumulada de desviaciones respecto a la
    media global alcanza su maximo (magnitud del cambio).

    Retorna
    -------
    dict con keys: change_index, change_value, cusum_series (lista).
    """
    arr = _to_array(series)
    clean = pd.Series(arr).ffill().bfill().to_numpy(dtype=float)
    if len(clean) < 4:
        return {"change_index": None, "error": "datos insuficientes"}
    mean = np.mean(clean)
    deviations = clean - mean
    cusum_pos = np.zeros(len(clean))
    cusum_neg = np.zeros(len(clean))
    for i in range(1, len(clean)):
        cusum_pos[i] = max(0, cusum_pos[i - 1] + deviations[i])
        cusum_neg[i] = max(0, cusum_neg[i - 1] - deviations[i])
    # punto de cambio = donde se maximiza |cusum_pos - cusum_neg| acumulado
    cum = np.concatenate(([0.0], np.cumsum(deviations)))
    if threshold is None:
        threshold = float(np.std(clean))
    # punto de cambio = indice donde la suma acumulada alcanza su maximo absoluto
    change_index = int(np.argmax(np.abs(cum[1:])))  # 0-based sobre la serie
    return {
        "change_index": change_index,
        "change_value": float(clean[change_index]) if change_index < len(clean) else None,
        "cusum_max": float(np.max(cusum_pos + cusum_neg)),
        "threshold": float(threshold),
    }
