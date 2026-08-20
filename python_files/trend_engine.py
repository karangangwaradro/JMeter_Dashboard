#!/usr/bin/env python3
"""
trend_engine.py — Performance Intelligence & Trend Analysis Engine for JmeterAI.

Implements:
1. Hierarchical Data Normalization (Project -> User Story -> Transaction -> Test Run)
2. Contextual Load Normalization & Regression Detection
3. Transparent Performance Health Score (0–100)
4. Arbitrary Multi-Run Comparison Matrix
5. Trend Time-Series Extractor
6. Standalone Executive Comparison Report HTML Generator
"""

import os
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

_ROOT = Path(__file__).parent.parent.resolve()
_DATA_DIR = _ROOT / "data"
_RESULTS_DIR = _ROOT / "Results"
_RESULTS_JSON_DIR = _RESULTS_DIR / "json"


def load_all_runs_data() -> List[Dict[str, Any]]:
    """Loads all test runs from runs.json enriched with individual run JSON data."""
    runs_file = _DATA_DIR / "runs.json"
    if not runs_file.exists():
        return []

    try:
        runs_manifest = json.loads(runs_file.read_text(encoding="utf-8")).get("runs", [])
    except Exception:
        return []

    enriched_runs = []
    for r in runs_manifest:
        run_id = r.get("id")
        res_file_name = r.get("result_file", f"{run_id}_result.json")
        res_path = _RESULTS_JSON_DIR / res_file_name
        if not res_path.exists():
            res_path = _RESULTS_DIR / res_file_name

        run_detail = {}
        if res_path.exists():
            try:
                run_detail = json.loads(res_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Merge summary metrics
        merged = dict(r)
        merged["detail"] = run_detail
        
        # Determine Project / Script Name
        jmx_name = r.get("jmx_name") or run_detail.get("jmx_name") or "Unknown Project"
        project_name = Path(jmx_name).stem.replace("_MultiUserStories", "").replace("_01", "").replace(" - Copy", "")
        merged["project"] = project_name
        merged["build_version"] = r.get("build_version") or run_detail.get("build_version") or "v1.0.0"
        merged["environment"] = r.get("environment") or run_detail.get("environment") or "UAT"

        # Parse Thread Groups (User Stories) from JMX if available
        jmx_path = _ROOT / "Tests" / jmx_name
        tg_info = []
        if jmx_path.exists():
            try:
                from python_files.sla_manager import parse_jmx_thread_groups
                tg_info = parse_jmx_thread_groups(jmx_path)
            except Exception:
                pass

        # Build mapping from TC/sampler label to Thread Group (User Story)
        label_to_story = {}
        for tg in tg_info:
            tg_name = tg.get("name", "").strip()
            if not tg_name:
                continue
            # ThreadGroup name is the User Story
            if tg.get("wrapper_tc"):
                label_to_story[tg["wrapper_tc"]] = tg_name
            for c_tc in tg.get("child_tcs", []):
                label_to_story[c_tc] = tg_name

        # Parse transactions & user stories from detail
        summary = run_detail.get("summary", {})
        labels = run_detail.get("labels", {})
        
        # User stories / Transactions map
        transactions = []
        user_stories = set()

        if labels:
            for lbl, stats in labels.items():
                # Check if label matches a ThreadGroup / TC mapping
                story = label_to_story.get(lbl)
                if not story:
                    # Fallback heuristic: TC prefix (e.g. TC01, TC02, TC03) or split prefix
                    parts = lbl.split("-", 1) if "-" in lbl else (lbl.split("_", 1) if "_" in lbl else [lbl])
                    first_token = parts[0].strip()
                    if first_token.upper().startswith("TC") or first_token.upper().startswith("T"):
                        story = first_token
                    else:
                        story = "Overall Scenario"

                user_stories.add(story)

                tx_data = {
                    "transaction_name": lbl,
                    "user_story": story,
                    "sample_count": stats.get("samples", stats.get("count", 0)),
                    "avg_rt": round(stats.get("avg", stats.get("mean", 0)), 2),
                    "p50": round(stats.get("median", stats.get("p50", stats.get("avg", 0))), 2),
                    "p90": round(stats.get("p90", stats.get("pct90", 0)), 2),
                    "p95": round(stats.get("p95", stats.get("pct95", 0)), 2),
                    "p99": round(stats.get("p99", stats.get("pct99", 0)), 2),
                    "min": stats.get("min", 0),
                    "max": stats.get("max", 0),
                    "throughput": round(stats.get("throughput", stats.get("tps", 0)), 2),
                    "error_rate": round(stats.get("error_pct", stats.get("error_rate", 0)), 2),
                    "failed_count": stats.get("errors", stats.get("failed", 0)),
                    "sla_rt_target": stats.get("sla_rt_target", 1000),
                    "sla_pass_rate": 100.0 if stats.get("error_pct", 0) < 5 and stats.get("p95", 0) <= 2000 else (50.0 if stats.get("p95", 0) <= 3000 else 0.0)
                }
                transactions.append(tx_data)
        
        merged["transactions"] = transactions
        merged["user_stories"] = sorted(list(user_stories)) if user_stories else ["Overall Scenario"]
        enriched_runs.append(merged)

    # Sort chronologically by epoch or timestamp
    enriched_runs.sort(key=lambda x: x.get("epoch", 0))
    return enriched_runs


def get_hierarchy_tree() -> Dict[str, Any]:
    """Returns the Project -> User Story -> Transaction hierarchy tree."""
    runs = load_all_runs_data()
    hierarchy = {}

    for r in runs:
        proj = r.get("project", "Default Project")
        if proj not in hierarchy:
            hierarchy[proj] = {}

        txs = r.get("transactions", [])
        if not txs:
            if "Overall" not in hierarchy[proj]:
                hierarchy[proj]["Overall"] = set()
            hierarchy[proj]["Overall"].add("Overall Benchmark")
        else:
            for tx in txs:
                story = tx.get("user_story", "Overall")
                tx_name = tx.get("transaction_name", "Transaction")
                if story not in hierarchy[proj]:
                    hierarchy[proj][story] = set()
                hierarchy[proj][story].add(tx_name)

    # Convert sets to sorted lists
    formatted = {}
    for proj, stories in hierarchy.items():
        formatted[proj] = {}
        for story, tx_set in stories.items():
            formatted[proj][story] = sorted(list(tx_set))

    return {"hierarchy": formatted}


def calculate_health_score(metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes a transparent 0-100 Performance Health Score.
    Weightings:
      - Response Time Score (30%)
      - P95 Response Time Score (25%)
      - Throughput Efficiency Score (20%)
      - Reliability / Error Score (15%)
      - SLA Compliance Score (10%)
    """
    avg_rt = metrics.get("avg_rt", 500)
    p95_rt = metrics.get("p95_rt", 1000)
    throughput = metrics.get("throughput", 10)
    users = max(metrics.get("users", 1), 1)
    error_rate = metrics.get("error_rate", 0)
    sla_pass = metrics.get("sla_pass_pct", 100.0 if error_rate < 1 else 80.0)

    # 1. RT Score (100 if <200ms, linear drop to 0 at 3000ms)
    rt_score = max(0, min(100, 100 - ((avg_rt - 200) / 28))) if avg_rt > 200 else 100

    # 2. P95 Score (100 if <500ms, linear drop to 0 at 5000ms)
    p95_score = max(0, min(100, 100 - ((p95_rt - 500) / 45))) if p95_rt > 500 else 100

    # 3. Throughput efficiency (TPS per virtual user ratio)
    tps_per_user = throughput / users
    tp_score = min(100, max(20, tps_per_user * 20))

    # 4. Error Score (100 if 0% errors, 0 if >10% errors)
    err_score = max(0, 100 - (error_rate * 10))

    # 5. SLA Score
    sla_score = max(0, min(100, sla_pass))

    # Weighted Composite
    health_score = round(
        (rt_score * 0.30) +
        (p95_score * 0.25) +
        (tp_score * 0.20) +
        (err_score * 0.15) +
        (sla_score * 0.10),
        1
    )

    return {
        "score": health_score,
        "breakdown": {
            "response_time": round(rt_score, 1),
            "p95": round(p95_score, 1),
            "throughput": round(tp_score, 1),
            "error_rate": round(err_score, 1),
            "sla_compliance": round(sla_score, 1)
        }
    }


def get_trend_analysis(project: str = "", user_story: str = "", transaction: str = "", limit: int = 10) -> Dict[str, Any]:
    """Generates time-series trend data for specific dimensional scope."""
    runs = load_all_runs_data()
    
    # Filter by project if specified
    if project:
        runs = [r for r in runs if r.get("project") == project]

    # Limit to latest N runs
    runs = runs[-limit:] if len(runs) > limit else runs

    trend_series = []
    for r in runs:
        run_id = r.get("id")
        ts = r.get("timestamp", "")
        users = r.get("users", 1)
        
        # Default run-level metrics
        avg_rt = r.get("avg_rt", 0)
        p95_rt = r.get("p95_rt", 0)
        tp = r.get("throughput", 0)
        err = r.get("error_rate", 0)
        sla_pct = 100.0 if err < 1 else max(0.0, 100.0 - err * 5)

        # If specific transaction or user story selected, recalculate scoped metrics
        txs = r.get("transactions", [])
        if transaction and txs:
            matching_txs = [t for t in txs if t.get("transaction_name") == transaction]
            if matching_txs:
                t_item = matching_txs[0]
                avg_rt = t_item.get("avg_rt", avg_rt)
                p95_rt = t_item.get("p95", p95_rt)
                tp = t_item.get("throughput", tp)
                err = t_item.get("error_rate", err)
                sla_pct = t_item.get("sla_pass_rate", sla_pct)
        elif user_story and txs:
            matching_txs = [t for t in txs if t.get("user_story") == user_story]
            if matching_txs:
                avg_rt = round(sum(t.get("avg_rt", 0) for t in matching_txs) / len(matching_txs), 2)
                p95_rt = round(max(t.get("p95", 0) for t in matching_txs), 2)
                tp = round(sum(t.get("throughput", 0) for t in matching_txs), 2)
                err = round(sum(t.get("error_rate", 0) for t in matching_txs) / len(matching_txs), 2)

        health = calculate_health_score({
            "avg_rt": avg_rt,
            "p95_rt": p95_rt,
            "throughput": tp,
            "users": users,
            "error_rate": err,
            "sla_pass_pct": sla_pct
        })

        trend_series.append({
            "run_id": run_id,
            "timestamp": ts,
            "users": users,
            "avg_rt": avg_rt,
            "p95_rt": p95_rt,
            "throughput": tp,
            "error_rate": err,
            "sla_pass_pct": sla_pct,
            "health_score": health["score"],
            "health_breakdown": health["breakdown"]
        })

    # Compute baseline vs latest delta
    latest = trend_series[-1] if trend_series else {}
    first = trend_series[0] if trend_series else {}

    delta_health = round(latest.get("health_score", 0) - first.get("health_score", 0), 1) if (latest and first) else 0
    delta_rt = round(((latest.get("avg_rt", 0) - first.get("avg_rt", 0)) / max(first.get("avg_rt", 1), 1)) * 100, 1) if (latest and first) else 0
    delta_p95 = round(((latest.get("p95_rt", 0) - first.get("p95_rt", 0)) / max(first.get("p95_rt", 1), 1)) * 100, 1) if (latest and first) else 0
    delta_tp = round(((latest.get("throughput", 0) - first.get("throughput", 0)) / max(first.get("throughput", 1), 1)) * 100, 1) if (latest and first) else 0
    delta_err = round(latest.get("error_rate", 0) - first.get("error_rate", 0), 1) if (latest and first) else 0

    return {
        "scope": {
            "project": project or "All Projects",
            "user_story": user_story or "All Stories",
            "transaction": transaction or "All Transactions"
        },
        "series": trend_series,
        "summary": {
            "current_health": latest.get("health_score", 0),
            "delta_health": delta_health,
            "delta_rt_pct": delta_rt,
            "delta_p95_pct": delta_p95,
            "delta_tp_pct": delta_tp,
            "delta_err_pts": delta_err
        }
    }


def compare_runs(run_ids: List[str]) -> Dict[str, Any]:
    """Generates comparison matrix and regression detection across arbitrary selected runs."""
    all_runs = load_all_runs_data()
    run_map = {r.get("id"): r for r in all_runs}

    selected_runs = [run_map[rid] for rid in run_ids if rid in run_map]
    if not selected_runs:
        # Fallback to latest up to 5 runs
        selected_runs = all_runs[-5:]

    # Matrix Table Data
    matrix = []
    metrics_to_compare = [
        ("Avg Response Time", "avg_rt", "ms", "lower"),
        ("P95 Response Time", "p95_rt", "ms", "lower"),
        ("Throughput", "throughput", "req/s", "higher"),
        ("Error Rate", "error_rate", "%", "lower"),
        ("Virtual Users", "users", "users", "neutral"),
    ]

    base_run = selected_runs[0]
    last_run = selected_runs[-1]

    for label, key, unit, pref in metrics_to_compare:
        row = {"metric": label, "unit": unit, "values": []}
        for r in selected_runs:
            val = r.get(key, 0)
            row["values"].append(val)
        
        # Calculate trend delta from base to last
        b_val = row["values"][0]
        l_val = row["values"][-1]

        if b_val == 0:
            pct_change = 0.0
        else:
            pct_change = round(((l_val - b_val) / b_val) * 100, 1)

        row["pct_change"] = pct_change

        # Determine indicator arrow & color
        if pref == "lower":
            if pct_change < 0:
                row["trend_str"] = f"↓ {abs(pct_change)}%"
                row["status"] = "improved"
            elif pct_change > 0:
                row["trend_str"] = f"↑ {pct_change}%"
                row["status"] = "degraded"
            else:
                row["trend_str"] = "→ 0%"
                row["status"] = "neutral"
        elif pref == "higher":
            if pct_change > 0:
                row["trend_str"] = f"↑ {pct_change}%"
                row["status"] = "improved"
            elif pct_change < 0:
                row["trend_str"] = f"↓ {abs(pct_change)}%"
                row["status"] = "degraded"
            else:
                row["trend_str"] = "→ 0%"
                row["status"] = "neutral"
        else:
            row["trend_str"] = f"{'↑' if pct_change > 0 else '↓'} {abs(pct_change)}%"
            row["status"] = "neutral"

        matrix.append(row)

    # Contextual Load Normalization Analysis
    base_users = max(base_run.get("users", 1), 1)
    last_users = max(last_run.get("users", 1), 1)
    user_delta_pct = round(((last_users - base_users) / base_users) * 100, 1)

    base_rt = base_run.get("avg_rt", 1)
    last_rt = last_run.get("avg_rt", 1)
    rt_delta_pct = round(((last_rt - base_rt) / max(base_rt, 1)) * 100, 1)

    load_normalization_insight = ""
    if user_delta_pct > 0:
        if rt_delta_pct <= (user_delta_pct * 0.5):
            load_normalization_insight = f"🟢 Efficient Scaling: Concurrent load increased by {user_delta_pct}% while response time increased by only {rt_delta_pct}%, demonstrating strong platform resilience."
        else:
            load_normalization_insight = f"🔴 Capacity Strain: Load increased by {user_delta_pct}% causing a disproportionate {rt_delta_pct}% rise in response time."
    elif user_delta_pct < 0:
        load_normalization_insight = f"ℹ️ Reduced Load Context: Load decreased by {abs(user_delta_pct)}%. Response time changed by {rt_delta_pct}%."
    else:
        load_normalization_insight = f"ℹ️ Equal Load Context: Virtual user count remained constant ({base_users} users)."

    # Automated Regression & Improvement Findings
    regressions = []
    improvements = []

    if rt_delta_pct > 15:
        regressions.append({
            "title": "Response Time Regression",
            "detail": f"Avg Response Time degraded from {base_rt} ms to {last_rt} ms ({rt_delta_pct:+}%).",
            "severity": "CRITICAL"
        })
    elif rt_delta_pct < -10:
        improvements.append({
            "title": "Response Time Improvement",
            "detail": f"Avg Response Time improved from {base_rt} ms to {last_rt} ms ({rt_delta_pct}%).",
            "impact": "HIGH"
        })

    base_err = base_run.get("error_rate", 0)
    last_err = last_run.get("error_rate", 0)
    if last_err > base_err + 1.0:
        regressions.append({
            "title": "Error Rate Spike",
            "detail": f"Error rate increased from {base_err}% to {last_err}%.",
            "severity": "HIGH"
        })
    elif last_err < base_err:
        improvements.append({
            "title": "Reliability Gain",
            "detail": f"Error rate decreased from {base_err}% to {last_err}%.",
            "impact": "HIGH"
        })

    tp_delta_pct = matrix[2]["pct_change"]
    if tp_delta_pct > 15:
        improvements.append({
            "title": "Throughput Boost",
            "detail": f"Throughput increased by {tp_delta_pct}% ({base_run.get('throughput')} → {last_run.get('throughput')} req/s).",
            "impact": "MEDIUM"
        })

    # Identify Best and Worst Runs
    best_run = min(selected_runs, key=lambda x: (x.get("error_rate", 100), x.get("avg_rt", 99999)))
    worst_run = max(selected_runs, key=lambda x: (x.get("error_rate", 0), x.get("avg_rt", 0)))

    return {
        "runs": [
            {
                "id": r.get("id"),
                "timestamp": r.get("timestamp"),
                "users": r.get("users"),
                "project": r.get("project"),
                "status": r.get("status")
            } for r in selected_runs
        ],
        "comparison_matrix": matrix,
        "load_normalization_insight": load_normalization_insight,
        "regressions": regressions,
        "improvements": improvements,
        "best_run": best_run.get("id"),
        "worst_run": worst_run.get("id")
    }


def generate_comparison_html(comparison_data: Dict[str, Any]) -> str:
    """Renders a standalone, styled HTML Comparison Report document."""
    runs = comparison_data.get("runs", [])
    matrix = comparison_data.get("comparison_matrix", [])
    insight = comparison_data.get("load_normalization_insight", "")
    regressions = comparison_data.get("regressions", [])
    improvements = comparison_data.get("improvements", [])

    headers_html = "".join([f"<th>{r.get('id')} ({r.get('users')} users)</th>" for r in runs])
    rows_html = ""

    for row in matrix:
        vals_td = "".join([f"<td style='text-align:right;'>{v} {row['unit']}</td>" for v in row["values"]])
        color = "#10b981" if row["status"] == "improved" else ("#ef4444" if row["status"] == "degraded" else "#94a3b8")
        rows_html += f"""
        <tr>
            <td><strong>{row['metric']}</strong></td>
            {vals_td}
            <td style='text-align:center; font-weight:bold; color:{color};'>{row['trend_str']}</td>
        </tr>
        """

    reg_html = "".join([f"<li style='color:#f87171; margin-bottom:0.4rem;'><strong>{r['title']}:</strong> {r['detail']}</li>" for r in regressions]) or "<li>No critical regressions detected.</li>"
    imp_html = "".join([f"<li style='color:#34d399; margin-bottom:0.4rem;'><strong>{i['title']}:</strong> {i['detail']}</li>" for i in improvements]) or "<li>No major improvements noted.</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Multi-Run Performance Comparison Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #334155; }}
        h1, h2, h3 {{ color: #38bdf8; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 10px 14px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; text-align: left; color: #94a3b8; }}
        .badge {{ background: #0284c7; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; display: inline-block; }}
        .insight-box {{ background: rgba(56, 189, 248, 0.1); border-left: 4px solid #38bdf8; padding: 1rem; border-radius: 4px; margin-top: 1rem; }}
    </style>
</head>
<body>
    <h1>⚡ Performance Intelligence Comparison Report</h1>
    <div class="card">
        <h2>Executive Summary</h2>
        <div class="insight-box">{insight}</div>
    </div>

    <div class="card">
        <h2>Side-by-Side Performance Matrix</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    {headers_html}
                    <th style="text-align:center;">Trend</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>Automated Insights</h2>
        <div style="display: flex; gap: 2rem;">
            <div style="flex: 1;">
                <h3 style="color:#ef4444;">🔴 Performance Regressions</h3>
                <ul>{reg_html}</ul>
            </div>
            <div style="flex: 1;">
                <h3 style="color:#10b981;">🟢 Key Improvements</h3>
                <ul>{imp_html}</ul>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html
