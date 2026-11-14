# Contrato de la API (tarjeta B1)

Base local: `http://localhost:8000`. Documentación interactiva, siempre al día: `http://localhost:8000/docs`.
La fuente de verdad del formato es [`backend/app/schemas.py`](../backend/app/schemas.py). Si cambias algo allí, actualiza este archivo y avisa al frontend.

- Todos los endpoints son `GET` y devuelven JSON.
- Los textos que ve el usuario vienen en inglés.
- CORS permitido para `http://localhost:3000` (Next.js). Se cambia con `CORS_ORIGINS` en `backend/.env`.

## Parámetros comunes

| Parámetro | Valores | Por defecto |
|---|---|---|
| `region` | `santa_cruz`, `chiquitania`, `bolivia` | `santa_cruz` |
| `season` | `ANN` (año completo), `DRY` (jun–oct), `FIRE` (ago–sep). Los meses están **a confirmar** | `ANN` |
| `start`, `end` | Años. Sequía: 1981–2025. Focos: 2001–2025 | Sequía 1981–2025, focos 2003–2025 |

## Veredictos

| `verdict` | Cuándo |
|---|---|
| `"Real change"` | p < 0,05. En la sequía se usa el **q-valor** (p corregido por FDR entre los 6 indicadores) |
| `"Not yet certain"` | No alcanza ese umbral |
| `"Not enough data"` | Menos de 10 años; `trend` viene en `null` |

## Errores

Nunca se devuelven datos inventados. Siempre `{"detail": "<mensaje>"}`:

| Código | Cuándo | Ejemplo de `detail` |
|---|---|---|
| 404 | Región, época o indicador desconocidos | `Unknown region 'mars'. Options: santa_cruz, chiquitania, bolivia` |
| 422 | Años fuera de rango o `start >= end` | `Years must satisfy 1981 <= start < end <= 2025` |
| 502 | NASA POWER no respondió y no hay caché | `NASA POWER request failed: ...` |
| 503 | Aún no existe el CSV de FIRMS | `firms_monthly_cells.csv not found. Run scripts/download_firms.py first (needs FIRMS_MAP_KEY).` |

Mientras no esté la MAP_KEY, **`/api/hotspots`, `/api/hotspots/grid` y `/api/link` responden 503**. El frontend debe mostrar un estado de "datos de focos pendientes".

---

## `GET /api/regions`

Regiones y épocas para armar los selectores. Ejemplo recortado (vienen 3 regiones y 3 épocas):

```json
{
  "regions": [
    {
      "id": "santa_cruz",
      "name": "Santa Cruz department",
      "bbox": { "west": -64.8, "south": -20.5, "east": -57.4, "north": -13.4 },
      "note": "Approximate rectangle: also includes parts of Beni, Chuquisaca, Brazil and Paraguay."
    }
  ],
  "seasons": [
    { "id": "ANN", "name": "Full year", "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] }
  ]
}
```

## `GET /api/drought?region=santa_cruz&season=DRY`

El tablero de sequía: 6 indicadores y el resumen. **Respuesta real** (14 nov), recortada a 1 indicador y 3 años:

```json
{
  "region": { "id": "santa_cruz", "name": "Santa Cruz department", "bbox": { "...": "..." }, "note": "..." },
  "season": { "id": "DRY", "name": "Dry season (Jun-Oct, to confirm)", "months": [6, 7, 8, 9, 10] },
  "start": 1981,
  "end": 2025,
  "source": "MERRA-2 via NASA POWER",
  "summary": {
    "pointing_to_drying": 6,
    "real_changes": 6,
    "total": 6,
    "text": "6 of 6 indicators point to drying (6 are real changes)"
  },
  "indicators": [
    {
      "param": "PRECTOTCORR",
      "label": "Rainfall",
      "unit": "mm/day",
      "definition": "Average daily rainfall, bias-corrected.",
      "series": [
        { "year": 1981, "value": 1.688 },
        { "year": 1982, "value": 2.117 },
        { "year": 2025, "value": 1.228 }
      ],
      "trend": {
        "slope_per_decade": -0.143,
        "slope_low_per_decade": -0.222,
        "slope_high_per_decade": -0.076,
        "total_change": -0.627,
        "intercept": 1.724,
        "p_value": 0.00013,
        "q_value": 0.00016,
        "ols_slope_per_decade": -0.151,
        "ols_p_value": 0.00021,
        "notes": [],
        "n_years": 45,
        "method": "Mann-Kendall (Hamed-Rao) + Sen slope"
      },
      "points_to_drying": true,
      "verdict": "Real change"
    }
  ]
}
```

