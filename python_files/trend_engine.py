#!/usr/bin/env python3
"""
trend_engine.py — Lightweight Historical Trend Analysis Engine for PerfPilot.

Primary Purpose:
  Identifies high-level directional patterns across 3 to 20+ releases (R1 -> R2 -> R3... Rn).
  Answers: "How has performance behaved over time / Where is performance heading?"

Features:
1. Multi-Release Hierarchy Extraction (Project -> User Story -> Hierarchy Scope -> Releases).
2. Clean Management-Grade KPIs (Releases Analyzed, Current RT, Overall Trend %, SLA Status, Best Release, Worst Release).
3. Exactly 6 Hero Trend Visuals:
   - Graph 1: Response Time Trend Line (R1 ... Rn)
   - Graph 2: SLA Compliance Trend (Pass % vs Breach %)
   - Graph 3: Transaction Performance Heatmap Matrix (Tx x Releases)
   - Graph 4: Average Response Time by Release
   - Graph 5: Severity Distribution Evolution Stack (Pass, Low, Moderate, High, Critical)
   - Graph 6: Baseline vs Current Summary
4. Concise, High-Level Trend AI Observations (Superficial directional findings, no root cause speculation).
5. Standalone Management Trend Dashboard HTML Generator.
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


def extract_label_hierarchy_map(jmx_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses JMX file recursively to map every label to:
      - user_story: e.g. "US01_Browse_Catalog"
      - item_type: "MAIN_TRANSACTION" | "SUB_TRANSACTION" | "HTTP_REQUEST"
      - item_type_label: "Main Transaction" | "Sub-Transaction" | "HTTP Request"
      - parent_tc: name of parent Transaction Controller
      - depth: 0 (Main), 1 (Sub L1), 2 (Sub L2 / Request), ... N
    """
    hierarchy_map = {}
    if not jmx_name:
        return hierarchy_map

    jmx_path = _ROOT / "Tests" / jmx_name
    if not jmx_path.exists():
        return hierarchy_map

    try:
        from python_files.sla_manager import parse_jmx_full_tree
        tree, _ = parse_jmx_full_tree(jmx_path)

        def _walk_node(node: Dict[str, Any], user_story: str, parent_name: str, depth: int, is_root_tx: bool):
            name = node.get("name", "").strip()
            node_type = node.get("type", "transaction")
            
            if name:
                if node_type == "transaction":
                    if is_root_tx:
                        i_type = "MAIN_TRANSACTION"
                        i_label = "Main Transaction"
                    else:
                        i_type = "SUB_TRANSACTION"
                        i_label = f"Sub-Transaction (L{depth})" if depth > 1 else "Sub-Transaction"
                else:
                    i_type = "HTTP_REQUEST"
                    i_label = "HTTP Request"

                hierarchy_map[name] = {
                    "user_story": user_story,
                    "item_type": i_type,
                    "item_type_label": i_label,
                    "parent_tc": parent_name,
                    "depth": depth
                }

            for child in node.get("children", []):
                _walk_node(
                    node=child,
                    user_story=user_story,
                    parent_name=name or parent_name,
                    depth=depth + 1,
                    is_root_tx=False
                )

        for tg in tree:
            tg_name = tg.get("name", "").strip() or "Overall Scenario"
            for main_node in tg.get("children", []):
                _walk_node(
                    node=main_node,
                    user_story=tg_name,
                    parent_name="",
                    depth=0,
                    is_root_tx=(main_node.get("type") == "transaction")
                )
    except Exception as e:
        print(f"[Trend Hierarchy] Warning: {e}", flush=True)

    return hierarchy_map


