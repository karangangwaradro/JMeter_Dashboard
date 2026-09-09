"""
compare.py — Differential run comparison (Run A vs Run B) endpoints.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query

from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["Run Comparison"])


@router.get("/compare-runs/list")
@router.get("/comparison/runs")
def get_compare_runs_list() -> Dict[str, Any]:
    """Returns available historical runs for comparison dropdown."""
    try:
        from app.services.analytics.comparison import get_available_runs
        runs = get_available_runs()
        return {"success": True, "runs": runs}
    except Exception as e:
        logger.error(f"Error fetching comparison runs: {e}")
        return {"success": False, "runs": [], "message": str(e)}


@router.get("/compare-runs")
@router.get("/comparison/data")
def compare_runs(
    baseline_id: Optional[str] = Query(None),
    current_id: Optional[str] = Query(None),
    run_a: Optional[str] = Query(None),
    run_b: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Computes exact differential scorecard, delta percentiles, and AI comparative insights."""
    b_id = baseline_id or run_a
    c_id = current_id or run_b

    if not b_id or not c_id:
        raise HTTPException(status_code=400, detail="Both baseline_id and current_id are required")

    try:
        from app.services.analytics.comparison import compare_two_runs
        res = compare_two_runs(baseline_id=b_id, current_id=c_id)
        return res
    except Exception as e:
        logger.error(f"Run comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison/draft")
@router.get("/compare-runs/draft")
def get_comparison_draft(current_id: Optional[str] = Query(None), run_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Retrieves saved draft comparison state for a run."""
    c_id = current_id or run_id or ""
    try:
        from app.services.analytics.comparison import load_comparison_draft
        draft = load_comparison_draft(c_id)
        if draft:
            return {"success": True, "draft": draft}
        return {"success": False, "message": "No draft found"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/comparison/draft")
def save_comparison_draft(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Saves comparison draft state into the result JSON."""
    run_id = payload.get("run_id", payload.get("current_id", ""))
    draft_data = payload.get("draft", payload)
    try:
        from app.services.analytics.comparison import save_comparison_draft as save_draft_fn
        success = save_draft_fn(run_id, draft_data)
        return {"success": success}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/comparison/clear-draft")
def clear_comparison_draft(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Clears comparison draft state for a run."""
    run_id = payload.get("run_id", payload.get("current_id", ""))
    try:
        from app.services.analytics.comparison import clear_comparison_draft as clear_draft_fn
        success = clear_draft_fn(run_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "message": str(e)}
