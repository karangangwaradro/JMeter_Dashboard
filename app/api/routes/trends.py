"""
trends.py — Historical multi-release trend analysis endpoints.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import logger

router = APIRouter(prefix="/api/trend", tags=["Historical Trends"])


class TrendCompareRequest(BaseModel):
    selected_releases: list[str]
    item_type_filter: str = "ALL"
    project: str = ""
    user_story: str = ""


class TrendReportRequest(BaseModel):
    trend_data: Dict[str, Any]


@router.get("/hierarchy")
def get_trend_hierarchy() -> Dict[str, Any]:
    """Returns project -> user story -> release hierarchy tree."""
    try:
        from app.services.analytics.trends import get_hierarchy_tree
        tree = get_hierarchy_tree()
        return {"success": True, **tree}
    except Exception as e:
        logger.error(f"Error fetching trend hierarchy: {e}")
        return {"success": False, "message": str(e)}


@router.get("/analysis")
def get_trend_analysis(
    project: str = Query(""),
    user_story: str = Query(""),
    item_type: str = Query("ALL"),
    limit: int = Query(10),
) -> Dict[str, Any]:
    """Computes multi-release KPI trends, heatmaps, and directional observations."""
    try:
        from app.services.analytics.trends import build_trend_analysis
        data = build_trend_analysis(
            project_filter=project,
            user_story_filter=user_story,
            item_type_filter=item_type,
            limit=limit,
        )
        return data
    except Exception as e:
        logger.error(f"Error computing trend analysis: {e}")
        return {"success": False, "message": str(e)}


@router.post("/compare")
def compare_trend_releases(req: TrendCompareRequest) -> Dict[str, Any]:
    """Generates directional comparison across selected releases."""
    try:
        from app.services.analytics.trends import build_trend_analysis
        data = build_trend_analysis(
            project_filter=req.project,
            user_story_filter=req.user_story,
            item_type_filter=req.item_type_filter,
            limit=len(req.selected_releases),
        )
        return data
    except Exception as e:
        logger.error(f"Trend compare error: {e}")
        return {"success": False, "message": str(e)}


@router.post("/generate-report")
def generate_trend_report(req: TrendReportRequest) -> Dict[str, Any]:
    """Compiles a standalone Historical Trend Dashboard HTML document."""
    try:
        from app.services.analytics.trends import generate_trend_dashboard_html
        html = generate_trend_dashboard_html(req.trend_data)
        return {"success": True, "html": html}
    except Exception as e:
        logger.error(f"Failed to generate trend HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))
