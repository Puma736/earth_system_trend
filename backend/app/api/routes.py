from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas, services
from app.api.deps import check_years, get_region, get_season
from app.data import firms, power
from app.regions import Region, Season

router = APIRouter(prefix="/api")


@router.get("/regions", response_model=schemas.RegionsResponse)
def list_regions() -> schemas.RegionsResponse:
    return services.catalog()


@router.get("/drought", response_model=schemas.DroughtResponse)
def drought(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(power.FIRST_YEAR),
    end: int = Query(power.LAST_YEAR),
) -> schemas.DroughtResponse:
    check_years(start, end, power.FIRST_YEAR, power.LAST_YEAR)
    return services.drought(region, season, start, end)


@router.get("/hotspots", response_model=schemas.HotspotsResponse)
def hotspots(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
) -> schemas.HotspotsResponse:
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    return services.hotspots(region, season, start, end)


@router.get("/hotspots/grid", response_model=schemas.HotspotGridResponse)
def hotspot_grid(
    year: int = Query(..., ge=firms.FIRST_YEAR, le=firms.LAST_YEAR),
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
) -> schemas.HotspotGridResponse:
    return services.hotspot_grid(region, season, year)


@router.get("/link", response_model=schemas.LinkResponse)
def link(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    indicator: str = Query("GWETTOP", description="One of the drought indicators"),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
) -> schemas.LinkResponse:
    if indicator not in power.DROUGHT_INDICATORS:
        raise HTTPException(404, f"Unknown indicator. Options: {', '.join(power.DROUGHT_INDICATORS)}")
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    return services.link(region, season, indicator, start, end)


@router.get("/lead", response_model=schemas.LeadResponse)
def lead(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
) -> schemas.LeadResponse:
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    return services.lead(region, season, start, end)
