#!/usr/bin/env python3
"""Quick test script to verify the report generator compiles without errors."""
import sys
sys.path.insert(0, r"D:\BlazemeterMCPZIP\JmeterAI")

import json
from pathlib import Path

results_dir = Path(r"D:\BlazemeterMCPZIP\JmeterAI\Results")
result_files = sorted(results_dir.glob("*_result.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if not result_files:
    print("No result JSON files found.")
    sys.exit(1)

latest = result_files[0]
print(f"Loading: {latest.name}")

with open(latest, "r", encoding="utf-8") as f:
    parsed = json.load(f)

timestamp = latest.name.replace("run_", "").replace("_result.json", "")
az_file = results_dir / f"azure_{timestamp}.json"

azure_data = {}
if az_file.exists():
    with open(az_file, "r", encoding="utf-8") as f:
        azure_data = json.load(f)

ai_insights = parsed.get("ai_insights", {})
report_path = results_dir / f"run_{timestamp}_report.html"
jmx_name = parsed.get("jmx_name", "Scenario")
users = parsed.get("users", 1)

try:
    from python_files.report_generator import generate_report
    generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
    print(f"SUCCESS: Report compiled -> {report_path.name}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
