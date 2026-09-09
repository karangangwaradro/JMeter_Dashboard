"""
reports.py — Report catalog, publishing, and static artifact management routes.
"""

from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.constants import RESULTS_HTML_DIR, RESULTS_PUBLISHED_DIR
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["Report Management"])


class PublishReportRequest(BaseModel):
    report_name: str
    html_content: str


@router.get("/reports")
def list_reports() -> Dict[str, Any]:
    """Lists generated HTML reports and published versions."""
    reports: List[Dict[str, Any]] = []

    for d in (RESULTS_HTML_DIR, RESULTS_PUBLISHED_DIR):
        if d.exists():
            for f in sorted(d.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
                is_pub = "published" in f.name.lower() or d == RESULTS_PUBLISHED_DIR
                reports.append({
                    "name": f.name,
                    "filename": f.name,
                    "url": f"/Results/{'Published' if is_pub else 'html'}/{f.name}",
                    "size": f.stat().st_size,
                    "is_published": is_pub,
                    "mtime": f.stat().st_mtime,
                })

    return {"reports": reports}


@router.post("/save-published-report")
def save_published_report(req: PublishReportRequest) -> Dict[str, Any]:
    """Saves a permanent published report with frozen comparisons and disabled editing."""
    try:
        clean_name = Path(req.report_name).name
        if not clean_name.endswith(".html"):
            clean_name += ".html"
        if not clean_name.endswith("_published.html"):
            clean_name = clean_name.replace(".html", "_published.html")

        RESULTS_PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
        target_path = RESULTS_PUBLISHED_DIR / clean_name
        target_path.write_text(req.html_content, encoding="utf-8")

        logger.info(f"Published permanent report: {clean_name}")
        return {
            "success": True,
            "message": "Report published successfully",
            "published_url": f"/Results/Published/{clean_name}",
            "filename": clean_name,
        }
    except Exception as e:
        logger.error(f"Error publishing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
