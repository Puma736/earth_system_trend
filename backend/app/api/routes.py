from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas, services
from app.api.deps import check_years, get_region, get_season
from app.data.firms import FIRST_COMPARABLE_YEAR
from app.data.power import DROUGHT_INDICATORS
from app.regions import REGIONS, SEASONS, Region, Season

router = APIRouter(prefix="/api")

POWER_FIRST_YEAR = 1981
LAST_YEAR = 2025


@router.get("/regions", response_model=schemas.RegionsResponse)
def list_regions() -> schemas.RegionsResponse:
    return schemas.RegionsResponse(
        regions=[services.region_out(r) for r in REGIONS.values()],
        seasons=[services.season_out(s) for s in SEASONS.values()],
    )


@router.get("/drought", response_model=schemas.DroughtResponse)
def drought(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(POWER_FIRST_YEAR),
    end: int = Query(LAST_YEAR),
) -> schemas.DroughtResponse:
    check_years(start, end, POWER_FIRST_YEAR, LAST_YEAR)
    return services.drought(region, season, start, end)


@router.get("/hotspots", response_model=schemas.HotspotsResponse)
def hotspots(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(FIRST_COMPARABLE_YEAR),
    end: int = Query(LAST_YEAR),
) -> schemas.HotspotsResponse:
    check_years(start, end, 2001, LAST_YEAR)
    return services.hotspots(region, season, start, end)


@router.get("/hotspots/grid", response_model=schemas.HotspotGridResponse)
def hotspot_grid(
    year: int = Query(..., ge=2001, le=LAST_YEAR),
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
) -> schemas.HotspotGridResponse:
    return services.hotspot_grid(region, season, year)


@router.get("/link", response_model=schemas.LinkResponse)
def link(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    indicator: str = Query("GWETTOP", description="One of the drought indicators"),
    start: int = Query(FIRST_COMPARABLE_YEAR),
    end: int = Query(LAST_YEAR),
) -> schemas.LinkResponse:
    if indicator not in DROUGHT_INDICATORS:
        raise HTTPException(404, f"Unknown indicator. Options: {', '.join(DROUGHT_INDICATORS)}")
    check_years(start, end, 2001, LAST_YEAR)
    return services.link(region, season, indicator, start, end)
