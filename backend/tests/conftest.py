"""Fixtures compartidas. Ningún test llama a la red."""

import csv

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.data import power


def synthetic_monthly(start: int, end: int, base: float, slope_per_year: float) -> power.Monthly:
    return {
        year: {m: base + slope_per_year * (year - start) + 0.01 * m for m in range(1, 13)}
        for year in range(start, end + 1)
    }


@pytest.fixture
def fake_power(monkeypatch):
    """POWER falso: lluvia, suelo y humedad bajan; temperatura sube."""

    trends = {
        "PRECTOTCORR": (3.0, -0.03),
        "GWETTOP": (0.6, -0.002),
        "GWETROOT": (0.6, -0.001),
        "EVPTRNS": (8.0, -0.03),
        "T2M_MAX": (31.0, 0.05),
        "RH2M": (70.0, 0.0),  # plano
    }

    def fetch(param, bbox, start, end, inside=None):
        base, slope = trends[param]
        return synthetic_monthly(start, end, base, slope)

    monkeypatch.setattr(power, "fetch_regional", fetch)
    return fetch


@pytest.fixture
def firms_csv(tmp_path, monkeypatch):
    """CSV de FIRMS falso con focos que crecen cada año, todos dentro de Santa Cruz."""
    path = tmp_path / "firms_monthly_cells.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "month", "lat", "lon", "count"])
        for year in range(2003, 2026):
            for month in (8, 9):
                w.writerow([year, month, -17.75, -61.25, 100 + 20 * (year - 2003)])
            w.writerow([year, 1, -17.75, -61.25, 5])
        # Una celda fuera de Santa Cruz (no debe contarse)
        w.writerow([2010, 8, -10.25, -68.25, 99999])

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)
