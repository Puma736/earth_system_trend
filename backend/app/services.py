"""Lógica que arma las respuestas a partir de los datos y la estadística.

Los routers solo validan parámetros y llaman a estas funciones, así se pueden
probar sin levantar el servidor.
"""

from __future__ import annotations

from app import schemas
from app.data import firms, power
from app.regions import REGIONS, SEASONS, Region, Season
from app.stats.trend import ALPHA, MIN_YEARS, TrendResult, fdr, spearman, trend


def region_out(r: Region) -> schemas.RegionOut:
    b = r.bbox
    return schemas.RegionOut(
        id=r.id,
        name=r.name,
        note=r.note,
        bbox=schemas.BBoxOut(west=b.west, south=b.south, east=b.east, north=b.north),
    )


def season_out(s: Season) -> schemas.SeasonOut:
    return schemas.SeasonOut(id=s.id, name=s.name, months=list(s.months))


def indicator_out(i: power.Indicator) -> schemas.IndicatorOut:
    return schemas.IndicatorOut(param=i.param, label=i.label, unit=i.unit, definition=i.definition)


def catalog() -> schemas.RegionsResponse:
    """Todo lo que el frontend necesita para armar los selectores."""
    return schemas.RegionsResponse(
        regions=[region_out(r) for r in REGIONS.values()],
        seasons=[season_out(s) for s in SEASONS.values()],
        years=schemas.YearsOut(
            drought=schemas.YearRange(start=power.FIRST_YEAR, end=power.LAST_YEAR),
            hotspots=schemas.YearRange(start=firms.FIRST_COMPARABLE_YEAR, end=firms.LAST_YEAR),
        ),
        indicators=[indicator_out(i) for i in power.DROUGHT_INDICATORS.values()],
    )


def _verdict(p_or_q: float | None) -> schemas.Verdict:
    if p_or_q is None:
        return "Not enough data"
    return "Real change" if p_or_q < ALPHA else "Not yet certain"


def _trend_out(t: TrendResult, q: float | None = None) -> schemas.TrendOut:
    return schemas.TrendOut(
        slope_per_decade=t.slope_per_decade,
        intercept=t.intercept,
        p_value=t.p_value,
        q_value=q,
        n_years=t.n_years,
        method=t.method,
        slope_low_per_decade=t.slope_low_per_decade,
        slope_high_per_decade=t.slope_high_per_decade,
        total_change=t.total_change,
        ols_slope_per_decade=t.ols_slope_per_decade,
        ols_p_value=t.ols_p_value,
        notes=list(t.notes),
    )


def _try_trend(series: dict[int, float]) -> TrendResult | None:
    if len(series) < MIN_YEARS:
        return None
    years = sorted(series)
    return trend(years, [series[y] for y in years])


# ---------------------------------------------------------------------------
# Sequía
# ---------------------------------------------------------------------------

def drought_series(param: str, region: Region, season: Season, start: int, end: int) -> dict[int, float]:
    """Promedio de la época por año, de start a end.

    Siempre se pide a POWER el período completo y los años se recortan aquí. Así
    cualquier rango de años, y también /api/link, reusa la caché que deja warm_cache.
    """
    monthly = power.fetch_regional(param, region.bbox, power.FIRST_YEAR, power.LAST_YEAR)
    seasonal = power.seasonal_series(monthly, season.months)
    return {year: value for year, value in seasonal.items() if start <= year <= end}


def drought(region: Region, season: Season, start: int, end: int) -> schemas.DroughtResponse:
    indicators = list(power.DROUGHT_INDICATORS.values())
    series = {i.param: drought_series(i.param, region, season, start, end) for i in indicators}
    trends = {p: _try_trend(s) for p, s in series.items()}

    with_trend = [p for p, t in trends.items() if t is not None]
    q_values = dict(zip(with_trend, fdr([trends[p].p_value for p in with_trend])))

    out: list[schemas.DroughtIndicatorOut] = []
    for ind in indicators:
        t = trends[ind.param]
        q = q_values.get(ind.param)
        drying = None if t is None else (t.direction == ind.drying_sign)
        out.append(
            schemas.DroughtIndicatorOut(
                param=ind.param,
                label=ind.label,
                unit=ind.unit,
                definition=ind.definition,
                series=[schemas.YearValue(year=y, value=v) for y, v in sorted(series[ind.param].items())],
                trend=None if t is None else _trend_out(t, q),
                points_to_drying=drying,
                verdict=_verdict(q),
            )
        )

    pointing = sum(1 for i in out if i.points_to_drying)
    real = sum(1 for i in out if i.points_to_drying and i.verdict == "Real change")
    summary = schemas.DroughtSummary(
        pointing_to_drying=pointing,
        real_changes=real,
        total=len(out),
        text=f"{pointing} of {len(out)} indicators point to drying ({real} are real changes)",
    )
    return schemas.DroughtResponse(
        region=region_out(region),
        season=season_out(season),
        start=start,
        end=end,
        summary=summary,
        indicators=out,
    )


# ---------------------------------------------------------------------------
# Focos de calor
# ---------------------------------------------------------------------------

def hotspots(region: Region, season: Season, start: int, end: int) -> schemas.HotspotsResponse:
    counts = firms.yearly_counts(region.bbox, season.months, start, end)
    t = _try_trend({y: float(c) for y, c in counts.items()})

    percent = None
    if t is not None and t.intercept > 0:
        span_decades = (end - start) / 10
        percent = 100 * t.slope_per_decade * span_decades / t.intercept

    return schemas.HotspotsResponse(
        region=region_out(region),
        season=season_out(season),
        start=start,
        end=end,
        series=[schemas.YearValue(year=y, value=c) for y, c in sorted(counts.items())],
        trend=None if t is None else _trend_out(t),
        percent_change=percent,
        verdict=_verdict(None if t is None else t.p_value),
    )


def hotspot_grid(region: Region, season: Season, year: int) -> schemas.HotspotGridResponse:
    return schemas.HotspotGridResponse(
        region=region_out(region),
        season=season_out(season),
        year=year,
        cell_deg=firms.CELL_DEG,
        cells=firms.grid_for_year(region.bbox, season.months, year),
    )


# ---------------------------------------------------------------------------
# El puente
# ---------------------------------------------------------------------------

def link(region: Region, season: Season, param: str, start: int, end: int) -> schemas.LinkResponse:
    dry = drought_series(param, region, season, start, end)
    fires = firms.yearly_counts(region.bbox, season.months, start, end)
    years = sorted(set(dry) & set(fires))
    points = [schemas.LinkPoint(year=y, drought_value=dry[y], hotspots=fires[y]) for y in years]

    rho = p = None
    if len(points) >= 3:
        res = spearman([pt.drought_value for pt in points], [pt.hotspots for pt in points])
        rho, p = res.rho, res.p_value

    indicator = power.DROUGHT_INDICATORS[param]
    return schemas.LinkResponse(
        region=region_out(region),
        season=season_out(season),
        indicator=param,
        indicator_label=indicator.label,
        indicator_unit=indicator.unit,
        points=points,
        rho=rho,
        p_value=p,
        n_years=len(points),
    )
