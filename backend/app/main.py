from typing import Any

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.investigate import CATALOG, engine_name, run_investigation

app = FastAPI(title="NASA Space API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "engine": engine_name()}


@app.get("/catalog")
def catalog() -> dict[str, Any]:
    return CATALOG


@app.post("/investigations")
def investigations(query: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return run_investigation(query)
