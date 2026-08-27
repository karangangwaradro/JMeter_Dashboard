#!/usr/bin/env python3
"""
jtl_parser.py — JMeter JTL / CSV Results Parser for PerfPilot.

Parses Apache JMeter JTL log files (CSV format) into structured performance metrics,
transaction breakdowns, error diagnostics, and time-series datasets for reporting and analytics.
"""

import csv
import math
from pathlib import Path
from typing import Dict, Any, List, Optional


def pct(lst: List[int], p: float) -> int:
    """Calculate percentile from a sorted list of integer response times."""
    if not lst:
        return 0
    idx = max(0, int(len(lst) * p / 100) - 1)
    return lst[idx]


def get_col(row_dict: dict, key_name: str, default: Any = "") -> Any:
    """Retrieve column value case-insensitively from a CSV row dictionary."""
    if key_name in row_dict:
        return row_dict[key_name]
    for k, v in row_dict.items():
        if k and k.lower() == key_name.lower():
            return v
    return default


def parse_jtl(jtl_path: Path) -> Dict[str, Any]:
    """
    Parse a JMeter JTL CSV file and return a comprehensive, structured result dictionary.

    Returns:
        {
            "summary": dict,         # Aggregate test metrics (total, avg_rt, p90/p95, TPS, error_rate, etc.)
            "labels": dict,          # Per-transaction metrics (counts, latencies, percentiles, error rates)
            "time_series": dict,     # Time-bucketed metric arrays for Chart.js
            "error_details": dict,   # Error categorization, response codes, failure messages, and sample occurrences
            "raw_rows": int          # Total sample count parsed
        }
    """
    jtl_path = Path(jtl_path)
    if not jtl_path.exists():
        return {"error": f"JTL file not found: {jtl_path}", "samples": [], "summary": {}, "labels": {}}

    rows = []
    try:
        with open(jtl_path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        return {"error": f"Failed to parse JTL: {e}", "samples": [], "summary": {}, "labels": {}}

    if not rows:
        return {"samples": [], "summary": {}, "labels": {}, "time_series": {}, "error_details": {}, "raw_rows": 0}

    total = len(rows)
    errors = sum(1 for r in rows if str(get_col(r, "success", "true")).lower() == "false")
    elapsed_values = []
    label_data = {}
    tg_label_data = {}
    timestamps = []
    # Error detail tracking: {error_key: {code, message, failure_message, count, occurrences: [{label, timestamp, elapsed}]}}
    error_details = {}

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

        # Thread Group Disaggregation
        t_name = get_col(r, "threadName", "").strip()
        tg_key = t_name.rsplit(" ", 1)[0].strip() if (" " in t_name and any(c.isdigit() for c in t_name.rsplit(" ", 1)[1])) else t_name
        if tg_key:
            if tg_key not in tg_label_data:
                tg_label_data[tg_key] = {}
            if label not in tg_label_data[tg_key]:
                tg_label_data[tg_key][label] = {"count": 0, "errors": 0, "elapsed": [], "success_flags": []}
            tg_label_data[tg_key][label]["count"] += 1

        is_succ = str(get_col(r, "success", "true")).lower() == "true"
        if not is_succ:
            label_data[label]["errors"] += 1
            if tg_key and tg_key in tg_label_data and label in tg_label_data[tg_key]:
                tg_label_data[tg_key][label]["errors"] += 1

            # Collect error details for error analysis donut
            resp_code = str(get_col(r, "responseCode", "")).strip()
            resp_msg = str(get_col(r, "responseMessage", "")).strip()
            failure_msg = str(get_col(r, "failureMessage", "")).strip()
            
            # Check if this row is a Transaction Controller container rollup
            # (JMeter sets "Number of samples in transaction : N, number of failing/failed samples : M" for container rollups)
            f_lower = failure_msg.lower()
            r_lower = resp_msg.lower()
            lbl_lower = label.lower()
            url_val = str(get_col(r, "URL", "")).strip()
            data_type = str(get_col(r, "dataType", "")).strip()

            is_tc_rollup = (
                "samples in transaction" in f_lower or
                "samples in transaction" in r_lower or
                "failed samples" in f_lower or
                "failed samples" in r_lower or
                "failing samples" in f_lower or
                "failing samples" in r_lower or
                "transaction failed" in f_lower or
                "transaction failed" in r_lower or
                lbl_lower.startswith("tc") or
                lbl_lower.startswith("t-") or
                "transaction controller" in lbl_lower or
                "overall_iteration" in lbl_lower or
                "controller" in lbl_lower or
                url_val in ("", "null", "None") or
                not data_type
            )

            # ONLY track actual HTTP request errors or assertion failures (avoiding duplicate transaction container rollups)
            if not is_tc_rollup:
                # Build a descriptive error key
                if failure_msg:
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
            e_val = int(get_col(r, "elapsed", 0))
            label_data[label]["elapsed"].append(e_val)
            if tg_key and tg_key in tg_label_data and label in tg_label_data[tg_key]:
                tg_label_data[tg_key][label]["elapsed"].append(e_val)
                tg_label_data[tg_key][label]["success_flags"].append(is_succ)
        except (ValueError, TypeError):
            pass

    elapsed_values.sort()
    n = len(elapsed_values)

    # Per-label stats (global)
    labels_summary = {}
    for lname, ldata in label_data.items():
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

    # Per-label stats by Thread Group (disaggregated)
    labels_by_tg = {}
    for tg_k, tg_lbls in tg_label_data.items():
        labels_by_tg[tg_k] = {}
        for lname, ldata in tg_lbls.items():
            sorted_elapsed = sorted(ldata["elapsed"])
            ln = len(sorted_elapsed)
            labels_by_tg[tg_k][lname] = {
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
                            buckets[b_idx] = {"elapsed": [], "errors": 0, "count": 0, "threads": []}
                        buckets[b_idx]["elapsed"].append(e_val)
                        buckets[b_idx]["count"] += 1
                        try:
                            th_val = int(get_col(r, "allThreads", 0))
                            if th_val > 0:
                                buckets[b_idx]["threads"].append(th_val)
                        except (ValueError, TypeError):
                            pass
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
    ts_active_threads = []

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
            th_list = bdata.get("threads", [])
            ts_active_threads.append(max(th_list) if th_list else (ts_active_threads[-1] if ts_active_threads else 0))
        else:
            if ts_avg_rt:
                ts_avg_rt.append(ts_avg_rt[-1])
                ts_p95_rt.append(ts_p95_rt[-1])
                ts_p99_rt.append(ts_p99_rt[-1])
                ts_active_threads.append(ts_active_threads[-1] if ts_active_threads else 0)
            else:
                ts_avg_rt.append(round(sum(elapsed_values) / n, 2) if n > 0 else 0)
                ts_p95_rt.append(pct(elapsed_values, 95))
                ts_p99_rt.append(pct(elapsed_values, 99))
                ts_active_threads.append(0)
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
        "ts_active_threads": ts_active_threads,
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

    leaf_http_errors = sum(ed["count"] for ed in error_details.values())

    summary = {
        "total":            total,
        "total_iterations": total_iterations,
        "errors":           leaf_http_errors if (error_details or leaf_http_errors > 0) else errors,
        "tc_errors":        tc_errors,
        "error_rate":       tc_error_rate,
        "raw_error_rate":   round(((leaf_http_errors if (error_details or leaf_http_errors > 0) else errors) / total * 100), 2) if total > 0 else 0,
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
        "labels_by_tg":  labels_by_tg,
        "time_series":   time_series,
        "error_details": error_details,
        "raw_rows":      len(rows)
    }
