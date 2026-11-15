# Fuentes de datos

Enlaces que el equipo usa para cada fuente.

> **La MAP_KEY de FIRMS nunca va en este repo, ni en Trello, ni en un documento compartido por enlace.** Va solo en `backend/.env`, que git ignora. Ver `backend/.env.example`.

## NASA FIRMS (focos de calor, MODIS)

| Qué | Enlace |
|---|---|
| Portada de la API | https://firms.modaps.eosdis.nasa.gov/api/ |
| Pedir la MAP_KEY | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| API por área (la que usa `scripts/download_firms.py`) | https://firms.modaps.eosdis.nasa.gov/api/area/ |
| Hasta qué fecha hay datos de cada sensor | https://firms.modaps.eosdis.nasa.gov/api/data_availability/ |
| Mapa interactivo (para ver 2019 y 2024) | https://firms.modaps.eosdis.nasa.gov/map/ |
| Descarga del archivo histórico | https://firms.modaps.eosdis.nasa.gov/download/ |

- **Formato:** `.../api/area/csv/<MAP_KEY>/MODIS_SP/<oeste,sur,este,norte>/<días 1-5>/<AAAA-MM-DD>`.
- **Límite:** 5.000 consultas cada 10 minutos.
- **Alternativa al script:** pedir el histórico de Bolivia (MODIS, 2003–2025) en la página de descarga. Llega por email. Si llega, ahorra las ~1.700 consultas de F1.

## NASA POWER (MERRA-2, sequía)

Sin cuenta ni clave. La usa `backend/app/data/power.py`.

| Qué | Enlace |
|---|---|
| Documentación | https://power.larc.nasa.gov/docs/ |
| API mensual | https://power.larc.nasa.gov/docs/services/api/temporal/monthly/ |
| API interactiva (Swagger) | https://power.larc.nasa.gov/api/pages/ |
| Visor con mapa | https://power.larc.nasa.gov/data-access-viewer/ |
| Lista de variables mensuales (JSON) | https://power.larc.nasa.gov/api/system/manager/parameters?community=AG&temporal=monthly |

## Giovanni (validación, tarjeta B10)

Hace falta una cuenta gratuita de NASA Earthdata Login (tarjeta 8).

| Qué | Enlace |
|---|---|
| Giovanni | https://giovanni.gsfc.nasa.gov/giovanni/ |
| Crear la cuenta de Earthdata Login | https://urs.earthdata.nasa.gov |
| Manual de uso | https://giovanni.gsfc.nasa.gov/giovanni/doc/UsersManualworkingdocument.docx.html |
| Giovanni en GES DISC | https://disc.gsfc.nasa.gov/information/tools?title=Giovanni |
| MERRA-2 `M2TMNXSLV`: temperatura (`T2M`) | https://disc.gsfc.nasa.gov/datasets/M2TMNXSLV_5.12.4/summary |
| MERRA-2 `M2TMNXFLX`: lluvia (`PRECTOTCORR`) | https://disc.gsfc.nasa.gov/datasets/M2TMNXFLX_5.12.4/summary |
| MERRA-2 `M2TMNXLND`: humedad del suelo (`GWETTOP`, a verificar) | https://disc.gsfc.nasa.gov/datasets/M2TMNXLND_5.12.4/summary |
| Qué es MERRA-2 (GMAO) | https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/ |
| Variables de cada producto MERRA-2 (PDF) | https://gmao.gsfc.nasa.gov/pubs/docs/Bosilovich785.pdf |
