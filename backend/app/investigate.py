"""Investigación climática con sci_lab_math, o con las mismas pruebas en Python puro."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAB_SRC = ROOT / "ALGORITMOS" / "src"
ADMIN_PATH = ROOT / "front" / "data" / "bolivia-admin.json"

CAVEAT = (
    "El Z-score usa la media y la desviación de toda la serie; |Z| > 2 cuenta como anomalía. "
    "Mann-Kendall y la pendiente de Sen describen la serie con su estacionalidad. "
    "Un desfase o una correlación no demuestran causalidad."
)

LAB_KEY = {
    "precipitation": "precipitacion",
    "temperature": "temperatura",
    "soil_moisture": "humedad_suelo",
    "ndvi": "ndvi",
    "lst": "temperatura_superficial",
}
NAMES = {
    "precipitation": "Precipitación",
    "temperature": "Temperatura",
    "soil_moisture": "Humedad del suelo",
    "ndvi": "NDVI",
    "lst": "Temperatura superficial",
}
UNITS = {
    "precipitation": "mm/mes",
    "temperature": "°C",
    "soil_moisture": "%",
    "ndvi": "índice",
    "lst": "K",
}
WATER = ("precipitation", "soil_moisture")
HEAT = ("temperature", "lst")
REGIONS = {
    "bolivia": ("Bolivia", -16.5, -64.5, 1.0),
    "la_paz": ("La Paz", -16.5, -68.15, 0.55),
    "cochabamba": ("Cochabamba", -17.39, -66.16, 0.7),
    "santa_cruz": ("Santa Cruz", -17.78, -63.18, 1.15),
    "beni": ("Beni", -14.83, -64.9, 0.9),
    "chaco": ("Chaco", -20.04, -63.52, 1.3),
}
PLACES = [
    ("la_paz", "La Paz", -16.5, -68.15, 0.55),
    ("cochabamba", "Cochabamba", -17.39, -66.16, 0.7),
    ("santa_cruz", "Santa Cruz", -17.78, -63.18, 1.15),
    ("beni", "Beni", -14.83, -64.9, 0.9),
    ("chaco", "Chaco", -20.04, -63.52, 1.3),
    ("pando", "Pando", -11.03, -68.77, 0.4),
]

CATALOG: dict[str, Any] = {
    "regions": [
        {"id": key, "name": value[0], "lat": value[1], "lon": value[2]} for key, value in REGIONS.items()
    ],
    "variables": [
        {
            "id": "precipitation",
            "code": "PRECIP",
            "name": "Precipitación",
            "unit": "mm/mes",
            "definition": "Agua del mes. El perfil clima marca sequía si la tendencia decreciente es significativa.",
            "source": "Laboratorio sci_lab_math",
        },
        {
            "id": "temperature",
            "code": "TEMP",
            "name": "Temperatura",
            "unit": "°C",
            "definition": "Temperatura del aire. El perfil clima marca calentamiento si la tendencia creciente es significativa.",
            "source": "Laboratorio sci_lab_math",
        },
        {
            "id": "soil_moisture",
            "code": "HSUELO",
            "name": "Humedad del suelo",
            "unit": "%",
            "definition": "Agua en el suelo, en porcentaje. Entra en la alerta de sequía junto con la precipitación.",
            "source": "Laboratorio sci_lab_math",
        },
        {
            "id": "ndvi",
            "code": "NDVI",
            "name": "NDVI",
            "unit": "índice",
            "definition": "Verdor de la vegetación, como en el ejemplo NASA del laboratorio.",
            "source": "Laboratorio sci_lab_math",
        },
        {
            "id": "lst",
            "code": "LST",
            "name": "Temperatura superficial",
            "unit": "K",
            "definition": "Temperatura de la superficie en kelvin, ejemplo NASA del laboratorio.",
            "source": "Laboratorio sci_lab_math",
        },
    ],
    "cases": [
        {
            "id": "drought",
            "label": "Sequía",
            "variables": ["precipitation", "soil_moisture", "ndvi", "temperature"],
            "questions": [
                {"id": "trend", "text": "Tendencia del agua disponible"},
                {"id": "anomaly", "text": "Anomalías extremas (|Z| > 2)"},
                {"id": "change", "text": "Punto de cambio de la media"},
                {"id": "lag", "text": "Qué variable precede a otra"},
            ],
        },
        {
            "id": "heat",
            "label": "Calor",
            "variables": ["temperature", "lst", "ndvi", "precipitation"],
            "questions": [
                {"id": "trend", "text": "Tendencia de la temperatura"},
                {"id": "anomaly", "text": "Anomalías extremas (|Z| > 2)"},
                {"id": "forecast", "text": "Media proyectada con la pendiente de Sen"},
                {"id": "lag", "text": "Qué variable precede a otra"},
            ],
        },
        {
            "id": "signal",
            "label": "Completo",
            "variables": ["precipitation", "temperature", "soil_moisture", "ndvi", "lst"],
            "questions": [
                {"id": "trend", "text": "Tendencia monotónica (Mann-Kendall y Sen)"},
                {"id": "anomaly", "text": "Anomalías |Z| > 2"},
                {"id": "change", "text": "Punto de cambio (CUSUM)"},
                {"id": "lag", "text": "Correlación y desfase temporal"},
                {"id": "forecast", "text": "Media proyectada con la pendiente de Sen"},
                {"id": "pattern", "text": "Componente principal y ciclo dominante"},
            ],
        },
    ],
}


_LAB_MODULES: dict[str, Any] | None = None
_LAB_CHECKED = False


def engine_name() -> str:
    return "sci_lab_math" if _modules() is not None else "local"


def _modules() -> dict[str, Any] | None:
    global _LAB_MODULES, _LAB_CHECKED
    if _LAB_CHECKED:
        return _LAB_MODULES
    _LAB_CHECKED = True
    if str(LAB_SRC) not in sys.path:
        sys.path.insert(0, str(LAB_SRC))
    try:
        from sci_lab_math import anomalies, changepoints, extensions, forecasting, patterns, relations, trends

        _LAB_MODULES = {
            "anomalies": anomalies,
            "changepoints": changepoints,
            "extensions": extensions,
            "forecasting": forecasting,
            "patterns": patterns,
            "relations": relations,
            "trends": trends,
        }
    except Exception:
        _LAB_MODULES = None
    return _LAB_MODULES


def run_investigation(query: dict[str, Any]) -> dict[str, Any]:
    variables = [item for item in query.get("variables") or [] if item in LAB_KEY]
    if not variables:
        variables = ["precipitation", "temperature"]
    aggregation = query.get("aggregation") or "monthly"
    question = query.get("question_id") or "trend"
    anchors = _anchors(query)
    study = _study_anchor(query, anchors)
    series = [_build_series(query, study, variable, aggregation) for variable in variables]
    lab = _try_lab(series, _scope_subject(query), question == "forecast")
    statistics = [_describe(item, aggregation, lab) for item in series]
    relations = _relations(series, aggregation, lab)
    pattern = _pattern(series, _focus(query, relations, variables), aggregation, lab)
    if question == "forecast":
        series = [_with_forecast(item, aggregation, lab) for item in series]
    cells = _map_cells(query, _focus(query, relations, variables), anchors, aggregation)
    event = _event(query, statistics, series, cells)
    result_query = {
        "region_id": query.get("region_id") or "bolivia",
        "case_id": query.get("case_id") or "drought",
        "question_id": question,
        "variables": variables,
        "start": query.get("start") or "2001-01",
        "end": query.get("end") or "2024-12",
        "aggregation": aggregation,
        "department_id": query.get("department_id"),
        "province_id": query.get("province_id"),
        "place": query.get("place"),
    }
    wrapped = {**query, "question_id": question, "variables": variables, "aggregation": aggregation}
    return {
        "query": result_query,
        "series": series,
        "map_cells": cells,
        "map_variable": _focus(wrapped, relations, variables),
        "map_caption": _caption(wrapped, _focus(wrapped, relations, variables)),
        "statistics": statistics,
        "relations": relations,
        "sequence_label": _sequence(wrapped, statistics, relations, pattern),
        "event": event,
        "hotspots": [],
        "pattern": pattern,
        "conclusion": _conclusion(wrapped, statistics, relations, pattern, event, _forecast_from_lab(lab)),
        "caveat": CAVEAT,
        "source": "api",
    }


def _forecast_from_lab(lab: dict[str, Any] | None) -> bool:
    if not lab:
        return False
    for value in (lab.get("forecast") or {}).values():
        if isinstance(value, dict) and value.get("forecast") and "error" not in value:
            return True
    return False


def _try_lab(series: list[dict[str, Any]], entity: str, forecast: bool = False) -> dict[str, Any] | None:
    modules = _modules()
    if modules is None or not series or not series[0]["points"]:
        return None
    built: dict[str, Any] = {
        "entity_name": entity,
        "trends": {},
        "anomalies": {},
        "changepoints": {},
        "relations": {},
        "patterns": {},
        "forecast": {},
        "periods": {},
    }
    try:
        for item in series:
            key = LAB_KEY[item["variable"]]
            values = [point["value"] for point in item["points"]]
            built["trends"][key] = {
                "mann_kendall": modules["trends"].mann_kendall(values),
                "linear_regression": modules["trends"].linear_regression(values),
            }
            scores = _finite(modules["anomalies"].z_score(values))
            built["anomalies"][key] = {
                "n_anomalies_z2": int(sum(abs(score) > 2 for score in scores)),
                "last_z_score": scores[-1] if scores else 0.0,
                "mean": _mean(values),
            }
            built["changepoints"][key] = {"cusum": modules["changepoints"].cusum(values)}
            spectrum = modules["extensions"].fft_frequencies(values, sampling_rate=1.0)
            built["periods"][item["variable"]] = _period_from_fft(spectrum)
            if forecast:
                steps = 3 if len(item["points"][0]["date"]) == 4 else 12
                seasonal = 12 if steps == 12 and len(values) >= 24 else 0
                built["forecast"][key] = modules["forecasting"].sarima_forecast(
                    values,
                    order=(1, 1, 1),
                    steps=steps,
                    s=seasonal,
                    non_negative=True,
                )
        if len(series) >= 2:
            frame = {LAB_KEY[item["variable"]]: [point["value"] for point in item["points"]] for item in series}
            pca = modules["patterns"].pca_analysis(frame, n_components=min(len(series), 5))
            built["patterns"]["pca"] = {"explained_variance_ratio": pca.get("explained_variance_ratio") or []}
        max_lag = min(12, len(series[0]["points"]) // 4)
        if max_lag >= 1:
            for index, left in enumerate(series):
                for right in series[index + 1 :]:
                    left_values = [point["value"] for point in left["points"]]
                    right_values = [point["value"] for point in right["points"]]
                    pair = modules["relations"].best_lag(left_values, right_values, max_lag=max_lag)
                    lag = pair.get("lag")
                    correlation = pair.get("correlation")
                    built["relations"][f"{LAB_KEY[left['variable']]}__vs__{LAB_KEY[right['variable']]}"] = {
                        "best_lag": {
                            "lag": None if lag is None else int(lag),
                            "correlation": None if correlation is None else float(correlation),
                            "p_value": None if pair.get("p_value") is None else float(pair["p_value"]),
                            "n": len(left_values) - (0 if lag is None else abs(int(lag))),
                        }
                    }
    except Exception:
        return None
    return built


def _finite(series: Any) -> list[float]:
    values = series.tolist() if hasattr(series, "tolist") else list(series)
    numbers: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if math.isnan(number) or math.isinf(number):
            number = 0.0
        numbers.append(number)
    return numbers


def _period_from_fft(spectrum: Any) -> float | None:
    if not isinstance(spectrum, dict) or spectrum.get("error"):
        return None
    top = spectrum.get("top_frequencies") or []
    if not top:
        return None
    freq = float(top[0][0])
    if freq <= 0:
        return None
    return 1.0 / freq


def _fit(values: list[float]) -> tuple[float, float, float, str]:
    modules = _modules()
    if modules is not None and len(values) >= 4:
        try:
            fitted = modules["trends"].mann_kendall(values)
            if isinstance(fitted, dict) and "error" not in fitted and "sens_slope" in fitted:
                return (
                    float(fitted["sens_slope"]),
                    float(fitted["intercept"]),
                    float(fitted["p_value"]),
                    str(fitted.get("trend") or ""),
                )
        except Exception:
            pass
    slope, p_value, _ = _mann_kendall(values)
    return slope, _sen_intercept(values, slope), p_value, ""


def _describe(series: dict[str, Any], aggregation: str, lab: dict[str, Any] | None) -> dict[str, Any]:
    values = [point["value"] for point in series["points"]]
    slope, p_value, n = _mann_kendall(values)
    scores = _zscores(values)
    change = _cusum(values)
    steps = 3 if aggregation == "annual" else 12
    historical = _mean(values)
    projected = _sen_mean(values, steps, series["variable"])
    significant = n >= 4 and p_value < 0.05 and slope != 0
    direction = "flat" if not significant else "up" if slope > 0 else "down"
    variable = series["variable"]
    r_squared = _r2(values)
    if lab is not None:
        key = LAB_KEY[variable]
        mk = lab.get("trends", {}).get(key, {}).get("mann_kendall", {})
        if isinstance(mk, dict) and "p_value" in mk:
            p_value = float(mk["p_value"])
            if mk.get("sens_slope") is not None:
                slope = float(mk["sens_slope"])
            trend = mk.get("trend")
            significant = trend in ("increasing", "decreasing") and p_value < 0.05
            direction = "up" if trend == "increasing" else "down" if trend == "decreasing" else "flat"
            if mk.get("intercept") is not None and mk.get("sens_slope") is not None:
                projected = _project(values, steps, variable, float(mk["sens_slope"]), float(mk["intercept"]))
        fitted = lab.get("trends", {}).get(key, {}).get("linear_regression", {})
        if isinstance(fitted, dict) and fitted.get("r_squared") is not None and "error" not in fitted:
            r_squared = float(fitted["r_squared"])
        anomaly = lab.get("anomalies", {}).get(key, {})
        if isinstance(anomaly, dict) and "n_anomalies_z2" in anomaly:
            n_anomalies = int(anomaly["n_anomalies_z2"])
            last_z = float(anomaly.get("last_z_score") or 0)
            historical = float(anomaly.get("mean") or historical)
        else:
            n_anomalies = sum(abs(score) > 2 for score in scores)
            last_z = scores[-1] if scores else 0
        cusum = lab.get("changepoints", {}).get(key, {}).get("cusum", {})
        if isinstance(cusum, dict) and cusum.get("change_index") is not None:
            index = int(cusum["change_index"])
            change_date = series["points"][index]["date"] if 0 <= index < len(series["points"]) else None
        else:
            change_date = series["points"][change]["date"] if change is not None else None
        forecast = lab.get("forecast", {}).get(key, {})
        if isinstance(forecast, dict) and forecast.get("forecast") and "error" not in forecast:
            projected = _mean([float(item) for item in forecast["forecast"]])
    else:
        n_anomalies = sum(abs(score) > 2 for score in scores)
        last_z = scores[-1] if scores else 0
        change_date = series["points"][change]["date"] if change is not None else None
    per_decade = slope * (10 if aggregation == "annual" else 120)
    pct = 0 if historical == 0 else (projected - historical) / abs(historical) * 100
    return {
        "variable": variable,
        "test": "mann_kendall",
        "slope_per_decade": per_decade,
        "slope_per_step": slope,
        "p_value": p_value,
        "significant": significant,
        "n": n,
        "direction": direction,
        "r_squared": r_squared,
        "n_anomalies": n_anomalies,
        "last_z": last_z,
        "change_date": change_date,
        "mean": historical,
        "projected_mean": projected,
        "projected_pct": pct,
    }


def _with_forecast(series: dict[str, Any], aggregation: str, lab: dict[str, Any] | None) -> dict[str, Any]:
    values = [point["value"] for point in series["points"]]
    center = _mean(values)
    sd = _sd(values)
    last = series["points"][-1]["date"]
    key = LAB_KEY[series["variable"]]
    raw = None
    if lab is not None:
        forecast = lab.get("forecast", {}).get(key, {})
        if isinstance(forecast, dict) and forecast.get("forecast") and "error" not in forecast:
            raw = [float(item) for item in forecast["forecast"]]
    if raw is None:
        slope, intercept, _, _ = _fit(values)
        raw = [intercept + slope * (len(values) + step) for step in range(3 if aggregation == "annual" else 12)]
    points = []
    for step, value in enumerate(raw, start=1):
        clipped = _clip(value, series["variable"])
        points.append(
            {
                "date": _future(last, step, aggregation),
                "value": round(_clip(clipped, series["variable"]), 3 if series["variable"] == "ndvi" else 2),
                "anomaly": round(clipped - center, 3 if series["variable"] == "ndvi" else 2),
                "z": 0 if sd == 0 else (clipped - center) / sd,
            }
        )
    return {**series, "forecast": points}


def _relations(series: list[dict[str, Any]], aggregation: str, lab: dict[str, Any] | None) -> list[dict[str, Any]]:
    if lab is not None:
        found = []
        for key, value in lab.get("relations", {}).items():
            left, _, right = key.partition("__vs__")
            pair = value.get("best_lag") or {}
            if pair.get("correlation") is None or abs(float(pair["correlation"])) < 0.4:
                continue
            lag = int(pair.get("lag") or 0)
            driver = _from_lab(left if lag >= 0 else right)
            response = _from_lab(right if lag >= 0 else left)
            if driver is None or response is None:
                continue
            r = float(pair["correlation"])
            p_value = float(pair.get("p_value") or 1)
            n = int(pair.get("n") or len(series[0]["points"]))
            found.append(_relation(driver, response, abs(lag), aggregation, r, p_value, n))
        return sorted(found, key=lambda item: abs(item["r"]), reverse=True)[:4]
    found = []
    max_lag = min(12, len(series[0]["points"]) // 4) if series else 0
    if max_lag < 1:
        return []
    for i, left in enumerate(series):
        for right in series[i + 1 :]:
            pair = _cross_best(
                [point["value"] for point in left["points"]],
                [point["value"] for point in right["points"]],
                max_lag,
            )
            if pair is None or abs(pair["r"]) < 0.4:
                continue
            lag = pair["lag"]
            driver = right["variable"] if lag < 0 else left["variable"]
            response = left["variable"] if lag < 0 else right["variable"]
            found.append(_relation(driver, response, abs(lag), aggregation, pair["r"], pair["p"], pair["n"]))
    return sorted(found, key=lambda item: abs(item["r"]), reverse=True)[:4]


def _relation(driver: str, response: str, lag: int, aggregation: str, r: float, p_value: float, n: int) -> dict[str, Any]:
    unit = "años" if aggregation == "annual" and lag != 1 else "año" if aggregation == "annual" else "mes" if lag == 1 else "meses"
    sense = "en el mismo sentido" if r >= 0 else "en sentido opuesto"
    same = "en el mismo año" if aggregation == "annual" else "en el mismo mes"
    when = f"Ocurre {same}" if lag == 0 else f"{NAMES[driver]} va {lag} {unit} antes que {NAMES[response]}"
    season = " Con un ciclo anual, un desfase así puede ser la estación." if aggregation == "monthly" and lag >= 6 else ""
    p_text = "p < 0.001" if p_value < 0.001 else f"p = {p_value:.3f}"
    return {
        "driver": driver,
        "response": response,
        "lag": lag,
        "lag_unit": "years" if aggregation == "annual" else "months",
        "r": r,
        "p_value": p_value,
        "n": n,
        "sentence": (
            f"{NAMES[driver]} y {NAMES[response]} se mueven {sense}. {when} "
            f"(r = {r:.2f}, {p_text}, n = {n}).{season}"
        ),
    }


def _pattern(series: list[dict[str, Any]], variable: str, aggregation: str, lab: dict[str, Any] | None) -> dict[str, Any]:
    share = None
    period = None
    if lab is not None:
        ratio = lab.get("patterns", {}).get("pca", {}).get("explained_variance_ratio") or []
        if ratio:
            share = float(ratio[0])
        if (lab.get("periods") or {}).get(variable) is not None:
            period = float(lab["periods"][variable])
    if share is None:
        share = _pc1([[point["value"] for point in item["points"]] for item in series])
    focus = next((item for item in series if item["variable"] == variable), series[0] if series else None)
    if period is None and focus:
        period = _period([point["value"] for point in focus["points"]])
    return {
        "pc1_share": share,
        "period_steps": None if period is None else round(period),
        "period_unit": "years" if aggregation == "annual" else "months",
        "variable": focus["variable"] if focus else variable,
    }


def _event(query: dict[str, Any], statistics: list[dict[str, Any]], series: list[dict[str, Any]], cells: list[dict[str, Any]]) -> dict[str, Any] | None:
    case_id = query.get("case_id")
    if case_id == "drought":
        lead = next((item for item in statistics if item["variable"] in WATER and item["significant"] and item["direction"] == "down"), None)
        kind = "drought"
        stressed = lambda value: value < 0
    elif case_id == "heat":
        lead = next((item for item in statistics if item["variable"] in HEAT and item["significant"] and item["direction"] == "up"), None)
        kind = "thermal_stress"
        stressed = lambda value: value > 0
    else:
        return None
    if lead is None:
        return None
    points = next(item["points"] for item in series if item["variable"] == lead["variable"])
    start = lead["change_date"] or points[0]["date"]
    end = points[-1]["date"]
    inside = [point for point in points if start <= point["date"] <= end]
    return {
        "kind": kind,
        "start": start,
        "end": end,
        "duration": max(1, len(inside)),
        "duration_unit": "years" if len(points[0]["date"]) == 4 else "months",
        "intensity": lead["slope_per_step"],
        "intensity_unit": f"{UNITS[lead['variable']]} por periodo",
        "extent_count": sum(1 for cell in cells if stressed(cell["value"])),
        "extent_total": len(cells),
        "recovery_note": None,
    }


def _map_cells(query: dict[str, Any], variable: str, anchors: list[dict[str, Any]], aggregation: str) -> list[dict[str, Any]]:
    province = query.get("province_id")
    place = query.get("place")
    cells = []
    for anchor in anchors:
        series = _build_series(query, anchor, variable, aggregation)
        values = [point["value"] for point in series["points"]]
        scores = [point["z"] for point in series["points"]]
        question = query.get("question_id")
        slope, intercept, _, _ = _fit(values)
        if question == "change":
            index = _cusum(values)
            value = scores[index] if index is not None else (scores[-1] if scores else 0)
        elif question == "forecast":
            value = _project(values, 3 if aggregation == "annual" else 12, variable, slope, intercept) - _mean(values)
        elif question == "anomaly":
            value = scores[-1] if scores else 0
        else:
            value = slope
        selected = anchor["id"] == province if province else anchor["id"] == "place" if place else anchor["id"] == query.get("region_id")
        cells.append(
            {
                "id": anchor["id"],
                "name": anchor["name"],
                "lat": anchor["lat"],
                "lon": anchor["lon"],
                "value": value,
                "selected": selected,
            }
        )
    return cells


def _conclusion(query: dict[str, Any], statistics: list[dict[str, Any]], relations: list[dict[str, Any]], pattern: dict[str, Any], event: dict[str, Any] | None, lab_used: bool = False) -> str:
    n = statistics[0]["n"] if statistics else 0
    step = "medias anuales" if query.get("aggregation") == "annual" else "meses"
    scope = f"Serie de {_scope_subject(query)}: {n} {step}."
    question = query.get("question_id")
    if question == "anomaly":
        parts = []
        for item in statistics:
            z = f"{item['last_z']:.2f}"
            if item["n_anomalies"] == 0:
                parts.append(f"{NAMES[item['variable']]} no tiene observaciones con |Z| > 2. El último Z es {z}.")
            else:
                count = "1 observación" if item["n_anomalies"] == 1 else f"{item['n_anomalies']} observaciones"
                parts.append(f"{NAMES[item['variable']]} tiene {count} con |Z| > 2. El último Z es {z}.")
        return f"{scope} {' '.join(parts)}"
    if question == "change":
        dated = [item for item in statistics if item["change_date"]]
        text = " ".join(
            f"El CUSUM de {NAMES[item['variable']]} alcanza su máximo en {item['change_date']}. Ahí el cambio es de media, no una causa."
            for item in dated
        ) or "No hay suficientes observaciones para un CUSUM."
        return f"{scope} {text}"
    if question == "lag":
        text = " ".join(item["sentence"] for item in relations[:2]) or "Entre las variables elegidas no aparece un desfase con |r| mayor que 0.4."
        return f"{scope} {text}"
    if question == "forecast":
        steps = "3 años" if query.get("aggregation") == "annual" else "12 meses"
        lead = "El pronóstico ARIMA/SARIMA del laboratorio" if lab_used else f"Al prolongar la pendiente de Sen {steps}"
        text = " ".join(
            (
                f"{lead}, la media de {NAMES[item['variable']]} queda en "
                f"{item['projected_mean']:.2f} {UNITS[item['variable']]} frente a la histórica {item['mean']:.2f} "
                f"({item['projected_pct']:+.1f}%)."
            )
            for item in statistics
        )
        return f"{scope} {text}"
    if question == "pattern":
        share = "no se puede separar un componente" if pattern["pc1_share"] is None else f"el primer componente reúne el {pattern['pc1_share'] * 100:.1f}% de la varianza"
        period = ""
        if pattern["period_steps"] is not None:
            unit = "años" if pattern["period_unit"] == "years" else "meses"
            period = f" La frecuencia dominante de {NAMES[pattern['variable']]} corresponde a un periodo de {pattern['period_steps']} {unit}."
        return f"{scope} Con las variables elegidas, {share}.{period}"
    trends = " ".join(_trend_sentence(item) for item in statistics)
    return f"{scope} {trends} {_alert(query, statistics, event)}".strip()


def _trend_sentence(item: dict[str, Any]) -> str:
    slope = f"{item['slope_per_step']:+.4f} {UNITS[item['variable']]} por periodo"
    p_text = "p < 0.001" if item["p_value"] < 0.001 else f"p = {item['p_value']:.3f}"
    name = NAMES[item["variable"]]
    if not item["significant"]:
        return f"{name} no muestra una tendencia monotónica significativa ({p_text}, pendiente de Sen {slope})."
    way = "creciente" if item["direction"] == "up" else "decreciente"
    fit = f" La recta explica el {item['r_squared'] * 100:.1f}% de la varianza." if item["r_squared"] > 0.5 else ""
    return f"{name} muestra tendencia {way} ({p_text}, pendiente de Sen {slope}).{fit}"


def _alert(query: dict[str, Any], statistics: list[dict[str, Any]], event: dict[str, Any] | None) -> str:
    case_id = query.get("case_id")
    if case_id == "drought":
        names = [NAMES[item["variable"]] for item in statistics if item["variable"] in WATER and item["significant"] and item["direction"] == "down"]
        if not names:
            return "El perfil clima no marca alerta de sequía: ni la precipitación ni la humedad del suelo tienen una tendencia decreciente significativa."
        where = f" El CUSUM sitúa el cambio alrededor de {event['start']}." if event else ""
        return f"El perfil clima marca alerta de sequía en {' y '.join(names)} porque la tendencia decreciente es significativa.{where} Es una etiqueta de la serie, no una causa."
    if case_id == "heat":
        names = [NAMES[item["variable"]] for item in statistics if item["variable"] in HEAT and item["significant"] and item["direction"] == "up"]
        if not names:
            return "El perfil clima no marca calentamiento: la temperatura elegida no tiene una tendencia creciente significativa."
        where = f" El CUSUM sitúa el cambio alrededor de {event['start']}." if event else ""
        return f"El perfil clima marca calentamiento en {' y '.join(names)} porque la tendencia creciente es significativa.{where} Es una etiqueta de la serie, no una causa."
    return ""


def _sequence(query: dict[str, Any], statistics: list[dict[str, Any]], relations: list[dict[str, Any]], pattern: dict[str, Any]) -> str:
    question = query.get("question_id")
    if question == "lag":
        lagged = [item for item in relations if item["lag"] > 0]
        if not lagged:
            return "Sin desfase con |r| mayor que 0.4."
        return " · ".join(f"{NAMES[item['driver']]}, luego {NAMES[item['response']]} ({item['lag']})" for item in lagged[:3])
    if question == "anomaly":
        return " · ".join(f"{NAMES[item['variable']]}: {item['n_anomalies']} |Z|>2" for item in statistics)
    if question == "change":
        return " · ".join(f"{NAMES[item['variable']]}: {item['change_date'] or 'sin fecha'}" for item in statistics)
    if question == "forecast":
        return " · ".join(f"{NAMES[item['variable']]} {item['projected_pct']:+.1f}%" for item in statistics)
    if question == "pattern":
        share = "PC1 n/d" if pattern["pc1_share"] is None else f"PC1 {pattern['pc1_share'] * 100:.0f}%"
        period = "" if pattern["period_steps"] is None else f" · ciclo {pattern['period_steps']}"
        return f"{share}{period}"
    parts = []
    for item in statistics:
        way = "crece" if item["significant"] and item["direction"] == "up" else "baja" if item["significant"] else "sin tendencia"
        parts.append(f"{NAMES[item['variable']]} {way} ({item['slope_per_step']:+.3f} {UNITS[item['variable']]})")
    return " · ".join(parts)


def _caption(query: dict[str, Any], variable: str) -> str:
    name = NAMES.get(variable, variable)
    question = query.get("question_id")
    where = ""
    if query.get("province_id"):
        feature = _admin_index().get(query["province_id"])
        if feature:
            where = f" en {feature['name']}"
    elif query.get("place"):
        where = f" cerca de {query['place'].get('name', 'el lugar')}"
    if question == "anomaly":
        return f"{name}: último Z-score{where}. El tamaño es la magnitud de ese Z."
    if question == "change":
        return f"{name}: Z-score en la fecha del CUSUM{where}."
    if question == "forecast":
        return f"{name}: media proyectada menos media histórica{where}."
    if question == "pattern":
        return f"{name}: pendiente de Sen por periodo{where}. El ciclo va en la conclusión."
    if question == "lag":
        return f"{name}: pendiente de Sen por periodo{where}. El orden temporal va bajo el mapa."
    return f"{name}: pendiente de Sen por periodo{where}. El tamaño es la magnitud de esa pendiente."


def _focus(query: dict[str, Any], relations: list[dict[str, Any]], variables: list[str]) -> str:
    if query.get("question_id") == "lag" and relations:
        return relations[0]["driver"]
    if query.get("case_id") == "drought" and "precipitation" in variables:
        return "precipitation"
    if query.get("case_id") == "heat" and "temperature" in variables:
        return "temperature"
    if query.get("case_id") == "heat" and "lst" in variables:
        return "lst"
    return variables[0]


def _scope_subject(query: dict[str, Any]) -> str:
    index = _admin_index()
    province = index.get(query.get("province_id") or "")
    where: list[str] = []
    if province and province.get("level") == "province":
        department = index.get(province.get("department_id") or "")
        if department:
            where.append(f"la provincia {province['name']} ({department['name']})")
        else:
            where.append(f"la provincia {province['name']}")
    else:
        department = index.get(query.get("department_id") or "")
        if department and department.get("level") == "department":
            where.append(f"el departamento {department['name']}")
        else:
            where.append(REGIONS.get(query.get("region_id") or "", ("Bolivia", 0, 0, 1))[0])
    place = query.get("place")
    if place:
        where.append(f"el lugar {place.get('name') or 'el lugar'}")
    return ", ".join(where)


def _study_anchor(query: dict[str, Any], anchors: list[dict[str, Any]]) -> dict[str, Any]:
    if query.get("province_id"):
        found = next((item for item in anchors if item["id"] == query["province_id"]), None)
        if found:
            return found
    if query.get("place"):
        found = next((item for item in anchors if item["id"] == "place"), None)
        if found:
            return found
    region = query.get("region_id")
    found = next((item for item in anchors if item["id"] == region), None)
    if found:
        return found
    name, lat, lon, factor = REGIONS.get(region or "", ("Bolivia", -16.5, -64.5, 1.0))
    return {"id": region or "bolivia", "name": name, "lat": lat, "lon": lon, "factor": factor}


def _anchors(query: dict[str, Any]) -> list[dict[str, Any]]:
    index = _admin_index()
    province = index.get(query.get("province_id") or "")
    if province and province.get("level") == "province":
        points = _sample_inside(province.get("geometry") or {}, 6, (province["lat"], province["lon"]))
        compass = ["", "norte", "este", "sur", "oeste", "noreste"]
        factors = [1.2, 0.7, 1.45, 0.85, 1.6, 0.55]
        return [
            {
                "id": province["id"] if index == 0 else f"{province['id']}--{index}",
                "name": province["name"] if index == 0 else f"{province['name']} {compass[index] if index < len(compass) else index}",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "factor": factors[index] if index < len(factors) else 1,
            }
            for index, (lat, lon) in enumerate(points)
        ]
    place = query.get("place")
    if place:
        lat, lon, name = float(place["lat"]), float(place["lon"]), str(place.get("name") or "Lugar")
        offsets = [
            (0, 0, name, 1.2),
            (0.16, 0.08, f"{name} norte", 0.75),
            (-0.1, 0.14, f"{name} este", 1.4),
            (0.06, -0.16, f"{name} sur", 0.9),
            (-0.14, -0.08, f"{name} oeste", 1.15),
        ]
        return [
            {"id": "place" if i == 0 else f"place--{i}", "name": label, "lat": round(lat + dlat, 4), "lon": round(lon + dlon, 4), "factor": factor}
            for i, (dlat, dlon, label, factor) in enumerate(offsets)
        ]
    return [
        {"id": item[0], "name": item[1], "lat": item[2], "lon": item[3], "factor": item[4]}
        for item in PLACES
    ]


_ADMIN: dict[str, dict[str, Any]] | None = None


def _admin_index() -> dict[str, dict[str, Any]]:
    global _ADMIN
    if _ADMIN is not None:
        return _ADMIN
    _ADMIN = {}
    if not ADMIN_PATH.exists():
        return _ADMIN
    import json

    data = json.loads(ADMIN_PATH.read_text(encoding="utf-8"))
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        if props.get("level") not in ("department", "province"):
            continue
        if not props.get("id"):
            continue
        lat, lon = _centroid(geometry)
        _ADMIN[props["id"]] = {
            "id": props["id"],
            "name": props.get("name") or props["id"],
            "level": props["level"],
            "department_id": props.get("department_id") or "",
            "lat": lat,
            "lon": lon,
            "geometry": geometry,
        }
    return _ADMIN


def _centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    if geometry.get("type") == "Polygon":
        ring = geometry.get("coordinates", [[]])[0]
    elif geometry.get("type") == "MultiPolygon":
        polygons = geometry.get("coordinates") or [[[]]]
        ring = max(polygons, key=lambda item: len(item[0]) if item else 0)[0]
    else:
        return -16.5, -64.5
    if not ring:
        return -16.5, -64.5
    lon = sum(point[0] for point in ring) / len(ring)
    lat = sum(point[1] for point in ring) / len(ring)
    return lat, lon


def _sample_inside(geometry: dict[str, Any], count: int, fallback: tuple[float, float]) -> list[tuple[float, float]]:
    bounds = _bounds(geometry)
    found: list[tuple[float, float]] = []
    if bounds is not None:
        west, east, south, north = bounds
        width = max(east - west, 0.01)
        height = max(north - south, 0.01)
        steps = 9
        for y in range(steps):
            for x in range(steps):
                lon = west + ((x + 0.5) / steps) * width
                lat = south + ((y + 0.5) / steps) * height
                if _contains(geometry, lon, lat):
                    found.append((lat, lon))
    if not found:
        found.append(fallback)
    origin_lat = sum(point[0] for point in found) / len(found)
    origin_lon = sum(point[1] for point in found) / len(found)
    pool = found[:]
    chosen: list[tuple[float, float]] = []

    def gap(point: tuple[float, float], other: tuple[float, float]) -> float:
        return (point[0] - other[0]) ** 2 + (point[1] - other[1]) ** 2

    first = min(range(len(pool)), key=lambda item: gap(pool[item], (origin_lat, origin_lon)))
    chosen.append(pool.pop(first))
    while len(chosen) < count and pool:
        pick = max(range(len(pool)), key=lambda item: min(gap(pool[item], other) for other in chosen))
        chosen.append(pool.pop(pick))
    while len(chosen) < count:
        last = chosen[-1]
        chosen.append((last[0] + 0.04, last[1] + 0.04))
    return chosen[:count]


def _bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    rings = _rings(geometry)
    if not rings:
        return None
    west = east = rings[0][0][0]
    south = north = rings[0][0][1]
    for ring in rings:
        for lon, lat in ring:
            west = min(west, lon)
            east = max(east, lon)
            south = min(south, lat)
            north = max(north, lat)
    return west, east, south, north


def _rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        return geometry.get("coordinates") or []
    if geometry.get("type") == "MultiPolygon":
        rings: list[list[list[float]]] = []
        for polygon in geometry.get("coordinates") or []:
            rings.extend(polygon)
        return rings
    return []


def _contains(geometry: dict[str, Any], lon: float, lat: float) -> bool:
    if geometry.get("type") == "Polygon":
        return _polygon_contains(geometry.get("coordinates") or [], lon, lat)
    if geometry.get("type") == "MultiPolygon":
        return any(_polygon_contains(polygon, lon, lat) for polygon in geometry.get("coordinates") or [])
    return False


def _polygon_contains(rings: list[list[list[float]]], lon: float, lat: float) -> bool:
    if not rings or not _ring_contains(rings[0], lon, lat):
        return False
    return all(not _ring_contains(ring, lon, lat) for ring in rings[1:])


def _ring_contains(ring: list[list[float]], lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]
        crosses = (yi > lat) != (yj > lat)
        if crosses and lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _build_series(query: dict[str, Any], anchor: dict[str, Any], variable: str, aggregation: str) -> dict[str, Any]:
    start = _parse(query.get("start") or "2001-01")
    end = _parse(query.get("end") or "2024-12")
    count = max(1, (end[0] * 12 + end[1] - 1) - (start[0] * 12 + start[1] - 1) + 1)
    rand = _mulberry32(_hash(f"{anchor['id']}|{anchor['factor']}|{variable}|{query.get('start')}|{query.get('end')}"))
    points = []
    year, month = start
    for index in range(count):
        value = _lab_value(variable, index, count, float(anchor["factor"]), rand)
        points.append({"date": f"{year:04d}-{month:02d}", "value": round(value, 3 if variable == "ndvi" else 2), "anomaly": 0, "z": 0})
        month += 1
        if month == 13:
            month = 1
            year += 1
    if aggregation == "annual":
        buckets: dict[str, list[float]] = {}
        for point in points:
            buckets.setdefault(point["date"][:4], []).append(point["value"])
        points = [
            {"date": year_key, "value": round(_mean(group), 3 if variable == "ndvi" else 2), "anomaly": 0, "z": 0}
            for year_key, group in buckets.items()
        ]
    center = _mean([point["value"] for point in points])
    scores = _zscores([point["value"] for point in points])
    for point, score in zip(points, scores):
        point["anomaly"] = round(point["value"] - center, 3 if variable == "ndvi" else 2)
        point["z"] = score
    return {"variable": variable, "unit": UNITS[variable], "points": points}


def _lab_value(variable: str, index: int, count: int, factor: float, rand) -> float:
    season = math.sin(2 * math.pi * index / 12)
    warm = math.cos(2 * math.pi * index / 12)
    start = max(0, count - max(2, round(count * 0.3)))
    span = count - start
    ramp = (index - start) / span if index >= start and span > 0 else 0
    stress = ramp * factor
    if variable == "precipitation":
        value = 80 + 60 * season + _normal(rand) * 15
        if ramp > 0:
            value = value * (1 - 0.55 * min(stress, 1.4)) + _normal(rand) * 5
        return max(0, value)
    if variable == "temperature":
        value = 26 + 4 * warm + _normal(rand) * 1.2
        if ramp > 0:
            value += 1.8 * stress + _normal(rand) * 0.6
        return value
    if variable == "soil_moisture":
        value = 30 + 10 * season + _normal(rand) * 4
        if ramp > 0:
            value += -12 * stress + _normal(rand) * 2
        return min(60, max(3, value))
    if variable == "ndvi":
        value = 0.55 + 0.2 * season + _normal(rand) * 0.03 - 0.0004 * index
        if ramp > 0:
            value -= 0.12 * stress
        return min(0.95, max(0.05, value))
    value = 298 + 8 * season + _normal(rand) * 1 + 0.015 * index
    if ramp > 0:
        value += 1.6 * stress
    return max(250, value)


def _mann_kendall(values: list[float]) -> tuple[float, float, int]:
    n = len(values)
    if n < 4:
        return 0.0, 1.0, n
    s = 0
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = values[j] - values[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1
            slopes.append(diff / (j - i))
    variance = n * (n - 1) * (2 * n + 5) / 18
    if s > 0:
        z_stat = (s - 1) / math.sqrt(variance)
    elif s < 0:
        z_stat = (s + 1) / math.sqrt(variance)
    else:
        z_stat = 0
    p_value = min(1, max(0, 2 * (1 - _normal_cdf(abs(z_stat)))))
    slopes.sort()
    mid = len(slopes) // 2
    slope = slopes[mid] if len(slopes) % 2 else (slopes[mid - 1] + slopes[mid]) / 2
    return slope, p_value, n


def _zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    center = _mean(values)
    variance = sum((value - center) ** 2 for value in values) / len(values)
    sd = math.sqrt(variance)
    if sd == 0:
        return [0.0 for _ in values]
    return [(value - center) / sd for value in values]


def _cusum(values: list[float]) -> int | None:
    if len(values) < 4:
        return None
    center = _mean(values)
    acc = 0.0
    best = 0
    best_abs = -1.0
    for i, value in enumerate(values):
        acc += value - center
        if abs(acc) > best_abs:
            best_abs = abs(acc)
            best = i
    return best


def _r2(values: list[float]) -> float:
    n = len(values)
    if n < 3:
        return 0
    x_mean = (n - 1) / 2
    y_mean = _mean(values)
    sxx = sxy = syy = 0.0
    for i, value in enumerate(values):
        dx = i - x_mean
        dy = value - y_mean
        sxx += dx * dx
        sxy += dx * dy
        syy += dy * dy
    if sxx == 0 or syy == 0:
        return 0
    return (sxy * sxy) / (sxx * syy)


def _sen_intercept(values: list[float], slope: float) -> float:
    residuals = sorted(value - slope * index for index, value in enumerate(values))
    mid = len(residuals) // 2
    if not residuals:
        return 0
    if len(residuals) % 2:
        return residuals[mid]
    return (residuals[mid - 1] + residuals[mid]) / 2


def _project(values: list[float], steps: int, variable: str, slope: float, intercept: float) -> float:
    if not values or steps <= 0:
        return _mean(values)
    total = sum(_clip(intercept + slope * (len(values) + step), variable) for step in range(steps))
    return total / steps


def _sen_mean(values: list[float], steps: int, variable: str) -> float:
    if not values or steps <= 0:
        return _mean(values)
    slope, intercept, _, _ = _fit(values)
    return _project(values, steps, variable, slope, intercept)


def _cross_best(x: list[float], y: list[float], max_lag: int) -> dict[str, float | int] | None:
    best = None
    for lag in range(-max_lag, max_lag + 1):
        xx = x[: len(x) - lag] if lag >= 0 else x[-lag:]
        yy = y[lag:] if lag >= 0 else y[: len(y) + lag]
        n = min(len(xx), len(yy))
        if n < 4:
            continue
        r = _pearson(xx[:n], yy[:n])
        if r is None:
            continue
        if best is None or abs(r) > abs(best["r"]):
            best = {"lag": lag, "r": r, "p": _corr_p(r, n), "n": n}
    return best


def _pearson(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 3:
        return None
    ma, mb = _mean(a[:n]), _mean(b[:n])
    num = da = db = 0.0
    for i in range(n):
        xa, xb = a[i] - ma, b[i] - mb
        num += xa * xb
        da += xa * xa
        db += xb * xb
    if da == 0 or db == 0:
        return 0
    return num / math.sqrt(da * db)


def _corr_p(r: float, n: int) -> float:
    clipped = max(-0.999999, min(0.999999, r))
    if n <= 3:
        return 1
    z_stat = math.atanh(clipped) * math.sqrt(n - 3)
    return min(1, max(0, 2 * (1 - _normal_cdf(abs(z_stat)))))


def _pc1(columns: list[list[float]]) -> float | None:
    width = len(columns)
    length = len(columns[0]) if columns else 0
    if width < 2 or length < 3:
        return None
    means = [_mean(column) for column in columns]
    stds = []
    for column, center in zip(columns, means):
        stds.append(math.sqrt(sum((value - center) ** 2 for value in column) / length))
    corr = [[0.0 for _ in range(width)] for _ in range(width)]
    for i in range(width):
        corr[i][i] = 1
        if stds[i] == 0:
            continue
        for j in range(i + 1, width):
            if stds[j] == 0:
                continue
            dot = sum(((columns[i][t] - means[i]) / stds[i]) * ((columns[j][t] - means[j]) / stds[j]) for t in range(length))
            corr[i][j] = corr[j][i] = dot / length
    vector = [1 / math.sqrt(width) for _ in range(width)]
    value = 0.0
    for _ in range(48):
        nxt = [sum(corr[i][j] * vector[j] for j in range(width)) for i in range(width)]
        norm = math.sqrt(sum(item * item for item in nxt)) or 1
        vector = [item / norm for item in nxt]
        value = sum(vector[i] * sum(corr[i][j] * vector[j] for j in range(width)) for i in range(width))
    return value / width


def _period(values: list[float]) -> float | None:
    n = len(values)
    if n < 4:
        return None
    center = _mean(values)
    best_amp = 0.0
    best_k = 0
    for k in range(1, n // 2 + 1):
        real = imag = 0.0
        for t, value in enumerate(values):
            angle = 2 * math.pi * k * t / n
            sample = value - center
            real += sample * math.cos(angle)
            imag -= sample * math.sin(angle)
        amp = math.hypot(real, imag) / n
        if amp > best_amp:
            best_amp = amp
            best_k = k
    if best_k == 0:
        return None
    return n / best_k


def _from_lab(name: str) -> str | None:
    for key, label in LAB_KEY.items():
        if label == name:
            return key
    return None


def _clip(value: float, variable: str) -> float:
    if variable == "precipitation":
        return max(0, value)
    if variable == "soil_moisture":
        return min(60, max(3, value))
    if variable == "ndvi":
        return min(0.95, max(0.05, value))
    if variable == "lst":
        return max(250, value)
    return value


def _future(last: str, step: int, aggregation: str) -> str:
    if aggregation == "annual" or len(last) == 4:
        return str(int(last) + step)
    year, month = _parse(last)
    month += step
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return f"{year:04d}-{month:02d}"


def _parse(value: str) -> tuple[int, int]:
    parts = value.split("-")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 1


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def _sd(values: list[float]) -> float:
    if not values:
        return 0
    center = _mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


def _normal_cdf(x: float) -> float:
    t = 1 / (1 + 0.2316419 * abs(x))
    d = 0.3989422804014327 * math.exp(-x * x / 2)
    p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return 1 - p if x >= 0 else p


def _normal(rand) -> float:
    u = 0.0
    v = 0.0
    while u == 0:
        u = rand()
    while v == 0:
        v = rand()
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def _hash(value: str) -> int:
    hashed = 2166136261
    for char in value:
        hashed ^= ord(char)
        hashed = _imul(hashed, 16777619)
    return hashed & 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF


def _i32(n: int) -> int:
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n >= 0x80000000 else n


def _mulberry32(seed: int):
    state = _i32(seed)

    def rand() -> float:
        nonlocal state
        state = _i32(state + 0x6D2B79F5)
        t = _i32(_imul(state ^ ((state & 0xFFFFFFFF) >> 15), state | 1))
        t = _i32((t + _imul(t ^ ((t & 0xFFFFFFFF) >> 7), 61 | t)) ^ t)
        return (((t ^ ((t & 0xFFFFFFFF) >> 14)) & 0xFFFFFFFF)) / 4294967296

    return rand
