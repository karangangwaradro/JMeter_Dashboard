#!/usr/bin/env python3
"""
comparison_engine.py — Dedicated 2-Run Performance Comparison Engine for PerfPilot.

Primary Purpose:
  Detailed engineering comparison between EXACTLY TWO JMeter test runs (Run A vs Run B).
  Answers: "What changed from Run A to Run B?"

Core Visualizations & Analytics:
1. Overall Performance Split Cards: Avg RT, P95, P99 with individual micro-bars and % deltas.
2. Transaction Response Time Comparison: Horizontal grouped bar chart (Run A vs Run B) sortable by largest degradation / % change / absolute RT.
3. Response Time Change % (Hero Chart): Diverging horizontal bar chart (Improvement on left, Degradation on right).
4. SLA Compliance Comparison: 100% stacked bar (Pass % vs Breach % with pp delta).
5. SLA Status Transition Matrix: 4-quadrant transition matrix (Pass->Pass, Pass->Fail [New], Fail->Pass [Resolved], Fail->Fail [Persistent]).
6. SLA Breach Margin Chart: Diverging bar chart measuring (RT - SLA Target).
7. Throughput Comparison: Grouped horizontal bars (Run A vs Run B TPS + % change).
8. Error Rate Comparison: Grouped bar chart (Run A vs Run B Error % + pp change).
9. Percentile Comparison: Tail latency progression (P50 -> P90 -> P95 -> P99).
10. Transaction Performance Matrix: Clean scan heatmap (Tx x [RT, P95, TPS, Errors, SLA status]).
11. Compact Numerical Observations: Every single graph includes a concise, grounded factual observation underneath.
"""

import os
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

_ROOT = Path(__file__).parent.parent.resolve()
_DATA_DIR = _ROOT / "data"
_RESULTS_DIR = _ROOT / "Results"
_RESULTS_JSON_DIR = _RESULTS_DIR / "json"
_CONFIG_DIR = _ROOT / "config"


def get_available_runs() -> List[Dict[str, Any]]:
    """Returns all available runs sorted newest to oldest for the Run A & Run B selectors."""
    runs_file = _DATA_DIR / "runs.json"
    if not runs_file.exists():
        return []

    try:
        runs = json.loads(runs_file.read_text(encoding="utf-8")).get("runs", [])
    except Exception:
        return []

    runs.sort(key=lambda x: x.get("epoch", 0), reverse=True)
    return runs


def load_single_run_enriched(run_id: str) -> Optional[Dict[str, Any]]:
    """Loads a single test run enriched with its result JSON and SLA targets."""
    runs = get_available_runs()
    manifest_entry = next((r for r in runs if r.get("id") == run_id), None)
    if not manifest_entry:
        return None

    res_file = manifest_entry.get("result_file", f"{run_id}_result.json")
    res_path = _RESULTS_JSON_DIR / res_file
    if not res_path.exists():
        res_path = _RESULTS_DIR / res_file

    detail = {}
    if res_path.exists():
        try:
            detail = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    merged = dict(manifest_entry)
    merged["detail"] = detail

    jmx_name = merged.get("jmx_name") or detail.get("jmx_name") or "Unknown"
    merged["project"] = Path(jmx_name).stem.replace("_MultiUserStories", "").replace("_01", "").replace(" - Copy", "")

    from python_files.trend_engine import extract_label_hierarchy_map, classify_label_heuristic
    from python_files.sla_manager import load_sla_targets

    jmx_h_map = extract_label_hierarchy_map(jmx_name)
    sla_map, def_rt, def_err = load_sla_targets(jmx_name, actual_users=merged.get("users"))

    summary_data = detail.get("summary", {})
    dur_sec = float(summary_data.get("duration_sec", merged.get("duration_sec", 60.0))) or 60.0

    labels = detail.get("labels", {})
    transactions = []
    user_stories = set()

    for lbl, stats in labels.items():
        h_info = jmx_h_map.get(lbl) or classify_label_heuristic(lbl)
        story = h_info["user_story"]
        user_stories.add(story)

        sla_target = sla_map.get(lbl, {})
        target_rt = float(sla_target.get("rt", def_rt))
        target_err = float(sla_target.get("err", def_err))
        is_crit = bool(sla_target.get("is_critical", 0))

        avg_val = float(stats.get("avg", stats.get("avg_rt", stats.get("mean", 0))))
        p50_val = float(stats.get("median", stats.get("p50", avg_val)))
        p90_val = float(stats.get("p90", stats.get("pct90", avg_val)))
        p95_val = float(stats.get("p95", stats.get("pct95", p90_val)))
        p99_val = float(stats.get("p99", stats.get("pct99", p95_val)))
        err_rate = float(stats.get("error_pct", stats.get("error_rate", 0)))
        count_val = int(stats.get("count", stats.get("samples", 0)))
        errors_cnt = int(stats.get("errors", stats.get("error_count", 0)))

        raw_rate = stats.get("rate", stats.get("tps", stats.get("throughput")))
        if raw_rate is not None:
            tps_val = float(raw_rate)
        else:
            tps_val = round(count_val / max(dur_sec, 1.0), 2)

        is_passed = (p90_val <= target_rt) and (err_rate <= target_err)
        sla_margin = avg_val - target_rt  # positive = breach, negative = within SLA

        transactions.append({
            "transaction_name": lbl,
            "user_story": story,
            "item_type": h_info["item_type"],
            "item_type_label": h_info["item_type_label"],
            "parent_tc": h_info.get("parent_tc", ""),
            "depth": h_info.get("depth", 0),
            "avg_rt": round(avg_val, 2),
            "p50": round(p50_val, 2),
            "p90": round(p90_val, 2),
            "p95": round(p95_val, 2),
            "p99": round(p99_val, 2),
            "tps": round(tps_val, 2),
            "error_rate": round(err_rate, 2),
            "errors": errors_cnt,
            "samples": count_val,
            "sla_target_rt": target_rt,
            "sla_margin": round(sla_margin, 2),
            "is_critical": is_crit,
            "sla_status": "Pass" if is_passed else "Breach",
            "sla_passed": is_passed
        })

    merged["transactions"] = transactions
    merged["user_stories"] = sorted(list(user_stories)) if user_stories else ["Overall Scenario"]
    return merged


