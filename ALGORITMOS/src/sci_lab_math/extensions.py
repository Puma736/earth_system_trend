"""Modulo de extensiones: FFT, Kriging e simulacion Monte Carlo."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import fft as sp_fft
from pykrige.ok import OrdinaryKriging


def fft_frequencies(series, sampling_rate: float = 1.0) -> dict:
    """Analisis de frecuencias con Transformada Rapida de Fourier (FFT).

    Retorna frecuencias dominantes y amplitudes.

    Parametros
    ----------
    series : array-like
    sampling_rate : float
        Muestras por unidad de tiempo (ej. 12 para datos mensuales anuales).

    Retorna
    -------
    dict con frequencies, amplitudes, top_frequencies (lista de (freq, amp)).
    """
    s = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    if len(s) < 4:
        return {"error": "datos insuficientes"}
    arr = s.to_numpy(dtype=float)
    arr = arr - np.mean(arr)
    n = len(arr)
    freqs = sp_fft.rfftfreq(n, d=1.0 / sampling_rate)
    amps = np.abs(sp_fft.rfft(arr)) / n
    # top 5 frecuencias (excluyendo DC)
    order = np.argsort(amps[1:])[::-1] + 1
    top = [(float(freqs[i]), float(amps[i])) for i in order[:5]]
    return {
        "n": int(n),
        "frequencies": [float(f) for f in freqs],
        "amplitudes": [float(a) for a in amps],
        "top_frequencies": top,
    }


def kriging_interpolation(x, y, z, grid_x, grid_y, variogram_model: str = "linear") -> dict:
    """Interpolacion espacial por Kriging ordinario.

    Parametros
    ----------
    x, y : array-like coordenadas de los puntos de medicion.
    z : array-like valores medidos.
    grid_x, grid_y : array-like coordenadas de la grilla de salida.
    variogram_model : str ('linear', 'power', 'gaussian', 'spherical', 'exponential').

    Retorna
    -------
    dict con grid_z (2D lista), variance (2D lista).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    gx = np.asarray(grid_x, dtype=float)
    gy = np.asarray(grid_y, dtype=float)
    try:
        ok = OrdinaryKriging(x, y, z, variogram_model=variogram_model, verbose=False, enable_plotting=False)
        z_pred, ss = ok.execute("grid", gx, gy)
    except Exception as e:
        return {"error": str(e)}
    return {
        "grid_z": np.asarray(z_pred).tolist(),
        "variance": np.asarray(ss).tolist(),
        "variogram_model": variogram_model,
    }


def monte_carlo_simulation(base_value: float, volatility: float, n_steps: int = 30,
                           n_simulations: int = 1000, seed: int = 42) -> dict:
    """Simulacion Monte Carlo de escenarios (movimiento browniano geometrico).

    Util para estimar rangos de valores futuros de una variable.

    Parametros
    ----------
    base_value : float valor inicial.
    volatility : float desviacion estandar de retornos.
    n_steps : int pasos temporales.
    n_simulations : int numero de trayectorias.

    Retorna
    -------
    dict con mean_final, p5, p50, p95, paths (muestra).
    """
    rng = np.random.default_rng(seed)
    shocks = rng.normal(0, volatility, size=(n_simulations, n_steps))
    paths = base_value * np.exp(np.cumsum(shocks, axis=1))
    finals = paths[:, -1]
    return {
        "base_value": float(base_value),
        "volatility": float(volatility),
        "n_steps": int(n_steps),
        "n_simulations": int(n_simulations),
        "mean_final": float(np.mean(finals)),
        "p5": float(np.percentile(finals, 5)),
        "p50": float(np.percentile(finals, 50)),
        "p95": float(np.percentile(finals, 95)),
        "sample_paths": paths[:5].tolist(),
    }
