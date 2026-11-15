"""Prueba generica: metricas mensuales de ventas y trafico web de una empresa.

Verifica que la libreria se adapta a un dominio distinto al climatico.
"""

import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sci_lab_math.interpreter import DataAnalyzer


def make_data():
    rng = np.random.default_rng(7)
    n = 48
    months = np.arange(n)
    dates = pd.date_range("2021-01-01", periods=n, freq="MS")
    # ventas con tendencia creciente + estacionalidad
    ventas = 100 + 2.5*months + 20*np.sin(2*np.pi*months/12) + rng.normal(0, 8, n)
    ventas = np.clip(ventas, 0, None)
    # trafico web
    trafico = 5000 + 80*months + 1200*np.sin(2*np.pi*months/12) + rng.normal(0, 400, n)
    trafico = np.clip(trafico, 0, None)
    # tasa de conversion (%)
    conversion = 2.0 + 0.03*months + 0.5*np.sin(2*np.pi*months/12) + rng.normal(0, 0.2, n)
    conversion = np.clip(conversion, 0.1, 10)
    df = pd.DataFrame({
        "date": dates,
        "ventas": ventas,
        "trafico_web": trafico,
        "tasa_conversion": conversion,
    })
    return df


def main():
    df = make_data()
    analyzer = DataAnalyzer(df, entity_name="Empresa Demo", date_col="date",
                           domain="general", non_negative=True)
    result = analyzer.analyze(forecast_steps=6)
    print("ENTIDAD:", result["entity_name"], "| DOMINIO:", result["domain"])
    print("FRECUENCIA:", result["frequency"], "| SEASONAL:", result["seasonal_period"])
    print("VARIABLES:", result["variables"])
    print("\nCONCLUSIONES:")
    for c in result["conclusiones_cientificas"]:
        print(c)
    import json
    out = os.path.join(ROOT, "tests", "resultado_generico.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print("\nGuardado en:", out)


if __name__ == "__main__":
    main()