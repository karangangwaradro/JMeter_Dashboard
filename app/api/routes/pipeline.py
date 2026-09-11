"""
pipeline.py — Real-time Pipeline Progress Monitoring Endpoints.
Allows frontend and CLI clients to monitor active pipeline stages, timing, diagnostic logs,
and completion status in real-time.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.pipeline.tracker import pipeline_tracker

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Monitoring"])


class InitPipelineRequest(BaseModel):
    run_id: str
    tool: str = "jmeter"
    test_name: str = "Performance Execution"


@router.post("/init")
def init_pipeline(req: InitPipelineRequest) -> Dict[str, Any]:
    """Pre-initializes the live pipeline stepper before or during file upload."""
    pipeline_tracker.start_pipeline(
        run_id=req.run_id,
        tool=req.tool,
        test_name=req.test_name,
        initial_stage="ingestion",
        initial_detail=f"Receiving {req.tool} test artifact and preparing ingestion pipeline...",
    )
    return {"success": True, "run_id": req.run_id}


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
