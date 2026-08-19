#!/usr/bin/env python3
"""
web_server.py — Local Web Server for JmeterAI.

Serves the web/ SPA dashboard and exposes REST API endpoints:
  - GET  /api/status            → System health (JMeter, Azure, AI status)
  - GET  /api/tests             → List JMX test scripts in Tests/
  - GET  /api/jmx-config        → Read JMX configuration (users, duration, rampup)
  - POST /api/save-config       → Update JMX load parameters directly in XML
  - POST /api/run-test          → Launch local JMeter execution
  - GET  /api/jmeter-progress   → Poll active test run progress & stats
  - POST /api/stop-test         → Stop running JMeter process
  - GET  /api/reports           → List generated HTML reports
  - GET  /api/runs              → List past run history stored in data/runs.json
  - POST /api/upload-jmx        → Upload JMX / CSV files
  - POST /api/delete-jmx        → Delete test asset
  - POST /api/azure-config      → Update Azure Monitor configuration
"""

import os
import sys
import json
import re
import urllib.parse
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ── Paths ─────────────────────────────────────────────────────────────────────
_SERVICES_DIR  = Path(__file__).parent.resolve()
_ROOT_DIR      = _SERVICES_DIR.parent.resolve()
_WEB_DIR       = _ROOT_DIR / "web"
_TESTS_DIR     = _ROOT_DIR / "Tests"
_RESULTS_DIR   = _ROOT_DIR / "Results"
_RESULTS_HTML_DIR = _RESULTS_DIR / "html"
_RESULTS_JSON_DIR = _RESULTS_DIR / "json"
_RESULTS_JTL_DIR  = _RESULTS_DIR / "jtl"
_PUBLISHED_DIR = _RESULTS_DIR / "Published"
_DATA_DIR      = _ROOT_DIR / "data"

for d in (_RESULTS_HTML_DIR, _RESULTS_JSON_DIR, _RESULTS_JTL_DIR, _PUBLISHED_DIR):
    d.mkdir(parents=True, exist_ok=True)

if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

