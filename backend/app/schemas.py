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


class YearRange(BaseModel):
    start: int
    end: int


class YearsOut(BaseModel):
    drought: YearRange = Field(description="Years accepted by /api/drought (MERRA-2 via NASA POWER)")
    hotspots: YearRange = Field(description="Comparable years for /api/hotspots and /api/link (MODIS Terra + Aqua)")


class IndicatorOut(BaseModel):
    param: str
    label: str
    unit: str
    definition: str


class RegionsResponse(BaseModel):
    regions: list[RegionOut]
    seasons: list[SeasonOut]
    years: YearsOut
    indicators: list[IndicatorOut] = Field(description="The 6 drought indicators, in dashboard order")


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
    change_year: int | None = Field(None, description="First year of a new level (Pettitt test)")
    change_p_value: float | None = Field(None, description="Pettitt p-value; show the change only if < 0.05")
    change_mean_before: float | None = None
    change_mean_after: float | None = None


class BaselineOut(BaseModel):
    start: int
    end: int
    mean: float
    sd: float = Field(description="Sample standard deviation of the baseline years")


class YearAnomaly(BaseModel):
    year: int
    anomaly: float = Field(description="Value minus the baseline mean, in the indicator unit")
    z: float | None = Field(description="Anomaly in baseline standard deviations; null if the baseline is flat")
    percent_of_normal: float | None = Field(description="Value as % of the baseline mean; null if the mean is not positive")
    rank: int = Field(description="1 = most extreme year of the full record (driest, or most hotspots)")


class DroughtIndicatorOut(IndicatorOut):
    series: list[YearValue]
    trend: TrendOut | None
    points_to_drying: bool | None
    verdict: Verdict
    baseline: BaselineOut | None = Field(None, description="Normal period for the anomalies")
    anomalies: list[YearAnomaly] = Field(default_factory=list, description="One per year of the series")
    rank_of: int = Field(0, description="Number of years in the full record used for the rank")
    rank_by: Literal["lowest", "highest"] = Field("lowest", description="Rank 1 is the lowest or the highest value")


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
    baseline: BaselineOut | None = Field(None, description="Comparable record used as normal for the anomalies")
    anomalies: list[YearAnomaly] = Field(default_factory=list, description="One per year of the series")
    rank_of: int = Field(0, description="Number of years in the full record used for the rank")
    rank_by: Literal["lowest", "highest"] = Field("lowest", description="Rank 1 is the lowest or the highest value")


class HotspotCell(BaseModel):
    lat: float = Field(description="Latitude of the cell center")
    lon: float = Field(description="Longitude of the cell center")
    count: int


class HotspotGridResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    year: int
    cell_deg: float
    cells: list[HotspotCell]


class PlaceGridResponse(BaseModel):
    place_id: str
    name: str
    season: SeasonOut
    year: int
    cell_deg: float
    cells: list[HotspotCell]
    note: str


class LinkPoint(BaseModel):
    year: int
    drought_value: float
    hotspots: int


class LinkResponse(BaseModel):
    region: RegionOut
    season: SeasonOut
    indicator: str
    indicator_label: str
    indicator_unit: str
    points: list[LinkPoint]
    rho: float | None
    p_value: float | None
    n_years: int
    method: str = "Spearman rank correlation"
    caveat: str = "Relationship, not proof of cause."


class LeadItem(BaseModel):
    param: str
    label: str
    unit: str
    rho: float | None
    p_value: float | None
    q_value: float | None = Field(None, description="p-value after FDR correction across the 6 indicators")
    n_years: int
    verdict: Verdict


class LeadResponse(BaseModel):
    """¿La época húmeda anterior (oct-mar) anticipa los focos de la época elegida?"""

    region: RegionOut
    season: SeasonOut
    start: int
    end: int
    wet_months: list[int] = Field(description="Months of the previous wet season: Oct-Dec of the year before, Jan-Mar")
    items: list[LeadItem]
    method: str = "Spearman rank correlation, one fixed lag of one season, FDR across indicators"
    caveat: str = "Relationship, not proof of cause."
