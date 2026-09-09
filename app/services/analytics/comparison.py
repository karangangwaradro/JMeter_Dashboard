#!/usr/bin/env python3
"""
comparison.py — Modern Run Comparison Service.

Computes exact differential analytics between two test runs:
  1. AI Comparative Insights & Verdict
  2. Iteration Stats & Throughput (TPS) Parity
  3. Response Time Analytics (Avg, P90, P95, P99, Delta %, Variance Chart data)
  4. Error & Reliability Comparison (Error count, Error % pp delta)
  5. Critical Transactions & 4-Quadrant SLA Transition Matrix
"""

import os
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.core.constants import DATA_DIR, RESULTS_DIR, RESULTS_JSON_DIR

_DATA_DIR = DATA_DIR
_RESULTS_DIR = RESULTS_DIR
_RESULTS_JSON_DIR = RESULTS_JSON_DIR


def get_available_runs() -> List[Dict[str, Any]]:
    """Returns all available test runs sorted newest to oldest."""
    runs_file = _DATA_DIR / "runs.json"
    if not runs_file.exists():
        return []
    try:
        data = json.loads(runs_file.read_text(encoding="utf-8"))
        runs = data.get("runs", [])
        runs.sort(key=lambda x: x.get("epoch", 0), reverse=True)
        return runs
    except Exception as e:
        print(f"[comparison] Error loading runs.json: {e}", flush=True)
        return []


def load_run_data(run_id: str) -> Optional[Dict[str, Any]]:
    """Loads manifest info and detailed JSON metrics for a specific run ID."""
    runs = get_available_runs()
    manifest = next((r for r in runs if r.get("id") == run_id), None)
    
    # Try finding JSON result file
    res_path = _RESULTS_JSON_DIR / f"{run_id}_result.json"
    if not res_path.exists():
        res_path = _RESULTS_DIR / f"{run_id}_result.json"
    
    detail = {}
    if res_path.exists():
        try:
            detail = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[comparison] Error reading {res_path}: {e}", flush=True)

    if not manifest and not detail:
        return None

    run_info = dict(manifest) if manifest else {}
    run_info["detail"] = detail
    run_info["id"] = run_id
    if "jmx_name" not in run_info and "jmx_name" in detail:
        run_info["jmx_name"] = detail["jmx_name"]
    if "users" not in run_info and "users" in detail:
        run_info["users"] = detail.get("users", 1)
    if "execution_time" not in run_info and "execution_time" in detail:
        run_info["execution_time"] = detail["execution_time"]

    return run_info


