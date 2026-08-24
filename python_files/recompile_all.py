import sys
import json
import importlib
from pathlib import Path

_ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


def run():
    import python_files.report_generator as rg_module
    importlib.reload(rg_module)

    try:
        from python_files.organize_results import organize
        organize()
    except Exception as org_err:
        print(f"[Recompile] Organize warning: {org_err}", flush=True)

    results_dir = _ROOT_DIR / "Results"
    html_dir    = results_dir / "html"
    json_dir    = results_dir / "json"
    jtl_dir     = results_dir / "jtl"

    for d in (html_dir, json_dir, jtl_dir):
        d.mkdir(parents=True, exist_ok=True)

    runs_path   = _ROOT_DIR / "data" / "runs.json"

    runs_data = {"runs": []}
    if runs_path.exists():
        runs_data = json.loads(runs_path.read_text(encoding="utf-8"))

    res_set = set(json_dir.glob("*_result.json"))
    res_set.update(results_dir.glob("*_result.json"))
    result_files = sorted([f for f in res_set if f.is_file()])
    print(f"[Recompile] Found {len(result_files)} result files.", flush=True)

    for res_file in result_files:
        fname = res_file.name
        timestamp = fname[4:-12] if fname.startswith("run_") and fname.endswith("_result.json") else fname.replace("_result.json", "")
        report_path = html_dir / f"run_{timestamp}_report.html"

        print(f"[Recompile] {fname} -> {report_path.name}", flush=True)
        with open(res_file, "r", encoding="utf-8") as f:
            parsed = json.load(f)

        azure_file = json_dir / f"azure_{timestamp}.json"
        if not azure_file.exists():
            azure_file = results_dir / f"azure_{timestamp}.json"
        azure_data = {}
        if azure_file.exists():
            with open(azure_file, "r", encoding="utf-8") as f:
                azure_data = json.load(f)

        ai_insights = parsed.get("ai_insights", {})
        jmx_name    = parsed.get("jmx_name", "Scenario")
        users       = parsed.get("users", 1)

        # Re-parse JTL to get time_series with label_ts_map
        jtl_file = jtl_dir / f"run_{timestamp}.jtl"
        if not jtl_file.exists():
            jtl_file = results_dir / f"run_{timestamp}.jtl"
        if jtl_file.exists():
            try:
                from python_files.jtl_parser import parse_jtl
                re_parsed = parse_jtl(jtl_file)
                ts = re_parsed.get("time_series", {})
                if re_parsed.get("labels"):
                    parsed["labels"] = re_parsed["labels"]
                if ts:
                    parsed["time_series"] = ts
                    print(f"[Recompile]   JTL re-parsed: {len(ts.get('label_ts_map', {}))} transaction series", flush=True)
                if re_parsed.get("summary"):
                    parsed["summary"] = re_parsed["summary"]
                    print(f"[Recompile]   Summary updated: Total Iterations={re_parsed['summary'].get('total_iterations')}, Error Rate={re_parsed['summary'].get('error_rate')}%", flush=True)
            except Exception as e:
                print(f"[Recompile]   JTL re-parse error: {e}", flush=True)

        out_file = rg_module.generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
        print(f"[Recompile]   Done: {report_path.exists()}", flush=True)

        for r_item in runs_data.get("runs", []):
            if r_item.get("id") == f"run_{timestamp}":
                r_item["report_file"] = report_path.name

    runs_path.write_text(json.dumps(runs_data, indent=2), encoding="utf-8")
    print("[Recompile] All reports compiled!", flush=True)


# Allow direct script execution
if __name__ == "__main__":
    run()