# Ensure required folders exist
for d in (_WEB_DIR, _TESTS_DIR, _RESULTS_DIR, _DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _load_env():
    env_path = _ROOT_DIR / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key and val:
                    os.environ[key] = val


_load_env()

try:
    from python_files.organize_results import organize
    organize()
except Exception:
    pass

# Auto-recompile all HTML reports with updated template on server start
try:
    from python_files.recompile_all import run as _recompile_run
    _recompile_run()
except Exception as _re_err:
    print(f"[Init] Report recompilation warning: {_re_err}", flush=True)


class PlatformRequestHandler(SimpleHTTPRequestHandler):
    """Serves static frontend files (web/) and dynamic /api/* endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_WEB_DIR), **kwargs)

    def log_message(self, fmt, *args):
        print(f"  [{self.command}] {self.path}", flush=True)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors()
        self.end_headers()

    def _add_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, abs_path: Path):
        if not abs_path.exists() or not abs_path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ext = abs_path.suffix.lower()
        mime = {".html": "text/html", ".json": "application/json",
                ".css": "text/css",   ".js":   "application/javascript"}.get(ext, "application/octet-stream")
        data = abs_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ─────────────────────────────────────────────────────────────────────────
    # GET Handlers
    # ─────────────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path

        # Serve files outside web/ (/Results/*)
        if path.startswith("/Results/"):
            rel_file = path.replace("/Results/", "")
            target_path = _RESULTS_DIR / rel_file
            if not target_path.exists() or not target_path.is_file():
                ext = target_path.suffix.lower()
                if ext == ".html":
                    alt = _RESULTS_HTML_DIR / target_path.name
                    if not alt.exists():
                        alt = _PUBLISHED_DIR / target_path.name
                elif ext == ".json":
                    alt = _RESULTS_JSON_DIR / target_path.name
                elif ext == ".jtl":
                    alt = _RESULTS_JTL_DIR / target_path.name
                else:
                    alt = target_path
                if alt.exists():
                    target_path = alt
            self._serve_file(target_path)
            return

        # ── /api/status ──
        if path == "/api/status":
            _load_env()
            from python_files.run_local_jmeter import check_jmeter
            jmeter_info = check_jmeter()
            azure_configured = bool(os.environ.get("AZURE_RESOURCE_IDS", "").strip())
            gemini_configured = bool(os.environ.get("GEMINI_API_KEY", "").strip())
            github_configured = bool(os.environ.get("GITHUB_TOKEN", "").strip())

            self._send_json({
                "jmeter": jmeter_info,
                "azure_configured": azure_configured,
                "gemini_configured": gemini_configured,
                "github_configured": github_configured,
                "ai_configured": gemini_configured or github_configured,
                "ai_mode": "Gemini 2.0 Ready" if gemini_configured else ("GitHub AI (GPT-4o) Ready" if github_configured else "Rule-based Fallback Mode"),
                "jmeter_home": os.environ.get("JMETER_HOME", "")
            })
            return

        # ── /api/tests ──
        if path == "/api/tests":
            allowed_exts = {".jmx", ".csv", ".txt", ".dat"}
            files = sorted([f.name for f in _TESTS_DIR.iterdir() if f.is_file() and f.suffix.lower() in allowed_exts]) if _TESTS_DIR.exists() else []
            self._send_json({"tests": files})
            return

        # ── /api/jmx-config ──
        if path == "/api/jmx-config":
            query = urllib.parse.parse_qs(parsed.query)
            jmx_name = query.get("jmx", [""])[0]
            if not jmx_name:
                self._send_json({"success": False, "message": "jmx parameter required"}, 400)
                return
            jmx_path = _TESTS_DIR / jmx_name
            if not jmx_path.exists():
                self._send_json({"success": False, "message": f"File '{jmx_name}' not found"}, 404)
                return
            from python_files.jmx_editor import read_jmx_config
            cfg = read_jmx_config(jmx_path)
            self._send_json({"success": True, "config": cfg})
            return

        # ── /api/jmeter-progress ──
        if path == "/api/jmeter-progress":
            from python_files.run_local_jmeter import LIVE_STATE
            now = time.time()
            active_start = LIVE_STATE.get("start_time", 0)
            calc_elapsed = int(now - active_start) if (LIVE_STATE.get("active") and active_start > 0) else 0

            self._send_json({
                "running": LIVE_STATE.get("active", False),
                "done": LIVE_STATE.get("done", False),
                "jmx_name": LIVE_STATE.get("jmx_name", ""),
                "jtl_file": LIVE_STATE.get("jtl_file", ""),
                "elapsed_sec": calc_elapsed,
                "elapsed_str": f"{calc_elapsed // 60}m {calc_elapsed % 60}s",
                "live_stats": LIVE_STATE.get("live_stats", {}),
                "failed_requests": LIVE_STATE.get("failed_requests", {}),
                "error": LIVE_STATE.get("error")
            })
            return

        # ── /api/reports ──
        if path == "/api/reports":
            draft_reports = []
            published_reports = []

            # Draft reports in Results/html/ (and fallback Results/)
            report_files = set()
            if _RESULTS_HTML_DIR.exists():
                report_files.update([f for f in _RESULTS_HTML_DIR.glob("*.html") if f.is_file()])
            if _RESULTS_DIR.exists():
                report_files.update([f for f in _RESULTS_DIR.glob("*.html") if f.is_file()])

            for f in sorted(list(report_files), key=lambda x: x.stat().st_mtime, reverse=True):
                draft_reports.append({
                    "name": f.name,
                    "created_at": f.stat().st_mtime,
                    "size": f.stat().st_size,
                    "url": f"/Results/html/{f.name}"
                })

            # Published reports in Results/Published/
            if _PUBLISHED_DIR.exists():
                for f in sorted([f for f in _PUBLISHED_DIR.glob("*.html") if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True):
                    published_reports.append({
                        "name": f.name,
                        "created_at": f.stat().st_mtime,
                        "size": f.stat().st_size,
                        "url": f"/Results/Published/{f.name}"
                    })

            self._send_json({
                "reports": draft_reports,
                "draft_reports": draft_reports,
                "published_reports": published_reports
            })
            return

        # ── /api/recompile-report ──
        if path == "/api/recompile-report":
            try:
                query = urllib.parse.parse_qs(parsed.query)
                target_run = query.get("run_id", [""])[0].strip()

                res_set = set(_RESULTS_JSON_DIR.glob("*_result.json"))
                res_set.update(_RESULTS_DIR.glob("*_result.json"))
                result_files = sorted([f for f in res_set if f.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
                if target_run:
                    result_files = [f for f in result_files if target_run in f.name]

                if not result_files:
                    self._send_json({"success": False, "message": f"No result JSON files found for target '{target_run or 'all'}'"}, 404)
                    return

                import importlib
                import python_files.apdex_calculator as ap_module
                import python_files.report_generator as rg_module
                importlib.reload(ap_module)
                importlib.reload(rg_module)

                compiled_count = 0
                runs_path = _DATA_DIR / "runs.json"
                r_data = json.loads(runs_path.read_text(encoding="utf-8")) if runs_path.exists() else {"runs": []}

                for target_file in result_files:
                    with open(target_file, "r", encoding="utf-8") as f:
                        parsed_res = json.load(f)

                    timestamp = target_file.name.replace("run_", "").replace("_result.json", "")
                    azure_file = _RESULTS_JSON_DIR / f"azure_{timestamp}.json"
                    if not azure_file.exists():
                        azure_file = _RESULTS_DIR / f"azure_{timestamp}.json"
                    azure_data = {}
                    if azure_file.exists():
                        with open(azure_file, "r", encoding="utf-8") as f:
                            azure_data = json.load(f)

                    ai_insights = parsed_res.get("ai_insights", {})
                    report_path = _RESULTS_HTML_DIR / f"run_{timestamp}_report.html"
                    jmx_name = parsed_res.get("jmx_name", "Scenario")
                    users = parsed_res.get("users", 1)

                    jtl_file = _RESULTS_JTL_DIR / f"run_{timestamp}.jtl"
                    if not jtl_file.exists():
                        jtl_file = _RESULTS_DIR / f"run_{timestamp}.jtl"
                    if jtl_file.exists():
                        try:
                            from python_files.run_local_jmeter import parse_jtl
                            re_p = parse_jtl(jtl_file)
                            if re_p.get("labels"):
                                parsed_res["labels"] = re_p["labels"]
                            if re_p.get("summary"):
                                parsed_res["summary"] = re_p["summary"]
                            if re_p.get("time_series"):
                                parsed_res["time_series"] = re_p["time_series"]
                        except Exception as e:
                            print(f"[Recompile] Error parsing JTL: {e}")

                    rg_module.generate_report(parsed_res, azure_data, ai_insights, report_path, jmx_name, users)
                    compiled_count += 1

                    for r_item in r_data.get("runs", []):
                        if r_item.get("id") == f"run_{timestamp}":
                            r_item["report_file"] = report_path.name

                runs_path.write_text(json.dumps(r_data, indent=2), encoding="utf-8")
                self._send_json({"success": True, "message": f"Successfully recompiled {compiled_count} reports with multi-tab layout!"})
            except Exception as re_err:
                self._send_json({"success": False, "message": f"Failed to recompile reports: {re_err}"}, 500)
            return

        # ── /api/sla ──
        if path == "/api/sla":
            query = urllib.parse.parse_qs(parsed.query)
            jmx_name = query.get("jmx", [""])[0]
            from python_files.sla_manager import load_sla_targets, parse_jmx_hierarchy, save_sla_targets, get_sla_file_path
            
            targets, default_rt, default_err = load_sla_targets(jmx_name)
            paired_path = get_sla_file_path(jmx_name)
            
            identifications = []
            identifications.append({
                "label": "default", "rt": default_rt, "err": default_err, "is_critical": 0,
                "status": "Global Default", "defined": True
            })
            
            if jmx_name:
                jmx_path = _TESTS_DIR / jmx_name
                tc_list, tc_samplers = parse_jmx_hierarchy(jmx_path)
                for tc in tc_list:
                    if tc in targets:
                        is_crit = 1 if targets[tc].get("is_critical") in (1, True, "1", "true") else 0
                        identifications.append({
                            "label": tc, "rt": targets[tc]["rt"], "err": targets[tc]["err"], "is_critical": is_crit,
                            "status": "Explicitly Defined", "defined": True
                        })
                    else:
                        identifications.append({
                            "label": tc, "rt": default_rt, "err": default_err, "is_critical": 0,
                            "status": "Auto-Extracted from JMX", "defined": False
                        })
                
                # Auto-create paired CSV if missing
                clean_name = Path(jmx_name).stem
                expected_csv = _TESTS_DIR / f"{clean_name}_sla.csv"
                if not expected_csv.exists() and tc_list:
                    slas_to_save = [{"label": item["label"], "rt": item["rt"], "err": item["err"], "is_critical": item["is_critical"]} for item in identifications]
                    save_sla_targets(slas_to_save, jmx_name)
            else:
                for lbl, tdata in targets.items():
                    is_crit = 1 if tdata.get("is_critical") in (1, True, "1", "true") else 0
                    identifications.append({
                        "label": lbl, "rt": tdata["rt"], "err": tdata["err"], "is_critical": is_crit,
                        "status": "Explicitly Defined", "defined": True
                    })

            self._send_json({"success": True, "identifications": identifications, "targets": targets})
            return

        # ── /api/runs ──
        if path == "/api/runs":
            runs_path = _DATA_DIR / "runs.json"
            runs = []
            if runs_path.exists():
                try:
                    runs = json.loads(runs_path.read_text(encoding="utf-8")).get("runs", [])
                except Exception:
                    runs = []
            self._send_json({"runs": runs})
            return

        # Static file fallback
        super().do_GET()

    # ─────────────────────────────────────────────────────────────────────────
    # POST Handlers
    # ─────────────────────────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path

        # Multipart File Upload
        if path == "/api/upload-jmx":
            self._handle_file_upload()
            return

        # Parse JSON body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {}

        # ── /api/save-published-report ──
        if path == "/api/save-published-report":
            report_name = body.get("report_name", "")
            html_content = body.get("html_content", "")
            if not report_name or not html_content:
                self._send_json({"success": False, "message": "report_name and html_content are required"}, 400)
                return
            try:
                # Ensure filename is safe and ends with .html
                report_name = "".join(c for c in report_name if c.isalnum() or c in " ._-")
                if not report_name.endswith(".html"):
                    report_name += ".html"
                
                # Ensure published directory exists
                _PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
                
                out_path = _PUBLISHED_DIR / report_name
                out_path.write_text(html_content, encoding="utf-8")
                
                self._send_json({
                    "success": True, 
                    "message": "Report published successfully.",
                    "file": report_name,
                    "url": f"/Results/Published/{report_name}"
                })
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # ── /api/save-config ──
        if path == "/api/save-config":
            jmx_name = body.get("jmx", "")
            thread_groups = body.get("thread_groups", [])
            
            # Legacy support: if old 'tests' format is sent
            if not jmx_name and body.get("tests"):
                tests = body.get("tests", [])
                if tests:
                    jmx_name = tests[0].get("jmx", "")
                    thread_groups = [{
                        "name": "__all__",
                        "users": int(t.get("users", 1)),
                        "duration": t.get("duration", "0"),
                        "rampup": t.get("rampup", "0"),
                        "iterations": int(t.get("iterations", 1))
                    } for t in tests]
            
            if not jmx_name:
                self._send_json({"success": False, "message": "jmx name is required"}, 400)
                return
            
            jmx_path = _TESTS_DIR / jmx_name
            if not jmx_path.exists():
                self._send_json({"success": False, "message": f"JMX '{jmx_name}' not found"}, 404)
                return
            
            from python_files.jmx_editor import update_jmx_thread_groups
            if thread_groups:
                success = update_jmx_thread_groups(jmx_path, thread_groups)
                if success:
                    self._send_json({"success": True, "message": f"Updated {len(thread_groups)} thread group(s) in {jmx_name}."})
                else:
                    self._send_json({"success": False, "message": "No changes were applied. Check thread group names."}, 400)
            else:
                self._send_json({"success": False, "message": "thread_groups array required"}, 400)
            return

        # ── /api/run-test ──
        if path == "/api/run-test":
            jmx_name = body.get("jmx", "")
            thread_groups = body.get("thread_groups", [])
            
            # Legacy support: if old 'tests' format is sent
            if not jmx_name and body.get("tests"):
                tests = body.get("tests", [])
                if tests:
                    jmx_name = tests[0].get("jmx", "")
                    thread_groups = [{
                        "name": "__all__",
                        "users": int(t.get("users", 1)),
                        "duration": t.get("duration", "0"),
                        "rampup": t.get("rampup", "0"),
                        "iterations": int(t.get("iterations", 1))
                    } for t in tests]
            
            if not jmx_name:
                self._send_json({"success": False, "message": "jmx name is required"}, 400)
                return

            # Check if already running
            from python_files.run_local_jmeter import LIVE_STATE, run_local_jmeter
            if LIVE_STATE.get("active"):
                self._send_json({"success": False, "message": f"A test is already running ({LIVE_STATE.get('jmx_name')})"}, 409)
                return

            # Launch in background thread
            def _run_bg():
                run_local_jmeter(jmx_name=jmx_name, thread_groups=thread_groups)

            t = threading.Thread(target=_run_bg, daemon=True)
            t.start()
            
            tg_count = len(thread_groups) if thread_groups else 0
            self._send_json({
                "success": True,
                "message": f"Started test '{jmx_name}' with {tg_count} thread group(s) in background.",
                "jmx_name": jmx_name
            })
            return

        # ── /api/stop-test ──
        if path == "/api/stop-test":
            from python_files.run_local_jmeter import LIVE_STATE
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/IM", "java.exe", "/T"], capture_output=True, text=True)
                else:
                    subprocess.run(["pkill", "-f", "jmeter"], capture_output=True, text=True)

                LIVE_STATE["active"] = False
                LIVE_STATE["done"] = False
                self._send_json({"success": True, "message": "Stopped running JMeter processes."})
            except Exception as e:
                self._send_json({"success": False, "message": f"Failed to stop process: {e}"}, 500)
            return

        # ── /api/delete-run ──
        if path == "/api/delete-run":
            run_id = body.get("run_id", "")
            if not run_id:
                self._send_json({"success": False, "message": "run_id is required"}, 400)
                return
            
            try:
                deleted_files = []
                if _RESULTS_DIR.exists():
                    for f in _RESULTS_DIR.iterdir():
                        if not f.is_file(): continue
                        if run_id in f.name:
                            try:
                                f.unlink()
                                deleted_files.append(f.name)
                            except Exception as e:
                                print(f"Error deleting {f.name}: {e}")

                runs_path = _DATA_DIR / "runs.json"
                if runs_path.exists():
                    try:
                        runs_data = json.loads(runs_path.read_text(encoding="utf-8"))
                        original_len = len(runs_data.get("runs", []))
                        runs_data["runs"] = [r for r in runs_data.get("runs", []) if r.get("id") != run_id]
                        if len(runs_data["runs"]) < original_len:
                            runs_path.write_text(json.dumps(runs_data, indent=2), encoding="utf-8")
                            deleted_files.append("Entry removed from runs.json")
                    except Exception as e:
                        print(f"Error updating runs.json: {e}")

                self._send_json({
                    "success": True, 
                    "message": f"Deleted {len(deleted_files)} files associated with {run_id}."
                })
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # ── /api/sla ──
        if path == "/api/sla":
            slas_list = body.get("slas", [])
            jmx_name = body.get("jmx", "")
            if not slas_list:
                self._send_json({"success": False, "message": "slas array is required"}, 400)
                return
            try:
                from python_files.sla_manager import save_sla_targets, load_sla_targets
                existing_targets, _, _ = load_sla_targets(jmx_name)
                for item in slas_list:
                    lbl = item.get("label", "").strip()
                    if lbl in existing_targets:
                        ex = existing_targets[lbl]
                        item["minor_pct"] = ex.get("minor_pct", 100.0)
                        item["mod_pct"] = ex.get("mod_pct", 200.0)
                        item["crit_pct"] = ex.get("crit_pct", 300.0)
                saved_path = save_sla_targets(slas_list, jmx_name)
                self._send_json({"success": True, "message": f"Saved SLA targets to {saved_path}"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # ── /api/delete-jmx ──
        if path == "/api/delete-jmx":
            jmx_name = body.get("jmx", "")
            if not jmx_name:
                self._send_json({"success": False, "message": "jmx parameter required"}, 400)
                return
            target = _TESTS_DIR / jmx_name
            if target.exists():
                target.unlink()
                self._send_json({"success": True, "message": f"Deleted '{jmx_name}'"})
            else:
                self._send_json({"success": False, "message": "File not found"}, 404)
            return

        # ── /api/delete-run ──
        if path == "/api/delete-run":
            run_id = body.get("run_id", "")
            if not run_id:
                self._send_json({"success": False, "message": "run_id parameter required"}, 400)
                return
            
            deleted_files = []
            results_dir = _RESULTS_DIR
            
            # Find and delete all related files matching run_id timestamp / pattern
            # 1. Direct timestamp string matching (e.g. 20260803_195051)
            clean_ts = run_id.replace("run_", "").replace("azure_", "")
            
            if results_dir.exists():
                for f in results_dir.iterdir():
                    if f.is_file() and clean_ts in f.name:
                        try:
                            f.unlink()
                            deleted_files.append(f.name)
                        except Exception as e:
                            print(f"[Delete] Failed to delete file {f.name}: {e}", flush=True)

            # 2. Update runs.json
            runs_path = _DATA_DIR / "runs.json"
            if runs_path.exists():
                try:
                    runs_data = json.loads(runs_path.read_text(encoding="utf-8"))
                    runs_list = runs_data.get("runs", [])
                    new_runs = [r for r in runs_list if r.get("id") != run_id and clean_ts not in str(r.get("id"))]
                    runs_data["runs"] = new_runs
                    runs_path.write_text(json.dumps(runs_data, indent=2), encoding="utf-8")
                except Exception as e:
                    print(f"[Delete] Error updating runs.json: {e}", flush=True)

            self._send_json({
                "success": True,
                "message": f"Successfully deleted report {run_id} and {len(deleted_files)} related file(s).",
                "deleted_files": deleted_files
            })
            return

        # ── /api/save-published-report ──
        if path == "/api/save-published-report":
            report_name = body.get("report_name", "")
            content = body.get("html_content", "")
            if not report_name or not content:
                self._send_json({"success": False, "message": "report_name and html_content required"}, 400)
                return

            clean_filename = Path(report_name).name
            if not clean_filename.endswith(".html"):
                clean_filename += ".html"

            dest_path = _PUBLISHED_DIR / clean_filename
            try:
                dest_path.write_text(content, encoding="utf-8")
                self._send_json({
                    "success": True,
                    "message": f"Report successfully published to Results/Published/{clean_filename}",
                    "file": clean_filename,
                    "url": f"/Results/Published/{clean_filename}"
                })
            except Exception as e:
                self._send_json({"success": False, "message": f"Failed to save report: {e}"}, 500)
            return

        # ── /api/azure-config ──
        if path == "/api/azure-config":
            resource_ids = body.get("resource_ids", "")
            env_path = _ROOT_DIR / "config" / ".env"
            
            # Read existing lines or create
            lines = []
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines()

            updated = False
            new_lines = []
            for line in lines:
                if line.startswith("AZURE_RESOURCE_IDS="):
                    new_lines.append(f"AZURE_RESOURCE_IDS={resource_ids}")
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                new_lines.append(f"AZURE_RESOURCE_IDS={resource_ids}")

            env_path.write_text("\n".join(new_lines), encoding="utf-8")
            os.environ["AZURE_RESOURCE_IDS"] = resource_ids
            self._send_json({"success": True, "message": "Azure Monitor configuration saved."})
            return

        self._send_json({"success": False, "message": f"Unknown endpoint: {path}"}, 404)

    # ─────────────────────────────────────────────────────────────────────────
    # File Upload Handler
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_file_upload(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json({"success": False, "message": "Must be multipart/form-data"}, 400)
                return

            # Extract boundary robustly
            boundary_match = re.search(r'boundary=(?:["\']?)([^"\';\s]+)', content_type)
            if not boundary_match:
                self._send_json({"success": False, "message": "Missing boundary in Content-Type"}, 400)
                return

            boundary = boundary_match.group(1).encode("utf-8")
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)

            parts = raw_body.split(b"--" + boundary)
            filename, saved = "", False

            for part in parts:
                if b"filename=" not in part:
                    continue
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    continue
                headers_raw = part[:header_end].decode("utf-8", errors="ignore")
                file_data   = part[header_end + 4:]

                # Clean trailing boundary markers
                for suffix in (b"\r\n", b"--\r\n", b"--"):
                    if file_data.endswith(suffix):
                        file_data = file_data[:-len(suffix)]

                m = re.search(r'filename="?([^";\r\n]+)"?', headers_raw)
                if not m:
                    continue

                filename = Path(m.group(1).replace("\\", "/")).name
                lower_name = filename.lower()
                allowed_exts = (".jmx", ".csv", ".txt", ".dat")
                if not any(lower_name.endswith(ext) for ext in allowed_exts):
                    self._send_json({"success": False, "message": "Only .jmx, .csv, .txt, and .dat files allowed"}, 400)
                    return

                _TESTS_DIR.mkdir(parents=True, exist_ok=True)
                dest = _TESTS_DIR / filename
                dest.write_bytes(file_data)
                saved = True
                print(f"[Upload] Saved {filename} to {dest}", flush=True)
                break

            if saved:
                self._send_json({"success": True, "message": f"Uploaded '{filename}' to Tests/"})
            else:
                self._send_json({"success": False, "message": "No valid file part found in upload payload"}, 400)
        except Exception as e:
            print(f"[Upload Error] {e}", flush=True)
            self._send_json({"success": False, "message": f"Upload error: {e}"}, 500)


def start_server(port: int = 8080):
    httpd = HTTPServer(("", port), PlatformRequestHandler)
    print(f"\n  ⚡ JmeterAI Web Dashboard → http://localhost:{port}/")
    print(f"  Press Ctrl+C to stop.\n", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  [SERVER] Stopped.")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
