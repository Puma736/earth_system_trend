"""Contrato de la API: lo que recibe el frontend.

Si cambias algo aquí, avisa al equipo de frontend (tarjeta B1 de Trello).
Todos los textos de cara al usuario van en inglés.
"""

from typing import Literal

from pydantic import BaseModel, Field

# "Real change": p < 0,05 (en la sequía se usa el q-valor, ya corregido por FDR).
# "Not yet certain": no alcanza. "Not enough data": menos de 10 años.
Verdict = Literal["Real change", "Not yet certain", "Not enough data"]


class BBoxOut(BaseModel):
    west: float
    south: float
    east: float
    north: float


class RegionOut(BaseModel):
    id: str
    name: str
    bbox: BBoxOut
    note: str


class SeasonOut(BaseModel):
    id: str
    name: str
    months: list[int]


class RegionsResponse(BaseModel):
    regions: list[RegionOut]
    seasons: list[SeasonOut]


class YearValue(BaseModel):
    year: int
    value: float


class TrendOut(BaseModel):
    slope_per_decade: float
    intercept: float = Field(description="Value of the Sen line in the first year, for drawing it")
    p_value: float
    q_value: float | None = Field(None, description="p-value after FDR correction across indicators")
    n_years: int
    method: str
    slope_low_per_decade: float = Field(description="Lower end of the 95% range of the Sen slope")
    slope_high_per_decade: float = Field(description="Upper end of the 95% range of the Sen slope")
    total_change: float = Field(description="Change over the whole period along the Sen line, in the indicator unit")
    ols_slope_per_decade: float = Field(description="Control: linear regression slope")
    ols_p_value: float = Field(description="Control: linear regression t-test p-value")
    notes: list[str] = Field(default_factory=list, description="Warnings when the methods disagree")


class DroughtIndicatorOut(BaseModel):
    param: str
    label: str
    unit: str
    definition: str
    series: list[YearValue]
    trend: TrendOut | None
    points_to_drying: bool | None
    verdict: Verdict


class DroughtSummary(BaseModel):
    pointing_to_drying: int
    real_changes: int
    total: int
    text: str


class DroughtResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    start: int
    end: int
    source: str = "MERRA-2 via NASA POWER"
    summary: DroughtSummary
    indicators: list[DroughtIndicatorOut]


class HotspotsResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    start: int
    end: int
    source: str = "NASA FIRMS, MODIS (Terra + Aqua), confidence >= 30, vegetation fires"
    series: list[YearValue]
    trend: TrendOut | None
    percent_change: float | None = Field(None, description="Change over the period along the Sen line, in %")
    verdict: Verdict


class HotspotGridResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    year: int
    cell_deg: float
    cells: list[dict]


class LinkPoint(BaseModel):
    year: int
    drought_value: float
    hotspots: int


class LinkResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    indicator: str
    indicator_label: str
    points: list[LinkPoint]
    rho: float | None
    p_value: float | None
    n_years: int
    method: str = "Spearman rank correlation"
    caveat: str = "Relationship, not proof of cause."
