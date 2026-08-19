#!/usr/bin/env python3
"""
run_local_jmeter.py — Local JMeter Test Runner for JmeterAI.

Runs a JMX test plan using the locally installed Apache JMeter CLI.
Parses the resulting .jtl file and returns structured results.
Provides a live JTL watcher thread for real-time metrics streaming.
"""

import os
import sys
import json
import csv
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR  = Path(__file__).parent.resolve()
_ROOT_DIR    = _SCRIPT_DIR.parent.resolve()
_TESTS_DIR   = _ROOT_DIR / "Tests"
_RESULTS_DIR = _ROOT_DIR / "Results"
_DATA_DIR    = _ROOT_DIR / "data"
_LOGS_DIR    = _ROOT_DIR / "logs"

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# ── Environment ───────────────────────────────────────────────────────────────

def _load_env():
    """Load environment variables from config/.env if present."""
    env_path = _ROOT_DIR / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key and val and key not in os.environ:
                    os.environ[key] = val

_load_env()


# ── JMeter discovery ──────────────────────────────────────────────────────────

def find_jmeter_bin() -> str:
    """
    Return the path to the jmeter executable.
    Priority: env var JMETER_HOME > config/.env > system PATH
    """
    jmeter_home = os.environ.get("JMETER_HOME", "")
    if jmeter_home:
        for candidate in [
            Path(jmeter_home) / "jmeter.bat",
            Path(jmeter_home) / "jmeter",
            Path(jmeter_home) / "bin" / "jmeter.bat",
            Path(jmeter_home) / "bin" / "jmeter",
        ]:
            if candidate.exists():
                return str(candidate)
    return "jmeter"


def check_jmeter() -> dict:
    """Check if JMeter is available and return version info."""
    jmeter_bin = find_jmeter_bin()
    if not os.path.exists(jmeter_bin) and jmeter_bin != "jmeter":
        return {"available": False, "error": f"JMeter binary not found at '{jmeter_bin}'"}

    try:
        env = os.environ.copy()
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.exists(java_home):
            env["PATH"] = os.path.join(java_home, "bin") + os.path.pathsep + env.get("PATH", "")

        cmd = [jmeter_bin, "-v"]
        if os.name == 'nt' and jmeter_bin.endswith(".bat"):
            cmd = ["cmd.exe", "/c", jmeter_bin, "-v"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=8, env=env
        )
        version_text = (result.stdout + result.stderr).strip()
        if result.returncode == 0 or "Apache JMeter" in version_text:
            version = "Apache JMeter"
            for line in version_text.splitlines():
                if "Apache JMeter" in line:
                    version = line.strip()
                    break
            return {"available": True, "version": version, "bin": jmeter_bin}
        return {"available": False, "error": f"Exit code {result.returncode}: {version_text[:300]}"}
    except subprocess.TimeoutExpired:
        if os.path.exists(jmeter_bin):
            return {"available": True, "version": "Apache JMeter (Local)", "bin": jmeter_bin}
        return {"available": False, "error": "JMeter verification timed out"}
    except FileNotFoundError:
        return {"available": False, "error": f"JMeter not found at '{jmeter_bin}'. Set JMETER_HOME in config/.env"}
    except Exception as e:
        return {"available": False, "error": str(e)}


# ── JTL Parser ────────────────────────────────────────────────────────────────

