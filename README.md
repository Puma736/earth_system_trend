# NASA Space

## Documentación del proyecto

| Archivo | Qué tiene |
|---|---|
| [docs/api.md](docs/api.md) | Contrato de la API (lo que recibe el frontend) |
| [docs/metodos.md](docs/metodos.md) | Métodos estadísticos que usamos y cuáles quedan fuera |
| [docs/fuentes.md](docs/fuentes.md) | Enlaces de FIRMS, POWER y Giovanni |
| [docs/propuesta-condiciones-fuego.md](docs/propuesta-condiciones-fuego.md) | Propuesta (no aprobada): detector de condiciones favorables para incendios |

## Frontend

Requiere Node.js y npm.

```powershell
cd front
npm install
npm run dev
```

Abre <http://localhost:3000>.

## Backend (FastAPI)

Requiere Python 3.10 o superior.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

La API queda disponible en <http://localhost:8000>. La ruta `/health` verifica que esté en funcionamiento y la documentación interactiva está en `/docs`.

Copia `backend/.env.example` como `backend/.env` y completa los valores. El `.env` nunca se sube al repo.

### Endpoints

El formato completo de cada respuesta, con ejemplos, está en [docs/api.md](docs/api.md). Las épocas son `ANN`, `DRY` y `FIRE`.

| Ruta | Qué devuelve | Fuente |
|---|---|---|
| `GET /api/regions` | Regiones (rectángulos) y épocas disponibles | — |
| `GET /api/drought?region=&season=&start=&end=` | Tablero de 6 indicadores con tendencia, q-valor (FDR) y veredicto, más el resumen | MERRA-2 vía POWER |
| `GET /api/hotspots?region=&season=&start=&end=` | Focos por año con tendencia y % de cambio | FIRMS (MODIS) |
| `GET /api/hotspots/grid?year=&region=&season=` | Focos por celda de 0,5° de un año, para el mapa | FIRMS (MODIS) |
| `GET /api/link?region=&season=&indicator=` | Sequía frente a focos por año, con Spearman | POWER + FIRMS |

Las respuestas de POWER se guardan en `backend/.cache/`, así que la primera consulta tarda unos segundos y las siguientes son inmediatas. Antes de una demo o después de desplegar, precarga las 3 regiones:

```powershell
cd backend
python -m scripts.warm_cache
```

### Datos de FIRMS

Los endpoints de focos responden 503 hasta que exista `backend/data/firms_monthly_cells.csv`. Para generarlo, con `FIRMS_MAP_KEY` en el `.env`:

```powershell
cd backend
python -m scripts.download_firms --start 2003-01-01 --end 2025-12-31
```

### Estructura

```
backend/app/
  main.py          app, CORS y manejo de errores
  config.py        variables de entorno
  regions.py       regiones y épocas
  schemas.py       contrato de la API (lo que recibe el frontend)
  services.py      arma las respuestas
  api/             rutas
  data/power.py    MERRA-2 vía POWER, con caché
  data/firms.py    lee el CSV agregado de FIRMS
  stats/trend.py   Hamed-Rao, Sen, FDR y Spearman
backend/scripts/download_firms.py
backend/tests/
```

### Tests

```powershell
cd backend
python -m pytest
```
