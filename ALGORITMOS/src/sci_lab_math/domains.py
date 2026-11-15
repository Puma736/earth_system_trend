"""Perfiles de dominio para la interpretacion de resultados.

Cada perfil define reglas de conclusion (alertas) y vocabulario neutro.
"""

from __future__ import annotations

from typing import Any, Dict, List


PROFILES = {
    "general": {
        "name": "General",
        "alerts": [],
    },
    "clima": {
        "name": "Clima / Ambiental",
        "alerts": ["drought", "thermal_stress"],
    },
    "finanzas": {
        "name": "Finanzas",
        "alerts": ["drawdown", "volatility"],
    },
    "industria": {
        "name": "Industria / IoT",
        "alerts": ["sensor_drift", "out_of_range"],
    },
}


def get_profile(domain: str) -> Dict[str, Any]:
    return PROFILES.get(domain, PROFILES["general"])


def apply_alerts(domain: str, variable: str, trend: Dict[str, Any],
                 anomalies: Dict[str, Any], conclusions: List[str]) -> None:
    """Agrega alertas especificas del dominio a la lista de conclusiones."""
    vlow = variable.lower()
    mk = trend.get("mann_kendall", {})
    tr = mk.get("trend") if isinstance(mk, dict) else None
    p = mk.get("p_value", 1.0) if isinstance(mk, dict) else 1.0

    if domain == "clima":
        if tr == "decreasing" and p < 0.05 and any(k in vlow for k in ("precip", "lluvia", "humed", "soil", "water")):
            conclusions.append(f"ALERTA DE SEQUIA: {variable} muestra tendencia decreciente significativa; posible reduccion de disponibilidad hidrica.")
        if tr == "increasing" and p < 0.05 and any(k in vlow for k in ("temp", "temperatura")):
            conclusions.append(f"CALENTAMIENTO: {variable} muestra tendencia creciente significativa; posible estres termico.")

    if domain == "finanzas":
        if tr == "decreasing" and p < 0.05:
            conclusions.append(f"ALERTA FINANCIERA: {variable} en tendencia descendente significativa; posible deterioro.")
        if anomalies.get("n_anomalies_z2", 0) > 0:
            conclusions.append(f"VOLATILIDAD: {variable} presenta {anomalies['n_anomalies_z2']} anomalias (|Z|>2).")

    if domain == "industria":
        if anomalies.get("n_anomalies_z2", 0) > 0:
            conclusions.append(f"SENSOR/PROCESO: {variable} presenta {anomalies['n_anomalies_z2']} lecturas anomalas (|Z|>2).")
        if tr == "increasing" and p < 0.05:
            conclusions.append(f"DRIFT: {variable} muestra deriva creciente significativa.")