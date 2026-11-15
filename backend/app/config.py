"""Configuración leída desde variables de entorno o desde backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from pydantic import field_validator
from typing import Annotated

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    firms_map_key: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    data_dir: Path = BACKEND_DIR / "data"
    cache_dir: Path = BACKEND_DIR / ".cache"
    # En serverless (Vercel) solo se puede escribir en /tmp: la caché nueva va aquí
    # cuando cache_dir es de solo lectura. La lectura siempre prueba cache_dir primero.
    cache_fallback_dir: Path = Path("/tmp/.cache")
    power_base_url: str = "https://power.larc.nasa.gov/api/temporal/monthly"
    power_timeout_s: float = 60.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    @property
    def firms_csv(self) -> Path:
        return self.data_dir / "firms_monthly_cells.csv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
