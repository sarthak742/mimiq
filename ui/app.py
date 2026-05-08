# FILE: ui/app.py
"""FastAPI web UI for Mimiq — proxies to cloud_brain and renders reports."""

from __future__ import annotations

import os
from pathlib import Path

import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import CLOUD_BRAIN_PORT
from executor.hitl_overlay import get_overlay_state, set_overlay_decision, HitlDecision
from utils.composer import compose_plan

app = FastAPI(title="Mimiq UI")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/brain/status")
async def brain_status() -> JSONResponse:
    try:
        resp = requests.get(
            f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/health", timeout=2
        )
        return JSONResponse(resp.json())
    except Exception:
        return JSONResponse(
            {
                "status": "offline",
                "active_provider": "AMD — offline",
                "active_model": "unknown",
            }
        )


@app.get("/api/hitl/state")
async def hitl_state() -> JSONResponse:
    return JSONResponse(get_overlay_state())


@app.post("/api/hitl/decide")
async def hitl_decide(request: Request) -> JSONResponse:
    body = await request.json()
    decision_str = str(body.get("decision", "")).upper()
    mapping = {
        "APPROVE": HitlDecision.APPROVE,
        "REJECT": HitlDecision.REJECT,
        "SKIP": HitlDecision.SKIP,
    }
    if decision_str not in mapping:
        return JSONResponse({"error": "Invalid decision"}, status_code=400)
    set_overlay_decision(mapping[decision_str])
    return JSONResponse({"status": "ok", "decision": decision_str})


@app.post("/api/compose")
async def compose(request: Request) -> JSONResponse:
    body = await request.json()
    goal = str(body.get("goal", ""))
    manifest_1 = body.get("manifest_1", {})
    manifest_2 = body.get("manifest_2")
    if not goal or not manifest_1:
        return JSONResponse(
            {"error": "goal and manifest_1 required"}, status_code=400
        )
    final_manifest, gap_report = compose_plan(goal, manifest_1, manifest_2)
    return JSONResponse(
        {"final_manifest": final_manifest, "gap_report": gap_report}
    )


@app.get("/api/report")
async def get_report() -> FileResponse | JSONResponse:
    report_path = Path(os.environ.get("OUTPUT_DIR", "output")) / "report.html"
    if report_path.exists():
        return FileResponse(str(report_path), media_type="text/html")
    return JSONResponse(
        {"error": "No report generated yet"}, status_code=404
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("UI_PORT", "8080")),
    )
