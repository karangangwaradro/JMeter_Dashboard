#!/usr/bin/env python3
"""
recompile_all.py — Batch recompiles all historical test runs into updated HTML reports.
"""
import sys
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.constants import RESULTS_DIR, RESULTS_JSON_DIR, RESULTS_HTML_DIR, RESULTS_JTL_DIR, DATA_DIR
from app.cli.organize_results import organize
from app.services.reporting.engine.generator import generate_report
from app.services.analytics.sla_manager import load_sla_targets
from app.services.ai.insights import generate_insights


def recompile_all(regen_ai: bool = False):
    try:
        organize()
    except Exception as org_err:
        print(f"[Recompile] Organize warning: {org_err}", flush=True)

    for d in (RESULTS_HTML_DIR, RESULTS_JSON_DIR, RESULTS_JTL_DIR):
        d.mkdir(parents=True, exist_ok=True)

    runs_path = DATA_DIR / "runs.json"
    runs_data = {"runs": []}
    if runs_path.exists():
        runs_data = json.loads(runs_path.read_text(encoding="utf-8"))

    res_set = set(RESULTS_JSON_DIR.glob("*_result.json"))
    res_set.update(RESULTS_DIR.glob("*_result.json"))
    result_files = sorted([f for f in res_set if f.is_file()])
    print(f"[Recompile] Found {len(result_files)} result files. (Regenerate AI: {regen_ai})", flush=True)

    for res_file in result_files:
        fname = res_file.name
        timestamp = fname[4:-12] if fname.startswith("run_") and fname.endswith("_result.json") else fname.replace("_result.json", "")
        report_path = RESULTS_HTML_DIR / f"run_{timestamp}_report.html"

        print(f"[Recompile] {fname} -> {report_path.name}", flush=True)
        with open(res_file, "r", encoding="utf-8") as f:
            parsed = json.load(f)

        azure_file = RESULTS_JSON_DIR / f"azure_{timestamp}.json"
        if not azure_file.exists():
            azure_file = RESULTS_DIR / f"azure_{timestamp}.json"
        azure_data = {}
        if azure_file.exists():
            with open(azure_file, "r", encoding="utf-8") as f:
                azure_data = json.load(f)

        ai_insights = parsed.get("ai_insights", {})
        jmx_name = parsed.get("jmx_name", "Scenario")
        users = parsed.get("users", 1)

        # Re-parse JTL to refresh time_series with label_ts_map if available
        jtl_file = RESULTS_JTL_DIR / f"run_{timestamp}.jtl"
        if not jtl_file.exists():
            jtl_file = RESULTS_DIR / f"run_{timestamp}.jtl"
        if jtl_file.exists():
            try:
                from app.integrations.jmeter.jtl_parser import parse_jtl
                re_parsed = parse_jtl(jtl_file)
                ts = re_parsed.get("time_series", {})
                if re_parsed.get("labels"):
                    parsed["labels"] = re_parsed["labels"]
                if re_parsed.get("labels_by_tg"):
                    parsed["labels_by_tg"] = re_parsed["labels_by_tg"]
                if re_parsed.get("error_details") is not None:
                    parsed["error_details"] = re_parsed["error_details"]
                if ts:
                    parsed["time_series"] = ts
                if re_parsed.get("summary"):
                    parsed["summary"] = re_parsed["summary"]
            except Exception as e:
                print(f"[Recompile]   JTL re-parse error: {e}", flush=True)

        # Regenerate live AI insights if requested
        if regen_ai:
            try:
                sla_targets, default_rt, default_err = load_sla_targets(jmx_name, actual_users=users)
                infra_summary = azure_data.get("infra_summary", {}) if isinstance(azure_data, dict) else {}
                infra_to_pass = azure_data if (isinstance(azure_data, dict) and azure_data) else infra_summary
                print(f"[Recompile]   Regenerating AI insights...", flush=True)
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
                    error_details=parsed.get("error_details", {}),
                    users=users,
                    rampup=parsed.get("rampup", 0),
                )
                if fresh_ai and fresh_ai.get("source") != "none":
                    parsed["ai_insights"] = fresh_ai
                    ai_insights = fresh_ai
                    print(f"[Recompile]   AI insights updated.", flush=True)
            except Exception as ai_err:
                print(f"[Recompile]   AI regeneration error: {ai_err}", flush=True)

        # Persist cleaned/updated parsed result back to JSON
        res_file.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

        generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
        root_report = RESULTS_DIR / f"run_{timestamp}_report.html"
        if root_report != report_path:
            import shutil
            try:
                shutil.copy2(report_path, root_report)
            except Exception:
                pass
        print(f"[Recompile]   Done: {report_path.exists()}", flush=True)

        for r_item in runs_data.get("runs", []):
            if r_item.get("id") == f"run_{timestamp}":
                r_item["report_file"] = report_path.name
                if ai_insights and ai_insights.get("source") != "none":
                    r_item["has_ai_insights"] = True

    runs_path.write_text(json.dumps(runs_data, indent=2), encoding="utf-8")
    print("[Recompile] All reports compiled!", flush=True)


if __name__ == "__main__":
    regen_flag = "--ai" in sys.argv
    recompile_all(regen_ai=regen_flag)
