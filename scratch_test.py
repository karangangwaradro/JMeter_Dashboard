import json, os, traceback
from pathlib import Path
from python_files.ai_insights import generate_insights, _load_env
import python_files.report_generator as rg_mod

_load_env()
result_path = Path("Results/json/run_20260820_161201_result.json")
with open(result_path, "r", encoding="utf-8") as f:
    parsed = json.load(f)

print("[AI Test] Calling Gemini to generate fresh AI insights...")
summary = parsed.get("summary", {})
labels = parsed.get("labels", {})
ts = parsed.get("time_series", {})
infra = parsed.get("azure_infra", {})
corr = parsed.get("correlation", {})

ai_insights = generate_insights(
    test_name=parsed.get("jmx_name", "Test_Run"),
    summary=summary,
    labels=labels,
    time_series=ts,
    infra=infra,
    correlation=corr
)

print("[AI Test] Generated Source:", ai_insights.get("source"))
parsed["ai_insights"] = ai_insights

with open(result_path, "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2)

report_path = Path("Results/html/run_20260820_161201_report.html")
rg_mod.generate_report(
    parsed=parsed,
    azure_data=infra,
    ai_insights=ai_insights,
    report_path=report_path,
    jmx_name=parsed.get("jmx_name", "Test"),
    users=parsed.get("users", 20)
)
print("[AI Test] Report recompiled with live AI insights successfully!")
