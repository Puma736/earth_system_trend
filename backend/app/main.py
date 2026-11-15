from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.data.errors import DataNotAvailable, DataSourceError
from app.investigate import CATALOG, engine_name, run_investigation


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Carga el motor de /investigations al arrancar: con pandas, statsmodels y compañía instalados
    # la importación tarda unos segundos, y así no le toca a la primera consulta de /health.
    engine_name()
    yield


app = FastAPI(
    title="Drought & Hotspots API",
    version="0.3.0",
    description=(
        "Is Santa Cruz drying out? Are there more fire hotspots? NASA POWER (MERRA-2) + FIRMS (MODIS). "
        "/catalog and /investigations serve the /investigation screen, which uses simulated series."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(DataSourceError)
async def _source_error(_: Request, exc: DataSourceError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(DataNotAvailable)
async def _not_available(_: Request, exc: DataNotAvailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "engine": engine_name()}


# Pantalla /investigation (rama velaxd). Las series las genera investigate.py: no son datos de la NASA.
@app.get("/catalog")
def catalog() -> dict[str, Any]:
    return CATALOG


@app.post("/investigations")
def investigations(query: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return run_investigation(query)


app.include_router(router)
