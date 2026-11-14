from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.data.errors import DataNotAvailable, DataSourceError

app = FastAPI(
    title="Drought & Hotspots API",
    version="0.2.0",
    description="Is Santa Cruz drying out? Are there more fire hotspots? NASA POWER (MERRA-2) + FIRMS (MODIS).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET"],
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
    return {"status": "ok"}


app.include_router(router)