def classify_label_heuristic(lbl: str) -> Dict[str, Any]:
    """Fallback heuristic classification when label is not in JMX tree."""
    u_lbl = lbl.upper()
    if u_lbl.startswith("T-") or u_lbl.startswith("T_") or "OVERALL" in u_lbl:
        return {"user_story": "Overall Scenario", "item_type": "MAIN_TRANSACTION", "item_type_label": "Main Transaction", "parent_tc": "", "depth": 0}
    elif u_lbl.startswith("TC") or u_lbl.startswith("T0") or u_lbl.startswith("T1") or any(k in u_lbl for k in ("LAUNCH", "SELECT", "CHECKOUT", "BIND", "LOGIN", "SEARCH")):
        return {"user_story": lbl.split("-", 1)[0] if "-" in lbl else "User Flow", "item_type": "SUB_TRANSACTION", "item_type_label": "Sub-Transaction", "parent_tc": "", "depth": 1}
    else:
        return {"user_story": "HTTP Requests", "item_type": "HTTP_REQUEST", "item_type_label": "HTTP Request", "parent_tc": "", "depth": 2}


def load_all_runs_data() -> List[Dict[str, Any]]:
    """Loads all test runs from runs.json enriched with individual run JSON data, hierarchy info, and SLA info."""
    runs_file = _DATA_DIR / "runs.json"
    if not runs_file.exists():
        return []

    try:
        runs_manifest = json.loads(runs_file.read_text(encoding="utf-8")).get("runs", [])
    except Exception:
        return []

    from python_files.sla_manager import load_sla_targets

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

        merged = dict(r)
        merged["detail"] = run_detail
        
        jmx_name = r.get("jmx_name") or run_detail.get("jmx_name") or "Unknown Project"
        project_name = Path(jmx_name).stem.replace("_MultiUserStories", "").replace("_01", "").replace(" - Copy", "")
        merged["project"] = project_name
        merged["build_version"] = r.get("build_version") or run_detail.get("build_version") or ""
        merged["environment"] = r.get("environment") or run_detail.get("environment") or "QA"

        jmx_h_map = extract_label_hierarchy_map(jmx_name)
        sla_map, def_rt, def_err = load_sla_targets(jmx_name, actual_users=merged.get("users"))

        summary = run_detail.get("summary", {})
        labels = run_detail.get("labels", {})
        
        transactions = []
        user_stories = set()

        if labels:
            for lbl, stats in labels.items():
                h_info = jmx_h_map.get(lbl) or classify_label_heuristic(lbl)
                story = h_info["user_story"]
                user_stories.add(story)

                sla_target = sla_map.get(lbl, {})
                target_rt = sla_target.get("rt", def_rt)
                target_err = sla_target.get("err", def_err)
                is_crit_tx = bool(sla_target.get("is_critical", 0))

                avg_val = stats.get("avg", stats.get("avg_rt", stats.get("mean", 0)))
                p50_val = stats.get("median", stats.get("p50", avg_val))
                p90_val = stats.get("p90", stats.get("pct90", avg_val))
                p95_val = stats.get("p95", stats.get("pct95", p90_val))
                err_rate = stats.get("error_pct", stats.get("error_rate", 0))

                # Severity logic
                if p90_val <= target_rt and err_rate <= target_err:
                    severity = "PASS"
                    sla_status = "Pass"
                elif p90_val <= target_rt * 1.25:
                    severity = "LOW"
                    sla_status = "Low Breach"
                elif p90_val <= target_rt * 2.0:
                    severity = "MODERATE"
                    sla_status = "Moderate Breach"
                elif p90_val <= target_rt * 3.0:
                    severity = "HIGH"
                    sla_status = "High Breach"
                else:
                    severity = "CRITICAL"
                    sla_status = "Critical Breach"

                dur_sec = float(summary.get("duration_sec", merged.get("duration_sec", 60.0))) or 60.0
                count_val = int(stats.get("count", stats.get("samples", 0)))
                raw_rate = stats.get("rate", stats.get("tps", stats.get("throughput")))
                if raw_rate is not None:
                    tps_val = float(raw_rate)
                else:
                    tps_val = round(count_val / max(dur_sec, 1.0), 2)

                transactions.append({
                    "transaction_name": lbl,
                    "user_story": story,
                    "item_type": h_info["item_type"],
                    "item_type_label": h_info["item_type_label"],
                    "parent_tc": h_info.get("parent_tc", ""),
                    "depth": h_info.get("depth", 0),
                    "avg_rt": round(float(avg_val), 2),
                    "p50": round(float(p50_val), 2),
                    "p90": round(float(p90_val), 2),
                    "p95": round(float(p95_val), 2),
                    "tps": round(float(tps_val), 2),
                    "error_rate": round(float(err_rate), 2),
                    "sla_target_rt": float(target_rt),
                    "is_critical_tx": is_crit_tx,
                    "severity": severity,
                    "sla_status": sla_status,
                    "sla_passed": severity == "PASS"
                })

        transactions.sort(key=lambda x: (x.get("user_story", ""), x.get("depth", 0), x.get("transaction_name", "")))
        merged["transactions"] = transactions
        merged["user_stories"] = sorted(list(user_stories)) if user_stories else ["Overall Scenario"]

        main_and_subs = [t for t in transactions if t["item_type"] in ("MAIN_TRANSACTION", "SUB_TRANSACTION")]
        eval_pool = main_and_subs if main_and_subs else transactions

        total_tx = len(eval_pool)
        passed_tx = sum(1 for t in eval_pool if t["sla_passed"])
        merged["sla_pass_rate"] = round((passed_tx / total_tx * 100), 1) if total_tx > 0 else 100.0
        merged["critical_breaches"] = sum(1 for t in eval_pool if t["severity"] == "CRITICAL")
        merged["high_breaches"] = sum(1 for t in eval_pool if t["severity"] == "HIGH")
        
        enriched_runs.append(merged)

    enriched_runs.sort(key=lambda x: x.get("epoch", 0))
    return enriched_runs


