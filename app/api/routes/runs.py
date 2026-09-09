"""
runs.py — Run history, catalog querying, deletion, and report recompilation endpoints.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.constants import DATA_DIR, RESULTS_DIR, RESULTS_JSON_DIR, RESULTS_HTML_DIR, RESULTS_JTL_DIR
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["Runs & Recompilation"])


class DeleteRunRequest(BaseModel):
    run_id: str


class RecompileRequest(BaseModel):
    run_id: Optional[str] = None
    target: Optional[str] = None
    regen_ai: bool = False


@router.get("/runs")
def list_runs() -> Dict[str, Any]:
    """Lists historical test runs recorded in data/runs.json."""
    runs_file = DATA_DIR / "runs.json"
    if not runs_file.exists():
        return {"runs": []}
    try:
        data = json.loads(runs_file.read_text(encoding="utf-8"))
        runs = data.get("runs", [])
        return {"runs": runs}
    except Exception as e:
        logger.error(f"Error loading runs.json: {e}")
        return {"runs": []}


@router.post("/delete-run")
def delete_run(req: DeleteRunRequest) -> Dict[str, Any]:
    """Deletes a test run and its associated JSON, JTL, and HTML files."""
    run_id = req.run_id
    deleted_files = []

    for d in (RESULTS_JSON_DIR, RESULTS_HTML_DIR, RESULTS_JTL_DIR, RESULTS_DIR):
        for pattern in (f"{run_id}*", f"run_{run_id}*", f"azure_{run_id}*"):
            for p in d.glob(pattern):
                if p.is_file():
                    try:
                        p.unlink()
                        deleted_files.append(p.name)
                    except Exception:
                        pass

    # Remove from runs.json
    runs_file = DATA_DIR / "runs.json"
    if runs_file.exists():
        try:
            catalog = json.loads(runs_file.read_text(encoding="utf-8"))
            catalog["runs"] = [r for r in catalog.get("runs", []) if r.get("id") != run_id and run_id not in r.get("id", "")]
            runs_file.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {"success": True, "message": f"Deleted run {run_id}", "files": deleted_files}


@router.api_route("/recompile-report", methods=["GET", "POST"])
def recompile_report_endpoint(req: Optional[RecompileRequest] = None) -> Dict[str, Any]:
    """Recompiles an HTML report from its result JSON."""
    target_run = req.run_id or req.target if req else ""
    try:
        res_set = set(RESULTS_JSON_DIR.glob("*_result.json"))
        res_set.update(RESULTS_DIR.glob("*_result.json"))
        result_files = sorted([f for f in res_set if f.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        if target_run:
            result_files = [f for f in result_files if target_run in f.name]

        if not result_files:
            raise HTTPException(status_code=404, detail="No result JSON files found")

        recompiled = []
        for rf in result_files[:5]:
            try:
                parsed = json.loads(rf.read_text(encoding="utf-8"))
                run_id = parsed.get("run_id", rf.name.replace("_result.json", ""))
                az_file = RESULTS_JSON_DIR / f"azure_{run_id.replace('run_', '')}.json"
                azure_data = json.loads(az_file.read_text(encoding="utf-8")) if az_file.exists() else {}

                out_html = RESULTS_HTML_DIR / f"{run_id}_report.html"
                from app.services.reporting.engine.generator import generate_report
                generate_report(
                    parsed=parsed,
                    azure_data=azure_data,
                    ai_insights=parsed.get("ai_insights", {}),
                    report_path=out_html,
                    jmx_name=parsed.get("jmx_name", "Scenario"),
                    users=parsed.get("users", 1),
                )
                recompiled.append(out_html.name)
            except Exception as item_err:
                logger.error(f"Recompilation error on {rf.name}: {item_err}")

        return {"success": True, "recompiled_count": len(recompiled), "reports": recompiled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
