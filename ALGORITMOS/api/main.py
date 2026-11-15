"""API ligera FastAPI para sci_lab_math.

Endpoint: POST /api/analyze-region
Body JSON: { "region": "...", "dates": [...], "variables": { "var": [...] } }
o { "region": "...", "data": { "date": [...], "var": [...] } }
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sci_lab_math.interpreter import RegionAnalyzer

app = FastAPI(title="sci_lab_math API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    entity_name: Optional[str] = None
    region: Optional[str] = None
    dates: Optional[List[Any]] = None
    variables: Optional[Dict[str, List[Any]]] = None
    data: Optional[Dict[str, List[Any]]] = None
    date_col: Optional[str] = None
    target_cols: Optional[List[str]] = None
    domain: Optional[str] = "general"
    non_negative: Optional[Any] = False
    forecast_steps: Optional[int] = 12


def _handle(req: AnalyzeRequest):
    payload = {}
    name = req.entity_name or req.region
    if name is not None:
        payload["entity_name"] = name
    if req.variables is not None and req.dates is not None:
        payload["dates"] = req.dates
        payload["variables"] = req.variables
    elif req.data is not None:
        payload["data"] = req.data
    else:
        payload = req.model_dump(exclude_none=True)
    from sci_lab_math.interpreter import DataAnalyzer
    analyzer = DataAnalyzer(payload, entity_name=name, date_col=req.date_col,
                           target_cols=req.target_cols, domain=req.domain or "general",
                           non_negative=req.non_negative or False,
                           forecast_steps=req.forecast_steps or 12)
    return analyzer.analyze()


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return _handle(req)


@app.post("/api/analyze-region")
def analyze_region(req: AnalyzeRequest):
    return _handle(req)


# Servir interfaz web
WEB_DIR = os.path.join(ROOT, "web")
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")