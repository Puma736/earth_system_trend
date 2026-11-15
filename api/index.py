"""Entrada serverless de Vercel para el backend FastAPI (backend/app/main.py).

El proyecto de Vercel del backend usa la raíz del repo como Root Directory, porque
el backend también lee front/data/bolivia-admin.json. Ver docs/deploy-vercel.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402,F401
