# NASA Space

## Documentación del proyecto

| Archivo | Qué tiene |
|---|---|
| [docs/api.md](docs/api.md) | Contrato de la API (lo que recibe el frontend) |
| [docs/metodos.md](docs/metodos.md) | Métodos estadísticos que usamos y cuáles quedan fuera |
| [docs/fuentes.md](docs/fuentes.md) | Enlaces de FIRMS, POWER y Giovanni |
| [docs/propuesta-condiciones-fuego.md](docs/propuesta-condiciones-fuego.md) | Propuesta (no aprobada): detector de condiciones favorables para incendios |

## Frontend

Requiere Node.js y npm, y el backend corriendo (ver abajo): todos los datos salen de la API, ya no hay datos simulados.

```powershell
cd front
npm install
Copy-Item .env.example .env.local
npm run dev
```

Abre <http://localhost:3000>.

El navegador no llama al backend directamente: pide `/api/...` al mismo servidor de Next.js (puerto 3000) y este lo reenvía al backend. `front/.env.local` dice dónde está el backend:

```
BACKEND_URL=http://127.0.0.1:8000
```

- Si el backend corre en otro puerto (por ejemplo, porque el 8000 está ocupado), cambia esa línea y reinicia `npm run dev`. En un build, el valor se lee al hacer `npm run build`.
- Como todo pasa por el puerto 3000, no hace falta configurar CORS ni abrir el puerto del backend.
- Opcional: con `NEXT_PUBLIC_API_URL` el navegador llama directo a esa URL (por ejemplo, con el backend desplegado aparte). En ese caso el backend debe aceptar el origen del front en `CORS_ORIGINS`.
- El `.env.local` no se sube al repo.
- Los textos de la interfaz están en inglés, igual que los que devuelve la API.

### Probar desde otra computadora

Las dos computadoras tienen que estar en la misma red.

1. Levanta el backend y el front como arriba. El backend puede seguir en `127.0.0.1`: solo se usa el puerto 3000.
2. Busca la IP de esta computadora: `npm run dev` la muestra al arrancar (`Network: http://<ip>:3000`) y también sale con `ipconfig` (IPv4 del Wi-Fi). Puede cambiar cuando te reconectas.
3. Desde la otra computadora, abre `http://<ip>:3000`.

Si no carga:

- **Firewall de Windows:** tiene que permitir `node.exe` en el tipo de red actual (pública o privada). Windows lo pregunta la primera vez que corres `npm run dev`. Si lo rechazaste, abre PowerShell como administrador y permite solo el puerto 3000, y solo desde tu red local:

  ```powershell
  New-NetFirewallRule -DisplayName "Next dev 3000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000 -RemoteAddress LocalSubnet
  ```

  Para quitarla después: `Remove-NetFirewallRule -DisplayName "Next dev 3000"`.
- **Redes que aíslan equipos:** muchas redes Wi-Fi de universidades, hoteles o invitados no dejan que los dispositivos se vean entre sí. Eso no se arregla desde la computadora: usa el hotspot de un celular u otra red.
- En la terminal de `npm run dev` puede aparecer el aviso "Cross origin request detected" (`allowedDevOrigins`). En Next.js 15 es solo un aviso y no bloquea nada.

### Estructura del front

```
front/
  next.config.ts        reenvía /api/* y /health al backend (BACKEND_URL)
  app/                  página, layout y estilos globales
  components/
    workstation.tsx     filtros y estado compartido (región, época, años, año del mapa)
    drought-board.tsx   tablero de los 6 indicadores (/api/drought)
    hotspots-panel.tsx  focos por año (/api/hotspots)
    map-panel.tsx       mapa de focos por celda (/api/hotspots/grid)
    geo-map.tsx         mapa Leaflet (trend-map.tsx lo carga solo en el navegador)
    bridge-panel.tsx    sequía frente a focos (/api/link)
    methods-panel.tsx   métodos y límites
    chart-kit.tsx       piezas comunes de las gráficas y estados de error
  lib/
    api.ts              cliente de la API, con tiempos de espera y mensajes de error
    types.ts            copia en TypeScript de backend/app/schemas.py
    use-resource.ts     pide un recurso, cancela el anterior y conserva el dato mientras recarga
    format.ts           formato de números, p-valores y unidades
    hotspot-scale.ts    escala de colores del mapa
    bolivia.ts          límites departamentales (GeoBolivia)
```

Un clic en una barra de focos o en un punto del puente cambia el año del mapa.

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

Si el puerto 8000 está ocupado, usa otro y pon ese puerto en `BACKEND_URL`, en `front/.env.local`:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Copia `backend/.env.example` como `backend/.env` y completa los valores. El `.env` nunca se sube al repo.

### Endpoints

El formato completo de cada respuesta, con ejemplos, está en [docs/api.md](docs/api.md). Las épocas son `ANN`, `DRY` y `FIRE`.

| Ruta | Qué devuelve | Fuente |
|---|---|---|
| `GET /api/regions` | Regiones (rectángulos), épocas, años válidos y los 6 indicadores | — |
| `GET /api/drought?region=&season=&start=&end=` | Tablero de 6 indicadores con tendencia, q-valor (FDR) y veredicto, más el resumen | MERRA-2 vía POWER |
| `GET /api/hotspots?region=&season=&start=&end=` | Focos por año con tendencia y % de cambio | FIRMS (MODIS) |
| `GET /api/hotspots/grid?year=&region=&season=` | Focos por celda de 0,5° de un año, para el mapa | FIRMS (MODIS) |
| `GET /api/link?region=&season=&indicator=&start=&end=` | Sequía frente a focos por año, con Spearman | POWER + FIRMS |

Las respuestas de POWER se guardan en `backend/.cache/`. El backend siempre descarga 1981–2025 y recorta los años después, así que cualquier rango sale de la misma caché: la primera consulta de cada región tarda unos segundos y las siguientes son inmediatas, incluso sin internet. Antes de una demo o después de desplegar, precarga las 3 regiones:

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
