# main.py
# FastAPI Application — Entry Point
# Orchestrates the full pipeline (ingest -> parse -> correlate) and exposes REST API endpoints.

import os
from dataclasses import asdict
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import TimelineRequest, TimelineResponse
import ingestor
import parser
import correlator


app = FastAPI(title="Timeline Parser Mark I", version="1.0.0")

# Serves any future CSS/JS assets. check_dir=False so the app doesn't crash
# on startup if the static/ folder doesn't exist yet.
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")


# ── Global Exception Handlers ──────────────────────────────────────────────────
# Ensures every error — expected or not — reaches the browser as clean JSON,
# never a raw Python traceback.

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": f"An unexpected error occurred: {str(exc)}"}
    )


# ── Helper: Duration Calculation ────────────────────────────────────────────────

def _calculate_duration(records: list) -> int:
    """
    Calculates the time span, in seconds, between the first and last record.
    Falls back to 0 if timestamps can't be parsed or fewer than 2 records exist.
    """
    if len(records) < 2:
        return 0

    try:
        first = datetime.strptime(records[0].timestamp, "%b %d %H:%M:%S")
        last = datetime.strptime(records[-1].timestamp, "%b %d %H:%M:%S")
        return int((last - first).total_seconds())
    except (ValueError, TypeError):
        return 0


# ── Helper: Entity Extraction ────────────────────────────────────────────────────

def _extract_entities(records: list) -> List[str]:
    """
    Extracts unique, non-empty user and IP values from the matched records.
    """
    entities = set()
    for record in records:
        if record.user:
            entities.add(record.user)
        if record.ip:
            entities.add(record.ip)
    return sorted(entities)


# ── Endpoint: Health Check ────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "timeline-parser-mark1"}


# ── Endpoint: Serve Web UI ────────────────────────────────────────────────────────

@app.get("/")
def serve_ui():
    index_path = "static/index.html"
    if not os.path.isfile(index_path):
        raise HTTPException(
            status_code=404,
            detail="Web UI not found. static/index.html has not been created yet."
        )
    return FileResponse(index_path)


# ── Endpoint: Timeline ────────────────────────────────────────────────────────────

@app.post("/api/timeline", response_model=TimelineResponse)
def get_timeline(request: TimelineRequest):
    """
    Runs the full pipeline: ingest -> parse -> correlate.
    Returns a structured, chronological timeline based on the given filter.
    """

    # ── Stage 1: Ingest ───────────────────────────────────────────────────────
    try:
        raw_lines = ingestor.ingest(request.log_path)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during ingestion: {str(e)}")

    # ── Stage 2: Parse ────────────────────────────────────────────────────────
    try:
        records = parser.parse(raw_lines)

    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during parsing: {str(e)}")

    # ── Stage 3: Correlate ────────────────────────────────────────────────────
    try:
        matched = correlator.correlate(records, request.filter_key, request.filter_value)

    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during correlation: {str(e)}")

    # ── Stage 4: Build Response ───────────────────────────────────────────────
    try:
        timeline_dicts = [asdict(record) for record in matched]

        return TimelineResponse(
            filter=f"{request.filter_key}={request.filter_value}",
            total_events=len(matched),
            duration_seconds=_calculate_duration(matched),
            entities=_extract_entities(matched),
            timeline=timeline_dicts
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error while building response: {str(e)}")