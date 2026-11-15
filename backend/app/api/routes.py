from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas, services
from app.api.deps import check_years, get_region, get_season
from app.data import firms, power
from app.data.provinces import covers_department, focus
from app.regions import Region, Season

router = APIRouter(prefix="/api")


def _scope(region: Region, provinces: str) -> tuple[Region, object]:
    try:
        scoped, inside = focus(region, provinces.split(",") if provinces else [])
    except KeyError as exc:
        raise HTTPException(422, f"Unknown province: {exc}") from exc
    if inside is None and region.clip:
        inside = lambda lat, lon: covers_department(region.id, lat, lon)
    return scoped, inside


@router.get("/regions", response_model=schemas.RegionsResponse)
def list_regions() -> schemas.RegionsResponse:
    return services.catalog()


@router.get("/drought", response_model=schemas.DroughtResponse)
def drought(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(power.FIRST_YEAR),
    end: int = Query(power.LAST_YEAR),
    provinces: str = Query("", description="Comma-separated province ids. Empty keeps the region rectangle."),
) -> schemas.DroughtResponse:
    check_years(start, end, power.FIRST_YEAR, power.LAST_YEAR)
    scoped, _inside = _scope(region, provinces)
    return services.drought(scoped, season, start, end)


@router.get("/hotspots", response_model=schemas.HotspotsResponse)
def hotspots(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
    provinces: str = Query("", description="Comma-separated province ids. Empty keeps the region rectangle."),
) -> schemas.HotspotsResponse:
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    scoped, inside = _scope(region, provinces)
    return services.hotspots(scoped, season, start, end, inside)


@router.get("/hotspots/grid", response_model=schemas.HotspotGridResponse)
def hotspot_grid(
    year: int = Query(..., ge=firms.FIRST_YEAR, le=firms.LAST_YEAR),
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    provinces: str = Query("", description="Comma-separated province ids. Empty keeps the region rectangle."),
) -> schemas.HotspotGridResponse:
    scoped, inside = _scope(region, provinces)
    return services.hotspot_grid(scoped, season, year, inside)


@router.get("/hotspots/places", response_model=schemas.PlaceGridResponse)
def hotspot_places(
    year: int = Query(..., ge=firms.FIRST_YEAR, le=firms.LAST_YEAR),
    season: Season = Depends(get_season),
) -> schemas.PlaceGridResponse:
    """Focos de los municipios de Warnes y Montero. La primera consulta de un año descarga FIRMS."""
    return services.place_grid(season, year)


@router.get("/link", response_model=schemas.LinkResponse)
def link(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    indicator: str = Query("GWETTOP", description="One of the drought indicators"),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
    provinces: str = Query("", description="Comma-separated province ids. Empty keeps the region rectangle."),
) -> schemas.LinkResponse:
    if indicator not in power.DROUGHT_INDICATORS:
        raise HTTPException(404, f"Unknown indicator. Options: {', '.join(power.DROUGHT_INDICATORS)}")
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    scoped, inside = _scope(region, provinces)
    return services.link(scoped, season, indicator, start, end, inside)


@router.get("/lead", response_model=schemas.LeadResponse)
def lead(
    region: Region = Depends(get_region),
    season: Season = Depends(get_season),
    start: int = Query(firms.FIRST_COMPARABLE_YEAR),
    end: int = Query(firms.LAST_YEAR),
    provinces: str = Query("", description="Comma-separated province ids. Empty keeps the region rectangle."),
) -> schemas.LeadResponse:
    check_years(start, end, firms.FIRST_YEAR, firms.LAST_YEAR)
    scoped, inside = _scope(region, provinces)
    return services.lead(scoped, season, start, end, inside)
