#!/usr/bin/env python3
import json
from pathlib import Path
from python_files.report_generator import generate_report

results_dir = Path("D:/BlazemeterMCPZIP/JmeterAI/Results")
result_files = sorted(results_dir.glob("*_result.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if result_files:
    latest_result = result_files[0]
    print(f"Loading latest result JSON: {latest_result.name}")
    with open(latest_result, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    timestamp = latest_result.name.replace("run_", "").replace("_result.json", "")
    azure_file = results_dir / f"azure_{timestamp}.json"
    azure_data = {}
    if azure_file.exists():
        with open(azure_file, "r", encoding="utf-8") as f:
            azure_data = json.load(f)

    ai_insights = parsed.get("ai_insights", {})
    report_path = results_dir / f"run_{timestamp}_report.html"
    jmx_name = parsed.get("jmx_name", "Scenario")
    users = parsed.get("users", 1)

    import importlib
    import python_files.report_generator as rg_mod
    importlib.reload(rg_mod)
    rg_mod.generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
    print(f"Successfully recompiled report: {report_path.name}")
else:
    print("No result JSON found.")
