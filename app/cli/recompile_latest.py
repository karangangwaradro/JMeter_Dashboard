#!/usr/bin/env python3
"""
recompile_latest.py — Recompiles the most recent test run into HTML report.
"""
import sys
import json
from pathlib import Path

# Ensure root directory is on path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.constants import RESULTS_DIR, RESULTS_JSON_DIR, RESULTS_HTML_DIR
from app.services.reporting.engine.generator import generate_report
from app.services.analytics.sla_manager import load_sla_targets
from app.services.ai.insights import generate_insights


def recompile_latest(regen_ai: bool = True):
    RESULTS_HTML_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_DIR.mkdir(parents=True, exist_ok=True)

    result_files = set(RESULTS_JSON_DIR.glob("*_result.json"))
    result_files.update(RESULTS_DIR.glob("*_result.json"))
    sorted_results = sorted([f for f in result_files if f.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)

    if not sorted_results:
        print("No result JSON found.")
        return

    latest_result = sorted_results[0]
    print(f"Loading latest result JSON: {latest_result.name}")
    with open(latest_result, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    timestamp = latest_result.name.replace("run_", "").replace("_result.json", "")
    azure_file = RESULTS_JSON_DIR / f"azure_{timestamp}.json"
    if not azure_file.exists():
        azure_file = RESULTS_DIR / f"azure_{timestamp}.json"

    azure_data = {}
    if azure_file.exists():
        with open(azure_file, "r", encoding="utf-8") as f:
            azure_data = json.load(f)

    # Regenerate fresh AI insights with updated prompt
    if regen_ai:
        try:
            jmx_name = parsed.get("jmx_name", "Scenario")
            actual_users = parsed.get("users", 1)
            sla_targets, default_rt, default_err = load_sla_targets(jmx_name, actual_users=actual_users)
            infra_summary = azure_data.get("infra_summary", {}) if isinstance(azure_data, dict) else {}

            infra_to_pass = azure_data if (isinstance(azure_data, dict) and azure_data) else infra_summary
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
            print("Generating fresh AI insights...", flush=True)
            fresh_ai = generate_insights(
                test_name=jmx_name,
                summary=parsed.get("summary", {}),
                labels=parsed.get("labels", {}),
                time_series=parsed.get("time_series", {}),
                infra=infra_to_pass,
                correlation=parsed.get("correlation", {}),
                sla_targets=sla_targets,
                default_rt=default_rt,
                default_err=default_err,
                error_details=error_details,
                users=actual_users,
                rampup=parsed.get("rampup", 0),
                labels_by_tg=labels_by_tg,
            )
            if fresh_ai and fresh_ai.get("source") != "none":
                parsed["ai_insights"] = fresh_ai
                with open(latest_result, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
                print("Fresh AI insights saved to result JSON.", flush=True)
        except Exception as e:
            print(f"AI insights regeneration warning: {e}", flush=True)

    ai_insights = parsed.get("ai_insights", {})
    report_path = RESULTS_HTML_DIR / f"run_{timestamp}_report.html"
    jmx_name = parsed.get("jmx_name", "Scenario")
    users = parsed.get("users", 1)

    generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
    print(f"Successfully recompiled report: {report_path.name}")


if __name__ == "__main__":
    regen_ai = "--no-ai" not in sys.argv
    recompile_latest(regen_ai=regen_ai)
