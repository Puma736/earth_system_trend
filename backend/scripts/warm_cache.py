"""Precarga la caché de NASA POWER para las regiones de la demo.

Así la primera consulta de la demo no tarda: las 6 variables de cada región
quedan guardadas en backend/.cache/. Úsalo antes de la demo y después de desplegar.

    python -m scripts.warm_cache                     # todas las regiones
    python -m scripts.warm_cache santa-cruz la-paz  # solo algunas
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import services  # noqa: E402
from app.data import power  # noqa: E402
from app.data.errors import DataSourceError  # noqa: E402
from app.regions import REGIONS, SEASONS  # noqa: E402

# Todas las consultas piden este período a POWER (ver services.drought_series).
START, END = power.FIRST_YEAR, power.LAST_YEAR


def main(region_ids: list[str]) -> int:
    unknown = [r for r in region_ids if r not in REGIONS]
    if unknown:
        print(f"Unknown region(s): {', '.join(unknown)}. Options: {', '.join(REGIONS)}")
        return 2

    failed = 0
    for rid in region_ids or list(REGIONS):
        region = REGIONS[rid]
        t0 = time.time()
        try:
            # Las 3 épocas usan la misma descarga mensual; DRY basta para llenar la caché.
            result = services.drought(region, SEASONS["DRY"], START, END)
        except DataSourceError as exc:
            failed += 1
            print(f"{rid:12} FAILED: {exc}")
            continue
        print(f"{rid:12} {time.time() - t0:5.1f}s  DRY: {result.summary.text}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
