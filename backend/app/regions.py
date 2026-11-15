"""Preset regions (Santa Cruz de la Sierra & Bolivia) and the variable catalog.

Each variable maps to NASA POWER parameters; the first parameter that returns
data wins, the rest act as fallbacks.
"""

REGIONS: dict[str, dict] = {
    # --- Santa Cruz subregions (primary focus) ---
    "scz_capital": {
        "name": "Santa Cruz de la Sierra",
        "lat": -17.7833,
        "lon": -63.1821,
        "group": "santa_cruz",
    },
    "scz_chiquitania": {
        "name": "Chiquitanía / Roboré",
        "lat": -18.3333,
        "lon": -59.7500,
        "group": "santa_cruz",
    },
    "scz_norte": {
        "name": "Norte Integrado / Montero",
        "lat": -17.3387,
        "lon": -63.2505,
        "group": "santa_cruz",
    },
    "scz_valles": {
        "name": "Valles Cruceños / Vallegrande",
        "lat": -18.4897,
        "lon": -64.1069,
        "group": "santa_cruz",
    },
    "scz_pantanal": {
        "name": "Pantanal / Puerto Suárez",
        "lat": -18.9667,
        "lon": -57.7981,
        "group": "santa_cruz",
    },
    "scz_chaco": {
        "name": "Cordillera / Camiri",
        "lat": -20.0385,
        "lon": -63.5183,
        "group": "santa_cruz",
    },
    # --- Bolivia departments ---
    "la_paz": {
        "name": "La Paz",
        "lat": -16.5000,
        "lon": -68.1500,
        "group": "departamento",
    },
    "cochabamba": {
        "name": "Cochabamba",
        "lat": -17.3895,
        "lon": -66.1568,
        "group": "departamento",
    },
    "oruro": {
        "name": "Oruro",
        "lat": -17.9833,
        "lon": -67.1500,
        "group": "departamento",
    },
    "potosi": {
        "name": "Potosí",
        "lat": -19.5836,
        "lon": -65.7531,
        "group": "departamento",
    },
    "tarija": {
        "name": "Tarija",
        "lat": -21.5355,
        "lon": -64.7296,
        "group": "departamento",
    },
    "chuquisaca": {
        "name": "Sucre / Chuquisaca",
        "lat": -19.0333,
        "lon": -65.2627,
        "group": "departamento",
    },
    "beni": {
        "name": "Trinidad / Beni",
        "lat": -14.8333,
        "lon": -64.9000,
        "group": "departamento",
    },
    "pando": {
        "name": "Cobija / Pando",
        "lat": -11.0267,
        "lon": -68.7692,
        "group": "departamento",
    },
}

VARIABLES: dict[str, dict] = {
    "temperature": {
        "label": "Temperatura a 2 m",
        "label_en": "2 m Air Temperature",
        "nasa_params": ["T2M", "T2M_MAX"],
        "unit": "°C",
    },
    "precipitation": {
        "label": "Precipitación corregida",
        "label_en": "Corrected Precipitation",
        "nasa_params": ["PRECTOTCORR"],
        "unit": "mm/día",
    },
    "soil_moisture": {
        "label": "Humedad superficial del suelo",
        "label_en": "Surface Soil Wetness",
        "nasa_params": ["GWETTOP"],
        "unit": "fracción 0-1",
    },
    "root_moisture": {
        "label": "Humedad radicular / agua en perfil",
        "label_en": "Root Zone / Profile Soil Wetness",
        "nasa_params": ["GWETROOT", "GWETPROF"],
        "unit": "fracción 0-1",
    },
    "evaporation": {
        "label": "Evapotranspiración / Humedad relativa",
        "label_en": "Evapotranspiration / Relative Humidity",
        "nasa_params": ["EVPTRNS", "RH2M"],
        "unit": "mm/día o %",
    },
    "wind": {
        "label": "Velocidad del viento a 2 m",
        "label_en": "2 m Wind Speed",
        "nasa_params": ["WS2M"],
        "unit": "m/s",
    },
    "ndvi_proxy": {
        "label": "Radiación PAR (proxy vegetativo)",
        "label_en": "PAR Radiation (vegetation proxy)",
        "nasa_params": ["ALLSKY_SFC_PAR_TOT"],
        "unit": "W/m²",
    },
}