def get_hierarchy_tree() -> Dict[str, Any]:
    """Returns the Project -> User Story -> Transaction hierarchy tree with item types."""
    runs = load_all_runs_data()
    hierarchy = {}

    for r in runs:
        proj = r.get("project", "Default Project")
        if proj not in hierarchy:
            hierarchy[proj] = {}

        txs = r.get("transactions", [])
        if not txs:
            if "Overall" not in hierarchy[proj]:
                hierarchy[proj]["Overall"] = []
        else:
            for tx in txs:
                story = tx.get("user_story", "Overall")
                tx_name = tx.get("transaction_name", "Transaction")
                i_type = tx.get("item_type", "SUB_TRANSACTION")
                depth = tx.get("depth", 0)
                parent = tx.get("parent_tc", "")

                if story not in hierarchy[proj]:
                    hierarchy[proj][story] = []

                existing_names = [item["name"] for item in hierarchy[proj][story]]
                if tx_name not in existing_names:
                    hierarchy[proj][story].append({
                        "name": tx_name,
                        "type": i_type,
                        "depth": depth,
                        "parent": parent
                    })

    return {"hierarchy": hierarchy}


def build_trend_analysis(
    project: str = "",
    user_story: str = "",
    item_type_filter: str = "TRANSACTIONS_ONLY",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Builds the lightweight Historical Trend Dashboard across 3 to 20+ releases.
    Answers: How has performance behaved over time / Where is performance heading?
    """
    all_runs = load_all_runs_data()
    if project:
        all_runs = [r for r in all_runs if r.get("project") == project]

    if not all_runs:
        return {"success": False, "message": "No test runs found matching the requested criteria."}

    runs = all_runs[-limit:] if len(all_runs) > limit else all_runs
    if len(runs) < 2:
        runs = all_runs[-2:] if len(all_runs) >= 2 else all_runs

    # Scope allowed item types
    allowed_types = None
    if item_type_filter == "MAIN_TRANSACTION":
        allowed_types = {"MAIN_TRANSACTION"}
    elif item_type_filter == "SUB_TRANSACTION":
        allowed_types = {"SUB_TRANSACTION"}
    elif item_type_filter == "HTTP_REQUEST":
        allowed_types = {"HTTP_REQUEST"}
    elif item_type_filter == "TRANSACTIONS_ONLY":
        allowed_types = {"MAIN_TRANSACTION", "SUB_TRANSACTION"}

    all_items_dict = {}
    for r in runs:
        for t in r.get("transactions", []):
            name = t["transaction_name"]
            if user_story and t.get("user_story") != user_story:
                continue
            if allowed_types and t.get("item_type") not in allowed_types:
                continue
            if name not in all_items_dict:
                all_items_dict[name] = t

    tx_list = sorted(
        list(all_items_dict.keys()),
        key=lambda x: (
            all_items_dict[x].get("user_story", ""),
            all_items_dict[x].get("depth", 0),
            x
        )
    )

    # Calculate release timeline nodes with scoped metrics
    release_nodes = []
    for i, r in enumerate(runs):
        rel_code = f"R{i+1}"
        r["rel_code"] = rel_code
        r_txs = [t for t in r.get("transactions", []) if t["transaction_name"] in all_items_dict]
        
        if r_txs:
            s_avg = round(sum(t["avg_rt"] for t in r_txs) / len(r_txs), 2)
            passed = sum(1 for t in r_txs if t["sla_passed"])
            s_pass = round((passed / len(r_txs)) * 100, 1)
        else:
            s_avg = r.get("avg_rt", 0.0)
            s_pass = r.get("sla_pass_rate", 100.0)

        release_nodes.append({
            "code": rel_code,
            "id": r["id"],
            "users": r.get("users", 1),
            "timestamp": r.get("timestamp", ""),
            "avg_rt": s_avg,
            "sla_pass_rate": s_pass,
            "is_baseline": (i == 0),
            "is_current": (i == len(runs) - 1)
        })

    # High-level KPIs
    r_first = release_nodes[0]
    r_last = release_nodes[-1]

    trend_delta_pct = round(((r_last["avg_rt"] - r_first["avg_rt"]) / max(r_first["avg_rt"], 1e-6)) * 100, 2) if r_first["avg_rt"] > 0 else 0.0
    sla_delta_pp = round(r_last["sla_pass_rate"] - r_first["sla_pass_rate"], 1)

    best_rel = min(release_nodes, key=lambda x: x["avg_rt"])["code"]
    worst_rel = max(release_nodes, key=lambda x: x["avg_rt"])["code"]
    curr_sla_status = "Pass" if r_last["sla_pass_rate"] >= 90.0 else ("Warning" if r_last["sla_pass_rate"] >= 75.0 else "Critical")

    kpis = {
        "releases_analyzed": len(release_nodes),
        "current_rt": r_last["avg_rt"],
        "baseline_rt": r_first["avg_rt"],
        "overall_trend_pct": trend_delta_pct,
        "current_sla_pass_rate": r_last["sla_pass_rate"],
        "sla_delta_pp": sla_delta_pp,
        "current_sla_status": curr_sla_status,
        "best_release": best_rel,
        "worst_release": worst_rel,
        "items_tracked": len(tx_list)
    }

    # Concise AI Observations (Superficial, high-level direction only)
    trend_observations = [
        f"**Trend Direction:** Average response time {'increased' if trend_delta_pct > 0 else 'decreased'} across the analyzed releases from **{r_first['avg_rt']:.2f}ms in {r_first['code']}** to **{r_last['avg_rt']:.2f}ms in {r_last['code']} ({trend_delta_pct:+.2f}%)**.",
        f"**SLA Compliance:** Overall pass rate shifted from **{r_first['sla_pass_rate']:.1f}%** to **{r_last['sla_pass_rate']:.1f}%** ({sla_delta_pp:+.1f} pp).",
        f"**Peak Latency:** Highest response time was recorded in **{worst_rel}**.",
        f"**Best Performance:** Lowest response time was recorded in **{best_rel}**."
    ]

    # Graph 3: Transaction Performance Heatmap
    run_tx_maps = [{t["transaction_name"]: t for t in r.get("transactions", [])} for r in runs]
    heatmap_matrix = []
    for tx_name in tx_list:
        meta_info = all_items_dict.get(tx_name, {})
        vals = []
        sevs = []
        for i, r_map in enumerate(run_tx_maps):
            item = r_map.get(tx_name, {})
            vals.append(item.get("avg_rt", 0.0))
            sevs.append(item.get("severity", "PASS"))

        heatmap_matrix.append({
            "transaction": tx_name,
            "user_story": meta_info.get("user_story", "Overall"),
            "item_type": meta_info.get("item_type", "SUB_TRANSACTION"),
            "depth": meta_info.get("depth", 0),
            "values": vals,
            "severities": sevs
        })

    # Graph 5: Severity Distribution Evolution Stack
    severity_distribution = []
    for i, r_map in enumerate(run_tx_maps):
        counts = {"PASS": 0, "LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
        for tx_name in tx_list:
            sev = r_map.get(tx_name, {}).get("severity", "PASS")
            counts[sev] = counts.get(sev, 0) + 1
        severity_distribution.append({
            "release": release_nodes[i]["code"],
            "counts": counts,
            "total": len(tx_list)
        })

    # Graph 6: Baseline vs Current Summary
    baseline_vs_current_summary = []
    for tx_name in tx_list:
        ta = run_tx_maps[0].get(tx_name, {})
        tb = run_tx_maps[-1].get(tx_name, {})
        meta_info = all_items_dict.get(tx_name, {})
        a_val = ta.get("avg_rt", 0.0)
        b_val = tb.get("avg_rt", 0.0)
        d_pct = round(((b_val - a_val)/max(a_val, 1e-6))*100, 2) if a_val > 0 else 0.0

        baseline_vs_current_summary.append({
            "transaction": tx_name,
            "item_type": meta_info.get("item_type", "SUB_TRANSACTION"),
            "depth": meta_info.get("depth", 0),
            "baseline_rt": a_val,
            "current_rt": b_val,
            "delta_pct": d_pct
        })

    # Build Multi-Series Trend Data for Dynamic Multi-Select Trend Explorer
    story_names = sorted(list(set(meta.get("user_story", "Overall") for meta in all_items_dict.values())))

    overall_points = []
    for i, r in enumerate(runs):
        overall_points.append({
            "release": release_nodes[i]["code"],
            "run_id": r.get("id"),
            "users": r.get("users", 1),
            "avg_rt": release_nodes[i]["avg_rt"],
            "p90": round(float(r.get("detail", {}).get("summary", {}).get("p90", r.get("p95_rt", release_nodes[i]["avg_rt"]))), 1),
            "p95": round(float(r.get("p95_rt", r.get("detail", {}).get("summary", {}).get("p95", release_nodes[i]["avg_rt"]))), 1),
            "tps": round(float(r.get("throughput", r.get("detail", {}).get("summary", {}).get("throughput", 0.0))), 2),
            "error_rate": round(float(r.get("error_rate", r.get("detail", {}).get("summary", {}).get("error_rate", 0.0))), 2),
            "sla_pass_rate": release_nodes[i]["sla_pass_rate"]
        })

    story_series = {}
    for s in story_names:
        s_txs_names = [tx_n for tx_n, meta in all_items_dict.items() if meta.get("user_story") == s]
        s_points = []
        for i, r_map in enumerate(run_tx_maps):
            matched = [r_map[name] for name in s_txs_names if name in r_map]
            if matched:
                s_avg = round(sum(m["avg_rt"] for m in matched) / len(matched), 2)
                s_p90 = round(sum(m["p90"] for m in matched) / len(matched), 2)
                s_p95 = round(sum(m["p95"] for m in matched) / len(matched), 2)
                s_tps = round(sum(m["tps"] for m in matched), 2)
                s_err = round(sum(m["error_rate"] for m in matched) / len(matched), 2)
                s_passed = sum(1 for m in matched if m["sla_passed"])
                s_pass = round((s_passed / len(matched)) * 100, 1)
            else:
                s_avg, s_p90, s_p95, s_tps, s_err, s_pass = 0, 0, 0, 0, 0, 100

            s_points.append({
                "release": release_nodes[i]["code"],
                "run_id": runs[i].get("id"),
                "users": runs[i].get("users", 1),
                "avg_rt": s_avg,
                "p90": s_p90,
                "p95": s_p95,
                "tps": s_tps,
                "error_rate": s_err,
                "sla_pass_rate": s_pass
            })
        story_series[s] = {
            "name": s,
            "type": "STORY",
            "data": s_points
        }

    transaction_series = {}
    for tx_name in tx_list:
        meta_info = all_items_dict.get(tx_name, {})
        tx_points = []
        for i, r_map in enumerate(run_tx_maps):
            item = r_map.get(tx_name, {})
            tx_points.append({
                "release": release_nodes[i]["code"],
                "run_id": runs[i].get("id"),
                "users": runs[i].get("users", 1),
                "avg_rt": item.get("avg_rt", 0.0),
                "p90": item.get("p90", 0.0),
                "p95": item.get("p95", 0.0),
                "tps": item.get("tps", 0.0),
                "error_rate": item.get("error_rate", 0.0),
                "sla_target_rt": item.get("sla_target_rt", 500.0),
                "sla_passed": item.get("sla_passed", True)
            })
        transaction_series[tx_name] = {
            "name": tx_name,
            "user_story": meta_info.get("user_story", "Overall"),
            "item_type": meta_info.get("item_type", "SUB_TRANSACTION"),
            "depth": meta_info.get("depth", 0),
            "type": "TX",
            "data": tx_points
        }

    multi_series_data = {
        "overall": {
            "name": "Overall Scenario",
            "type": "OVERALL",
            "data": overall_points
        },
        "stories": story_series,
        "transactions": transaction_series,
        "releases": [n["code"] for n in release_nodes]
    }

    return {
        "success": True,
        "metadata": {
            "project": project or all_runs[-1].get("project", "Default Project"),
            "user_story": user_story or "All User Journeys",
            "item_type_filter": item_type_filter or "TRANSACTIONS_ONLY",
            "releases_count": len(release_nodes),
            "baseline_release": r_first["code"],
            "current_release": r_last["code"]
        },
        "kpis": kpis,
        "ai_observations": trend_observations,
        "release_nodes": release_nodes,
        "multi_series": multi_series_data,
        "heatmap": {
            "releases": [n["code"] for n in release_nodes],
            "matrix": heatmap_matrix
        },
        "severity_distribution": severity_distribution,
        "baseline_vs_current": baseline_vs_current_summary
    }


def generate_trend_dashboard_html(trend_data: Dict[str, Any]) -> str:
    """Renders a standalone Management Trend Dashboard in HTML."""
    meta = trend_data.get("metadata", {})
    kpis = trend_data.get("kpis", {})
    obs = trend_data.get("ai_observations", [])
    nodes = trend_data.get("release_nodes", [])
    heatmap = trend_data.get("heatmap", {})

    nodes_html = "".join([f"""
    <div style="background:#ffffff; border:2px solid {'#dc2626' if n['is_current'] else ('#0284c7' if n['is_baseline'] else '#e2e8f0')}; padding:0.5rem 1rem; border-radius:8px; text-align:center; min-width:85px;">
        <div style="font-weight:bold; font-size:1.1rem; color:#0f172a;">{n['code']}</div>
        <div style="font-size:0.75rem; color:#64748b;">{n['users']} Users</div>
        <div style="font-size:0.8rem; font-weight:600; color:#0284c7; margin-top:2px;">{n['avg_rt']:.0f}ms</div>
    </div>
    """ for n in nodes])

    bullets_html = "".join([f"<li>{b.replace('**', '<strong>').replace('**', '</strong>')}</li>" for b in obs])

    heatmap_headers = "".join([f"<th>{r}</th>" for r in heatmap.get("releases", [])])
    heatmap_rows = ""
    for row in heatmap.get("matrix", []):
        tds = ""
        for i, val in enumerate(row["values"]):
            sev = row["severities"][i]
            bg = "rgba(5, 150, 105, 0.12)" if sev == "PASS" else ("rgba(217, 119, 6, 0.18)" if sev in ("LOW", "MODERATE") else "rgba(220, 38, 38, 0.22)")
            tds += f"<td style='background:{bg}; text-align:right;'>{val:.0f} ms</td>"
        
        depth = row.get("depth", 0)
        indent = depth * 16
        i_type = row.get("item_type", "SUB_TRANSACTION")
        t_badge = "MAIN" if i_type == "MAIN_TRANSACTION" else ("SUB" if i_type == "SUB_TRANSACTION" else "REQ")
        badge_style = "background:#e0f2fe; color:#0369a1;" if i_type == "MAIN_TRANSACTION" else ("background:#fef3c7; color:#b45309;" if i_type == "SUB_TRANSACTION" else "background:#f1f5f9; color:#475569;")

        heatmap_rows += f"""
        <tr>
            <td>
                <div style="padding-left:{indent}px; display:flex; align-items:center; gap:0.4rem;">
                    <span style="font-size:0.65rem; font-weight:bold; padding:1px 4px; border-radius:3px; {badge_style}">{t_badge}</span>
                    <span><strong>{row['transaction']}</strong></span>
                </div>
            </td>
            {tds}
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Historical Trend Analysis Dashboard — {meta.get('project')}</title>
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
        .kpi-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.25rem; box-shadow: var(--shadow); }}
        .kpi-title {{ font-size: 0.75rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
        .kpi-value {{ font-size: 1.6rem; font-weight: 800; color: var(--text); margin: 0.25rem 0; }}

        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }}
        h2 {{ color: var(--text); font-size: 1.15rem; font-weight: 700; margin-bottom: 1rem; }}
        
        .bullet-box {{ background: var(--surface2); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 1.25rem; border-radius: 10px; margin-bottom: 1.5rem; }}
        .bullet-box ul {{ margin-left: 1.25rem; }}
        .bullet-box li {{ margin-bottom: 0.35rem; color: var(--text); font-size: 0.92rem; }}

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
            <span>Historical Trend Analysis Dashboard</span>
            <span style="font-size:0.8rem; background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; padding:3px 8px; border-radius:4px; font-weight:700;">Multi-Release Direction</span>
        </div>
        <div class="meta-grid">
            <div class="meta-item"><div class="meta-label">Project</div><div class="meta-val">{meta.get('project')}</div></div>
            <div class="meta-item"><div class="meta-label">User Journey Scope</div><div class="meta-val">{meta.get('user_story')}</div></div>
            <div class="meta-item"><div class="meta-label">Hierarchy Scope</div><div class="meta-val">{meta.get('item_type_filter')}</div></div>
            <div class="meta-item"><div class="meta-label">Releases Tracked</div><div class="meta-val">{meta.get('releases_count')} ({meta.get('baseline_release')} → {meta.get('current_release')})</div></div>
        </div>
        <div style="display:flex; gap:0.75rem; align-items:center; margin-top:1.25rem; overflow-x:auto;">
            {nodes_html}
        </div>
    </div>

    <!-- 2. Management KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Current Response Time</div>
            <div class="kpi-value">{kpis.get('current_rt', 0):.2f} ms</div>
            <div style="font-size:0.8rem; color:{'#dc2626' if kpis.get('overall_trend_pct', 0) > 0 else '#059669'}; font-weight:700;">
                {kpis.get('overall_trend_pct', 0):+.2f}% across releases
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Current SLA Pass Rate</div>
            <div class="kpi-value">{kpis.get('current_sla_pass_rate', 0):.1f}%</div>
            <div style="font-size:0.8rem; color:#64748b;">Status: <strong>{kpis.get('current_sla_status')}</strong></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Best Performing Release</div>
            <div class="kpi-value" style="color:#059669;">{kpis.get('best_release')}</div>
            <div style="font-size:0.8rem; color:#64748b;">Lowest overall latency</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Worst Performing Release</div>
            <div class="kpi-value" style="color:#dc2626;">{kpis.get('worst_release')}</div>
            <div style="font-size:0.8rem; color:#64748b;">Highest overall latency</div>
        </div>
    </div>

    <!-- 3. High-Level AI Observations -->
    <div class="card">
        <h2>Executive Trend Observations</h2>
        <div class="bullet-box">
            <ul>
                {bullets_html}
            </ul>
        </div>
    </div>

    <!-- 4. Heatmap Matrix -->
    <div class="card">
        <h2>Transaction Performance Heatmap Matrix</h2>
        <table>
            <thead>
                <tr><th>Hierarchy Item</th>{heatmap_headers}</tr>
            </thead>
            <tbody>
                {heatmap_rows}
            </tbody>
        </table>
    </div>

</body>
</html>"""
    return html
