"""
pipeline.py — Real-time Pipeline Progress Monitoring Endpoints.
Allows frontend and CLI clients to monitor active pipeline stages, timing, diagnostic logs,
and completion status in real-time.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException

from app.services.pipeline.tracker import pipeline_tracker

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Monitoring"])


@router.get("/status")
def get_pipeline_status(run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns real-time execution stage progress, sub-second timing,
    and diagnostic logs for a given run (or the latest active run).
    """
    status = pipeline_tracker.get_status(run_id)
    if not status:
        return {
            "active": False,
            "message": "No active pipeline running",
            "run_id": None,
            "overall_status": "idle",
            "stages": [],
            "logs": [],
        }
    return {
        "active": status["overall_status"] == "running",
        **status,
    }
