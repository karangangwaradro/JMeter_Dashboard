#!/usr/bin/env python3
import sys
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_files.report_generator import generate_report

results_dir = Path("D:/BlazemeterMCPZIP/PerfPilot/Results")
json_dir    = results_dir / "json"
html_dir    = results_dir / "html"

html_dir.mkdir(parents=True, exist_ok=True)
json_dir.mkdir(parents=True, exist_ok=True)

result_files = set(json_dir.glob("*_result.json"))
result_files.update(results_dir.glob("*_result.json"))
sorted_results = sorted([f for f in result_files if f.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)

if sorted_results:
    latest_result = sorted_results[0]
    print(f"Loading latest result JSON: {latest_result.name}")
    with open(latest_result, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    timestamp = latest_result.name.replace("run_", "").replace("_result.json", "")
    azure_file = json_dir / f"azure_{timestamp}.json"
    if not azure_file.exists():
        azure_file = results_dir / f"azure_{timestamp}.json"

    azure_data = {}
    if azure_file.exists():
        with open(azure_file, "r", encoding="utf-8") as f:
            azure_data = json.load(f)

    ai_insights = parsed.get("ai_insights", {})
    report_path = html_dir / f"run_{timestamp}_report.html"
    jmx_name = parsed.get("jmx_name", "Scenario")
    users = parsed.get("users", 1)

    import importlib
    import python_files.report_generator as rg_mod
    importlib.reload(rg_mod)
    rg_mod.generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
    print(f"Successfully recompiled report: {report_path.name}")
else:
    print("No result JSON found.")
