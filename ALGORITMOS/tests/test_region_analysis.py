"""Prueba del pipeline RegionAnalyzer con datos sinteticos de Santa Cruz (Bolivia).

Genera 10 anos (120 meses) de precipitacion, temperatura y humedad del suelo
con una sequia inducida en los ultimos 3 anos.
"""

import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sci_lab_math.interpreter import RegionAnalyzer


def make_data():
    rng = np.random.default_rng(42)
    n = 120  # 10 anos mensuales
    months = np.arange(n)
    # estacionalidad anual
    season = np.sin(2 * np.pi * months / 12)

    # precipitacion base (mm/mes)
    precip = 80 + 60 * season + rng.normal(0, 15, n)
    precip = np.clip(precip, 0, None)

    # temperatura base (C)
    temp = 26 + 4 * np.cos(2 * np.pi * months / 12) + rng.normal(0, 1.2, n)

    # humedad del suelo (%)
    soil = 30 + 10 * season + rng.normal(0, 4, n)
    soil = np.clip(soil, 5, 60)

    # sequia inducida en ultimos 3 anos (36 meses)
    drought = np.zeros(n)
    drought[-36:] = 1.0
    # reduccion gradual
    ramp = np.linspace(0, 1, 36)
    precip[-36:] = precip[-36:] * (1 - 0.55 * ramp) + rng.normal(0, 5, 36)
    precip = np.clip(precip, 0, None)
    soil[-36:] = soil[-36:] - 12 * ramp + rng.normal(0, 2, 36)
    soil = np.clip(soil, 3, 60)
    temp[-36:] = temp[-36:] + 1.8 * ramp + rng.normal(0, 0.6, 36)

    dates = pd.date_range("2014-01-01", periods=n, freq="MS")

    df = pd.DataFrame({
        "date": dates,
        "precipitacion": precip,
        "temperatura": temp,
        "humedad_suelo": soil,
    })
    return df


def main():
    df = make_data()
    analyzer = RegionAnalyzer(df, entity_name="Santa Cruz - Chiquitania", date_col="date", domain="clima", non_negative=True)
    result = analyzer.analyze(forecast_steps=12)

    print("=" * 80)
    print("ENTIDAD:", result["entity_name"])
    print("OBSERVACIONES:", result["n_observations"])
    print("RANGO:", result["date_range"])
    print("VARIABLES:", result["variables"])
    print("=" * 80)

    for v in result["variables"]:
        print(f"\n--- {v.upper()} ---")
        print("Tendencia lineal:", result["trends"][v]["linear_regression"])
        print("Mann-Kendall:", result["trends"][v]["mann_kendall"])
        print("Anomalias:", result["anomalies"][v])
        cp = result["changepoints"][v]
        print("PELT breakpoints:", cp["pelt"].get("breakpoints"))
        print("CUSUM change_index:", cp["cusum"].get("change_index"))
        fc = result["forecast"][v]
        if "error" not in fc:
            print("Pronostico (primeros 3):", [round(x, 2) for x in fc["forecast"][:3]])
            print("AIC:", round(fc["aic"], 2))

    print("\n" + "=" * 80)
    print("RELACIONES")
    print("=" * 80)
    for key, val in result["relations"].items():
        print(key, "-> Pearson:", val["pearson"], "| Best lag:", val["best_lag"])

    print("\n" + "=" * 80)
    print("PCA")
    print("=" * 80)
    pca = result["patterns"]["pca"]
    print("Varianza explicada:", [round(x, 3) for x in pca.get("explained_variance_ratio", [])])

    print("\n" + "=" * 80)
    print("CONCLUSIONES CIENTIFICAS")
    print("=" * 80)
    for c in result["conclusiones_cientificas"]:
        print(c)

    # guardar resultado json
    import json
    out_path = os.path.join(ROOT, "tests", "resultado_analisis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print("\nResultado guardado en:", out_path)


if __name__ == "__main__":
    main()