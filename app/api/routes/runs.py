"""
runs.py — Run history, catalog querying, deletion, and report recompilation endpoints.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.constants import DATA_DIR, RESULTS_DIR, RESULTS_JSON_DIR, RESULTS_HTML_DIR, RESULTS_JTL_DIR, STORAGE_NORMALIZED_DIR
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["Runs & Recompilation"])


class DeleteRunRequest(BaseModel):
    run_id: str


class RecompileRequest(BaseModel):
    run_id: Optional[str] = None
    target: Optional[str] = None
    regenerate_ai: Optional[bool] = False
    regen_ai: Optional[bool] = False


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
    """Recompiles an HTML report from its result JSON, optionally regenerating AI insights via LLM cascade."""
    target_run = req.run_id or req.target if req else ""
    should_regen_ai = bool(req and (req.regenerate_ai or req.regen_ai))

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
                jmx_name = parsed.get("jmx_name", "Scenario")
                users = parsed.get("users", 1)
                rampup = parsed.get("rampup", 0)

                az_file = RESULTS_JSON_DIR / f"azure_{run_id.replace('run_', '')}.json"
                azure_data = json.loads(az_file.read_text(encoding="utf-8")) if az_file.exists() else {}

                # Regenerate AI Insights if requested
                if should_regen_ai:
                    from app.services.ai.insights import generate_insights
                    from app.services.analytics.sla_manager import load_sla_targets

                    print(f"\n[RECOMPILE] Regenerating AI performance insights for '{run_id}' (JMX={jmx_name}, Users={users})...", flush=True)
                    sla_targets, default_rt, default_err = load_sla_targets(jmx_name, actual_users=users)
                    error_details = (
                        parsed.get("error_details")
                        or parsed.get("summary", {}).get("errors_breakdown")
                        or {}
                    )
                    labels_by_tg = (
                        parsed.get("labels_by_tg")
                        or parsed.get("summary", {}).get("transactions_by_thread_group")
                        or {}
                    )
                    fresh_ai = generate_insights(
                        test_name=jmx_name,
                        summary=parsed.get("summary", {}),
                        labels=parsed.get("labels", {}),
                        time_series=parsed.get("time_series", {}),
                        infra=azure_data,
                        correlation=parsed.get("correlation", {}),
                        sla_targets=sla_targets,
                        default_rt=default_rt,
                        default_err=default_err,
                        error_details=error_details,
                        users=users,
                        rampup=int(rampup if str(rampup).isdigit() else 0),
                        labels_by_tg=labels_by_tg,
                    )

                    if fresh_ai:
                        parsed["ai_insights"] = fresh_ai
                        rf.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
                        print(f"[RECOMPILE] Fresh AI Insights saved to {rf.name}", flush=True)

                        # Dual-write update to normalized schema metadata if exists
                        meta_path = STORAGE_NORMALIZED_DIR / f"{run_id}_metadata.json"
                        if meta_path.exists():
                            try:
                                m = json.loads(meta_path.read_text(encoding="utf-8"))
                                m["has_ai_insights"] = True
                                meta_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
                            except Exception:
                                pass

                        # Update data/runs.json catalog
                        runs_file = DATA_DIR / "runs.json"
                        if runs_file.exists():
                            try:
                                cat = json.loads(runs_file.read_text(encoding="utf-8"))
                                for r in cat.get("runs", []):
                                    if r.get("id") == run_id:
                                        r["has_ai_insights"] = True
                                runs_file.write_text(json.dumps(cat, indent=2), encoding="utf-8")
                            except Exception:
                                pass

                out_html = RESULTS_HTML_DIR / f"{run_id}_report.html"
                from app.services.reporting.engine.generator import generate_report
                generate_report(
                    parsed=parsed,
                    azure_data=azure_data,
                    ai_insights=parsed.get("ai_insights", {}),
                    report_path=out_html,
                    jmx_name=jmx_name,
                    users=users,
                )
                recompiled.append(out_html.name)
            except Exception as item_err:
                logger.error(f"Recompilation error on {rf.name}: {item_err}")

        action_msg = "with fresh AI insights" if should_regen_ai else "from cached metrics"
        return {
            "success": True,
            "recompiled_count": len(recompiled),
            "reports": recompiled,
            "message": f"Successfully recompiled {len(recompiled)} report(s) {action_msg}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
