# Despliegue en Vercel

Son **dos proyectos de Vercel** sobre el mismo repositorio (`Puma736/earth_system_trend`):

| Proyecto | Root Directory | Framework | Qué despliega |
|---|---|---|---|
| Backend | *(vacío: raíz del repo)* | Other | FastAPI como función serverless (`api/index.py`) |
| Front | `front` | Next.js | El tablero y `/investigation` |

El backend usa la raíz del repo porque también lee `front/data/bolivia-admin.json`.
`vercel.json`, `.vercelignore` y `api/` de la raíz solo afectan a ese proyecto.

## 1. Backend

1. En Vercel: **Add New → Project →** importar el repo. Dejar **Root Directory** vacío y **Framework Preset** en *Other*.
2. Variables de entorno:

   | Variable | Valor | Obligatoria |
   |---|---|---|
   | `CORS_ORIGINS` | URL del front, por ejemplo `https://<front>.vercel.app` (varias separadas por comas) | Solo si el front usa `NEXT_PUBLIC_API_URL` |
   | `FIRMS_MAP_KEY` | Clave de NASA FIRMS | No. Solo la usa `/api/hotspots/places` |

3. Desplegar y comprobar `https://<backend>.vercel.app/health`.

Cómo funciona:

- `vercel.json` reenvía todas las rutas a `api/index.py`, que importa `backend/app/main.py`.
- `api/requirements.txt` es `backend/requirements.txt` sin las librerías opcionales de `/investigations`
  (pandas, scikit-learn, statsmodels, ruptures, pykrige), para no pasar el límite de tamaño de la función.
  `/investigations` responde con su versión en Python puro y `/health` dice `"engine": "local"`.
- **Caché:** en Vercel solo se puede escribir en `/tmp`. `backend/app/data/power.py` lee primero la caché
  precalentada del repo (`backend/.cache/power/`, las 9 regiones) y, si falta algo, lo descarga de NASA POWER
  y lo guarda en `/tmp/.cache/power/` (`CACHE_FALLBACK_DIR`). Lo de `/tmp` se pierde cuando la función se recicla.
- `backend/data/firms_monthly_cells.csv` va en el repo, así `/api/hotspots` y `/api/hotspots/grid` no dan 503.

Para regenerar la caché después de cambiar regiones o el período:

```bash
cd backend
python -m scripts.warm_cache
git add .cache
```

## 2. Front

1. **Add New → Project →** importar el mismo repo, con **Root Directory** = `front` (Next.js se detecta solo).
2. Variables de entorno:

   | Variable | Valor | Obligatoria |
   |---|---|---|
   | `BACKEND_URL` | `https://<backend>.vercel.app` (sin barra final) | Sí |
   | `NEXT_PUBLIC_API_URL` | La misma URL, si quieres que el navegador llame directo al backend | No |

   `BACKEND_URL` se lee en el build: si cambia, hay que volver a desplegar.
3. Desplegar. El navegador pide `/api/*`, `/health`, `/catalog` y `/investigations` al front y Next.js los reenvía al backend.

## Verificación local

```bash
cd backend && python -m pytest
cd front && npm run build
```

## Video de la demo

`scripts/make_demo_video.py` graba `docs/demo_en_28s.mp4` y `docs/demo_es_28s.mp4` con el backend y el front levantados en local.
