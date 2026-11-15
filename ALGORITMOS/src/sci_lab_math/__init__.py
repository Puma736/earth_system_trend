"""sci_lab_math: biblioteca modular de analisis cientifico para variables ambientales y satelitales.

Modulos:
- trends: tendencias (regresion lineal, Mann-Kendall, Sen's slope)
- anomalies: anomalias (Z-score, desviacion absoluta/porcentual)
- relations: correlaciones (Pearson, Spearman, correlacion cruzada con lags)
- changepoints: puntos de cambio (PELT, CUSUM)
- patterns: PCA y K-means
- forecasting: ARIMA / SARIMA
- extensions: FFT, Kriging, Monte Carlo
- interpreter: RegionAnalyzer (pipeline completo)
"""

from . import trends, anomalies, relations, changepoints, patterns, forecasting, extensions, interpreter, domains

__all__ = [
    "trends",
    "anomalies",
    "relations",
    "changepoints",
    "patterns",
    "forecasting",
    "extensions",
    "interpreter",
]

__version__ = "0.1.0"