def build_run_comparison(
    run_a_id: str,
    run_b_id: str,
    project: str = "",
    user_story: str = "",
    item_type_filter: str = "TRANSACTIONS_ONLY"
) -> Dict[str, Any]:
    """
    Computes a complete, deep-dive 2-run comparison between Run A and Run B
    with the 8-10 core visualizations and compact analytical observations.
    """
    run_a = load_single_run_enriched(run_a_id)
    run_b = load_single_run_enriched(run_b_id)

    if not run_a or not run_b:
        return {"success": False, "message": "Could not load test run details for comparison."}

    # Filter allowed item types
    allowed_types = None
    if item_type_filter == "MAIN_TRANSACTION":
        allowed_types = {"MAIN_TRANSACTION"}
    elif item_type_filter == "SUB_TRANSACTION":
        allowed_types = {"SUB_TRANSACTION"}
    elif item_type_filter == "HTTP_REQUEST":
        allowed_types = {"HTTP_REQUEST"}
    elif item_type_filter == "TRANSACTIONS_ONLY":
        allowed_types = {"MAIN_TRANSACTION", "SUB_TRANSACTION"}

    tx_map_a = {t["transaction_name"]: t for t in run_a.get("transactions", [])}
    tx_map_b = {t["transaction_name"]: t for t in run_b.get("transactions", [])}

    all_tx_keys = set(tx_map_a.keys()).union(set(tx_map_b.keys()))
    filtered_keys = []
    for k in all_tx_keys:
        meta = tx_map_b.get(k) or tx_map_a.get(k)
        if user_story and meta.get("user_story") != user_story:
            continue
        if allowed_types and meta.get("item_type") not in allowed_types:
            continue
        filtered_keys.append(k)

    # Sort keys by hierarchy
    filtered_keys.sort(key=lambda k: (
        (tx_map_b.get(k) or tx_map_a.get(k)).get("user_story", ""),
        (tx_map_b.get(k) or tx_map_a.get(k)).get("depth", 0),
        k
    ))

    comparisons = []
    improved_cnt = 0
    degraded_cnt = 0
    unchanged_cnt = 0
    new_breaches = []
    resolved_breaches = []
    persistent_breaches = []
    persistent_passes = []

    for k in filtered_keys:
        ta = tx_map_a.get(k)
        tb = tx_map_b.get(k)
        meta = tb or ta

        a_rt = ta["avg_rt"] if ta else 0.0
        b_rt = tb["avg_rt"] if tb else 0.0
        rt_delta_abs = round(b_rt - a_rt, 2)
        rt_delta_pct = round(((b_rt - a_rt) / max(a_rt, 1e-6)) * 100, 2) if a_rt > 0 else 0.0

        a_tps = ta["tps"] if ta else 0.0
        b_tps = tb["tps"] if tb else 0.0
        tps_delta_pct = round(((b_tps - a_tps) / max(a_tps, 1e-6)) * 100, 2) if a_tps > 0 else 0.0

        a_err = ta["error_rate"] if ta else 0.0
        b_err = tb["error_rate"] if tb else 0.0
        err_delta_pp = round(b_err - a_err, 2)
        b_errors = tb["errors"] if tb else 0

        a_sla_st = ta["sla_status"] if ta else "Pass"
        b_sla_st = tb["sla_status"] if tb else "Pass"
        sla_target = meta["sla_target_rt"]
        is_crit = meta.get("is_critical", False)

        # SLA Transition Classification
        if a_sla_st == "Pass" and b_sla_st == "Breach":
            st_change = "New Breach"
            new_breaches.append(k)
        elif a_sla_st == "Breach" and b_sla_st == "Pass":
            st_change = "Resolved Breach"
            resolved_breaches.append(k)
        elif a_sla_st == "Breach" and b_sla_st == "Breach":
            st_change = "Persistent Breach"
            persistent_breaches.append(k)
        else:
            persistent_passes.append(k)
            if rt_delta_pct < -2.0:
                st_change = "Improved"
            elif rt_delta_pct > 2.0:
                st_change = "Degraded"
            else:
                st_change = "Unchanged"

        if rt_delta_pct < -2.0:
            improved_cnt += 1
        elif rt_delta_pct > 2.0:
            degraded_cnt += 1
        else:
            unchanged_cnt += 1

        # Percentiles
        p50_a = ta["p50"] if ta else 0.0
        p50_b = tb["p50"] if tb else 0.0
        p90_a = ta["p90"] if ta else 0.0
        p90_b = tb["p90"] if tb else 0.0
        p95_a = ta["p95"] if ta else 0.0
        p95_b = tb["p95"] if tb else 0.0
        p99_a = ta["p99"] if ta else 0.0
        p99_b = tb["p99"] if tb else 0.0

        # SLA Breach Margin (RT - SLA)
        sla_margin_a = round(a_rt - sla_target, 2)
        sla_margin_b = round(b_rt - sla_target, 2)

        # Matrix State per metric
        rt_state = "improved" if rt_delta_pct < -2.0 else ("degraded" if rt_delta_pct > 2.0 else "unchanged")
        p95_d_pct = round(((p95_b - p95_a)/max(p95_a, 1e-6))*100, 2) if p95_a > 0 else 0.0
        p95_state = "improved" if p95_d_pct < -2.0 else ("degraded" if p95_d_pct > 2.0 else "unchanged")
        tps_state = "improved" if tps_delta_pct > 2.0 else ("degraded" if tps_delta_pct < -2.0 else "unchanged")
        err_state = "degraded" if err_delta_pp > 0 else ("improved" if err_delta_pp < 0 else "unchanged")

        comparisons.append({
            "transaction": k,
            "user_story": meta.get("user_story", "Overall"),
            "item_type": meta.get("item_type", "SUB_TRANSACTION"),
            "item_type_label": meta.get("item_type_label", "Sub-Transaction"),
            "depth": meta.get("depth", 0),
            "is_critical": is_crit,
            "run_a_rt": a_rt,
            "run_b_rt": b_rt,
            "rt_delta_abs": rt_delta_abs,
            "rt_delta_pct": rt_delta_pct,
            "run_a_tps": a_tps,
            "run_b_tps": b_tps,
            "tps_delta_pct": tps_delta_pct,
            "run_a_err": a_err,
            "run_b_err": b_err,
            "err_delta_pp": err_delta_pp,
            "run_b_errors": b_errors,
            "sla_target": sla_target,
            "sla_margin_a": sla_margin_a,
            "sla_margin_b": sla_margin_b,
            "run_a_status": a_sla_st,
            "run_b_status": b_sla_st,
            "status_change": st_change,
            "percentiles": {
                "p50": {"run_a": p50_a, "run_b": p50_b, "delta_pct": round(((p50_b - p50_a) / max(p50_a, 1e-6)) * 100, 2) if p50_a > 0 else 0.0},
                "p90": {"run_a": p90_a, "run_b": p90_b, "delta_pct": round(((p90_b - p90_a) / max(p90_a, 1e-6)) * 100, 2) if p90_a > 0 else 0.0},
                "p95": {"run_a": p95_a, "run_b": p95_b, "delta_pct": p95_d_pct},
                "p99": {"run_a": p99_a, "run_b": p99_b, "delta_pct": round(((p99_b - p99_a) / max(p99_a, 1e-6)) * 100, 2) if p99_a > 0 else 0.0}
            },
            "matrix_states": {
                "rt": rt_state,
                "p95": p95_state,
                "tps": tps_state,
                "errors": err_state,
                "sla": b_sla_st
            }
        })

    # Overall Summary Scorecard Metrics
    tot = len(comparisons)
    a_avg_rt = round(sum(c["run_a_rt"] for c in comparisons) / max(tot, 1), 2)
    b_avg_rt = round(sum(c["run_b_rt"] for c in comparisons) / max(tot, 1), 2)
    rt_change_pct = round(((b_avg_rt - a_avg_rt) / max(a_avg_rt, 1e-6)) * 100, 2) if a_avg_rt > 0 else 0.0

    a_p95 = round(sum(c["percentiles"]["p95"]["run_a"] for c in comparisons) / max(tot, 1), 2)
    b_p95 = round(sum(c["percentiles"]["p95"]["run_b"] for c in comparisons) / max(tot, 1), 2)
    p95_change_pct = round(((b_p95 - a_p95) / max(a_p95, 1e-6)) * 100, 2) if a_p95 > 0 else 0.0

    a_p99 = round(sum(c["percentiles"]["p99"]["run_a"] for c in comparisons) / max(tot, 1), 2)
    b_p99 = round(sum(c["percentiles"]["p99"]["run_b"] for c in comparisons) / max(tot, 1), 2)
    p99_change_pct = round(((b_p99 - a_p99) / max(a_p99, 1e-6)) * 100, 2) if a_p99 > 0 else 0.0

    a_tps = round(sum(c["run_a_tps"] for c in comparisons), 2)
    b_tps = round(sum(c["run_b_tps"] for c in comparisons), 2)
    tps_change_pct = round(((b_tps - a_tps) / max(a_tps, 1e-6)) * 100, 2) if a_tps > 0 else 0.0

    a_err = round(sum(c["run_a_err"] for c in comparisons) / max(tot, 1), 2)
    b_err = round(sum(c["run_b_err"] for c in comparisons) / max(tot, 1), 2)
    err_change_pp = round(b_err - a_err, 2)

    a_pass_cnt = sum(1 for c in comparisons if c["run_a_status"] == "Pass")
    b_pass_cnt = sum(1 for c in comparisons if c["run_b_status"] == "Pass")
    a_pass_pct = round((a_pass_cnt / max(tot, 1)) * 100, 1)
    b_pass_pct = round((b_pass_cnt / max(tot, 1)) * 100, 1)
    sla_pass_change_pp = round(b_pass_pct - a_pass_pct, 1)

    scorecard = {
        "run_a_rt": a_avg_rt,
        "run_b_rt": b_avg_rt,
        "rt_change_pct": rt_change_pct,
        "run_a_p95": a_p95,
        "run_b_p95": b_p95,
        "p95_change_pct": p95_change_pct,
        "run_a_p99": a_p99,
        "run_b_p99": b_p99,
        "p99_change_pct": p99_change_pct,
        "run_a_tps": a_tps,
        "run_b_tps": b_tps,
        "tps_change_pct": tps_change_pct,
        "run_a_err": a_err,
        "run_b_err": b_err,
        "err_change_pp": err_change_pp,
        "run_a_sla_pass": a_pass_pct,
        "run_b_sla_pass": b_pass_pct,
        "sla_pass_change_pp": sla_pass_change_pp,
        "transactions_improved": improved_cnt,
        "transactions_degraded": degraded_cnt,
        "transactions_unchanged": unchanged_cnt,
        "new_sla_breaches": len(new_breaches),
        "resolved_sla_breaches": len(resolved_breaches),
        "persistent_breaches": len(persistent_breaches),
        "persistent_passes": len(persistent_passes)
    }

    # ─────────────────────────────────────────────────────────────
    # COMPACT GRAPH OBSERVATIONS (Exact numerical grounding)
    # ─────────────────────────────────────────────────────────────
    largest_deg_tx = max(comparisons, key=lambda x: x["rt_delta_pct"]) if comparisons else None
    largest_imp_tx = min(comparisons, key=lambda x: x["rt_delta_pct"]) if comparisons else None
    largest_tps_drop = min(comparisons, key=lambda x: x["tps_delta_pct"]) if comparisons else None

    # Exact bar counts matching chart sides (left = negative delta, right = positive delta)
    chart_imp_cnt = sum(1 for c in comparisons if c["rt_delta_pct"] < 0)
    chart_deg_cnt = sum(1 for c in comparisons if c["rt_delta_pct"] > 0)
    chart_zero_cnt = sum(1 for c in comparisons if c["rt_delta_pct"] == 0)

    imp_tx_plural = f"{chart_imp_cnt} transaction" if chart_imp_cnt == 1 else f"{chart_imp_cnt} transactions"
    deg_tx_plural = f"{chart_deg_cnt} transaction" if chart_deg_cnt == 1 else f"{chart_deg_cnt} transactions"

    max_deg_desc = f"{largest_deg_tx['transaction']} ({largest_deg_tx['rt_delta_pct']:+.2f}%)" if (largest_deg_tx and largest_deg_tx['rt_delta_pct'] > 0) else "None"
    max_imp_desc = f"{largest_imp_tx['transaction']} ({largest_imp_tx['rt_delta_pct']:+.2f}%)" if (largest_imp_tx and largest_imp_tx['rt_delta_pct'] < 0) else "None"

    graph_observations = {
        "overall_performance": f"Average response time {'increased' if rt_change_pct > 0 else 'decreased'} by {abs(rt_change_pct):.2f}% ({a_avg_rt:.2f}ms → {b_avg_rt:.2f}ms), with P95 latency shifting by {p95_change_pct:+.2f}% and P99 by {p99_change_pct:+.2f}%.",
        "tx_rt_grouped": f"{deg_tx_plural} degraded while {imp_tx_plural} improved." + (f" Largest regression: {max_deg_desc}." if max_deg_desc != "None" else ""),
        "rt_change_diverging": f"{imp_tx_plural} improved to the left while {deg_tx_plural} degraded to the right. Max degradation: {max_deg_desc}; max improvement: {max_imp_desc}.",
        "sla_compliance_stacked": f"Overall SLA compliance shifted from {a_pass_pct:.1f}% in Run A to {b_pass_pct:.1f}% in Run B ({sla_pass_change_pp:+.1f} percentage points).",
        "sla_transition_matrix": f"SLA transitions: {len(new_breaches)} new breaches, {len(resolved_breaches)} resolved breaches, {len(persistent_breaches)} persistent breaches, and {len(persistent_passes)} persistent passes.",
        "throughput_grouped": f"Aggregate throughput changed by {tps_change_pct:+.2f}% ({a_tps:.2f} TPS → {b_tps:.2f} TPS)." + (f" Largest throughput drop in {largest_tps_drop['transaction']} ({largest_tps_drop['tps_delta_pct']:+.2f}%)." if largest_tps_drop and largest_tps_drop['tps_delta_pct'] < 0 else ""),
        "error_rate_grouped": f"Overall error rate shifted by {err_change_pp:+.2f} pp ({a_err:.2f}% in Run A → {b_err:.2f}% in Run B).",
        "percentile_distribution": f"Tail latency comparison: P50 changed by {round(((b_avg_rt - a_avg_rt)/max(a_avg_rt, 1e-6))*100, 2):+.2f}%, P90 by {round(((b_p95 - a_p95)/max(a_p95, 1e-6))*100, 2):+.2f}%, P95 by {p95_change_pct:+.2f}%, and P99 by {p99_change_pct:+.2f}%.",
        "tx_performance_heatmap": f"Comprehensive health matrix scanned across {tot} transactions."
    }

    # ─────────────────────────────────────────────────────────────
    # 5 COMPARISON RANKINGS
    # ─────────────────────────────────────────────────────────────
    biggest_degradation = sorted([c for c in comparisons if c["rt_delta_pct"] > 0], key=lambda x: x["rt_delta_pct"], reverse=True)[:5]
    biggest_improvement = sorted([c for c in comparisons if c["rt_delta_pct"] < 0], key=lambda x: x["rt_delta_pct"])[:5]
    largest_sla_breach = sorted([c for c in comparisons if c["sla_margin_b"] > 0], key=lambda x: x["sla_margin_b"], reverse=True)[:5]
    largest_tps_change = sorted(comparisons, key=lambda x: abs(x["tps_delta_pct"]), reverse=True)[:5]
    highest_error_increase = sorted([c for c in comparisons if c["err_delta_pp"] > 0 or c["run_b_errors"] > 0], key=lambda x: (x["err_delta_pp"], x["run_b_errors"]), reverse=True)[:5]

    def _fmt_rank(rank_list, key_metric):
        res = []
        for i, item in enumerate(rank_list, 1):
            res.append({
                "rank": i,
                "transaction": item["transaction"],
                "item_type": item["item_type"],
                "run_a_rt": item["run_a_rt"],
                "run_b_rt": item["run_b_rt"],
                "delta_pct": item["rt_delta_pct"],
                "improvement_pct": abs(item["rt_delta_pct"]),
                "breach_margin_ms": item["sla_margin_b"],
                "sla_target": item["sla_target"],
                "run_a_tps": item["run_a_tps"],
                "run_b_tps": item["run_b_tps"],
                "tps_delta_pct": item["tps_delta_pct"],
                "run_a_err": item["run_a_err"],
                "run_b_err": item["run_b_err"],
                "err_delta_pp": item["err_delta_pp"],
                "run_b_errors": item["run_b_errors"]
            })
        return res

    rankings = {
        "biggest_degradation": _fmt_rank(biggest_degradation, "rt_delta_pct"),
        "biggest_improvement": _fmt_rank(biggest_improvement, "rt_delta_pct"),
        "largest_sla_breach": _fmt_rank(largest_sla_breach, "sla_margin_b"),
        "largest_throughput_change": _fmt_rank(largest_tps_change, "tps_delta_pct"),
        "highest_error_increase": _fmt_rank(highest_error_increase, "err_delta_pp")
    }

    # Concise Executive Comparison AI Insights (Strictly factual)
    ai_findings = [
        f"**Response Time Shift:** Average latency changed by **{rt_change_pct:+.2f}%** from **{a_avg_rt:.2f}ms in Run A** to **{b_avg_rt:.2f}ms in Run B** (P95: **{p95_change_pct:+.2f}%**, P99: **{p99_change_pct:+.2f}%**).",
        f"**SLA Compliance:** SLA pass rate changed from **{a_pass_pct:.1f}% to {b_pass_pct:.1f}% ({sla_pass_change_pp:+.1f} percentage points)**.",
        f"**Transaction State Transitions:** Recorded **{len(new_breaches)} new SLA breaches**, **{len(resolved_breaches)} resolved breaches**, **{improved_cnt} improved**, and **{degraded_cnt} degraded** transactions.",
        f"**Throughput & Errors:** Aggregate throughput shifted by **{tps_change_pct:+.2f}% ({a_tps:.2f} → {b_tps:.2f} TPS)**; error rate changed by **{err_change_pp:+.2f} pp**."
    ]

    return {
        "success": True,
        "metadata": {
            "project": project or run_b.get("project", "Default Project"),
            "user_story": user_story or "All User Journeys",
            "item_type_filter": item_type_filter or "TRANSACTIONS_ONLY",
            "run_a": {
                "id": run_a_id,
                "users": run_a.get("users", 1),
                "timestamp": run_a.get("timestamp", ""),
                "environment": run_a.get("environment", "QA"),
                "build_version": run_a.get("build_version", "")
            },
            "run_b": {
                "id": run_b_id,
                "users": run_b.get("users", 1),
                "timestamp": run_b.get("timestamp", ""),
                "environment": run_b.get("environment", "QA"),
                "build_version": run_b.get("build_version", "")
            }
        },
        "scorecard": scorecard,
        "graph_observations": graph_observations,
        "ai_findings": ai_findings,
        "sla_transitions": {
            "new_breaches": new_breaches,
            "resolved_breaches": resolved_breaches,
            "persistent_breaches": persistent_breaches,
            "persistent_passes": persistent_passes
        },
        "transaction_comparisons": comparisons,
        "rankings": rankings
    }


