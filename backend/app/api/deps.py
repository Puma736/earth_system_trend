from fastapi import HTTPException, Query

from app.regions import REGIONS, SEASONS, Region, Season


def get_region(region: str = Query("santa-cruz", description="Department id from /api/regions")) -> Region:
    try:
        return REGIONS[region]
    except KeyError:
        raise HTTPException(404, f"Unknown region '{region}'. Options: {', '.join(REGIONS)}")


def get_season(season: str = Query("ANN", description="Season id from /api/regions: ANN, DRY or FIRE")) -> Season:
    try:
        return SEASONS[season.upper()]
    except KeyError:
        raise HTTPException(404, f"Unknown season '{season}'. Options: {', '.join(SEASONS)}")


def check_years(start: int, end: int, min_year: int, max_year: int) -> None:
    if not (min_year <= start < end <= max_year):
        raise HTTPException(422, f"Years must satisfy {min_year} <= start < end <= {max_year}")
