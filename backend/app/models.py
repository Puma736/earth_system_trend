"""Pydantic request schemas for the Trend Detective API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LocationSpec(BaseModel):
    """A location: preset region id, free-text place, or raw coordinates."""

    region_id: str | None = None
    place: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class InvestigateRequest(LocationSpec):
    variable: str = "temperature"
    start_year: int = Field(default=1990, ge=1981)
    end_year: int | None = Field(default=None, ge=1982)
    lang: Literal["es", "en"] = "es"


class CorrelationRequest(LocationSpec):
    var_x: str = "precipitation"
    var_y: str = "soil_moisture"
    start_year: int = Field(default=1990, ge=1981)
    end_year: int | None = Field(default=None, ge=1982)
    max_lag: int = Field(default=6, ge=1, le=24)


class CompareRegionsRequest(BaseModel):
    a: LocationSpec
    b: LocationSpec
    variable: str = "temperature"
    start_year: int = Field(default=1990, ge=1981)
    end_year: int | None = Field(default=None, ge=1982)
    lang: Literal["es", "en"] = "es"