def generate_run_comparison_html(comp_data: Dict[str, Any]) -> str:
    """Renders a complete, standalone Run Comparison Engineering Report in HTML with active SVG charts and observation strips."""
    meta = comp_data.get("metadata", {})
    card = comp_data.get("scorecard", {})
    obs = comp_data.get("graph_observations", {})
    findings = comp_data.get("ai_findings", [])
    rows = comp_data.get("transaction_comparisons", [])
    trans = comp_data.get("sla_transitions", {})
    run_a = meta.get("run_a", {})
    run_b = meta.get("run_b", {})

    bullets_html = "".join([f"<li>{b.replace('**', '<strong>').replace('**', '</strong>')}</li>" for b in findings])

    # Table rows
    table_rows = ""
    for r in rows:
        d = r["rt_delta_pct"]
        d_col = "#dc2626" if d > 0 else "#059669"
        depth = r.get("depth", 0)
        indent = depth * 16
        i_type = r.get("item_type", "SUB_TRANSACTION")
        t_badge = "MAIN" if i_type == "MAIN_TRANSACTION" else ("SUB" if i_type == "SUB_TRANSACTION" else "REQ")
        badge_style = "background:#e0f2fe; color:#0369a1;" if i_type == "MAIN_TRANSACTION" else ("background:#fef3c7; color:#b45309;" if i_type == "SUB_TRANSACTION" else "background:#f1f5f9; color:#475569;")

        st_change = r.get("status_change", "Unchanged")
        st_style = "background:#fef2f2; color:#dc2626; border:1px solid #fecaca;" if st_change == "New Breach" else ("background:#ecfdf5; color:#059669; border:1px solid #a7f3d0;" if st_change in ("Resolved Breach", "Improved") else ("background:#fffbeb; color:#d97706; border:1px solid #fde68a;" if st_change == "Degraded" else "background:#f1f5f9; color:#64748b;"))

        table_rows += f"""
        <tr>
            <td>
                <div style="padding-left:{indent}px; display:flex; align-items:center; gap:0.4rem;">
                    <span style="font-size:0.65rem; font-weight:bold; padding:1px 4px; border-radius:3px; {badge_style}">{t_badge}</span>
                    <span><strong>{r['transaction']}</strong></span>
                </div>
            </td>
            <td><small style="color:#64748b;">{r['user_story']}</small></td>
            <td style="text-align:right;">{r['run_a_rt']:.2f} ms</td>
            <td style="text-align:right;">{r['run_b_rt']:.2f} ms</td>
            <td style="text-align:right; font-weight:bold; color:{d_col};">{d:+.2f}%</td>
            <td style="text-align:right;">{r['run_a_tps']:.2f} / {r['run_b_tps']:.2f}</td>
            <td style="text-align:right;">{r['sla_target']:.0f} ms</td>
            <td style="text-align:center;"><span style="font-size:0.75rem; font-weight:bold; padding:2px 6px; border-radius:4px; {'background:#ecfdf5; color:#059669;' if r['run_a_status']=='Pass' else 'background:#fef2f2; color:#dc2626;'}">{r['run_a_status']}</span></td>
            <td style="text-align:center;"><span style="font-size:0.75rem; font-weight:bold; padding:2px 6px; border-radius:4px; {'background:#ecfdf5; color:#059669;' if r['run_b_status']=='Pass' else 'background:#fef2f2; color:#dc2626;'}">{r['run_b_status']}</span></td>
            <td style="text-align:center;"><span style="font-size:0.75rem; font-weight:bold; padding:2px 6px; border-radius:4px; {st_style}">{st_change}</span></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
    <meta charset="UTF-8">
    <title>Run Comparison Engineering Report — {run_a.get('id')} vs {run_b.get('id')}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface2: #334155;
            --surface3: #1e293b;
            --border: #475569;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent-bg: rgba(56, 189, 248, 0.1);
            --green: #10b981;
            --green-bg: rgba(16, 185, 129, 0.1);
            --yellow: #f59e0b;
            --yellow-bg: rgba(245, 158, 11, 0.1);
            --red: #ef4444;
            --red-bg: rgba(239, 68, 68, 0.1);
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; padding: 2rem; }}
        .header-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.75rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }}
        .header-title {{ font-size: 1.5rem; font-weight: 800; color: var(--text); display: flex; align-items: center; justify-content: space-between; }}
        .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 0.85rem; margin-top: 1.25rem; }}
        .meta-item {{ background: var(--surface2); padding: 0.65rem 0.85rem; border-radius: 8px; border: 1px solid var(--border); }}
        .meta-label {{ font-size: 0.72rem; text-transform: uppercase; color: var(--muted); font-weight: 700; letter-spacing: 0.05em; }}
        .meta-val {{ font-size: 0.95rem; font-weight: 600; color: var(--text); margin-top: 0.15rem; }}

        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem; }}
        .kpi-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.25rem; box-shadow: var(--shadow); text-align: center; }}
        .kpi-title {{ font-size: 0.75rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
        .kpi-value {{ font-size: 1.45rem; font-weight: 800; color: var(--text); margin: 0.35rem 0; }}
        .kpi-delta {{ font-size: 0.82rem; font-weight: 700; }}

        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }}
        h2 {{ color: var(--text); font-size: 1.15rem; font-weight: 700; margin-bottom: 1rem; }}
        
        .bullet-box {{ background: var(--surface2); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 1.25rem; border-radius: 10px; margin-bottom: 1.5rem; }}
        .bullet-box ul {{ margin-left: 1.25rem; }}
        .bullet-box li {{ margin-bottom: 0.35rem; color: var(--text); font-size: 0.92rem; }}

        .obs-strip {{ background: var(--surface2); border: 1px solid var(--border); border-top: 1px dashed var(--accent); padding: 0.75rem 1rem; font-size: 0.85rem; color: var(--text); font-weight: 500; margin-top: 1rem; border-radius: 6px; }}
        .obs-strip strong {{ color: var(--accent); }}

        .trans-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-top: 1rem; }}
        .trans-box {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }}
        .trans-num {{ font-size: 1.6rem; font-weight: 800; margin-top: 0.2rem; color: var(--text); }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
        th {{ background: var(--surface2); text-align: left; color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.05em; }}
        td {{ color: var(--text); }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
    </style>
</head>
<body>

    <!-- 1. Header -->
    <div class="header-card">
        <div class="header-title">
            <span>Run Comparison Engineering Report</span>
            <span style="font-size:0.8rem; background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd; padding:3px 8px; border-radius:4px; font-weight:700;">2-Run Deep Dive</span>
        </div>
        <div class="meta-grid">
            <div class="meta-item"><div class="meta-label">Project</div><div class="meta-val">{meta.get('project')}</div></div>
            <div class="meta-item"><div class="meta-label">User Journey Scope</div><div class="meta-val">{meta.get('user_story')}</div></div>
            <div class="meta-item"><div class="meta-label">Hierarchy Scope</div><div class="meta-val">{meta.get('item_type_filter')}</div></div>
            <div class="meta-item"><div class="meta-label">Run A (Baseline)</div><div class="meta-val">{run_a.get('id')} ({run_a.get('users')} Users)</div></div>
            <div class="meta-item"><div class="meta-label">Run B (Target)</div><div class="meta-val">{run_b.get('id')} ({run_b.get('users')} Users)</div></div>
        </div>
    </div>

    <!-- 2. AI Executive Findings -->
    <div class="card">
        <h2>Executive Comparison Synthesis</h2>
        <div class="bullet-box">
            <ul>
                {bullets_html}
            </ul>
        </div>
    </div>

    <!-- 3. Overall Performance Split Cards -->
    <div class="card">
        <h2>1. Overall Performance — Run A vs Run B</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Average Response Time</div>
                <div class="kpi-value">{card.get('run_a_rt', 0):.2f}ms → {card.get('run_b_rt', 0):.2f}ms</div>
                <div class="kpi-delta" style="color:{'#dc2626' if card.get('rt_change_pct', 0) > 0 else '#059669'};">
                    {card.get('rt_change_pct', 0):+.2f}%
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">P95 Response Time</div>
                <div class="kpi-value">{card.get('run_a_p95', 0):.2f}ms → {card.get('run_b_p95', 0):.2f}ms</div>
                <div class="kpi-delta" style="color:{'#dc2626' if card.get('p95_change_pct', 0) > 0 else '#059669'};">
                    {card.get('p95_change_pct', 0):+.2f}%
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">P99 Response Time</div>
                <div class="kpi-value">{card.get('run_a_p99', 0):.2f}ms → {card.get('run_b_p99', 0):.2f}ms</div>
                <div class="kpi-delta" style="color:{'#dc2626' if card.get('p99_change_pct', 0) > 0 else '#059669'};">
                    {card.get('p99_change_pct', 0):+.2f}%
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Aggregate Throughput (TPS)</div>
                <div class="kpi-value">{card.get('run_a_tps', 0):.2f} → {card.get('run_b_tps', 0):.2f}</div>
                <div class="kpi-delta" style="color:{'#059669' if card.get('tps_change_pct', 0) > 0 else '#dc2626'};">
                    {card.get('tps_change_pct', 0):+.2f}%
                </div>
            </div>
        </div>
        <div class="obs-strip">
            <strong>Observation:</strong> {obs.get('overall_performance', '')}
        </div>
    </div>

    <!-- 4. SLA Status Transition Matrix -->
    <div class="card">
        <h2>5. SLA Status Transition Matrix</h2>
        <div class="trans-grid">
            <div class="trans-box">
                <div style="font-size:0.75rem; font-weight:700; color:#059669; text-transform:uppercase;">Pass → Pass</div>
                <div class="trans-num" style="color:#059669;">{len(trans.get('persistent_passes', []))}</div>
                <div style="font-size:0.72rem; color:#64748b;">Persistent Passes</div>
            </div>
            <div class="trans-box">
                <div style="font-size:0.75rem; font-weight:700; color:#dc2626; text-transform:uppercase;">Pass → Breach</div>
                <div class="trans-num" style="color:#dc2626;">{len(trans.get('new_breaches', []))}</div>
                <div style="font-size:0.72rem; color:#dc2626; font-weight:600;">New Breaches</div>
            </div>
            <div class="trans-box">
                <div style="font-size:0.75rem; font-weight:700; color:#059669; text-transform:uppercase;">Breach → Pass</div>
                <div class="trans-num" style="color:#059669;">{len(trans.get('resolved_breaches', []))}</div>
                <div style="font-size:0.72rem; color:#059669; font-weight:600;">Resolved Breaches</div>
            </div>
            <div class="trans-box">
                <div style="font-size:0.75rem; font-weight:700; color:#d97706; text-transform:uppercase;">Breach → Breach</div>
                <div class="trans-num" style="color:#d97706;">{len(trans.get('persistent_breaches', []))}</div>
                <div style="font-size:0.72rem; color:#64748b;">Persistent Breaches</div>
            </div>
        </div>
        <div class="obs-strip">
            <strong>Observation:</strong> {obs.get('sla_transition_matrix', '')}
        </div>
    </div>

    <!-- 5. Granular Transaction Comparison Table -->
    <div class="card">
        <h2>Detailed Transaction Performance Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Hierarchy Item</th>
                    <th>User Journey</th>
                    <th style="text-align:right;">Run A RT</th>
                    <th style="text-align:right;">Run B RT</th>
                    <th style="text-align:right;">Change %</th>
                    <th style="text-align:right;">TPS (A / B)</th>
                    <th style="text-align:right;">SLA Target</th>
                    <th style="text-align:center;">Run A</th>
                    <th style="text-align:center;">Run B</th>
                    <th style="text-align:center;">Status Change</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

</body>
</html>"""
    return html