def parse_jtl(jtl_path: Path) -> dict:
    """Parse a JMeter JTL CSV file and return a structured result dict."""
    rows = []
    try:
        with open(jtl_path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        return {"error": f"Failed to parse JTL: {e}", "samples": []}

    if not rows:
        return {"samples": [], "summary": {}, "labels": {}}

    total = len(rows)
    errors = sum(1 for r in rows if r.get("success", "true").lower() == "false")
    elapsed_values = []
    label_data = {}
    timestamps = []
    # Error detail tracking: {error_key: {code, message, count, occurrences: [{label, timestamp, elapsed}]}}
    error_details = {}

    def get_col(row_dict, key_name, default=""):
        if key_name in row_dict:
            return row_dict[key_name]
        for k, v in row_dict.items():
            if k and k.lower() == key_name.lower():
                return v
        return default

    for r in rows:
        try:
            elapsed = int(get_col(r, "elapsed", 0))
            elapsed_values.append(elapsed)
        except (ValueError, TypeError):
            pass

        try:
            ts = int(get_col(r, "timeStamp", 0))
            if ts > 0:
                timestamps.append(ts)
        except (ValueError, TypeError):
            pass

        label = get_col(r, "label", "Total")
        if label not in label_data:
            label_data[label] = {"count": 0, "errors": 0, "elapsed": [], "success_flags": []}
        label_data[label]["count"] += 1
        is_succ = str(get_col(r, "success", "true")).lower() == "true"
        if not is_succ:
            label_data[label]["errors"] += 1
            # Collect error details for error analysis donut
            resp_code = str(get_col(r, "responseCode", "")).strip()
            resp_msg = str(get_col(r, "responseMessage", "")).strip()
            failure_msg = str(get_col(r, "failureMessage", "")).strip()
            # Build a descriptive error key
            if failure_msg and "number of samples" not in failure_msg.lower():
                err_key = failure_msg[:80]
            elif resp_code and resp_code not in ("", "200"):
                err_key = f"{resp_code} {resp_msg}" if resp_msg else resp_code
            else:
                err_key = resp_msg if resp_msg else "Unknown Error"
            err_key = err_key.strip()
            if err_key not in error_details:
                error_details[err_key] = {
                    "code": resp_code,
                    "message": resp_msg,
                    "failure_message": failure_msg,
                    "count": 0,
                    "occurrences": []
                }
            error_details[err_key]["count"] += 1
            # Cap occurrences at 50 per error type to keep payload reasonable
            if len(error_details[err_key]["occurrences"]) < 50:
                try:
                    occ_ts = int(get_col(r, "timeStamp", 0))
                except (ValueError, TypeError):
                    occ_ts = 0
                try:
                    occ_elapsed = int(get_col(r, "elapsed", 0))
                except (ValueError, TypeError):
                    occ_elapsed = 0
                error_details[err_key]["occurrences"].append({
                    "label": label,
                    "timestamp": occ_ts,
                    "elapsed": occ_elapsed
                })
        label_data[label]["success_flags"].append(is_succ)
        try:
            label_data[label]["elapsed"].append(int(get_col(r, "elapsed", 0)))
        except (ValueError, TypeError):
            pass

    elapsed_values.sort()
    n = len(elapsed_values)

    def pct(lst, p):
        if not lst:
            return 0
        idx = max(0, int(len(lst) * p / 100) - 1)
        return lst[idx]

    # Per-label stats
    labels_summary = {}
    for lname, ldata in label_data.items():
        # Do not sort ldata["elapsed"] in-place here so it stays aligned with success_flags!
        sorted_elapsed = sorted(ldata["elapsed"])
        ln = len(sorted_elapsed)
        labels_summary[lname] = {
            "count":         ldata["count"],
            "errors":        ldata["errors"],
            "error_rate":    round(ldata["errors"] / ldata["count"] * 100, 2) if ldata["count"] > 0 else 0,
            "avg_rt":        round(sum(sorted_elapsed) / ln, 2) if ln > 0 else 0,
            "p50":           pct(sorted_elapsed, 50),
            "p90":           pct(sorted_elapsed, 90),
            "p95":           pct(sorted_elapsed, 95),
            "p99":           pct(sorted_elapsed, 99),
            "min_rt":        min(sorted_elapsed) if sorted_elapsed else 0,
            "max_rt":        max(sorted_elapsed) if sorted_elapsed else 0,
            "samples":       ldata["elapsed"],
            "success_flags": ldata["success_flags"]
        }

    # Time-series dynamic bucket aggregation (10s buckets for tests <=5min, 1m buckets for longer tests)
    start_ts = min(timestamps) if timestamps else 0
    end_ts   = max(timestamps) if timestamps else 0
    duration_sec = (end_ts - start_ts) / 1000 if end_ts > start_ts else 1

    bucket_sec = 10 if duration_sec <= 300 else 60
    bucket_ms = bucket_sec * 1000

    buckets = {}
    label_buckets = {}  # {label: {b_idx: {"elapsed": [], "errors": 0, "count": 0}}}

    if start_ts > 0:
        for r in rows:
            try:
                t_val = int(get_col(r, "timeStamp", 0))
                e_val = int(get_col(r, "elapsed", 0))
                lbl_val = get_col(r, "label", "Total")
                s_val = str(get_col(r, "success", "true")).lower() == "true"
                if t_val > 0:
                    b_idx = max(0, int((t_val - start_ts) // bucket_ms))
                    
                    if lbl_val not in label_buckets:
                        label_buckets[lbl_val] = {}
                    if b_idx not in label_buckets[lbl_val]:
                        label_buckets[lbl_val][b_idx] = {"elapsed": [], "errors": 0, "count": 0}
                    label_buckets[lbl_val][b_idx]["elapsed"].append(e_val)
                    label_buckets[lbl_val][b_idx]["count"] += 1
                    if not s_val:
                        label_buckets[lbl_val][b_idx]["errors"] += 1
            except Exception:
                pass

    # Build overall buckets from main transaction controllers if available, else all rows
    has_tc_rows = any(k.upper().startswith("TC") or "LAUNCH" in k.upper() or "SELECT" in k.upper() for k in label_buckets.keys())
    if start_ts > 0:
        for r in rows:
            try:
                t_val = int(get_col(r, "timeStamp", 0))
                e_val = int(get_col(r, "elapsed", 0))
                lbl_val = get_col(r, "label", "Total")
                s_val = str(get_col(r, "success", "true")).lower() == "true"
                if t_val > 0:
                    is_tc = (lbl_val.upper().startswith("TC") or "LAUNCH" in lbl_val.upper() or "SELECT" in lbl_val.upper())
                    if not has_tc_rows or is_tc:
                        b_idx = max(0, int((t_val - start_ts) // bucket_ms))
                        if b_idx not in buckets:
                            buckets[b_idx] = {"elapsed": [], "errors": 0, "count": 0}
                        buckets[b_idx]["elapsed"].append(e_val)
                        buckets[b_idx]["count"] += 1
                        if not s_val:
                            buckets[b_idx]["errors"] += 1
            except Exception:
                pass

    total_buckets = (max(buckets.keys()) + 1) if buckets else max(1, int(duration_sec // bucket_sec) + 1)
    ts_labels = []
    ts_avg_rt = []
    ts_p95_rt = []
    ts_p99_rt = []
    ts_throughput = []
    ts_errors = []

    for idx in range(total_buckets):
        if bucket_sec == 10:
            sec_val = (idx + 1) * 10
            ts_labels.append(f"{sec_val}s" if sec_val < 60 else f"{sec_val//60}m{sec_val%60}s" if sec_val%60 else f"{sec_val//60}m")
        else:
            ts_labels.append(f"{idx + 1}m")

        bdata = buckets.get(idx)
        if bdata and bdata["elapsed"]:
            bdata["elapsed"].sort()
            blen = len(bdata["elapsed"])
            ts_avg_rt.append(round(sum(bdata["elapsed"]) / blen, 2))
            ts_p95_rt.append(pct(bdata["elapsed"], 95))
            ts_p99_rt.append(pct(bdata["elapsed"], 99))
            ts_throughput.append(round(bdata["count"] / float(bucket_sec), 2))
            ts_errors.append(bdata["errors"])
        else:
            if ts_avg_rt:
                ts_avg_rt.append(ts_avg_rt[-1])
                ts_p95_rt.append(ts_p95_rt[-1])
                ts_p99_rt.append(ts_p99_rt[-1])
            else:
                ts_avg_rt.append(round(sum(elapsed_values) / n, 2) if n > 0 else 0)
                ts_p95_rt.append(pct(elapsed_values, 95))
                ts_p99_rt.append(pct(elapsed_values, 99))
            ts_throughput.append(0)
            ts_errors.append(0)

    # Per-label time series map
    label_ts_map = {}
    for lname_key, lb_dict in label_buckets.items():
        l_avg_rt, l_p95_rt, l_p99_rt, l_tp, l_err = [], [], [], [], []
        for idx in range(total_buckets):
            lbdata = lb_dict.get(idx)
            if lbdata and lbdata["elapsed"]:
                lbdata["elapsed"].sort()
                lblen = len(lbdata["elapsed"])
                l_avg_rt.append(round(sum(lbdata["elapsed"]) / lblen, 2))
                l_p95_rt.append(pct(lbdata["elapsed"], 95))
                l_p99_rt.append(pct(lbdata["elapsed"], 99))
                l_tp.append(round(lbdata["count"] / float(bucket_sec), 2))
                l_err.append(lbdata["errors"])
            else:
                l_avg_rt.append(0)
                l_p95_rt.append(0)
                l_p99_rt.append(0)
                l_tp.append(0)
                l_err.append(0)
        label_ts_map[lname_key] = {
            "ts_avg_rt": l_avg_rt,
            "ts_p95_rt": l_p95_rt,
            "ts_p99_rt": l_p99_rt,
            "ts_throughput": l_tp,
            "ts_errors": l_err
        }

    time_series = {
        "ts_labels": ts_labels,
        "ts_avg_rt": ts_avg_rt,
        "ts_p95_rt": ts_p95_rt,
        "ts_p99_rt": ts_p99_rt,
        "ts_throughput": ts_throughput,
        "ts_errors": ts_errors,
        "label_ts_map": label_ts_map
    }

    # Identify main Transaction Controllers (starting with 'TC' or configured hierarchy)
    tc_main_labels = {k: v for k, v in labels_summary.items() if k.upper().startswith("TC")}
    if not tc_main_labels:
        # Fallback to any label if no TC-prefixed transactions exist
        tc_main_labels = labels_summary

    # Total iterations = max executions of any main transaction (representing complete test loop count)
    total_iterations = max((v["count"] for v in tc_main_labels.values()), default=total) if tc_main_labels else total
    total_tx_executions = sum(v["count"] for v in tc_main_labels.values()) if tc_main_labels else total
    tc_errors = sum(v["errors"] for v in tc_main_labels.values()) if tc_main_labels else errors
    tc_error_rate = round((tc_errors / total_tx_executions * 100), 2) if total_tx_executions > 0 else 0.0

    avg_rt     = sum(elapsed_values) / n if n > 0 else 0
    throughput = total / duration_sec if duration_sec > 0 else 0

    summary = {
        "total":            total,
        "total_iterations": total_iterations,
        "errors":           errors,
        "tc_errors":        tc_errors,
        "error_rate":       tc_error_rate,
        "raw_error_rate":   round((errors / total * 100), 2) if total > 0 else 0,
        "avg_rt":           round(avg_rt, 2),
        "p50":              pct(elapsed_values, 50),
        "p90":              pct(elapsed_values, 90),
        "p95":              pct(elapsed_values, 95),
        "p99":              pct(elapsed_values, 99),
        "min_rt":           min(elapsed_values) if elapsed_values else 0,
        "max_rt":           max(elapsed_values) if elapsed_values else 0,
        "throughput":       round(throughput, 2),
        "duration_sec":     round(duration_sec, 1),
        "start_epoch":      start_ts // 1000 if start_ts else 0,
        "end_epoch":        end_ts // 1000 if end_ts else 0,
    }

    return {
        "summary":       summary,
        "labels":        labels_summary,
        "time_series":   time_series,
        "error_details": error_details,
        "raw_rows":      len(rows)
    }


# ── Live JTL Watcher ──────────────────────────────────────────────────────────

# Shared state for live metrics (accessed by web server polling)
LIVE_STATE = {
    "active": False,
    "jmx_name": "",
    "jtl_file": "",
    "start_time": 0,
    "done": False,
    "error": None,
    "live_stats": {},       # label -> {total, errors, total_rt, min_rt, max_rt}
    "failed_requests": {},  # label -> {count, status_code, sample_error}
    "stdout_lines": [],
}


def _watch_jtl_live(jtl_path: Path, stop_event: threading.Event):
    """Background thread that reads the JTL file in real-time during execution."""
    last_pos = 0
    header = None

    while not stop_event.is_set():
        if jtl_path.exists():
            try:
                with open(jtl_path, "r", encoding="utf-8", errors="replace") as f:
                    if last_pos > 0:
                        f.seek(last_pos)
                    else:
                        first_line = f.readline()
                        if first_line:
                            reader = csv.reader([first_line.strip()])
                            header_list = next(reader, [])
                            header = [h.strip() for h in header_list]
                            last_pos = f.tell()

                    if header:
                        lines = f.readlines()
                        if lines:
                            last_pos = f.tell()
                            reader = csv.reader(lines)
                            for row_parts in reader:
                                if not row_parts or len(row_parts) < len(header):
                                    continue
                                r = dict(zip(header, [p.strip() for p in row_parts]))
                                lbl = r.get("label", "Unknown")
                                success = r.get("success", "true").lower() == "true"
                                try:
                                    elapsed = int(r.get("elapsed", 0))
                                except Exception:
                                    elapsed = 0

                                if lbl not in LIVE_STATE["live_stats"]:
                                    LIVE_STATE["live_stats"][lbl] = {
                                        "total": 0, "errors": 0, "total_rt": 0,
                                        "min_rt": elapsed, "max_rt": elapsed
                                    }
                                st = LIVE_STATE["live_stats"][lbl]
                                st["total"] += 1
                                st["total_rt"] += elapsed
                                st["min_rt"] = min(st["min_rt"], elapsed)
                                st["max_rt"] = max(st["max_rt"], elapsed)

                                if not success:
                                    st["errors"] += 1
                                    code = r.get("responseCode", "500")
                                    msg = r.get("responseMessage", "HTTP Error")
                                    if lbl not in LIVE_STATE["failed_requests"]:
                                        LIVE_STATE["failed_requests"][lbl] = {
                                            "count": 0, "status_code": code, "sample_error": msg
                                        }
                                    LIVE_STATE["failed_requests"][lbl]["count"] += 1
            except Exception as watch_err:
                print(f"[Live Watcher Warning] {watch_err}", flush=True)

        time.sleep(0.5)


# ── Main Runner ───────────────────────────────────────────────────────────────

def run_local_jmeter(jmx_name: str = None, users: int = 1, duration: str = "0", rampup: str = "0",
                     thread_groups: list = None, tests: list = None) -> dict:
    """
    Run a single local JMeter test and return result metadata.
    
    New approach: a single JMX file with per-thread-group configuration.
    - jmx_name: the JMX filename in Tests/
    - thread_groups: list of per-TG configs [{name, users, duration, rampup, iterations}, ...]
    
    Legacy 'tests' parameter is still supported for backward compatibility.
    """
    from python_files.jmx_editor import update_jmx_thread_groups, to_seconds

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Legacy multi-test compatibility: use first test's JMX
    if tests is not None and len(tests) > 0:
        jmx_name = tests[0].get("jmx", jmx_name)
        if thread_groups is None:
            # Convert legacy tests format into thread_groups-like config
            thread_groups = [{
                "name": "__all__",
                "users": int(t.get("users", 1)),
                "duration": t.get("duration", "0"),
                "rampup": t.get("rampup", "0"),
                "iterations": int(t.get("iterations", 1))
            } for t in tests]

    if not jmx_name:
        return {"success": False, "error": "No JMX provided"}

    jmx_path = _TESTS_DIR / jmx_name
    if not jmx_path.exists():
        return {"success": False, "error": f"JMX '{jmx_name}' not found."}

    jmeter_info = check_jmeter()
    if not jmeter_info["available"]:
        return {"success": False, "error": jmeter_info["error"]}
    jmeter_bin = jmeter_info["bin"]

    # Pre-check CSV data files
    try:
        from python_files.jmx_editor import read_jmx_config
        cfg_check = read_jmx_config(jmx_path)
        missing_csvs = [c["filename"] for c in cfg_check.get("csv_files", []) if not c.get("exists")]
        if missing_csvs:
            missing_str = ", ".join(missing_csvs)
            return {
                "success": False,
                "error": f"Missing CSV Dataset File(s) for {jmx_name}: '{missing_str}'. Please upload them."
            }
    except Exception as check_err:
        print(f"[JMeter] CSV pre-check warning for {jmx_name}: {check_err}", flush=True)

    # Apply per-thread-group configuration to the JMX file
    if thread_groups:
        print(f"[JMeter] Applying per-thread-group configuration ({len(thread_groups)} groups)...", flush=True)
        update_jmx_thread_groups(jmx_path, thread_groups)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jtl_file = _RESULTS_DIR / f"run_{timestamp}.jtl"
    log_file = _LOGS_DIR / f"run_{timestamp}.log"

    # Calculate total users for reporting
    total_users = sum(int(tg.get("users", 1)) for tg in thread_groups) if thread_groups else users

    cmd = [
        jmeter_bin, "-n",
        "-Jjmeter.save.saveservice.autoflush=true",
        "-Jsummariser.interval=3",
        "-t", str(jmx_path),
        "-l", str(jtl_file),
        "-j", str(log_file),
    ]

    if os.name == 'nt' and jmeter_bin.endswith(".bat"):
        cmd = ["cmd.exe", "/c"] + cmd

    print(f"[JMeter] Launching: {' '.join(cmd)}", flush=True)

    start_time = time.time()
    execution_start = datetime.now(timezone.utc)

    LIVE_STATE["active"] = True
    LIVE_STATE["jmx_name"] = jmx_name
    LIVE_STATE["jtl_file"] = jtl_file.name
    LIVE_STATE["start_time"] = start_time
    LIVE_STATE["done"] = False
    LIVE_STATE["error"] = None
    LIVE_STATE["live_stats"] = {}
    LIVE_STATE["failed_requests"] = {}
    LIVE_STATE["stdout_lines"] = []

    # Start live JTL watcher
    stop_event = threading.Event()
    watcher_thread = threading.Thread(target=_watch_jtl_live, args=(jtl_file, stop_event), daemon=True)
    watcher_thread.start()

    # Setup environment
    env = os.environ.copy()
    jmeter_home_val = os.environ.get("JMETER_HOME", "")
    if not jmeter_home_val and jmeter_bin:
        jmeter_home_val = str(Path(jmeter_bin).parent.parent.resolve())
    elif jmeter_home_val and (jmeter_home_val.lower().endswith(r"\bin") or jmeter_home_val.lower().endswith("/bin")):
        jmeter_home_val = str(Path(jmeter_home_val).parent.resolve())

    if jmeter_home_val:
        env["JMETER_HOME"] = jmeter_home_val

    java_home = os.environ.get("JAVA_HOME", "")
    if java_home and os.path.exists(java_home):
        env["JAVA_HOME"] = java_home
        env["PATH"] = os.path.join(java_home, "bin") + os.path.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"

    # Run single JMeter process
    exit_code = -1
    try:
        process = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, cwd=str(_ROOT_DIR), env=env
        )
        for line in iter(process.stdout.readline, ''):
            if line:
                LIVE_STATE["stdout_lines"].append(line.strip())
                print(line, end='', flush=True)
        process.stdout.close()
        exit_code = process.wait()
    except Exception as e:
        LIVE_STATE["stdout_lines"].append(f"Process failed: {e}")
        print(f"[JMeter] Process error: {e}", flush=True)

    stop_event.set()
    watcher_thread.join(timeout=2.0)

    elapsed = time.time() - start_time
    execution_end = datetime.now(timezone.utc)
    execution_time_str = execution_start.strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"[JMeter] Test finished in {elapsed:.1f}s (exit code {exit_code})", flush=True)

    if exit_code != 0 and not jtl_file.exists():
        LIVE_STATE["active"] = False
        LIVE_STATE["done"] = True
        return {"success": False, "error": f"JMeter failed with exit code {exit_code}."}

    if not jtl_file.exists():
        LIVE_STATE["active"] = False
        return {"success": False, "error": f"JTL result file not found: {jtl_file}"}

    parsed = parse_jtl(jtl_file)
    parsed["execution_time"] = execution_time_str
    parsed["jmx_name"]      = jmx_name
    parsed["users"]          = total_users
    parsed["duration"]       = thread_groups[0].get("duration", "0") if thread_groups else duration
    parsed["rampup"]         = thread_groups[0].get("rampup", "0") if thread_groups else rampup
    parsed["jmeter_exit_code"] = exit_code
    parsed["start_epoch"]    = int(execution_start.timestamp())
    parsed["end_epoch"]      = int(execution_end.timestamp())
    parsed["run_id"]         = f"run_{timestamp}"

    # Store thread group config in parsed results for reporting
    if thread_groups:
        parsed["thread_groups"] = thread_groups

    azure_data = {}
    try:
        from python_files.azure_monitor import collect_azure_metrics
        print("[JMeter] Fetching Azure Monitor server-side metrics...", flush=True)
        azure_data = collect_azure_metrics(
            int(execution_start.timestamp()),
            int(execution_end.timestamp()),
            f"run_{timestamp}"
        )
        if azure_data and azure_data.get("infra_summary"):
            print(f"[JMeter] Azure metrics collected: CPU avg={azure_data['infra_summary'].get('avg_cpu', 'N/A')}%", flush=True)
        else:
            print("[JMeter] Azure Monitor not configured or no data returned", flush=True)
    except Exception as az_err:
        print(f"[JMeter] Azure Monitor collection skipped: {az_err}", flush=True)

    try:
        from python_files.correlation_engine import correlate_metrics
        print("[JMeter] Running correlation engine...", flush=True)
        correlation_data = correlate_metrics(parsed, azure_data)
        parsed["correlation"] = correlation_data
    except Exception as corr_err:
        print(f"[JMeter] Correlation step skipped: {corr_err}", flush=True)
        parsed["correlation"] = {}

    ai_insights = None
    try:
        from python_files.ai_insights import generate_insights
        print("[JMeter] Generating AI performance insights...", flush=True)
        summary_m = parsed.get("summary", {})
        infra_m = azure_data.get("infra_summary", {}) if isinstance(azure_data, dict) else {}
        ai_insights = generate_insights(
            test_name=parsed["jmx_name"],
            summary=summary_m,
            labels=parsed.get("labels", {}),
            time_series=parsed.get("time_series", {}),
            infra=infra_m,
            correlation=parsed.get("correlation", {})
        )
        if ai_insights:
            print("[JMeter] AI insights generated successfully", flush=True)
            parsed["ai_insights"] = ai_insights
    except Exception as ai_err:
        print(f"[JMeter] AI insights skipped: {ai_err}", flush=True)

    result_json_path = _RESULTS_DIR / f"run_{timestamp}_result.json"
    result_json_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    print(f"[JMeter] Result JSON: {result_json_path.name}", flush=True)

    if azure_data:
        azure_json_path = _RESULTS_DIR / f"azure_{timestamp}.json"
        azure_json_path.write_text(json.dumps(azure_data, indent=2), encoding="utf-8")

    report_path = _RESULTS_DIR / f"run_{timestamp}_report.html"
    try:
        import importlib
        import python_files.report_generator as rg_mod
        importlib.reload(rg_mod)
        rg_mod.generate_report(
            parsed=parsed,
            azure_data=azure_data,
            ai_insights=ai_insights,
            report_path=report_path,
            jmx_name=parsed["jmx_name"],
            users=parsed["users"]
        )
        print(f"[JMeter] HTML Report: {report_path.name}", flush=True)
    except Exception as rpt_err:
        print(f"[JMeter] Report generation error: {rpt_err}", flush=True)

    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        runs_path = _DATA_DIR / "runs.json"
        runs_data = {"runs": []}
        if runs_path.exists():
            try:
                runs_data = json.loads(runs_path.read_text(encoding="utf-8"))
            except Exception:
                runs_data = {"runs": []}

        summary_m = parsed.get("summary", {})
        run_entry = {
            "id": f"run_{timestamp}",
            "jmx_name": parsed["jmx_name"],
            "timestamp": execution_time_str,
            "epoch": int(execution_start.timestamp()),
            "users": parsed["users"],
            "duration": parsed["duration"],
            "rampup": parsed["rampup"],
            "total_samples": summary_m.get("total", 0),
            "avg_rt": summary_m.get("avg_rt", 0),
            "p95_rt": summary_m.get("p95", 0),
            "error_rate": summary_m.get("error_rate", 0),
            "throughput": summary_m.get("throughput", 0),
            "duration_sec": summary_m.get("duration_sec", 0),
            "has_azure": bool(azure_data and azure_data.get("infra_summary")),
            "has_ai_insights": bool(ai_insights),
            "report_file": report_path.name if report_path.exists() else None,
            "result_file": result_json_path.name,
            "status": "passed" if summary_m.get("error_rate", 0) <= 1.0 else "warning" if summary_m.get("error_rate", 0) <= 5.0 else "failed"
        }
        runs_data["runs"].insert(0, run_entry)
        runs_path.write_text(json.dumps(runs_data, indent=2), encoding="utf-8")
    except Exception as hist_err:
        print(f"[JMeter] History update warning: {hist_err}", flush=True)

    LIVE_STATE["active"] = False
    LIVE_STATE["done"] = True

    return {
        "success":       True,
        "run_id":        f"run_{timestamp}",
        "jtl_file":      str(jtl_file),
        "result_json":   str(result_json_path),
        "report_html":   str(report_path),
        "report_url":    f"/Results/{report_path.name}",
        "summary":       parsed.get("summary", {}),
        "execution_time": execution_time_str,
        "exit_code":     exit_code,
    }



