"""Descarga única de focos MODIS de NASA FIRMS y agregado por mes y celda de 0,5°.

Uso (desde backend/, con el entorno virtual activo):

    python -m scripts.download_firms --start 2003-01-01 --end 2025-12-31

- La MAP_KEY se lee de la variable de entorno FIRMS_MAP_KEY o de backend/.env.
  NUNCA la pongas en el código, en el repo ni en el chat.
- Cada respuesta cruda se guarda en data/firms_raw/ (ignorado por git), así que si
  el script se corta, al volver a correrlo continúa donde quedó.
- El resultado es data/firms_monthly_cells.csv (este sí se versiona).
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.data.firms import cell_center  # noqa: E402
from app.regions import REGIONS  # noqa: E402

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DAYS_PER_REQUEST = 5
MIN_CONFIDENCE = 30
VEGETATION_FIRE_TYPE = "0"
# FIRMS cuenta "transacciones", no consultas: una ventana de 5 días cuesta varias.
# Con 0,15 s entre consultas se llegó al límite tras ~500. Con 0,8 s se va más tranquilo,
# y si igual se llega al límite, se espera a que se libere la ventana de 10 minutos.
PAUSE_S = 0.8
LIMIT_TEXT = "exceeding allowed transaction limit"
LIMIT_WAIT_S = 60
LIMIT_MAX_WAITS = 15  # hasta 15 min esperando que se libere el límite


def windows(start: date, end: date):
    day = start
    while day <= end:
        days = min(DAYS_PER_REQUEST, (end - day).days + 1)
        yield day, days
        day += timedelta(days=days)


def fetch_chunk(client: httpx.Client, key: str, source: str, bbox: str, day: date, days: int, raw_dir: Path) -> str:
    path = raw_dir / f"{source}_{day.isoformat()}_{days}.csv"
    if path.exists():
        return path.read_text(encoding="utf-8")

    url = f"{API}/{key}/{source}/{bbox}/{days}/{day.isoformat()}"
    errors = limit_waits = 0
    while True:
        try:
            resp = client.get(url, timeout=120)
        except httpx.HTTPError as exc:
            # Nunca imprimir la excepción tal cual: su texto incluye la URL con la MAP_KEY.
            errors += 1
            if errors >= 5:
                raise RuntimeError(f"Could not download {day}: {type(exc).__name__}") from None
            print(f"  {day}: network error ({type(exc).__name__}). Retrying in {5 * errors}s", file=sys.stderr)
            time.sleep(5 * errors)
            continue

        text = resp.text
        if resp.status_code == 429 or LIMIT_TEXT in text.lower():
            limit_waits += 1
            if limit_waits > LIMIT_MAX_WAITS:
                raise RuntimeError(f"Transaction limit did not clear for {day}. Run the script again later.")
            print(f"  {day}: FIRMS transaction limit reached, waiting {LIMIT_WAIT_S}s "
                  f"({limit_waits}/{LIMIT_MAX_WAITS})", file=sys.stderr)
            time.sleep(LIMIT_WAIT_S)
            continue

        if resp.status_code != 200 or not text.startswith("latitude"):
            errors += 1
            body = text[:200].replace(key, "<MAP_KEY>")
            if errors >= 5:
                raise RuntimeError(f"Could not download {day}: HTTP {resp.status_code}: {body}")
            print(f"  {day}: HTTP {resp.status_code}: {body!r}. Retrying in {5 * errors}s", file=sys.stderr)
            time.sleep(5 * errors)
            continue

        # Solo se guarda una respuesta válida (empieza con la cabecera del CSV).
        path.write_text(text, encoding="utf-8")
        time.sleep(PAUSE_S)
        return text


def aggregate(texts, stats: dict) -> dict[tuple[int, int, float, float], int]:
    counts: dict[tuple[int, int, float, float], int] = defaultdict(int)
    for text in texts:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames and "type" not in reader.fieldnames:
            stats["missing_type_column"] = True
        for row in reader:
            stats["raw"] += 1
            try:
                if int(row["confidence"]) < MIN_CONFIDENCE:
                    continue
            except (KeyError, ValueError):
                continue
            if "type" in row and row["type"] != VEGETATION_FIRE_TYPE:
                continue
            lat, lon = float(row["latitude"]), float(row["longitude"])
            year, month = int(row["acq_date"][:4]), int(row["acq_date"][5:7])
            counts[(year, month, cell_center(lat), cell_center(lon))] += 1
            stats["kept"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2003, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--region", default="bolivia", choices=sorted(REGIONS),
                        help="Rectangle to download. Bolivia covers every sub-region.")
    parser.add_argument("--source", default="MODIS_SP", choices=["MODIS_SP", "MODIS_NRT"])
    args = parser.parse_args()

    settings = get_settings()
    key = settings.firms_map_key
    if not key:
        sys.exit("FIRMS_MAP_KEY is not set. Put it in backend/.env (see .env.example).")

    raw_dir = settings.data_dir / "firms_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    bbox = REGIONS[args.region].bbox.as_firms()

    chunks = list(windows(args.start, args.end))
    print(f"{len(chunks)} requests for {args.region} ({bbox}), {args.source}")

    texts = []
    with httpx.Client() as client:
        for i, (day, days) in enumerate(chunks, 1):
            texts.append(fetch_chunk(client, key, args.source, bbox, day, days, raw_dir))
            if i % 100 == 0:
                print(f"  {i}/{len(chunks)}")

    stats = {"raw": 0, "kept": 0, "missing_type_column": False}
    counts = aggregate(texts, stats)

    out = settings.firms_csv
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "month", "lat", "lon", "count"])
        for (year, month, lat, lon), n in sorted(counts.items()):
            writer.writerow([year, month, lat, lon, n])

    print(f"Raw detections: {stats['raw']}, kept: {stats['kept']}, rows written: {len(counts)} -> {out}")
    if stats["missing_type_column"]:
        print("WARNING: the 'type' column was missing; industrial/volcano sources were NOT filtered out.")


if __name__ == "__main__":
    main()