- Los 6 `param`, en este orden: `PRECTOTCORR`, `GWETTOP`, `GWETROOT`, `EVPTRNS`, `T2M_MAX`, `RH2M`.
- **Línea de tendencia** para la mini gráfica: `y = intercept + slope_per_decade / 10 * (year - start)`.
- **Rango del 95 %:** `slope_low_per_decade` a `slope_high_per_decade`. Sirve para mostrar "−0.14 mm/day per decade (between −0.22 and −0.08)".
- `total_change`: cuánto cambió en todo el período según la recta de Sen, en la unidad del indicador.
- `ols_slope_per_decade` y `ols_p_value`: regresión lineal, **solo como control**. No hace falta mostrarlos.
- `notes`: avisos en inglés para mostrar debajo del veredicto cuando los métodos no coinciden. Por ejemplo: "The 95% range of the Sen slope and the p-value disagree: treat this result with caution." Casi siempre viene vacío.
- El objeto `trend` de `/api/hotspots` tiene los mismos campos.
- `points_to_drying`: `true` si la tendencia va hacia la sequía (baja, o sube en el caso de `T2M_MAX`). `null` si no hay tendencia.
- Sin caché, la primera consulta tarda unos 10 s por región (6 descargas de POWER), y Bolivia unos 50 s (24). Después sale de la caché en el acto. Para precargarla: `python -m scripts.warm_cache`.

## `GET /api/hotspots?region=santa_cruz&season=FIRE`

Focos por año. *Ejemplo ilustrativo: los datos reales llegan con F1.*

```json
{
  "region": { "...": "..." },
  "season": { "id": "FIRE", "...": "..." },
  "start": 2003,
  "end": 2025,
  "source": "NASA FIRMS, MODIS (Terra + Aqua), confidence >= 30, vegetation fires",
  "series": [
    { "year": 2003, "value": 200 },
    { "year": 2004, "value": 240 }
  ],
  "trend": {
    "slope_per_decade": 400.0,
    "intercept": 200.0,
    "p_value": 0.00001,
    "q_value": null,
    "n_years": 23,
    "method": "Mann-Kendall (Hamed-Rao) + Sen slope"
  },
  "percent_change": 440.0,
  "verdict": "Real change"
}
```

- `value` es el número de focos del año (entero). Los años sin focos vienen con `0`.
- `percent_change`: cambio en todo el período según la recta de Sen, en %. Puede ser `null`.

## `GET /api/hotspots/grid?year=2019&region=santa_cruz&season=FIRE`

Densidad por celda de un año, para el mapa. *Ejemplo ilustrativo.* Cada celda mide `cell_deg` grados y `lat`/`lon` son su centro:

```json
{
  "region": { "...": "..." },
  "season": { "...": "..." },
  "year": 2019,
  "cell_deg": 0.5,
  "cells": [
    { "lat": -17.75, "lon": -61.25, "count": 480 }
  ]
}
```

Para dibujar la celda en Leaflet: rectángulo de `[lat - 0.25, lon - 0.25]` a `[lat + 0.25, lon + 0.25]`.

## `GET /api/link?region=santa_cruz&season=FIRE&indicator=GWETTOP`

El puente: sequía frente a focos, un punto por año. `indicator` es uno de los 6 `param`. *Ejemplo ilustrativo.*

```json
{
  "region": { "...": "..." },
  "season": { "...": "..." },
  "indicator": "GWETTOP",
  "indicator_label": "Surface soil moisture",
  "points": [
    { "year": 2019, "drought_value": 0.41, "hotspots": 5200 },
    { "year": 2024, "drought_value": 0.37, "hotspots": 6100 }
  ],
  "rho": -0.62,
  "p_value": 0.0016,
  "n_years": 23,
  "method": "Spearman rank correlation",
  "caveat": "Relationship, not proof of cause."
}
```

`rho` y `p_value` vienen en `null` si hay menos de 3 años en común.