def compare_two_runs(baseline_id: str, current_id: str) -> Dict[str, Any]:
    """
    Compares baseline (Run A) against current (Run B).
    Returns complete comparison dataset ready for UI rendering and AI insights.
    """
    run_a = load_run_data(baseline_id)
    run_b = load_run_data(current_id)

    if not run_a:
        return {"success": False, "message": f"Baseline run '{baseline_id}' not found."}
    if not run_b:
        return {"success": False, "message": f"Current run '{current_id}' not found."}

    detail_a = run_a.get("detail", {})
    detail_b = run_b.get("detail", {})
    summary_a = detail_a.get("summary", {})
    summary_b = detail_b.get("summary", {})
    labels_a = detail_a.get("labels", {})
    labels_b = detail_b.get("labels", {})

    # Load SLA targets for the current JMX test plan
    jmx_name = run_b.get("jmx_name") or detail_b.get("jmx_name") or run_a.get("jmx_name") or ""
    users_b = run_b.get("users", 1)
    sla_map = {}
    default_rt, default_err = 500.0, 1.0
    try:
        from app.services.analytics.sla_manager import load_sla_targets
        sla_map, default_rt, default_err = load_sla_targets(jmx_name, actual_users=users_b)
    except Exception as e:
        print(f"[comparison] SLA load warning: {e}", flush=True)

    # Duration and Throughput
    dur_a = float(summary_a.get("duration_sec", run_a.get("duration_sec", 60.0))) or 60.0
    dur_b = float(summary_b.get("duration_sec", run_b.get("duration_sec", 60.0))) or 60.0

    # Extract transaction labels (strictly match Transaction Controllers from JMX hierarchy)
    tc_ordered = []
    tc_to_samplers = {}
    child_samplers = set()
    try:
        from app.services.analytics.sla_manager import parse_jmx_hierarchy
        tc_ordered, tc_to_samplers = parse_jmx_hierarchy(jmx_name)
        for s_list in tc_to_samplers.values():
            child_samplers.update(s_list)
    except Exception as hier_err:
        print(f"[comparison] Hierarchy parse warning: {hier_err}", flush=True)

    all_keys = set(labels_a.keys()).union(labels_b.keys())
    if tc_ordered:
        tc_set = set(tc_ordered)
        target_labels = [k for k in all_keys if k in tc_set]
        # Preserve JMX logical execution order
        tc_idx_map = {name: idx for idx, name in enumerate(tc_ordered)}
        target_labels.sort(key=lambda x: tc_idx_map.get(x, 9999))
    elif child_samplers:
        target_labels = [k for k in all_keys if k not in child_samplers]
        target_labels.sort()
    else:
        # Fallback: if names have child request pattern like _R_01_, exclude them
        has_req_pattern = any("_R_" in k.upper() or "_REQ" in k.upper() for k in all_keys)
        has_tc_pattern = any(k.upper().startswith("TC") or "CONTROLLER" in k.upper() for k in all_keys)
        if has_req_pattern and has_tc_pattern:
            target_labels = [k for k in all_keys if not ("_R_" in k.upper() or "_REQ" in k.upper())]
        else:
            target_labels = list(all_keys)
        target_labels.sort()

    # ─────────────────────────────────────────────────────────────
    # 1. METRICS PER TRANSACTION
    # ─────────────────────────────────────────────────────────────
    tx_comparisons = []
    regressed_count = 0
    improved_count = 0
    unchanged_count = 0

    pass_to_pass = []
    pass_to_fail = []  # New Breaches!
    fail_to_pass = []  # Resolved Breaches!
    fail_to_fail = []  # Persistent Breaches!
    critical_tx_list = []

    for lbl in target_labels:
        la = labels_a.get(lbl, {})
        lb = labels_b.get(lbl, {})

        count_a = int(la.get("count", 0))
        count_b = int(lb.get("count", 0))

        rt_a = float(la.get("avg_rt", la.get("mean", la.get("avg", 0))))
        rt_b = float(lb.get("avg_rt", lb.get("mean", lb.get("avg", 0))))

        p90_a = float(la.get("p90", la.get("pct90", 0)))
        p90_b = float(lb.get("p90", lb.get("pct90", 0)))

        p95_a = float(la.get("p95", la.get("pct95", 0)))
        p95_b = float(lb.get("p95", lb.get("pct95", 0)))

        p99_a = float(la.get("p99", la.get("pct99", 0)))
        p99_b = float(lb.get("p99", lb.get("pct99", 0)))

        err_count_a = int(la.get("errors", 0))
        err_count_b = int(lb.get("errors", 0))

        err_rate_a = float(la.get("error_rate", 0))
        err_rate_b = float(lb.get("error_rate", 0))

        tps_a = round(count_a / dur_a, 2) if dur_a > 0 else 0
        tps_b = round(count_b / dur_b, 2) if dur_b > 0 else 0

        # Calculations
        rt_diff_ms = round(rt_b - rt_a, 2)
        rt_pct_change = round(((rt_b - rt_a) / rt_a * 100), 2) if rt_a > 0 else 0.0
        p90_pct_change = round(((p90_b - p90_a) / p90_a * 100), 2) if p90_a > 0 else 0.0
        p95_pct_change = round(((p95_b - p95_a) / p95_a * 100), 2) if p95_a > 0 else 0.0
        tps_pct_change = round(((tps_b - tps_a) / tps_a * 100), 2) if tps_a > 0 else 0.0
        err_change_pp = round(err_rate_b - err_rate_a, 2)
        count_diff = count_b - count_a

        # State classification
        if rt_pct_change <= -5.0:
            status = "IMPROVED"
            improved_count += 1
        elif rt_pct_change >= 5.0:
            status = "REGRESSED"
            regressed_count += 1
        else:
            status = "NEUTRAL"
            unchanged_count += 1

        # SLA Compliance & Transition
        sla_info = sla_map.get(lbl, {})
        target_rt = float(sla_info.get("rt", default_rt))
        target_err = float(sla_info.get("err", default_err))
        is_crit = bool(sla_info.get("is_critical", False) or "CRITICAL" in lbl.upper() or sla_info.get("critical", False))

        passed_sla_a = (p90_a <= target_rt) and (err_rate_a <= target_err) if count_a > 0 else True
        passed_sla_b = (p90_b <= target_rt) and (err_rate_b <= target_err) if count_b > 0 else True

        sla_transition = "PASS_TO_PASS"
        if passed_sla_a and passed_sla_b:
            sla_transition = "PASS_TO_PASS"
            pass_to_pass.append(lbl)
        elif passed_sla_a and not passed_sla_b:
            sla_transition = "PASS_TO_FAIL"
            pass_to_fail.append(lbl)
        elif not passed_sla_a and passed_sla_b:
            sla_transition = "FAIL_TO_PASS"
            fail_to_pass.append(lbl)
        else:
            sla_transition = "FAIL_TO_FAIL"
            fail_to_fail.append(lbl)

        tx_item = {
            "label": lbl,
            "is_critical": is_crit,
            "status": status,
            "count_a": count_a,
            "count_b": count_b,
            "count_diff": count_diff,
            "rt_a": round(rt_a, 2),
            "rt_b": round(rt_b, 2),
            "rt_diff_ms": rt_diff_ms,
            "rt_pct_change": rt_pct_change,
            "p90_a": round(p90_a, 2),
            "p90_b": round(p90_b, 2),
            "p90_pct_change": p90_pct_change,
            "p95_a": round(p95_a, 2),
            "p95_b": round(p95_b, 2),
            "p95_pct_change": p95_pct_change,
            "p99_a": round(p99_a, 2),
            "p99_b": round(p99_b, 2),
            "tps_a": tps_a,
            "tps_b": tps_b,
            "tps_pct_change": tps_pct_change,
            "err_count_a": err_count_a,
            "err_count_b": err_count_b,
            "err_rate_a": round(err_rate_a, 2),
            "err_rate_b": round(err_rate_b, 2),
            "err_change_pp": err_change_pp,
            "target_rt": target_rt,
            "target_err": target_err,
            "sla_passed_a": passed_sla_a,
            "sla_passed_b": passed_sla_b,
            "sla_transition": sla_transition,
            "breach_margin_ms": round(max(0, p90_b - target_rt), 2)
        }
        tx_comparisons.append(tx_item)
        if is_crit:
            critical_tx_list.append(tx_item)

    # ─────────────────────────────────────────────────────────────
    # 2. OVERALL SCORECARD & SUMMARY DELTAS
    # ─────────────────────────────────────────────────────────────
    overall_rt_a = float(summary_a.get("avg_rt", summary_a.get("mean", 0)))
    overall_rt_b = float(summary_b.get("avg_rt", summary_b.get("mean", 0)))
    overall_rt_pct = round(((overall_rt_b - overall_rt_a) / overall_rt_a * 100), 2) if overall_rt_a > 0 else 0.0

    overall_p90_a = float(summary_a.get("p90", summary_a.get("pct90", 0)))
    overall_p90_b = float(summary_b.get("p90", summary_b.get("pct90", 0)))
    overall_p90_pct = round(((overall_p90_b - overall_p90_a) / overall_p90_a * 100), 2) if overall_p90_a > 0 else 0.0

    overall_p95_a = float(summary_a.get("p95", summary_a.get("pct95", 0)))
    overall_p95_b = float(summary_b.get("p95", summary_b.get("pct95", 0)))
    overall_p95_pct = round(((overall_p95_b - overall_p95_a) / overall_p95_a * 100), 2) if overall_p95_a > 0 else 0.0

    overall_p99_a = float(summary_a.get("p99", summary_a.get("pct99", 0)))
    overall_p99_b = float(summary_b.get("p99", summary_b.get("pct99", 0)))

    iter_a = int(summary_a.get("total_iterations", summary_a.get("iterations", max((la.get("count", 0) for la in labels_a.values()), default=summary_a.get("total", 0)))))
    iter_b = int(summary_b.get("total_iterations", summary_b.get("iterations", max((lb.get("count", 0) for lb in labels_b.values()), default=summary_b.get("total", 0)))))
    iter_pct = round(((iter_b - iter_a) / iter_a * 100), 2) if iter_a > 0 else 0.0

    total_req_a = int(summary_a.get("total", sum(la.get("count", 0) for la in labels_a.values())))
    total_req_b = int(summary_b.get("total", sum(lb.get("count", 0) for lb in labels_b.values())))
    req_pct = round(((total_req_b - total_req_a) / total_req_a * 100), 2) if total_req_a > 0 else 0.0

    tps_tot_a = round(total_req_a / dur_a, 2) if dur_a > 0 else 0
    tps_tot_b = round(total_req_b / dur_b, 2) if dur_b > 0 else 0
    tps_tot_pct = round(((tps_tot_b - tps_tot_a) / tps_tot_a * 100), 2) if tps_tot_a > 0 else 0.0

    err_tot_a = int(summary_a.get("errors", sum(la.get("errors", 0) for la in labels_a.values())))
    err_tot_b = int(summary_b.get("errors", sum(lb.get("errors", 0) for lb in labels_b.values())))
    err_rate_tot_a = round((err_tot_a / total_req_a * 100), 2) if total_req_a > 0 else 0.0
    err_rate_tot_b = round((err_tot_b / total_req_b * 100), 2) if total_req_b > 0 else 0.0
    err_rate_tot_pp = round(err_rate_tot_b - err_rate_tot_a, 2)

    total_tx_count = len(tx_comparisons)
    sla_pass_a = sum(1 for t in tx_comparisons if t["sla_passed_a"])
    sla_pass_b = sum(1 for t in tx_comparisons if t["sla_passed_b"])
    sla_pass_rate_a = round((sla_pass_a / total_tx_count * 100), 1) if total_tx_count > 0 else 100.0
    sla_pass_rate_b = round((sla_pass_b / total_tx_count * 100), 1) if total_tx_count > 0 else 100.0
    sla_pass_rate_pp = round(sla_pass_rate_b - sla_pass_rate_a, 1)

    scorecard = {
        "run_a_id": baseline_id,
        "run_b_id": current_id,
        "run_a_time": run_a.get("execution_time", "N/A"),
        "run_b_time": run_b.get("execution_time", "N/A"),
        "run_a_users": run_a.get("users", 1),
        "run_b_users": run_b.get("users", 1),
        "run_a_rt": round(overall_rt_a, 2),
        "run_b_rt": round(overall_rt_b, 2),
        "rt_change_pct": overall_rt_pct,
        "run_a_p90": round(overall_p90_a, 2),
        "run_b_p90": round(overall_p90_b, 2),
        "p90_change_pct": overall_p90_pct,
        "run_a_p95": round(overall_p95_a, 2),
        "run_b_p95": round(overall_p95_b, 2),
        "p95_change_pct": overall_p95_pct,
        "run_a_p99": round(overall_p99_a, 2),
        "run_b_p99": round(overall_p99_b, 2),
        "run_a_iter": iter_a,
        "run_b_iter": iter_b,
        "iter_change_pct": iter_pct,
        "run_a_req": total_req_a,
        "run_b_req": total_req_b,
        "req_change_pct": req_pct,
        "run_a_tps": tps_tot_a,
        "run_b_tps": tps_tot_b,
        "tps_change_pct": tps_tot_pct,
        "run_a_err_count": err_tot_a,
        "run_b_err_count": err_tot_b,
        "run_a_err_rate": err_rate_tot_a,
        "run_b_err_rate": err_rate_tot_b,
        "err_change_pp": err_rate_tot_pp,
        "run_a_sla_pass": sla_pass_rate_a,
        "run_b_sla_pass": sla_pass_rate_b,
        "sla_pass_change_pp": sla_pass_rate_pp,
        "tx_improved": improved_count,
        "tx_regressed": regressed_count,
        "tx_unchanged": unchanged_count,
        "new_sla_breaches": len(pass_to_fail),
        "resolved_sla_breaches": len(fail_to_pass)
    }

    baseline_info = {
        "id": baseline_id,
        "execution_time": run_a.get("execution_time", ""),
        "users": run_a.get("users", 1),
        "jmx_name": run_a.get("jmx_name", "")
    }
    current_info = {
        "id": current_id,
        "execution_time": run_b.get("execution_time", ""),
        "users": run_b.get("users", 1),
        "jmx_name": run_b.get("jmx_name", "")
    }

    # ─────────────────────────────────────────────────────────────
    # 3. LIVE AI COMPARATIVE INSIGHTS GENERATION
    # ─────────────────────────────────────────────────────────────
    ai_verdict = _generate_comparative_ai_insights(
        sc=scorecard,
        txs=tx_comparisons,
        new_breaches=pass_to_fail,
        resolved_breaches=fail_to_pass,
        current_info=current_info,
        baseline_info=baseline_info
    )

    return {
        "success": True,
        "baseline_run": baseline_info,
        "current_run": current_info,
        "scorecard": scorecard,
        "ai_insights": ai_verdict,
        "transaction_comparisons": tx_comparisons,
        "critical_transactions": critical_tx_list,
        "sla_transitions": {
            "pass_to_pass": pass_to_pass,
            "pass_to_fail": pass_to_fail,
            "fail_to_pass": fail_to_pass,
            "fail_to_fail": fail_to_fail
        }
    }


