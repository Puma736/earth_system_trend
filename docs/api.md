# Contrato de la API (tarjeta B1)

Base local: `http://localhost:8000`. Documentación interactiva, siempre al día: `http://localhost:8000/docs`.
La fuente de verdad del formato es [`backend/app/schemas.py`](../backend/app/schemas.py). Si cambias algo allí, actualiza este archivo y [`front/lib/types.ts`](../front/lib/types.ts), que es su copia en TypeScript.

- Todos los endpoints son `GET` y devuelven JSON.
- Los textos que ve el usuario vienen en inglés.
- El navegador no llama al backend directamente: el servidor de Next.js reenvía `/api/*` y `/health` a `BACKEND_URL` (`front/.env.local`, ver [`front/next.config.ts`](../front/next.config.ts)). Si el backend corre en otro puerto, cambia esa variable y reinicia `npm run dev`.
- CORS permitido solo para `GET` desde `http://localhost:3000` y `http://127.0.0.1:3000`. Solo hace falta si el navegador llama directo, con `NEXT_PUBLIC_API_URL`. Se cambia con `CORS_ORIGINS` en `backend/.env`, separando los orígenes con comas.

## Parámetros comunes

| Parámetro | Valores | Por defecto |
|---|---|---|
| `region` | `santa_cruz`, `chiquitania`, `bolivia` | `santa_cruz` |
| `season` | `ANN` (año completo), `DRY` (jun–oct), `FIRE` (ago–sep). Los meses están **a confirmar** | `ANN` |
| `start`, `end` | Años. Sequía: 1981–2025. Focos y puente: 2001–2025 | Sequía 1981–2025, focos y puente 2003–2025 |

Los rangos de años también vienen en `/api/regions` (`years`), así el frontend no los repite.

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

Si falta `backend/data/firms_monthly_cells.csv`, **`/api/hotspots`, `/api/hotspots/grid` y `/api/link` responden 503**. El frontend lo muestra como "Hotspot data pending", con un botón para reintentar.

---

## `GET /api/regions`

Todo lo que el frontend necesita para armar los filtros: regiones, épocas, años válidos y los 6 indicadores. Ejemplo recortado (vienen 3 regiones, 3 épocas y 6 indicadores):

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
  ],
  "years": {
    "drought": { "start": 1981, "end": 2025 },
    "hotspots": { "start": 2003, "end": 2025 }
  },
  "indicators": [
    {
      "param": "PRECTOTCORR",
      "label": "Rainfall",
      "unit": "mm/day",
      "definition": "Average daily rainfall, bias-corrected."
    }
  ]
}
```

- `years.hotspots` es el período comparable (desde 2003, el primer año completo con Terra y Aqua). Los endpoints de focos aceptan desde 2001.
- `indicators` viene en el orden del tablero. La unidad `0-1` es una fracción (0 seco, 1 saturado).

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
- **Caché:** el backend siempre pide a POWER el período completo, 1981–2025, y después recorta los años pedidos. Así cualquier rango, y también `/api/link`, sale de la misma caché: cambiar los años en el frontend no vuelve a descargar nada.
- Sin caché, la primera consulta tarda unos 10 s por región (6 descargas de POWER), y Bolivia unos 50 s (24). Después sale de la caché en el acto, incluso sin internet. Para precargarla: `python -m scripts.warm_cache`.

## `GET /api/hotspots?region=santa_cruz&season=FIRE`

Focos por año. **Respuesta real** (14 nov), recortada a 3 años:

```json
{
  "region": { "...": "..." },
  "season": { "id": "FIRE", "...": "..." },
  "start": 2003,
  "end": 2025,
  "source": "NASA FIRMS, MODIS (Terra + Aqua), confidence >= 30, vegetation fires",
  "series": [
    { "year": 2003, "value": 18469 },
    { "year": 2004, "value": 62053 },
    { "year": 2025, "value": 8720 }
  ],
  "trend": {
    "slope_per_decade": -7746.0,
    "slope_low_per_decade": -19990.0,
    "slope_high_per_decade": 6083.3,
    "total_change": -17041.2,
    "intercept": 32180.6,
    "p_value": 0.213,
    "q_value": null,
    "ols_slope_per_decade": -1962.3,
    "ols_p_value": 0.824,
    "notes": [],
    "n_years": 23,
    "method": "Mann-Kendall (Hamed-Rao) + Sen slope"
  },
  "percent_change": -52.95,
  "verdict": "Not yet certain"
}
```

- `value` es el número de focos del año. Los años sin focos vienen con `0`.
- `percent_change`: cambio en todo el período según la recta de Sen, en %. Puede ser `null`.
- En los focos no hay q-valor (`q_value` es `null`): el veredicto usa el p-valor.

## `GET /api/hotspots/grid?year=2019&region=santa_cruz&season=FIRE`

Densidad por celda de un año, para el mapa. `year` va de 2001 a 2025. Cada celda mide `cell_deg` grados y `lat`/`lon` son su centro. **Respuesta real**, recortada a las 2 celdas con más focos (vienen 185):

```json
{
  "region": { "...": "..." },
  "season": { "...": "..." },
  "year": 2019,
  "cell_deg": 0.5,
  "cells": [
    { "lat": -15.75, "lon": -62.25, "count": 1709 },
    { "lat": -16.75, "lon": -59.25, "count": 1576 }
  ]
}
```

- Para dibujar la celda en Leaflet: rectángulo de `[lat - 0.25, lon - 0.25]` a `[lat + 0.25, lon + 0.25]`.
- Solo vienen las celdas con al menos un foco.
- El CSV de FIRMS se lee una sola vez y queda en memoria. Si se regenera, el backend lo vuelve a leer en la siguiente consulta, sin reiniciar.

## `GET /api/link?region=santa_cruz&season=FIRE&indicator=GWETTOP`

El puente: sequía frente a focos, un punto por año. `indicator` es uno de los 6 `param`. Acepta `start` y `end` como los focos (por defecto 2003–2025). **Respuesta real**, recortada a 2 años:

```json
{
  "region": { "...": "..." },
  "season": { "...": "..." },
  "indicator": "GWETTOP",
  "indicator_label": "Surface soil moisture",
  "indicator_unit": "0-1",
  "points": [
    { "year": 2019, "drought_value": 0.290, "hotspots": 50208 },
    { "year": 2024, "drought_value": 0.285, "hotspots": 125627 }
  ],
  "rho": -0.647,
  "p_value": 0.00084,
  "n_years": 23,
  "method": "Spearman rank correlation",
  "caveat": "Relationship, not proof of cause."
}
```

- `indicator_unit` es la misma unidad que en `/api/regions`, para rotular el eje.
- `rho` y `p_value` vienen en `null` si hay menos de 3 años en común.