def _generate_comparative_ai_insights(sc: Dict[str, Any], txs: List[Dict[str, Any]],
                                      new_breaches: List[str], resolved_breaches: List[str],
                                      current_info: Dict[str, Any] = None, baseline_info: Dict[str, Any] = None) -> Dict[str, Any]:
    # 1. Attempt actual LLM generation
    try:
        from app.services.ai.insights import generate_2run_comparison_ai_insights
        ai_res = generate_2run_comparison_ai_insights(
            scorecard=sc,
            transactions=txs,
            new_breaches=new_breaches,
            resolved_breaches=resolved_breaches,
            current_info=current_info or {},
            baseline_info=baseline_info or {}
        )
        if ai_res and ai_res.get("executive_summary"):
            return {
                "risk_level": ai_res.get("risk_level", "LOW RISK"),
                "risk_color": ai_res.get("risk_color", "var(--green)"),
                "status_badge": ai_res.get("status_badge", "🟢 STABLE PERFORMANCE"),
                "status_text": ai_res.get("status_text", ai_res.get("status_badge", "Stable Performance")),
                "executive_summary": ai_res.get("executive_summary", ""),
                "highlights": ai_res.get("highlights", ai_res.get("observations", [])),
                "recommendations": ai_res.get("recommendations", []),
                "findings": ai_res.get("findings", [])
            }
    except Exception as e:
        print(f"[comparison] Live LLM generation warning: {e}.", flush=True)

    # Strictly AI-based: Do NOT inject rule-based or hardcoded responses
    return {
        "risk_level": "N/A",
        "risk_color": "var(--muted)",
        "status_badge": "AI Analysis Unavailable",
        "status_text": "AI comparative insights unavailable",
        "executive_summary": "AI comparative insights are not available. Configure an active AI provider (OpenRouter, Gemini, or GitHub) to generate deep differential intelligence.",
        "highlights": [],
        "recommendations": [],
        "findings": []
    }


def save_comparison_draft(current_id: str, baseline_id: str, data: Dict[str, Any] = None,
                          custom_edits: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Saves or updates comparison draft for the given current run ID.
    Persists to Results/json/{current_id}_comparison_draft.json and optionally updates runs JSON.
    """
    if not current_id or not baseline_id:
        return {"success": False, "message": "current_id and baseline_id are required"}

    draft_record = {
        "current_id": current_id,
        "baseline_id": baseline_id,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": int(time.time()),
        "data": data or {},
        "custom_edits": custom_edits or {}
    }

    _RESULTS_JSON_DIR.mkdir(parents=True, exist_ok=True)
    draft_file = _RESULTS_JSON_DIR / f"{current_id}_comparison_draft.json"
    try:
        draft_file.write_text(json.dumps(draft_record, indent=2), encoding="utf-8")
        
        # Also sync into current_id_result.json if present
        res_path = _RESULTS_JSON_DIR / f"{current_id}_result.json"
        if not res_path.exists():
            res_path = _RESULTS_DIR / f"{current_id}_result.json"
        if res_path.exists():
            try:
                res_data = json.loads(res_path.read_text(encoding="utf-8"))
                res_data["comparison_draft"] = {
                    "baseline_id": baseline_id,
                    "updated_at": draft_record["updated_at"],
                    "custom_edits": custom_edits or {}
                }
                res_path.write_text(json.dumps(res_data, indent=2), encoding="utf-8")
            except Exception as r_err:
                print(f"[comparison] Result JSON draft sync note: {r_err}", flush=True)

        return {"success": True, "message": "Comparison draft saved successfully", "draft": draft_record}
    except Exception as e:
        print(f"[comparison] Error saving draft: {e}", flush=True)
        return {"success": False, "message": str(e)}


def load_comparison_draft(current_id: str) -> Optional[Dict[str, Any]]:
    """Loads saved comparison draft for the given current run ID."""
    if not current_id:
        return None

    draft_file = _RESULTS_JSON_DIR / f"{current_id}_comparison_draft.json"
    if not draft_file.exists():
        draft_file = _RESULTS_DIR / f"{current_id}_comparison_draft.json"

    if draft_file.exists():
        try:
            return json.loads(draft_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[comparison] Error reading draft file {draft_file}: {e}", flush=True)

    # Fallback to result JSON
    res_path = _RESULTS_JSON_DIR / f"{current_id}_result.json"
    if not res_path.exists():
        res_path = _RESULTS_DIR / f"{current_id}_result.json"
    if res_path.exists():
        try:
            res_data = json.loads(res_path.read_text(encoding="utf-8"))
            if "comparison_draft" in res_data:
                return {
                    "current_id": current_id,
                    **res_data["comparison_draft"]
                }
        except Exception:
            pass

    return None


def clear_comparison_draft(current_id: str) -> Dict[str, Any]:
    """Deletes saved comparison draft for the given current run ID."""
    if not current_id:
        return {"success": False, "message": "current_id is required"}

    for d in (_RESULTS_JSON_DIR, _RESULTS_DIR):
        draft_file = d / f"{current_id}_comparison_draft.json"
        if draft_file.exists():
            try:
                draft_file.unlink()
            except Exception as e:
                print(f"[comparison] Error unlinking {draft_file}: {e}", flush=True)

    res_path = _RESULTS_JSON_DIR / f"{current_id}_result.json"
    if not res_path.exists():
        res_path = _RESULTS_DIR / f"{current_id}_result.json"
    if res_path.exists():
        try:
            res_data = json.loads(res_path.read_text(encoding="utf-8"))
            if "comparison_draft" in res_data:
                del res_data["comparison_draft"]
                res_path.write_text(json.dumps(res_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {"success": True, "message": "Comparison draft cleared successfully"}
