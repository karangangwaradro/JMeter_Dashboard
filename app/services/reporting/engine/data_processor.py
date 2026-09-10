#!/usr/bin/env python3
"""
data_processor.py — Data preparation and metric computation for report generation.

Extracts all Python computation from the monolithic generator:
  - Summary stats, score, status
  - SLA target loading & evaluation
  - Transaction row building (tree and flat modes)
  - Chart data arrays (percentile, error, histogram, Apdex, SLA)
  - Azure/infra metric alignment
  - Correlation analysis
  - Findings engine integration
  - AI insights parsing
  - Performance intelligence panels
  - Iteration statistics
  - User story data structures
"""

import json
import re
from pathlib import Path
from datetime import datetime
from app.core.constants import STORAGE_NORMALIZED_DIR, RESULTS_DIR


def prepare_report_data(parsed: dict, azure_data: dict, ai_insights: dict,
                        jmx_name: str, users: int) -> dict:
    """
    Prepare all data needed for report rendering.
    
    This function contains all the Python computation that was in the
    monolithic generate_report(). It returns a context dict (ctx)
    consumed by the HTML component renderers, CSS builders, and JS builders.
    
    Args:
        parsed: Parsed JTL test results (summary, labels, time_series, etc.)
        azure_data: Azure Monitor infrastructure metrics
        ai_insights: AI-generated performance analysis
        jmx_name: Name of the JMeter test script
        users: Number of virtual users configured
    
    Returns:
        dict: Context dictionary with all computed values for rendering
    """
    summary = dict(parsed.get("summary", {}) or {})
    # ── Normalize summary keys across normalized schema & legacy JSON ────────
    if not summary.get("avg_rt") and summary.get("avg_response_time"):
        summary["avg_rt"] = summary["avg_response_time"]
    elif not summary.get("avg_response_time") and summary.get("avg_rt"):
        summary["avg_response_time"] = summary["avg_rt"]

    if not summary.get("min_rt") and summary.get("min_response_time"):
        summary["min_rt"] = summary["min_response_time"]
    elif not summary.get("min_response_time") and summary.get("min_rt"):
        summary["min_response_time"] = summary["min_rt"]

    if not summary.get("max_rt") and summary.get("max_response_time"):
        summary["max_rt"] = summary["max_response_time"]
    elif not summary.get("max_response_time") and summary.get("max_rt"):
        summary["max_response_time"] = summary["max_rt"]

    if not summary.get("duration_sec") and summary.get("duration_seconds"):
        summary["duration_sec"] = summary["duration_seconds"]
    elif not summary.get("duration_seconds") and summary.get("duration_sec"):
        summary["duration_seconds"] = summary["duration_sec"]

    if not summary.get("total") and summary.get("total_requests"):
        summary["total"] = summary["total_requests"]
    elif not summary.get("total_requests") and summary.get("total"):
        summary["total_requests"] = summary["total"]

    if summary.get("errors") is None and summary.get("failed_requests") is not None:
        summary["errors"] = summary["failed_requests"]
    elif summary.get("failed_requests") is None and summary.get("errors") is not None:
        summary["failed_requests"] = summary["errors"]

    parsed["summary"] = summary

    labels = parsed.get("labels", {})
    for lname, ldata in labels.items():
        if isinstance(ldata, dict):
            if not ldata.get("avg_rt") and ldata.get("avg_response_time"):
                ldata["avg_rt"] = ldata["avg_response_time"]
            if not ldata.get("min_rt") and ldata.get("min_response_time"):
                ldata["min_rt"] = ldata["min_response_time"]
            if not ldata.get("max_rt") and ldata.get("max_response_time"):
                ldata["max_rt"] = ldata["max_response_time"]

    ts = parsed.get("time_series", {})
    correlation = parsed.get("correlation", {})
    execution_time = parsed.get("execution_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    run_id = parsed.get("run_id", "unknown")
    ai_chat_history_json = json.dumps(parsed.get("ai_chat_history", {}))

    # Status
    error_rate = summary.get("error_rate", 0)
    avg_rt = summary.get("avg_rt", 0)
    status = "PASSED" if error_rate <= 1.0 else "WARNING" if error_rate <= 5.0 else "FAILED"
    status_color = "#10b981" if status == "PASSED" else "#f59e0b" if status == "WARNING" else "#ef4444"

    # Score
    score = 100
    if avg_rt > 2000: score -= 30
    elif avg_rt > 1000: score -= 20
    elif avg_rt > 500: score -= 10
    if error_rate > 5: score -= 30
    elif error_rate > 1: score -= 15
    score = max(0, min(100, score))

    if ai_insights and ai_insights.get("performance_score"):
        score = ai_insights["performance_score"]

    score_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"

    # Load SLA targets (.csv / .xlsx)
    sla_targets, default_rt, default_err = {}, 500.0, 1.0
    tc_ordered, tc_to_samplers = [], {}

    # Auto-resolve JMX test plan name if generic or missing extension
    resolved_jmx_name = jmx_name
    try:
        from app.core.constants import TESTS_DIR
        cand_p = TESTS_DIR / jmx_name if jmx_name else None
        if not cand_p or not cand_p.exists():
            if jmx_name and (TESTS_DIR / f"{jmx_name}.jmx").exists():
                resolved_jmx_name = f"{jmx_name}.jmx"
            else:
                for cand in TESTS_DIR.glob("*.jmx"):
                    try:
                        from app.services.analytics.sla_manager import parse_jmx_hierarchy
                        cand_tcs, _ = parse_jmx_hierarchy(cand)
                        if sum(1 for tc in cand_tcs if tc in labels) >= 3:
                            resolved_jmx_name = cand.name
                            break
                    except Exception:
                        pass
    except Exception:
        pass

    try:
        from app.services.analytics.sla_manager import load_sla_targets, parse_jmx_hierarchy
        sla_targets, default_rt, default_err = load_sla_targets(resolved_jmx_name, actual_users=users)
    except Exception as sla_err:
        print(f"[Report] SLA targets load warning: {sla_err}", flush=True)

    try:
        from app.services.analytics.sla_manager import parse_jmx_hierarchy
        tc_ordered, tc_to_samplers = parse_jmx_hierarchy(resolved_jmx_name)
    except Exception as hier_err:
        print(f"[Report] Hierarchy parse warning: {hier_err}", flush=True)

    # Parse full tree structure for hierarchical table display
    jmx_full_tree = []
    tg_to_transactions = {}
    try:
        from app.services.analytics.sla_manager import parse_jmx_full_tree
        jmx_full_tree, tg_to_transactions = parse_jmx_full_tree(resolved_jmx_name)
    except Exception as tree_err:
        print(f"[Report] Full tree parse warning: {tree_err}", flush=True)

    def _is_http_lbl(lbl: str) -> bool:
        u = (lbl or "").upper()
        return bool(
            "_R_" in u or "_R0" in u or "_R1" in u or
            u.startswith("HTTP_") or u.startswith("GET_") or u.startswith("POST_") or
            u.startswith("PUT_") or u.startswith("DELETE_")
        )

    def _is_tx_lbl(lbl: str) -> bool:
        if _is_http_lbl(lbl):
            return False
        u = (lbl or "").upper()
        return bool(
            u.startswith("TC") or u.startswith("T_") or u.startswith("T-") or
            any(w in u for w in ("LAUNCH", "SELECT", "SEARCH", "SIGN", "CHECKOUT", "CATALOG", "ORDER", "PAYMENT", "CART", "NAVIGATE", "LOGIN"))
        )

    # Filter for main report display: strictly transaction controllers only, NEVER leaf HTTP requests
    tc_set = set(tc_ordered) if tc_ordered else set()
    if tc_set:
        display_labels = {k: v for k, v in labels.items() if (k in tc_set and not _is_http_lbl(k))}
    else:
        display_labels = {k: v for k, v in labels.items() if _is_tx_lbl(k)}

    if not display_labels:
        display_labels = {k: v for k, v in labels.items() if not _is_http_lbl(k)} or labels

    # Compute Iterations (max executions of any main transaction, representing complete test loops)
    total_iterations = max((v.get("count", 0) for v in display_labels.values()), default=summary.get("total", 0))
    total_tx_executions = sum(v.get("count", 0) for v in display_labels.values()) if display_labels else summary.get("total", 0)
    tc_errors = sum(v.get("errors", 0) for v in display_labels.values()) if display_labels else summary.get("errors", 0)
    error_rate = round((tc_errors / total_tx_executions * 100), 2) if total_tx_executions > 0 else 0.0

    summary["total_iterations"] = total_iterations
    summary["total_tx_executions"] = total_tx_executions
    summary["tc_errors"] = tc_errors
    summary["error_rate"] = error_rate

    # Status update based on transaction error rate
    status = "PASSED" if error_rate <= 1.0 else "WARNING" if error_rate <= 5.0 else "FAILED"
    status_color = "#10b981" if status == "PASSED" else "#f59e0b" if status == "WARNING" else "#ef4444"

    # Track Transaction SLA Summary KPI Stats
    total_tx_count = len(display_labels)
    tx_under_sla = 0
    tx_breached_count = 0
    sla_minor_count = 0
    sla_mod_count = 0
    sla_crit_count = 0

    # Per-transaction rows with SLA evaluation & breach severity tracking
    labels_rows = ""
    sla_breaches = []
    all_apdex_scores = []
    
    from app.services.analytics.apdex import calculate_apdex, calculate_apdex_from_summary

    # ── Helper: Build a single transaction row (used for both flat and tree modes) ──
    def _build_tx_row(lname, ldata, depth=0, node_type="transaction", tg_name="", parent_classes=None, parent_cls_id="", is_hidden=False, toggle_btn_html="", is_overall=False):
        """Build HTML row for a transaction or request at the given tree depth."""
        nonlocal tx_under_sla, tx_breached_count, sla_crit_count, sla_mod_count, sla_minor_count

        target = sla_targets.get(lname, {"rt": default_rt, "err": default_err, "minor_pct": 100.0, "mod_pct": 200.0, "crit_pct": 300.0})
        target_rt = target.get("rt", default_rt)
        target_err = target.get("err", default_err)

        p90_val = ldata.get("p90", 0)
        avg_rt_val = ldata.get("avg_rt", 0)
        err_rate_val = ldata.get("error_rate", 0)

        is_transaction = (node_type == "transaction")
        is_display_tx = (lname in display_labels or lname in sla_targets)

        # Apdex score (only for transactions in display_labels)
        apdex_score = None
        apdex_cls = ""
        if is_display_tx:
            samples = ldata.get("samples")
            success_flags = ldata.get("success_flags")
            if samples:
                apdex_res = calculate_apdex(samples, success_flags, target_t=target_rt)
                apdex_score = apdex_res["apdex"]
            else:
                apdex_score = calculate_apdex_from_summary(avg_rt_val, p90_val, err_rate_val, target_t=target_rt)
            all_apdex_scores.append(apdex_score)
            apdex_cls = "pass" if apdex_score >= 0.85 else "fail" if apdex_score < 0.70 else ""

        # SLA deviation (only for display transactions)
        deviation_pct = 0
        severity_label = ""
        severity_color = "var(--green)"
        err_breached = False
        p90_breached = False
        sla_status_html = ""
        deviation_html = ""

        if is_display_tx:
            deviation_pct = ((p90_val - target_rt) / target_rt * 100) if target_rt > 0 else 0
            err_breached = err_rate_val > target_err
            severity_label = "No Deviation"
            severity_color = "var(--green)"

            if err_breached or deviation_pct > 90:
                severity_label = "Critical Deviation"
                severity_color = "var(--red)"
                sla_crit_count += 1
                is_breached = True
            elif deviation_pct > 60:
                severity_label = "Slightly Deviated"
                severity_color = "var(--yellow)"
                sla_mod_count += 1
                is_breached = True
            elif deviation_pct > 30:
                severity_label = "Acceptable Deviation"
                severity_color = "var(--yellow)"
                sla_minor_count += 1
                is_breached = False
            else:
                is_breached = False
            p90_breached = deviation_pct > 30

            if is_breached or deviation_pct > 30:
                tx_breached_count += 1 if is_breached else 0
                child_samplers = tc_to_samplers.get(lname, [])
                child_details = []
                if child_samplers:
                    for c_name in child_samplers:
                        c_data = labels.get(c_name, {})
                        if c_data:
                            child_details.append({
                                "label": c_name,
                                "p90": c_data.get("p90", 0),
                                "avg_rt": c_data.get("avg_rt", 0),
                                "error_rate": c_data.get("error_rate", 0),
                                "count": c_data.get("count", 0)
                            })
                sla_breaches.append({
                    "label": lname,
                    "severity": severity_label,
                    "target_rt": target_rt,
                    "target_err": target_err,
                    "p90": p90_val,
                    "avg_rt": avg_rt_val,
                    "error_rate": err_rate_val,
                    "child_samplers": child_details
                })
            else:
                tx_under_sla += 1

            dev_color = "var(--red)" if deviation_pct > 90 else "var(--yellow)" if deviation_pct > 30 else "var(--green)"
            deviation_html = f'<span style="color:{dev_color}; font-weight:600;">{deviation_pct:+.1f}%</span>'
            sla_status_html = f'<span style="color: {severity_color}; font-weight:700;">{severity_label}</span>'

        # Build the row HTML
        err_cls = "pass" if not err_breached else "fail"
        rt_cls = "pass" if not p90_breached else "fail"

        # Indentation & styling based on depth and type
        indent_px = depth * 20
        tg_attr = f' data-tg="{tg_name}"' if tg_name else ''
        parent_attr = f' data-parent-cls="{parent_cls_id}"' if parent_cls_id else ''
        extra_classes = (" " + " ".join(parent_classes)) if parent_classes else ""
        disp_style = "display: none;" if is_hidden else ""

        if node_type == "request":
            # Leaf HTTP request row
            name_html = f'<span style="padding-left:{indent_px}px; display:inline-flex; align-items:center; gap:0.4rem;"><span style="color:var(--muted); font-size:0.8rem;">↳</span> <code style="font-size:0.78rem; color:var(--muted);">{lname}</code></span>'
            row_style = 'background: var(--surface2); font-size: 0.78rem; color: var(--muted);'
            apdex_cell = '-'
            sla_rt_cell = '-'
            dev_cell = '-'
            status_cell = '-'
        elif is_display_tx:
            # Main transaction row (bold, with SLA)
            icon = '📁' if depth > 0 else '📊'
            prefix = toggle_btn_html if toggle_btn_html else '<span class="tree-toggle-spacer"></span>'
            name_html = f'<span style="padding-left:{indent_px}px; display:inline-flex; align-items:center; gap:0.25rem;">{prefix}<span>{icon}</span> <strong>{lname}</strong></span>'
            row_style = 'font-weight: 500;'
            apdex_cell = f'<span class="{apdex_cls}"><strong>{apdex_score:.2f}</strong></span>' if apdex_score is not None else '-'
            sla_rt_cell = f'<span class="tx-rt-val">{target_rt:.0f}</span>' if target_rt else '-'
            dev_cell = deviation_html if deviation_html else '-'
            status_cell = sla_status_html if sla_status_html else '-'
        else:
            # Overall Transaction / Sub-transaction
            icon = '📊' if depth == 0 else '📁'
            prefix = toggle_btn_html if toggle_btn_html else '<span class="tree-toggle-spacer"></span>'
            name_html = f'<span style="padding-left:{indent_px}px; display:inline-flex; align-items:center; gap:0.25rem;">{prefix}<span>{icon}</span> <strong style="font-weight:600; color:var(--text);">{lname}</strong></span>'
            row_style = 'font-size: 0.85rem;'
            apdex_cell = '-'
            sla_rt_cell = '-'
            dev_cell = '-'
            status_cell = '-'

        sla_td = f'<td class="tx-rt-cell" data-ms="{target_rt:.0f}">{sla_rt_cell}</td>' if (is_display_tx and target_rt) else '<td>-</td>'

        row_html = f"""
        <tr style="{disp_style} {row_style}" class="tree-row{extra_classes}" {tg_attr}{parent_attr} data-depth="{depth}" data-type="{node_type}">
            <td>{name_html}</td>
            <td>{ldata['count']:,}</td>
            <td>{apdex_cell}</td>
            <td class="{rt_cls} tx-rt-cell" data-ms="{ldata['avg_rt']:.1f}"><span class="tx-rt-val">{ldata['avg_rt']:.0f}</span></td>
            <td class="{rt_cls} tx-rt-cell" data-ms="{ldata['p90']}"><strong class="tx-rt-val">{ldata['p90']}</strong></td>
            <td class="tx-rt-cell" data-ms="{ldata['min_rt']}"><span class="tx-rt-val">{ldata['min_rt']}</span></td>
            <td class="tx-rt-cell" data-ms="{ldata['max_rt']}"><span class="tx-rt-val">{ldata['max_rt']}</span></td>
            <td class="{err_cls}">{ldata['error_rate']:.2f}%</td>
            {sla_td}
            <td>{dev_cell}</td>
            <td>{status_cell}</td>
        </tr>"""
        return row_html

    def _collect_leaf_requests(node):
        """Recursively collect all leaf request nodes under node, flattening any intermediate sub-transactions."""
        reqs = []
        for c in node.get("children", []):
            if c.get("type") == "request":
                reqs.append(c)
            else:
                reqs.extend(_collect_leaf_requests(c))
        return reqs

    def _find_matching_ldata(name, tg_specific, all_lbls):
        """Find matching sample data in thread-group specific labels or all labels, supporting normalized name matching."""
        if name in tg_specific:
            return tg_specific[name], name
        if name in all_lbls:
            return all_lbls[name], name
        simplified = re.sub(r'US\d+_|TC\d+_|_\d+$|_Err\d+$', '', name).strip('_')
        if simplified in tg_specific:
            return tg_specific[simplified], simplified
        if simplified in all_lbls:
            return all_lbls[simplified], simplified

        name_clean = re.sub(r'HTTP_|US\d+_|TC\d+|_', '', name).lower()
        for k, v in tg_specific.items():
            k_clean = re.sub(r'HTTP_|US\d+_|TC\d+|_', '', k).lower()
            if name_clean in k_clean or k_clean in name_clean:
                return v, k
        for k, v in all_lbls.items():
            k_clean = re.sub(r'HTTP_|US\d+_|TC\d+|_', '', k).lower()
            if name_clean in k_clean or k_clean in name_clean:
                return v, k

        return None, name

    def _get_matched_visible_requests(leaf_reqs, tg_specific, all_lbls):
        matched = []
        seen = set()
        for r in leaf_reqs:
            r_name = r.get("name", "")
            ldata, matched_k = _find_matching_ldata(r_name, tg_specific, all_lbls)
            if ldata:
                if matched_k not in seen:
                    seen.add(matched_k)
                    matched.append({
                        "name": matched_k,
                        "display_name": r_name,
                        "ldata": ldata
                    })
        return matched

    # ── Build labels_rows using tree or flat mode ──
    labels_by_tg = parsed.get("labels_by_tg", {})

    if jmx_full_tree:
        # TREE MODE: User Journey -> Overall Transaction -> Main Transactions -> All Requests (flattening sub-transactions)
        tg_filter_options = '<option value="ALL">All User Journeys</option>'
        for tg_node in jmx_full_tree:
            tg_name = tg_node["name"]
            tg_filter_options += f'<option value="{tg_name}">{tg_name}</option>'

        for tg_node in jmx_full_tree:
            tg_name = tg_node["name"]
            tg_specific_labels = labels_by_tg.get(tg_name, {})

            # User Journey header row
            labels_rows += f"""
            <tr class="tg-header-row" data-tg="{tg_name}" style="background: linear-gradient(135deg, var(--accent-bg), var(--surface2)); border-top: 2px solid var(--accent);">
                <td colspan="11" style="padding: 0.6rem 1rem; font-weight: 700; font-size: 0.88rem; color: var(--accent);">
                    <span style="display:inline-flex; align-items:center; gap:0.4rem;">🧭 User Journey: <span style="color:var(--text);">{tg_name}</span></span>
                </td>
            </tr>"""

            for top_child in tg_node.get("children", []):
                top_name = top_child["name"]
                top_ldata, _ = _find_matching_ldata(top_name, tg_specific_labels, labels)
                
                # Check if top_child has child transactions (Overall Transaction pattern)
                child_txs = [c for c in top_child.get("children", []) if c.get("type") == "transaction"]
                
                if child_txs:
                    # Level 2: Overall Transaction (depth 0)
                    top_cls_id = f"tree-children-{hash(top_name + tg_name) & 0xffffffff}"
                    has_children = any(_find_matching_ldata(c["name"], tg_specific_labels, labels)[0] for c in child_txs)
                    top_toggle_btn = f'<button onclick="toggleTreeChildren(this, \'{top_cls_id}\')" class="tree-toggle-btn" data-expanded="false" title="Expand / Collapse">▶</button>' if has_children else ''
                    
                    if top_ldata:
                        labels_rows += _build_tx_row(
                            top_name, top_ldata, depth=0, node_type="transaction", tg_name=tg_name,
                            is_hidden=False, toggle_btn_html=top_toggle_btn
                        )
                    
                    # Level 3: Main Transactions under Overall Transaction (depth 1)
                    for main_tx in child_txs:
                        main_name = main_tx["name"]
                        main_ldata, _ = _find_matching_ldata(main_name, tg_specific_labels, labels)
                        if not main_ldata:
                            continue
                        
                        # Collect all leaf requests under this main transaction (bypassing intermediate sub-transactions)
                        leaf_requests = _collect_leaf_requests(main_tx)
                        visible_requests = _get_matched_visible_requests(leaf_requests, tg_specific_labels, labels)
                        
                        main_cls_id = f"tree-children-{hash(main_name + tg_name) & 0xffffffff}"
                        main_toggle_btn = f'<button onclick="toggleTreeChildren(this, \'{main_cls_id}\')" class="tree-toggle-btn" data-expanded="false" title="Expand / Collapse">▶</button>' if visible_requests else ''
                        
                        labels_rows += _build_tx_row(
                            main_name, main_ldata, depth=1, node_type="transaction", tg_name=tg_name,
                            parent_classes=[top_cls_id], parent_cls_id=top_cls_id, is_hidden=True,
                            toggle_btn_html=main_toggle_btn
                        )
                        
                        # Level 4: All Requests under Main Transaction (depth 2)
                        for req in visible_requests:
                            req_name = req["name"]
                            req_ldata = req["ldata"]
                            labels_rows += _build_tx_row(
                                req_name, req_ldata, depth=2, node_type="request", tg_name=tg_name,
                                parent_classes=[top_cls_id, main_cls_id], parent_cls_id=main_cls_id, is_hidden=True
                            )
                else:
                    # top_child is directly a Main Transaction (no Overall Transaction)
                    leaf_requests = _collect_leaf_requests(top_child)
                    visible_requests = _get_matched_visible_requests(leaf_requests, tg_specific_labels, labels)
                    
                    top_cls_id = f"tree-children-{hash(top_name + tg_name) & 0xffffffff}"
                    top_toggle_btn = f'<button onclick="toggleTreeChildren(this, \'{top_cls_id}\')" class="tree-toggle-btn" data-expanded="false" title="Expand / Collapse">▶</button>' if visible_requests else ''
                    
                    if top_ldata:
                        labels_rows += _build_tx_row(
                            top_name, top_ldata, depth=0, node_type="transaction", tg_name=tg_name,
                            is_hidden=False, toggle_btn_html=top_toggle_btn
                        )
                        
                        for req in visible_requests:
                            req_name = req["name"]
                            req_ldata = req["ldata"]
                            labels_rows += _build_tx_row(
                                req_name, req_ldata, depth=1, node_type="request", tg_name=tg_name,
                                parent_classes=[top_cls_id], parent_cls_id=top_cls_id, is_hidden=True
                            )
    else:
        # FLAT MODE (fallback): No JMX tree available, use structured flat rendering
        if labels_by_tg:
            tg_filter_options = '<option value="ALL">All User Journeys</option>'
            for tg_name in labels_by_tg.keys():
                tg_filter_options += f'<option value="{tg_name}">{tg_name}</option>'

            for tg_name, tg_specific_labels in labels_by_tg.items():
                labels_rows += f"""
                <tr class="tg-header-row" data-tg="{tg_name}" style="background: linear-gradient(135deg, var(--accent-bg), var(--surface2)); border-top: 2px solid var(--accent);">
                    <td colspan="11" style="padding: 0.6rem 1rem; font-weight: 700; font-size: 0.88rem; color: var(--accent);">
                        <span style="display:inline-flex; align-items:center; gap:0.4rem;">🧭 User Journey: <span style="color:var(--text);">{tg_name}</span></span>
                    </td>
                </tr>"""

                for lname, ldata in sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True):
                    if lname in tg_specific_labels:
                        c_samplers_table = tc_to_samplers.get(lname, [])
                        matched_table_children = {}
                        for c_spec in c_samplers_table:
                            if c_spec in tg_specific_labels and c_spec != lname:
                                matched_table_children[c_spec] = tg_specific_labels[c_spec]
                            elif c_spec in labels and c_spec != lname:
                                matched_table_children[c_spec] = labels[c_spec]

                        if not matched_table_children:
                            tx_prefix = lname.rsplit("_", 1)[0] if "_" in lname else lname
                            for l_key, l_val in tg_specific_labels.items():
                                if l_key != lname and _is_http_lbl(l_key):
                                    if l_key.startswith(tx_prefix) or tx_prefix in l_key:
                                        matched_table_children[l_key] = l_val

                        c_cls_id = f"tree-children-{hash(lname + tg_name) & 0xffffffff}"
                        toggle_btn = f'<button onclick="toggleTreeChildren(this, \'{c_cls_id}\')" class="tree-toggle-btn" data-expanded="false" title="Expand / Collapse">▶</button>' if matched_table_children else ''

                        labels_rows += _build_tx_row(
                            lname, ldata, depth=0, node_type="transaction", tg_name=tg_name,
                            is_hidden=False, toggle_btn_html=toggle_btn
                        )

                        for cs_k, cs_v in matched_table_children.items():
                            labels_rows += _build_tx_row(
                                cs_k, cs_v, depth=1, node_type="request", tg_name=tg_name,
                                parent_classes=[c_cls_id], parent_cls_id=c_cls_id, is_hidden=True
                            )
        else:
            tg_filter_options = ''
            for lname, ldata in sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True):
                c_samplers_table = tc_to_samplers.get(lname, [])
                matched_table_children = {}
                for c_spec in c_samplers_table:
                    if c_spec in labels and c_spec != lname:
                        matched_table_children[c_spec] = labels[c_spec]

                if not matched_table_children:
                    tx_prefix = lname.rsplit("_", 1)[0] if "_" in lname else lname
                    for l_key, l_val in labels.items():
                        if l_key != lname and _is_http_lbl(l_key):
                            if l_key.startswith(tx_prefix) or tx_prefix in l_key:
                                matched_table_children[l_key] = l_val

                c_cls_id = f"tree-children-{hash(lname) & 0xffffffff}"
                toggle_btn = f'<button onclick="toggleTreeChildren(this, \'{c_cls_id}\')" class="tree-toggle-btn" data-expanded="false" title="Expand / Collapse">▶</button>' if matched_table_children else ''

                labels_rows += _build_tx_row(
                    lname, ldata, depth=0, node_type="transaction", tg_name="",
                    is_hidden=False, toggle_btn_html=toggle_btn
                )

                for cs_k, cs_v in matched_table_children.items():
                    labels_rows += _build_tx_row(
                        cs_k, cs_v, depth=1, node_type="request", tg_name="",
                        parent_classes=[c_cls_id], parent_cls_id=c_cls_id, is_hidden=True
                    )

    # Overall Average Apdex Score for header badge
    overall_apdex = round(sum(all_apdex_scores) / len(all_apdex_scores), 2) if all_apdex_scores else 1.00
    apdex_score_str = f"{overall_apdex:.2f}"
    score_color = "#10b981" if overall_apdex >= 0.85 else "#f59e0b" if overall_apdex >= 0.70 else "#ef4444"

    # Build Critical Transactions Table (Replaces Top 5 Slowest)
    critical_tx_rows = ""
    crit_tx_list = []
    for t_name, t_data in display_labels.items():
        t_target = sla_targets.get(t_name, {"rt": default_rt, "err": default_err}).get("rt", default_rt)
        t_err_target = sla_targets.get(t_name, {"rt": default_rt, "err": default_err}).get("err", default_err)
        t_p90 = t_data.get("p90", 0)
        dev_pct = ((t_p90 - t_target) / t_target * 100) if t_target > 0 else 0
        
        if dev_pct > 30 or t_data.get("error_rate", 0) > t_err_target:
            crit_tx_list.append((t_name, t_data, t_target, dev_pct, t_err_target))
            
    crit_tx_list.sort(key=lambda x: x[3], reverse=True) # sort by deviation descending
    
    for t_name, t_data, t_target, dev_pct, t_err_target in crit_tx_list[:10]:
        err_val = t_data.get("error_rate", 0)
        avg_val = t_data.get("avg_rt", 0)
        p95_val = t_data.get("p95", 0)
        
        sev_label = "Critical Breach (>100%)" if dev_pct > 100 else "Significant Breach (50-100%)" if dev_pct > 50 else "Minor Breach (0-50%)" if dev_pct > 0 else "Met SLA"
        sev_color = "var(--red)" if dev_pct > 100 else "#f97316" if dev_pct > 50 else "#eab308" if dev_pct > 0 else "var(--green)"
        if err_val > t_err_target:
            sev_label = "Error SLA Breached"
            sev_color = "var(--red)"
            
        critical_tx_rows += f"""
        <tr style="background: var(--surface1); border-bottom: 1px solid var(--border);">
            <td><strong>{t_name}</strong></td>
            <td>{avg_val:.0f} ms</td>
            <td>{p95_val} ms</td>
            <td style="color: {'var(--red)' if err_val > t_err_target else 'var(--green)'};">{err_val:.2f}%</td>
            <td>{t_target:.0f} ms</td>
            <td style="color: {sev_color}; font-weight: 600;">{dev_pct:+.1f}%</td>
            <td><span style="color: {sev_color}; font-weight:700;">{sev_label}</span></td>
        </tr>
        """
        
    if not critical_tx_rows:
        critical_tx_rows = '<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--muted);">✅ No critical SLA deviations detected.</td></tr>'

    crit_tx_table_html = f"""
    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
        <thead>
            <tr style="text-align: left; background: var(--surface2);">
                <th style="padding: 0.5rem;">Transaction</th><th>Avg RT</th><th>P95 RT</th><th>Error %</th><th>SLA Target (P90)</th><th>Deviation %</th><th>Severity</th>
            </tr>
        </thead>
        <tbody>
            {critical_tx_rows}
        </tbody>
    </table>
    """

    # Build SLA Breaches & Child Sampler HTML Block
    sla_breaches_html = ""
    if sla_breaches:
        for b in sla_breaches:
            child_html = ""
            if b["child_samplers"]:
                child_rows = "".join([
                    f"<tr><td><code>{c['label']}</code></td><td>{c['count']}</td><td>{c['avg_rt']:.0f} ms</td><td><strong>{c['p90']} ms</strong></td><td>{c['error_rate']:.2f}%</td></tr>"
                    for c in b["child_samplers"]
                ])
                child_html = f"""
                <div style="margin-top: 0.8rem; background: var(--surface2); padding: 0.8rem; border-radius: 8px;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: var(--muted); margin-bottom: 0.4rem;">Corresponding HTTP Requests inside Transaction Controller:</div>
                    <table>
                        <thead><tr><th>HTTP Request Label</th><th>Samples</th><th>Avg RT</th><th>P90 RT</th><th>Error %</th></tr></thead>
                        <tbody>{child_rows}</tbody>
                    </table>
                </div>"""

            sla_breaches_html += f"""
            <div class="rec-card critical" style="margin-bottom: 1rem;">
                <div class="rec-header">
                    <span class="rec-priority">SLA BREACH</span>
                    <span class="rec-category">Target: {b['target_rt']:.0f} ms P90 / {b['target_err']}% Error</span>
                </div>
                <div class="rec-title">⚠️ {b['label']}</div>
                <div class="rec-desc">
                    90th Percentile reached <strong>{b['p90']} ms</strong> (Target: {b['target_rt']:.0f} ms) | Error Rate: <strong>{b['error_rate']:.2f}%</strong> (Target: {b['target_err']}%)
                </div>
                {child_html}
            </div>"""
    else:
        sla_breaches_html = '<div class="rec-card pass" style="border-left: 4px solid var(--green); background: var(--green-bg);"><div class="rec-title" style="color:var(--green);">✅ All Transactions Met SLA Targets</div><div class="rec-desc">No 90th percentile SLA breaches detected.</div></div>'


    # Time series data
    ts_labels    = json.dumps(ts.get("ts_labels", []))
    ts_avg_rt    = json.dumps(ts.get("ts_avg_rt", []))
    ts_p95_rt    = json.dumps(ts.get("ts_p95_rt", []))
    ts_p99_rt    = json.dumps(ts.get("ts_p99_rt", []))
    ts_throughput = json.dumps(ts.get("ts_throughput", []))
    ts_errors    = json.dumps(ts.get("ts_errors", []))

    # --- Additional chart data prep ---
    # Percentile Comparison: Top 8 transactions by avg RT
    pct_labels_items = sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:8]
    pct_names  = json.dumps([l[0][:28] for l in pct_labels_items])
    pct_p50    = json.dumps([l[1].get("p50", 0) for l in pct_labels_items])
    pct_p90    = json.dumps([l[1].get("p90", 0) for l in pct_labels_items])
    pct_p95    = json.dumps([l[1].get("p95", 0) for l in pct_labels_items])
    pct_p99    = json.dumps([l[1].get("p99", 0) for l in pct_labels_items])

    # Error Rate by Transaction: Top 10 with highest error rate (exclude 0%)
    err_items = sorted(
        [(k, v) for k, v in display_labels.items() if v.get("error_rate", 0) > 0],
        key=lambda x: x[1].get("error_rate", 0), reverse=True
    )[:10]
    err_labels_json = json.dumps([l[0][:28] for l in err_items])
    err_rates_json  = json.dumps([round(l[1].get("error_rate", 0), 2) for l in err_items])
    err_counts_json = json.dumps([l[1].get("errors", 0) for l in err_items])

    # Error Analysis Donut: per-error-type breakdown from JTL parsing (strictly request-level)
    error_details_raw = parsed.get("error_details", {})
    cleaned_error_details = {}

    def _is_request_sampler(lbl: str) -> bool:
        u = (lbl or "").upper()
        return bool("_R_" in u or "_R0" in u or "_R1" in u or u.startswith("HTTP_") or u.startswith("GET_") or u.startswith("POST_"))

    for err_k, err_v in error_details_raw.items():
        k_lower = err_k.lower()
        msg_lower = (err_v.get("message") or "").lower()
        fmsg_lower = (err_v.get("failure_message") or "").lower()
        if any(w in k_lower or w in msg_lower or w in fmsg_lower for w in [
            "samples in transaction", "failed samples", "failing samples", "transaction failed"
        ]):
            continue
        
        filtered_occs = [
            occ for occ in err_v.get("occurrences", [])
            if _is_request_sampler(occ.get("label", "")) or not (
                "transaction controller" in occ.get("label", "").lower() or 
                "overall_iteration" in occ.get("label", "").lower() or
                "controller" in occ.get("label", "").lower()
            )
        ]
        
        cleaned_entry = dict(err_v)
        if filtered_occs:
            cleaned_entry["occurrences"] = filtered_occs
            cleaned_entry["count"] = len(filtered_occs) if len(err_v.get("occurrences", [])) == err_v.get("count", 0) else err_v.get("count", len(filtered_occs))
        elif err_v.get("count", 0) > 0:
            cleaned_entry["occurrences"] = err_v.get("occurrences", [])
            cleaned_entry["count"] = err_v.get("count", 0)
        else:
            continue
            
        cleaned_error_details[err_k] = cleaned_entry

    error_types_sorted = sorted(cleaned_error_details.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    total_errors_all = sum(ed["count"] for _, ed in error_types_sorted) if error_types_sorted else 0
    display_total_errors = total_errors_all
    
    error_donut_labels = json.dumps([k[:50] for k, _ in error_types_sorted])
    error_donut_counts = json.dumps([ed["count"] for _, ed in error_types_sorted])
    # Build detailed occurrences data for drill-down (serialized to JS)
    error_drill_data = {}
    start_epoch_ms = parsed.get("summary", {}).get("start_epoch", 0) * 1000 if parsed.get("summary", {}).get("start_epoch", 0) else 0
    for err_key, err_info in error_types_sorted:
        tx_summary = {}
        for occ in err_info.get("occurrences", []):
            lbl = occ.get("label", "Unknown")
            if lbl not in tx_summary:
                tx_summary[lbl] = {"count": 0, "total_rt": 0, "min_rt": 999999, "max_rt": 0, "first_ts": 0, "last_ts": 0}
            tx_summary[lbl]["count"] += 1
            tx_summary[lbl]["total_rt"] += occ.get("elapsed", 0)
            tx_summary[lbl]["min_rt"] = min(tx_summary[lbl]["min_rt"], occ.get("elapsed", 0))
            tx_summary[lbl]["max_rt"] = max(tx_summary[lbl]["max_rt"], occ.get("elapsed", 0))
            if tx_summary[lbl]["first_ts"] == 0 or occ.get("timestamp", 0) < tx_summary[lbl]["first_ts"]:
                tx_summary[lbl]["first_ts"] = occ.get("timestamp", 0)
            if occ.get("timestamp", 0) > tx_summary[lbl]["last_ts"]:
                tx_summary[lbl]["last_ts"] = occ.get("timestamp", 0)
        error_drill_data[err_key[:50]] = {
            "total": err_info["count"],
            "code": err_info.get("code", ""),
            "message": err_info.get("message", ""),
            "failure_message": err_info.get("failure_message", ""),
            "transactions": {
                lbl: {
                    "count": info["count"],
                    "avg_rt": round(info["total_rt"] / info["count"], 1) if info["count"] > 0 else 0,
                    "min_rt": info["min_rt"] if info["min_rt"] < 999999 else 0,
                    "max_rt": info["max_rt"],
                    "first_ts": info["first_ts"],
                    "last_ts": info["last_ts"]
                }
                for lbl, info in sorted(tx_summary.items(), key=lambda x: x[1]["count"], reverse=True)
            }
        }
    error_drill_json = json.dumps(error_drill_data)

    # Response Time Histogram: bucket all avg_rts into bands
    rt_bands = [0, 100, 250, 500, 1000, 2000, 5000, 99999999]
    rt_band_labels = ["<100ms", "100-250ms", "250-500ms", "500ms-1s", "1s-2s", "2s-5s", ">5s"]
    rt_band_counts = [0] * len(rt_band_labels)
    for ldata_item in display_labels.values():
        avg_v = ldata_item.get("avg_rt", 0)
        for bi in range(len(rt_bands) - 1):
            if rt_bands[bi] <= avg_v < rt_bands[bi + 1]:
                rt_band_counts[bi] += ldata_item.get("count", 0)
                break
    rt_hist_labels = json.dumps(rt_band_labels)
    rt_hist_counts = json.dumps(rt_band_counts)

    # SLA Pass/Fail Donut
    sla_pass_count  = sum(1 for lname_x, ldata_x in display_labels.items()
                          if ldata_x.get("p90", 0) <= sla_targets.get(lname_x, {"rt": default_rt})["rt"]
                          and ldata_x.get("error_rate", 0) <= sla_targets.get(lname_x, {"err": default_err})["err"])
    sla_breach_count = len(display_labels) - sla_pass_count

    # Active Virtual Users / Concurrency Over Time
    ts_tp_raw  = ts.get("ts_throughput", [])
    ts_rt_raw  = ts.get("ts_avg_rt", [])
    ts_active_threads = ts.get("ts_active_threads", [])
    if ts_active_threads and any(t > 0 for t in ts_active_threads):
        concurrency_est = json.dumps(ts_active_threads)
        peak_concurrency_est = max(ts_active_threads)
        concurrency_metric_note = "Actual active virtual user concurrency recorded by JMeter engine."
    else:
        # Fallback if allThreads was not in JTL
        concurrency_est = json.dumps([
            min(users, round(tp * (rt / 1000.0), 1)) if (tp and rt) else 0
            for tp, rt in zip(ts_tp_raw, ts_rt_raw)
        ])
        peak_concurrency_est = min(users, max([round(tp * (rt / 1000.0), 1) for tp, rt in zip(ts_tp_raw, ts_rt_raw)], default=users))
        concurrency_metric_note = "Estimated in-flight concurrency based on workload intensity."

    # ── User Journey (Thread Group) Breakdown for Load & Capacity Tab ──
    # ── User Journey (Thread Group) Breakdown for Load & Capacity Tab ──
    tg_configs = []
    try:
        from app.services.analytics.sla_manager import parse_jmx_thread_groups
        tg_configs = parse_jmx_thread_groups(jmx_name)
    except Exception as tg_err:
        print(f"[Report] Thread groups parse warning: {tg_err}", flush=True)

    if not tg_configs and tg_to_transactions:
        for tg_name, tcs in tg_to_transactions.items():
            tg_configs.append({
                "name": tg_name,
                "enabled": True,
                "wrapper_tc": None,
                "users": users // max(1, len(tg_to_transactions)) or 1,
                "duration": int(summary.get("duration_sec", 60)),
                "child_tcs": tcs
            })

    if not tg_configs:
        tg_configs.append({
            "name": "Default_User_Journey",
            "enabled": True,
            "wrapper_tc": None,
            "users": users,
            "duration": int(summary.get("duration_sec", 60)),
            "child_tcs": list(display_labels.keys())
        })

    total_tg_users = sum(tg.get("users", 1) for tg in tg_configs if tg.get("enabled", True)) if tg_configs else users
    test_dur_sec = max(1, int(summary.get("duration_sec", 60)))
    
    # ── High-Level Capacity Metrics ──
    cap_peak_tps = max(ts_tp_raw) if ts_tp_raw else summary.get('throughput', 0)
    cap_p95_val = summary.get('p95', 0)
    cap_p95_str = f"{cap_p95_val / 1000:.2f}s" if cap_p95_val >= 1000 else f"{cap_p95_val:.0f} ms"
    cap_err_rate_val = summary.get('raw_error_rate', summary.get('error_rate', 0))
    
    # Determine Safe Capacity & Overall Capacity Status
    has_global_err_breach = cap_err_rate_val > 1.0 or summary.get('errors', 0) > 50
    has_global_rt_breach = cap_p95_val > default_rt
    
    if has_global_err_breach and has_global_rt_breach:
        cap_status_text = "🔴 Capacity Breached"
        cap_status_color = "var(--red)"
        cap_safe_operating = f"~{max(1, total_tg_users // 2)} VUs (Constrained)"
    elif has_global_err_breach:
        cap_status_text = "🔴 Functional Error Limit"
        cap_status_color = "var(--red)"
        cap_safe_operating = f"{total_tg_users} VUs (Fix Errors)"
    elif has_global_rt_breach:
        cap_status_text = "🟡 Near Capacity (Latency)"
        cap_status_color = "var(--yellow)"
        cap_safe_operating = f"~{max(1, int(total_tg_users * 0.75))} VUs"
    else:
        cap_status_text = "🟢 Healthy Capacity"
        cap_status_color = "var(--green)"
        cap_safe_operating = f"{total_tg_users} VUs (Verified)"

    # ── Calculate Stepped Virtual User Ramp-Up & Workload Profile Data ──
    ramp_up_sec = max((tg.get("rampup") or tg.get("ramp_up") or 0) for tg in tg_configs) if tg_configs else 0
    if ramp_up_sec <= 0:
        raw_r = parsed.get("rampup") or summary.get("rampup") or summary.get("ramp_up")
        if raw_r:
            try:
                ramp_up_sec = int(str(raw_r).lower().replace("s", "").replace("sec", "").strip())
            except (ValueError, TypeError):
                pass
    if ramp_up_sec <= 0:
        ramp_up_sec = 0

    steady_state_sec = max(0, test_dur_sec - ramp_up_sec)
    
    def _fmt_clock(s):
        s = int(s or 0)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h}:{m:02d}:{sec:02d} hr"
        elif m > 0:
            return f"{m}:{sec:02d} min"
        else:
            return f"{sec}s"
            
    def _fmt_min_sec_badge(s):
        s = int(s or 0)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h}H {m}M {sec}S"
        elif m > 0 and sec > 0:
            return f"{m}M {sec}S"
        elif m > 0:
            return f"{m} MIN"
        else:
            return f"{sec} SEC"

    test_dur_formatted = _fmt_clock(test_dur_sec)
    ramp_up_text = _fmt_min_sec_badge(ramp_up_sec)
    steady_state_text = _fmt_min_sec_badge(steady_state_sec)

    # Generate elapsed timeline points with stepped VUs
    vu_time_points = []
    num_steps = min(total_tg_users, 10)
    if num_steps > 1 and ramp_up_sec > 0:
        for i in range(num_steps):
            t = int((i / (num_steps - 1)) * ramp_up_sec)
            vu = int(1 + i * (total_tg_users - 1) / max(1, num_steps - 1))
            vu_time_points.append((t, vu))
    else:
        vu_time_points.append((0, 1 if total_tg_users > 1 else total_tg_users))
        if ramp_up_sec > 0:
            vu_time_points.append((ramp_up_sec, total_tg_users))

    if test_dur_sec > ramp_up_sec:
        step_steady = max(30, (test_dur_sec - ramp_up_sec) // 7)
        cur_t = ramp_up_sec + step_steady
        while cur_t < test_dur_sec - 10:
            vu_time_points.append((cur_t, total_tg_users))
            cur_t += step_steady
        vu_time_points.append((test_dur_sec, total_tg_users))

    seen_times = set()
    final_time_points = []
    for t, vu in sorted(vu_time_points, key=lambda x: x[0]):
        if t not in seen_times:
            seen_times.add(t)
            final_time_points.append((t, vu))

    def _fmt_ts_label(s):
        s = int(s)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        else:
            return f"{m:02d}:{sec:02d}"

    vu_ramp_labels = [_fmt_ts_label(t) for t, _ in final_time_points]
    vu_ramp_data = [vu for _, vu in final_time_points]
    vu_ramp_labels_json = json.dumps(vu_ramp_labels)
    vu_ramp_data_json = json.dumps(vu_ramp_data)

    total_transactions_count = summary.get('total', 0)
    ts_lbls_list = json.loads(ts_labels)
    ts_vus_list = json.loads(concurrency_est) if concurrency_est else [total_tg_users] * len(ts_lbls_list)
    sla_ref_series = [round(default_rt, 1)] * len(ts_lbls_list)
    sla_ref_json = json.dumps(sla_ref_series)

    # ── Load Level Staging Matrix ──
    staging_rows_html = ""
    n_points = len(ts_lbls_list)
    if n_points >= 4:
        stg_chunks = [
            ("Ramp-up / Baseline", 0, max(1, n_points // 4)),
            ("Normal Operating Load", max(1, n_points // 4), max(2, n_points // 2)),
            ("High Load Phase", max(2, n_points // 2), max(3, (n_points * 3) // 4)),
            ("Peak Sustained Load", max(3, (n_points * 3) // 4), n_points)
        ]
        for stg_name, s_start, s_end in stg_chunks:
            chunk_vus = [int(x or 0) for x in ts_vus_list[s_start:s_end]] or [total_tg_users]
            chunk_tp = [float(x or 0) for x in ts_tp_raw[s_start:s_end]] or [cap_peak_tps]
            chunk_p95 = [float(x or 0) for x in ts.get("ts_p95_rt", [])[s_start:s_end]] or [cap_p95_val]
            chunk_err = [int(x or 0) for x in ts.get("ts_errors", [])[s_start:s_end]] or [0]
            
            c_vu_val = max(chunk_vus)
            c_tp_avg = sum(chunk_tp) / len(chunk_tp) if chunk_tp else 0
            c_p95_max = max(chunk_p95) if chunk_p95 else 0
            c_err_sum = sum(chunk_err)
            
            if c_err_sum > 0:
                c_eval = '<span style="color:var(--red); font-weight:700;">🔴 Functional Errors</span>'
            elif c_p95_max > default_rt:
                c_eval = '<span style="color:var(--yellow); font-weight:700;">🟡 Latency Breach</span>'
            else:
                c_eval = '<span style="color:var(--green); font-weight:700;">🟢 Healthy &amp; Stable</span>'
                
            staging_rows_html += f"""
            <tr style="border-bottom: 1px solid var(--border);">
                <td><strong>{stg_name}</strong></td>
                <td>{c_vu_val} VUs</td>
                <td>{c_tp_avg:.1f} TPS</td>
                <td>{c_p95_max} ms</td>
                <td style="color: {'var(--red)' if c_err_sum > 0 else 'var(--green)'}; font-weight: 600;">{c_err_sum} err</td>
                <td>{c_eval}</td>
            </tr>
            """
    else:
        staging_rows_html = f"""
        <tr style="border-bottom: 1px solid var(--border);">
            <td><strong>Full Test Execution</strong></td>
            <td>{total_tg_users} VUs</td>
            <td>{summary.get('throughput', 0):.1f} TPS</td>
            <td>{cap_p95_val} ms</td>
            <td style="color: {'var(--red)' if summary.get('errors', 0) > 0 else 'var(--green)'}; font-weight: 600;">{summary.get('errors', 0)} err</td>
            <td>{'<span style="color:var(--red); font-weight:700;">🔴 Errors</span>' if summary.get('errors', 0) > 0 else '<span style="color:var(--green); font-weight:700;">🟢 Stable</span>'}</td>
        </tr>
        """

    # ── User Journey Capacity Breakdown (Clean, Expandable Rows) ──
    tg_rows_html = ""
    bottleneck_cards_html = ""
    tg_passed_count = 0
    bottleneck_items = []
    
    for idx, tg in enumerate(tg_configs):
        tg_name = tg.get("name", "User Journey")
        tg_u = tg.get("users", 1)
        tg_dur = tg.get("duration", test_dur_sec)
        child_tcs = tg.get("child_tcs", [])
        wrapper_tc = tg.get("wrapper_tc")
        
        # Use disaggregated thread-group metrics if available
        tg_specific = labels_by_tg.get(tg_name, {})
        
        if wrapper_tc and (tg_specific.get(wrapper_tc) or wrapper_tc in labels):
            w_data = tg_specific.get(wrapper_tc) or labels[wrapper_tc]
            tg_iters = w_data.get("count", 0)
            tg_avg_rt = w_data.get("avg_rt", 0)
            tg_p90 = w_data.get("p90", 0)
            tg_errors = w_data.get("errors", 0)
        elif child_tcs:
            present_tcs_data = [tg_specific.get(tc) or labels.get(tc) for tc in child_tcs if (tg_specific.get(tc) or tc in labels)]
            present_tcs_data = [d for d in present_tcs_data if d]
            tg_iters = max((d.get("count", 0) for d in present_tcs_data), default=total_iterations)
            tg_avg_rt = (sum(d.get("avg_rt", 0) for d in present_tcs_data) / len(present_tcs_data)) if present_tcs_data else summary.get("avg_rt", 0)
            tg_p90 = max((d.get("p90", 0) for d in present_tcs_data), default=summary.get("p90", 0))
            tg_errors = sum(d.get("errors", 0) for d in present_tcs_data)
        else:
            tg_iters = total_iterations
            tg_avg_rt = summary.get("avg_rt", 0)
            tg_p90 = summary.get("p90", 0)
            tg_errors = summary.get("errors", 0)

        # Child samples & errors
        present_tcs = [tc for tc in child_tcs if (tg_specific.get(tc) or tc in labels)]
        tg_total_samples = sum((tg_specific.get(tc) or labels[tc]).get("count", 0) for tc in present_tcs) if present_tcs else tg_iters
        tg_err_rate = round((tg_errors / max(1, tg_total_samples) * 100), 2)
        tg_tps = round(tg_total_samples / max(1, tg_dur), 1)

        # Evaluate SLA compliance & specific failing transaction
        breached_tcs = []
        for tc in present_tcs:
            tc_data = tg_specific.get(tc) or labels.get(tc, {})
            tc_p90 = tc_data.get("p90", 0)
            tc_target = sla_targets.get(tc, {}).get("rt", default_rt)
            if tc_p90 > tc_target:
                breached_tcs.append((tc, tc_p90, tc_target))

        # Clear, separated SLA & Error Status
        if tg_errors > 0 and breached_tcs:
            sla_status_badge = f'<span style="color:var(--red); font-weight:700; font-size:0.8rem;">❌ SLA Breach &amp; Errors</span>'
            sla_explanation = f"P90: {tg_p90}ms vs SLA: {breached_tcs[0][2]:.0f}ms | {tg_errors} failed requests"
            capacity_rating = '<span style="background:rgba(239,68,68,0.12); color:#ef4444; border:1px solid #ef444455; padding:0.2rem 0.55rem; border-radius:10px; font-weight:700; font-size:0.75rem;">🔴 Constrained</span>'
            bottleneck_items.append((tg_name, "Primary Capacity Concern", f"Error rate: {tg_err_rate:.1f}% ({tg_errors} errors) · P90: {tg_p90}ms vs SLA {breached_tcs[0][2]:.0f}ms", "var(--red)", 1))
        elif tg_errors > 0:
            sla_status_badge = f'<span style="color:var(--red); font-weight:700; font-size:0.8rem;">❌ Error Breach</span>'
            sla_explanation = f"{tg_errors} failed HTTP requests ({tg_err_rate:.1f}%)"
            capacity_rating = '<span style="background:rgba(239,68,68,0.12); color:#ef4444; border:1px solid #ef444455; padding:0.2rem 0.55rem; border-radius:10px; font-weight:700; font-size:0.75rem;">🔴 Error Limit</span>'
            bottleneck_items.append((tg_name, "Functional Error Concern", f"Error rate: {tg_err_rate:.1f}% ({tg_errors} errors) · Requires endpoint investigation", "var(--red)", 2))
        elif breached_tcs:
            first_br = breached_tcs[0]
            sla_status_badge = f'<span style="color:var(--yellow); font-weight:700; font-size:0.8rem;">⚠️ SLA Breached</span>'
            sla_explanation = f"P90: {first_br[1]}ms vs SLA: {first_br[2]:.0f}ms on {first_br[0][:22]}"
            capacity_rating = '<span style="background:rgba(245,158,11,0.12); color:#f59e0b; border:1px solid #f59e0b55; padding:0.2rem 0.55rem; border-radius:10px; font-weight:700; font-size:0.75rem;">🟡 Latency Watch</span>'
            bottleneck_items.append((tg_name, "Latency SLA Deviation", f"P90: {first_br[1]}ms exceeds SLA target of {first_br[2]:.0f}ms · 0% errors", "var(--yellow)", 3))
        else:
            tg_passed_count += 1
            sla_status_badge = f'<span style="color:var(--green); font-weight:700; font-size:0.8rem;">✅ Met SLA</span>'
            sla_explanation = f"P90: {tg_p90}ms within target · 0% errors"
            capacity_rating = '<span style="background:rgba(16,185,129,0.12); color:#10b981; border:1px solid #10b98155; padding:0.2rem 0.55rem; border-radius:10px; font-weight:700; font-size:0.75rem;">🟢 Stable</span>'
            bottleneck_items.append((tg_name, "Stable Concurrency", f"P90: {tg_p90}ms · 0.00% error rate · Supported under tested load", "var(--green)", 4))

        # Build clean expandable child transaction breakdown table
        child_tx_subrows = ""
        for tc in child_tcs:
            tc_data = tg_specific.get(tc) or labels.get(tc, {})
            tc_p90 = tc_data.get("p90", 0)
            tc_avg = tc_data.get("avg_rt", 0)
            tc_count = tc_data.get("count", 0)
            tc_err_rate = tc_data.get("error_rate", 0)
            tc_target = sla_targets.get(tc, {}).get("rt", default_rt)
            tc_breached = tc_p90 > tc_target
            tc_dev = ((tc_p90 - tc_target) / tc_target * 100) if tc_target > 0 else 0
            
            child_tx_subrows += f"""
            <tr style="border-bottom: 1px solid var(--border); font-size: 0.78rem;">
                <td style="padding: 0.4rem 0.6rem; padding-left: 1.5rem;">↳ <code>{tc}</code></td>
                <td style="text-align:center;">{tc_count:,}</td>
                <td style="text-align:center;">{tc_avg:.0f} ms</td>
                <td style="text-align:center; color:{'var(--red)' if tc_breached else 'var(--text)'}; font-weight:700;">{tc_p90} ms</td>
                <td style="text-align:center; color:{'var(--red)' if tc_err_rate > 0 else 'var(--green)'};">{tc_err_rate:.2f}%</td>
                <td style="text-align:center;">{tc_target:.0f} ms</td>
                <td style="text-align:center; color:{'var(--red)' if tc_dev > 0 else 'var(--green)'}; font-weight:600;">{tc_dev:+.1f}%</td>
            </tr>
            """

        tg_share_pct = round((tg_u / total_tg_users) * 100, 1) if total_tg_users > 0 else 0
        tg_rows_html += f"""
        <tr style="border-bottom:1px solid var(--border);">
            <td style="padding:0.75rem 0.8rem; vertical-align:middle;">
                <div style="font-weight:700; font-size:0.9rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>👥</span> {tg_name}
                </div>
            </td>
            <td style="padding:0.75rem 0.8rem; text-align:center; vertical-align:middle;">
                <div style="font-size:1.05rem; font-weight:800; color:var(--text);">{tg_u} <small style="font-size:0.72rem; color:var(--muted); font-weight:600;">VU</small></div>
                <div style="font-size:0.72rem; color:var(--muted);">{tg_share_pct}% Load Share</div>
            </td>
            <td style="padding:0.75rem 0.8rem; text-align:center; vertical-align:middle;">
                <div style="font-size:1.05rem; font-weight:800; color:var(--text);">{tg_tps:.1f}</div>
                <div style="font-size:0.72rem; color:var(--muted);">TPS</div>
            </td>
            <td style="padding:0.75rem 0.8rem; text-align:center; vertical-align:middle;">
                <div style="font-size:0.92rem; font-weight:700; color:var(--text);">{tg_p90} ms</div>
                <div style="font-size:0.72rem; color:var(--muted);">P90 Latency</div>
            </td>
            <td style="padding:0.75rem 0.8rem; text-align:center; vertical-align:middle;">
                <div style="font-size:0.92rem; font-weight:800; color:{'var(--green)' if tg_errors == 0 else 'var(--red)'};">{tg_err_rate:.2f}%</div>
                <div style="font-size:0.72rem; color:var(--muted);">{tg_errors} errors</div>
            </td>
            <td style="padding:0.75rem 0.8rem; vertical-align:middle;">
                <div>{sla_status_badge}</div>
                <div style="font-size:0.72rem; color:var(--muted); margin-top:0.2rem;">{sla_explanation}</div>
            </td>
           
        </tr>
        """

    # Build Bottleneck Cards HTML
    bottleneck_items.sort(key=lambda x: x[4])
    bottleneck_cards_html = ""
    for b_name, b_title, b_desc, b_color, _ in bottleneck_items:
        bottleneck_cards_html += f"""
        <div class="kpi-card glass-panel" style="background:var(--surface1); border-left:4px solid {b_color}; padding:0.9rem 1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                <span style="font-weight:700; font-size:0.88rem; color:var(--text);">👥 {b_name}</span>
                <span style="font-size:0.7rem; font-weight:700; color:{b_color};">{b_title}</span>
            </div>
            <div style="font-size:0.78rem; color:var(--muted); line-height:1.45;">{b_desc}</div>
        </div>
        """

    tg_compliance_pct = round((tg_passed_count / max(1, len(tg_configs))) * 100) if tg_configs else 100

    # Azure data with fallback to demo metrics and timeline alignment
    if not azure_data or not azure_data.get("time_series", {}).get("cpu"):
        try:
            from app.core.constants import ROOT_DIR, DATA_DIR
            mock_path = DATA_DIR / "mock_azure_metrics.json"
            if not mock_path.exists():
                mock_path = ROOT_DIR / "app" / "server_metrics" / "azure" / "mock_azure_metrics.json"
            if mock_path.exists():
                from app.server_metrics.azure.parser import _parse_mock_metrics
                with open(mock_path, "r", encoding="utf-8") as f:
                    mock_raw = json.load(f)
                azure_data = _parse_mock_metrics(mock_raw)
        except Exception:
            pass

    azure_configured = bool(azure_data and (azure_data.get("configured") or azure_data.get("time_series", {}).get("cpu")))
    infra = azure_data.get("infra_summary", {}) if azure_data else {}
    azure_ts = azure_data.get("time_series", {}) if azure_data else {}

    def _align_series(raw_list, target_len):
        """Resample, duplicate, or interpolate metric data to match exact target timeline length."""
        if not raw_list:
            return [0.0] * target_len
        if len(raw_list) == target_len:
            return [round(float(x), 2) for x in raw_list]
        if target_len <= 1:
            return [round(float(raw_list[0]), 2)]
        res = []
        n_raw = len(raw_list)
        for i in range(target_len):
            pos = (i / (target_len - 1)) * (n_raw - 1)
            low_idx = int(pos)
            high_idx = min(low_idx + 1, n_raw - 1)
            frac = pos - low_idx
            val = float(raw_list[low_idx]) * (1.0 - frac) + float(raw_list[high_idx]) * frac
            res.append(round(val, 2))
        return res

    target_ts_len = max(1, len(ts_labels))

    raw_cpu = _align_series(azure_ts.get("cpu", [34.2, 41.7, 46.3, 82.6, 91.4, 68.2]), target_ts_len)
    raw_mem = _align_series(azure_ts.get("memory", [52.4, 55.7, 61.2, 74.8, 89.3, 82.7]), target_ts_len)
    raw_disk_q = _align_series(azure_ts.get("disk_queue", [1.4, 2.1, 7.8, 14.5, 12.0, 3.2]), target_ts_len)
    raw_disk_read = _align_series(azure_ts.get("disk_read_mb", [5.2, 7.3, 9.4, 52.4, 45.0, 12.0]), target_ts_len)
    raw_disk_write = _align_series(azure_ts.get("disk_write_mb", [3.1, 4.2, 8.4, 18.4, 15.0, 5.0]), target_ts_len)
    raw_net_in = _align_series(azure_ts.get("network_in", [17.6, 20.4, 43.6, 81.7, 71.5, 23.8]), target_ts_len)
    raw_net_out = _align_series(azure_ts.get("network_out", [8.9, 10.8, 27.4, 56.0, 45.8, 14.3]), target_ts_len)
    raw_avail = _align_series(azure_ts.get("availability", [100.0] * 6), target_ts_len)

    if not infra or not infra.get("avg_cpu"):
        infra = {
            "avg_cpu": round(sum(raw_cpu) / len(raw_cpu), 1),
            "max_cpu": round(max(raw_cpu), 1),
            "avg_memory": round(sum(raw_mem) / len(raw_mem), 1),
            "max_memory": round(max(raw_mem), 1),
            "avg_network_in_mbps": round(sum(raw_net_in) / len(raw_net_in), 1),
            "avg_network_out_mbps": round(sum(raw_net_out) / len(raw_net_out), 1),
            "avg_disk_read_iops": round(sum(raw_disk_read) / len(raw_disk_read), 1),
            "avg_disk_write_iops": round(sum(raw_disk_write) / len(raw_disk_write), 1)
        }

    peak_cpu_val = max(raw_cpu, default=0)
    peak_mem_val = max(raw_mem, default=0)
    peak_disk_q_val = max(raw_disk_q, default=0)
    min_avail_val = min(raw_avail, default=100.0)

    ts_cpu = json.dumps(raw_cpu)
    ts_memory = json.dumps(raw_mem)
    ts_disk_q_json = json.dumps(raw_disk_q)
    ts_disk_read_json = json.dumps(raw_disk_read)
    ts_disk_write_json = json.dumps(raw_disk_write)
    ts_net_in_json = json.dumps(raw_net_in)
    ts_net_out_json = json.dumps(raw_net_out)
    ts_avail_json = json.dumps(raw_avail)

    # Dynamic Pearson Correlation Calculation
    def calc_pearson_r(x_list, y_list):
        if not x_list or not y_list or len(x_list) != len(y_list) or len(x_list) < 2:
            return 0.0
        n = len(x_list)
        mean_x = sum(x_list) / n
        mean_y = sum(y_list) / n
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_list, y_list))
        std_x = (sum((x - mean_x) ** 2 for x in x_list)) ** 0.5
        std_y = (sum((y - mean_y) ** 2 for y in y_list)) ** 0.5
        if std_x == 0 or std_y == 0:
            return 0.0
        return round(cov / (std_x * std_y), 2)

    # Dynamic Correlation Matrix Values
    min_len = min(len(raw_cpu), len(ts_tp_raw))
    r_cpu_mem = calc_pearson_r(raw_cpu[:min_len], raw_mem[:min_len])
    r_cpu_tp  = calc_pearson_r(raw_cpu[:min_len], ts_tp_raw[:min_len])
    r_cpu_rt  = calc_pearson_r(raw_cpu[:min_len], ts_rt_raw[:min_len])
    r_mem_tp  = calc_pearson_r(raw_mem[:min_len], ts_tp_raw[:min_len])
    r_mem_rt  = calc_pearson_r(raw_mem[:min_len], ts_rt_raw[:min_len])
    r_tp_rt   = calc_pearson_r(ts_tp_raw, ts_rt_raw)

    # Dynamic Timeline Events Generation
    timeline_events = []
    for idx_t, lbl_t in enumerate(ts_labels):
        tp_v = ts_tp_raw[idx_t] if idx_t < len(ts_tp_raw) else 0
        rt_v = ts_rt_raw[idx_t] if idx_t < len(ts_rt_raw) else 0
        cpu_v = raw_cpu[idx_t] if idx_t < len(raw_cpu) else 0
        mem_v = raw_mem[idx_t] if idx_t < len(raw_mem) else 0

        if tp_v > 0 and not any(e['type'] == 'traffic' for e in timeline_events):
            timeline_events.append({'time': lbl_t, 'color': '#3b82f6', 'icon': '🚦', 'title': 'Traffic Ramp-up', 'desc': f'Request throughput reached {round(tp_v)} req/s', 'type': 'traffic'})
        if cpu_v >= 80 and not any(e['type'] == 'cpu' for e in timeline_events):
            timeline_events.append({'time': lbl_t, 'color': '#f59e0b', 'icon': '⚠️', 'title': 'CPU Saturation', 'desc': f'Host CPU utilization reached {round(cpu_v)}%', 'type': 'cpu'})
        if mem_v >= 80 and not any(e['type'] == 'mem' for e in timeline_events):
            timeline_events.append({'time': lbl_t, 'color': '#8b5cf6', 'icon': '⚠️', 'title': 'Memory Pressure', 'desc': f'Host memory utilization climbed to {round(mem_v)}%', 'type': 'mem'})
        if rt_v > default_rt and not any(e['type'] == 'rt' for e in timeline_events):
            timeline_events.append({'time': lbl_t, 'color': '#ef4444', 'icon': '🔴', 'title': 'Latency Spike', 'desc': f'Average response time reached {round(rt_v)} ms', 'type': 'rt'})

    if not timeline_events:
        timeline_events.append({'time': '00:00', 'color': '#10b981', 'icon': '✅', 'title': 'Stable Execution', 'desc': 'All workload and server metrics remained within normal operating limits.', 'type': 'stable'})

    timeline_html = ""
    for ev in timeline_events:
        timeline_html += f"""
        <div style="display:flex; align-items:center; gap:0.6rem; background:var(--surface2); padding:0.45rem 0.75rem; border-radius:6px; border-left:3px solid {ev['color']};">
            <span style="font-family:'JetBrains Mono', monospace; font-weight:700; color:{ev['color']};">{ev['time']}</span>
            <span>{ev['icon']} <strong>{ev['title']}:</strong> {ev['desc']}</span>
        </div>"""
    def _clean_client_text(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'\s*\([FR]-\d+\)', '', str(text))
        cleaned = re.sub(r'\s*\[[FR]-\d+\]', '', cleaned)
        cleaned = re.sub(r'\b[FR]-\d+\b:?\s*', '', cleaned)
        return re.sub(r'\s{2,}', ' ', cleaned).strip()

    def _build_validation_badge(val_id: str, label_text: str = "Validate as Performance Engineer") -> str:
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(val_id))
        return f'''<label class="human-val-label" id="val_lbl_{safe_id}" title="Click to validate this AI section as a Performance Engineer"><input type="checkbox" class="human-val-checkbox" data-val-id="{safe_id}" onchange="toggleAiValidation(this, '{safe_id}')"><span class="human-val-text">{label_text}</span></label>'''

    def _format_as_pointers(text_or_list) -> str:
        bullets = []
        if isinstance(text_or_list, list):
            bullets = [_clean_client_text(b) for b in text_or_list if _clean_client_text(b)]
        elif isinstance(text_or_list, str) and text_or_list.strip():
            raw_text = text_or_list.strip()
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            for line in lines:
                cleaned_l = re.sub(r'^[•\-\*\d\.\)\s]+', '', line).strip()
                if cleaned_l:
                    bullets.append(_clean_client_text(cleaned_l))
            if len(bullets) <= 1:
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', raw_text) if s.strip()]
                if len(sentences) > 1:
                    bullets = [_clean_client_text(s) for s in sentences if _clean_client_text(s)]
        if not bullets:
            return '<li style="color:var(--muted);">No executive overview pointers generated</li>'
        return "".join([f'<li style="margin-bottom:0.45rem; line-height:1.6;">{b}</li>' for b in bullets])

    # AI Insights
    ai_source = ai_insights.get("source", "none") if ai_insights else "none"
    ai_badge = " AI Generated" if ai_source in ("gemini", "github_ai", "gemini_2.0") else "⚠️ No AI Analysis"
    ai_badge_color = "#3b82f6" if ai_source in ("gemini", "github_ai", "gemini_2.0") else "#6b7280"

    exec_summary = ai_insights.get("executive_summary", "No AI analysis available.") if ai_insights else "AI insights not generated."
    root_cause = ai_insights.get("root_cause", "N/A") if ai_insights else "N/A"
    bottleneck = ai_insights.get("bottleneck_analysis", "N/A") if ai_insights else "N/A"
    tail_analysis = ai_insights.get("tail_latency_analysis", "N/A") if ai_insights else "N/A"
    infra_analysis = ai_insights.get("infra_analysis", "N/A") if ai_insights else "N/A"
    correlation_insights = ai_insights.get("correlation_insights", "N/A") if ai_insights else "N/A"

    # Recommendations
    recs_html = ""
    if ai_insights and ai_insights.get("recommendations"):
        for rec in ai_insights["recommendations"]:
            pri = rec.get("priority", "Medium")
            pri_class = "critical" if pri == "Critical" else "warning" if pri == "High" else "info"
            recs_html += f"""
            <div class="rec-card {pri_class}">
                <div class="rec-header">
                    <span class="rec-priority">{pri}</span>
                    <span class="rec-category">{rec.get('category', '')}</span>
                </div>
                <div class="rec-title" contenteditable="true">{rec.get('title', '')}</div>
                <div class="rec-desc" contenteditable="true">{rec.get('description', '')}</div>
                <div class="rec-impact">Expected Impact: <span contenteditable="true">{rec.get('expected_impact', 'TBD')}</span></div>
            </div>"""
    else:
        recs_html = '<div class="rec-card info"><div class="rec-title" contenteditable="true">No AI recommendations available</div><div class="rec-desc" contenteditable="true">AI analysis was either not run or did not generate recommendations for this test.</div></div>'

    # Roadmap
    roadmap_html = ""
    if ai_insights and ai_insights.get("optimization_roadmap"):
        for i, step in enumerate(ai_insights["optimization_roadmap"], 1):
            roadmap_html += f'<div class="roadmap-step"><span class="step-num">{i}</span><span contenteditable="true">{step}</span></div>'

    # Capacity Planning
    cap = ai_insights.get("capacity_planning", {}) if ai_insights else {}
    cap_html = ""
    if cap:
        est_max = cap.get('estimated_max_users')
        safe_conc = cap.get('safe_concurrency')
        sat_pt = cap.get('saturation_point')
        cap_html = f"""
        <div class="capacity-grid">
            <div class="cap-card"><div class="cap-label">Estimated Max Users</div><div class="cap-value" contenteditable="true">{est_max if est_max is not None else 'N/A'}</div></div>
            <div class="cap-card"><div class="cap-label">Safe Concurrency</div><div class="cap-value" contenteditable="true">{safe_conc if safe_conc is not None else 'N/A'}</div></div>
            <div class="cap-card"><div class="cap-label">Saturation Point</div><div class="cap-value" contenteditable="true">{sat_pt if sat_pt is not None else 'N/A'}</div></div>
        </div>
        <p class="cap-analysis" contenteditable="true">{cap.get('analysis', '')}</p>"""

    # Section display styles (computed after azure_configured, cap, and roadmap_html)
    azure_section_style = "display: block;" if azure_configured else "display: none;"
    cap_section_style = "display: block;" if cap else "display: none;"
    roadmap_section_style = "display: block;" if roadmap_html else "display: none;"

    # Correlation findings
    corr_html = ""
    if correlation and correlation.get("findings"):
        for f in correlation["findings"]:
            sev = f.get("severity", "info")
            sev_icon = "🔴" if sev == "critical" else "🟡" if sev == "warning" else "🔵"
            corr_html += f'<div class="corr-finding {sev}"><span>{sev_icon}</span> {f.get("message", "")}</div>'
    else:
        corr_html = '<div class="corr-finding info">No correlation findings — Azure Monitor may not be configured.</div>'

    # ── Findings Engine: Generate Structured Findings ──────────────────────────
    from app.services.ai.findings import generate_findings, enrich_findings_with_ai, SEVERITY_BADGES
    findings_result = generate_findings(
        summary=summary, labels=labels, display_labels=display_labels,
        time_series=ts, infra=infra, correlation=correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err,
        ai_insights=ai_insights, auto_ai=True
    )
    # Enrich with AI interpretations if available
    if ai_insights:
        findings_result = enrich_findings_with_ai(findings_result, ai_insights)

    all_findings = findings_result.get("findings", [])
    all_recommendations = findings_result.get("recommendations", [])
    chart_observations = findings_result.get("chart_observations", {})
    tx_findings_map = findings_result.get("transaction_findings", {})
    overall_assessment = findings_result.get("overall_assessment", {})
    
    data_quality_findings = findings_result.get("data_quality_findings", [])
    data_quality_html = ""
    if data_quality_findings:
        data_quality_html += '<div class="section glass-panel" style="margin-bottom: 1.5rem; border-left: 4px solid var(--yellow);">'
        data_quality_html += '<h2>⚠️ Data Quality Findings</h2>'
        for dq in data_quality_findings:
            sev_color = "var(--red)" if dq.get("severity", "").lower() == "critical" else "var(--yellow)" if dq.get("severity", "").lower() == "warning" else "var(--blue)"
            data_quality_html += f'''
            <div style="background:var(--surface2); border:1px solid var(--border); border-left:4px solid {sev_color}; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                <h4 style="margin:0 0 0.5rem 0; color:{sev_color};">{dq.get("issue", "Data issue")}</h4>
                <div style="font-size:0.85rem; margin-bottom:0.4rem;"><strong>Evidence:</strong> {dq.get("evidence", "")}</div>
                <div style="font-size:0.85rem; margin-bottom:0.4rem;"><strong>Impact:</strong> {dq.get("impact", "")}</div>
                <div style="font-size:0.85rem; color:var(--muted);"><strong>Action:</strong> {dq.get("action", "")}</div>
            </div>
            '''
        data_quality_html += '</div>'

    overall_rc = findings_result.get("overall_root_cause", {})
    overall_rc_html = ""
    if overall_rc:
        if isinstance(overall_rc, list):
            rc_cards = ""
            for item in overall_rc:
                if isinstance(item, dict):
                    f_name = item.get("finding", item.get("primary_bottleneck", "Finding"))
                    ev_text = item.get("evidence", "")
                    if isinstance(ev_text, list):
                        ev_text = " &middot; ".join(ev_text)
                    cause = item.get("likely_cause", item.get("assessment", ""))
                    conf = item.get("confidence", "Medium")
                    rc_cards += f'''
                    <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
                        <div style="font-size:0.95rem; font-weight:700; color:var(--text); margin-bottom:0.3rem;">{f_name}</div>
                        <p style="font-size:0.85rem; margin:0 0 0.4rem 0; color:var(--text);">{cause}</p>
                        {f"<div style='font-size:0.8rem; color:var(--muted); margin-bottom:0.4rem;'><strong>Evidence:</strong> {ev_text}</div>" if ev_text else ""}
                        <div style="font-size:0.75rem; font-weight:600; display:inline-block; padding:0.15rem 0.5rem; border-radius:4px; background:var(--surface); border:1px solid var(--border);">Confidence: {conf}</div>
                    </div>
                    '''
            overall_rc_html = f'''
            <div class="section glass-panel" style="margin-bottom: 1.5rem; border-left: 4px solid var(--blue);">
                <h2>🔍 Primary Root-Cause Assessment</h2>
                {rc_cards}
            </div>
            '''
        elif isinstance(overall_rc, dict):
            rc_ev = ""
            ev_data = overall_rc.get("evidence")
            if ev_data:
                ev_str = " &middot; ".join(ev_data) if isinstance(ev_data, list) else str(ev_data)
                rc_ev = f"<div style='margin-top:0.8rem; font-size:0.8rem; color:var(--muted);'><strong>Evidence:</strong> {ev_str}</div>"
            overall_rc_html = f'''
            <div class="section glass-panel" style="margin-bottom: 1.5rem; border-left: 4px solid var(--blue);">
                <h2>🔍 Primary Root-Cause Assessment</h2>
                <div style="font-size:1.05rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">{overall_rc.get("primary_bottleneck", "No bottleneck identified")}</div>
                <p style="font-size:0.9rem; margin-bottom:0.5rem;">{overall_rc.get("assessment", "")}</p>
                <div style="font-size:0.8rem; font-weight:600; display:inline-block; padding:0.2rem 0.6rem; border-radius:4px; background:var(--surface2); border:1px solid var(--border);">Confidence: {overall_rc.get("confidence", "Unknown")}</div>
                {rc_ev}
            </div>
            '''

    # ── Build inline observation HTML panels ──────────────────────────────────
    rt_obs = chart_observations.get("response_time", {})
    rt_observation_html = ""
    if rt_obs:
        status_code = rt_obs.get("status_code", "healthy")
        badge_text = rt_obs.get("badge", "🟢 Latency Stable")
        border_color = "var(--green)" if status_code == "healthy" else "var(--yellow)" if status_code == "variable" else "var(--red)"
        bg_color = "rgba(16,185,129,0.05)" if status_code == "healthy" else "rgba(245,158,11,0.05)" if status_code == "variable" else "rgba(239,68,68,0.05)"
        related_badge = f'<span class="finding-badge-inline" onclick="showFinding(\'{rt_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {rt_obs.get("related_finding", "")}</span>' if rt_obs.get("related_finding") else ""
        
        rt_observation_html = f'''
        <div class="glass-panel ai-sub-card" style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Performance Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    {related_badge}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{badge_text}</span>
                    {_build_validation_badge("chart_obs_rt")}
                </div>
            </div>
            
            <p style="font-size:0.88rem; line-height:1.6; color:var(--text); margin:0 0 0.55rem 0;" contenteditable="true">
                {rt_obs.get("observation", "")}
            </p>
            
            <div style="margin-bottom:0.55rem;">
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Why it matters:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--text); margin:0;" contenteditable="true">
                    {rt_obs.get("why_it_matters", "")}
                </p>
            </div>
            
            <div>
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Recommended validation:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--muted); margin:0;" contenteditable="true">
                    {rt_obs.get("validate", "")}
                </p>
            </div>
        </div>
        '''

    tp_obs = chart_observations.get("throughput", {})
    tp_observation_html = ""
    if tp_obs:
        status_code = tp_obs.get("status_code", "healthy")
        badge_text = tp_obs.get("badge", "🟢 Stable Throughput")
        border_color = "var(--green)" if status_code == "healthy" else "var(--yellow)" if status_code in ("variable", "degrading") else "var(--red)"
        bg_color = "rgba(16,185,129,0.05)" if status_code == "healthy" else "rgba(245,158,11,0.05)" if status_code in ("variable", "degrading") else "rgba(239,68,68,0.05)"
        tp_related_badge = f'<span class="finding-badge-inline" onclick="showFinding(\'{tp_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {tp_obs.get("related_finding", "")}</span>' if tp_obs.get("related_finding") else ""
        
        tp_observation_html = f'''
        <div class="glass-panel ai-sub-card" style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Performance Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    {tp_related_badge}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{badge_text}</span>
                    {_build_validation_badge("chart_obs_tp")}
                </div>
            </div>
            
            <p style="font-size:0.88rem; line-height:1.6; color:var(--text); margin:0 0 0.55rem 0;" contenteditable="true">
                {tp_obs.get("observation", "")}
            </p>
            
            <div style="margin-bottom:0.55rem;">
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Why it matters:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--text); margin:0;" contenteditable="true">
                    {tp_obs.get("why_it_matters", "")}
                </p>
            </div>
            
            <div>
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Recommended validation:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--muted); margin:0;" contenteditable="true">
                    {tp_obs.get("validate", "")}
                </p>
            </div>
        </div>
        '''

    infra_obs = chart_observations.get("infrastructure")
    infra_observation_html = ""
    if infra_obs:
        inf_status = infra_obs.get("status_code", "healthy")
        inf_badge = infra_obs.get("badge", "🟢 Infrastructure Healthy")
        inf_border = "var(--green)" if inf_status == "healthy" else "var(--yellow)" if inf_status == "variable" else "var(--red)"
        inf_bg = "rgba(16,185,129,0.05)" if inf_status == "healthy" else "rgba(245,158,11,0.05)" if inf_status == "variable" else "rgba(239,68,68,0.05)"
        infra_related = f'<span class="finding-badge-inline" onclick="showFinding(\'{infra_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {infra_obs.get("related_finding", "")}</span>' if infra_obs.get("related_finding") else ""
        
        infra_observation_html = f'''
        <div class="glass-panel ai-sub-card" style="border-left: 4px solid {inf_border}; background: {inf_bg}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Infrastructure Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    {infra_related}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{inf_badge}</span>
                    {_build_validation_badge("chart_obs_infra")}
                </div>
            </div>
            
            <p style="font-size:0.88rem; line-height:1.6; color:var(--text); margin:0 0 0.55rem 0;" contenteditable="true">
                {infra_obs.get("observation", "")}
            </p>
            
            <div style="margin-bottom:0.55rem;">
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Why it matters:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--text); margin:0;" contenteditable="true">
                    {infra_obs.get("why_it_matters", "")}
                </p>
            </div>
            
            <div>
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:0.15rem;">Recommended validation:</div>
                <p style="font-size:0.84rem; line-height:1.55; color:var(--muted); margin:0;" contenteditable="true">
                    {infra_obs.get("validate", "")}
                </p>
            </div>
        </div>
        '''

    # ── Build transaction finding badges for table column ─────────────────────
    # This map: tx_name → HTML badge string
    tx_finding_badges = {}
    for tx_name, finding in tx_findings_map.items():
        sev_icon, sev_color = SEVERITY_BADGES.get(finding["severity"], ("⚪", "var(--muted)"))
        fid = finding["id"]
        short_title = finding["title"].replace(tx_name + " ", "").replace("is the ", "")
        badge_html = f'<a href="#" onclick="showFinding(\'{fid}\'); return false;" style="text-decoration:none; cursor:pointer;"><span class="finding-badge" style="border-color:{sev_color}; color:{sev_color};">{sev_icon} {fid} {short_title}</span></a>'
        tx_finding_badges[tx_name] = badge_html

    # Replace badge placeholders in labels_rows with actual finding badges
    for tx_name in display_labels.keys():
        placeholder = f"__FINDING_BADGE_{tx_name}__"
        badge = tx_finding_badges.get(tx_name, '<span class="finding-badge" style="border-color:var(--green); color:var(--green);">🟢 Within target</span>')
        labels_rows = labels_rows.replace(placeholder, badge)

    # ── Build the restructured AI Summary tab content ─────────────────────────
    # 1. Overall Assessment
    assessment_html = f'''
    <div class="section glass-panel" style="border-left: 4px solid {overall_assessment.get('color', 'var(--accent)')}; margin-bottom: 1.5rem;">
        <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
            <span style="font-size:2rem;">{overall_assessment.get('icon', '🔵')}</span>
            <div>
                <h2 style="margin:0; font-size:1.15rem;">AI Performance Assessment</h2>
                <p style="margin:0.2rem 0 0 0; font-size:0.95rem; font-weight:700; color:{overall_assessment.get('color', 'var(--text)')}">{overall_assessment.get('status', 'Assessment unavailable')}</p>
            </div>
            <span class="ai-badge" style="margin-left:auto;">{ai_badge}</span>
        </div>
        <div style="display:flex; gap:1rem; flex-wrap:wrap; font-size:0.82rem;">
            <span style="background:rgba(239,68,68,0.1); color:#ef4444; padding:0.3rem 0.7rem; border-radius:8px; font-weight:700;">{overall_assessment.get('critical', 0)} Critical</span>
            <span style="background:rgba(245,158,11,0.1); color:#f59e0b; padding:0.3rem 0.7rem; border-radius:8px; font-weight:700;">{overall_assessment.get('high', 0)} High</span>
            <span style="background:rgba(245,158,11,0.08); color:#d97706; padding:0.3rem 0.7rem; border-radius:8px; font-weight:700;">{overall_assessment.get('medium', 0)} Medium</span>
            <span style="background:rgba(16,185,129,0.1); color:#10b981; padding:0.3rem 0.7rem; border-radius:8px; font-weight:700;">{overall_assessment.get('low', 0)} Low</span>
        </div>
    </div>
    '''

    # 2. Categorize Findings for Test Summary
    tx_findings_html, rt_findings_html, err_findings_html, infra_findings_html = "", "", "", ""
    for f in all_findings:
        sev_icon, sev_color = SEVERITY_BADGES.get(f["severity"], ("⚪", "var(--muted)"))
        evidence_items = ""
        for ev in f.get("evidence", []):
            baseline_text = f' (baseline: {ev["baseline"]})' if ev.get("baseline") else ""
            evidence_items += f'<div style="display:flex; justify-content:space-between; padding:0.15rem 0; font-size:0.75rem;"><span style="color:var(--muted);">{ev["metric"]}</span><span style="font-weight:600;">{ev["value"]}{baseline_text}</span></div>'

        finding_html = f'''
        <div style="margin-bottom:0.6rem; padding-bottom:0.6rem; border-bottom:1px solid var(--border);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.3rem;">
                <span style="color:{sev_color}; font-size:0.8rem;">{sev_icon}</span>
                <strong style="font-size:0.82rem;">{f['title']}</strong>
            </div>
            <p style="font-size:0.78rem; margin:0 0 0.4rem 0;" contenteditable="true">{f['observation']}</p>
            {f'<div style="background:var(--surface2); padding:0.4rem; border-radius:6px; margin-bottom:0.4rem;">{evidence_items}</div>' if evidence_items else ''}
        </div>
        '''
        
        c = f.get("category", "").lower()
        title_low = f.get("title", "").lower()
        if "infra" in c or "server" in c or "azure" in c or "cpu" in title_low or "memory" in title_low:
            infra_findings_html += finding_html
        elif "error" in c or "fail" in c or "exception" in title_low:
            err_findings_html += finding_html
        elif "latency" in c or "sla" in c or "slow" in c or "response" in c or "apdex" in title_low:
            rt_findings_html += finding_html
        else:
            tx_findings_html += finding_html

    # Build Key Performance Findings list (Client-facing 1-liners without metric table dumps)
    key_findings_html = ""
    for f in all_findings:
        sev_icon, sev_color = SEVERITY_BADGES.get(f["severity"], ("⚪", "var(--muted)"))
        sev_str = str(f.get("severity", "")).lower()
        dev_label = "Critical Deviation" if "critical" in sev_str else "Slight Deviation" if "high" in sev_str else "Minor Deviation"
        title_clean = f["title"].replace(" shows significant latency deviation", "").replace(" SLA deviation", "")
        obs_clean = f.get("observation", "")
        
        key_findings_html += f'''
        <div style="margin-bottom: 0.8rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--border);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                <span style="font-size:0.9rem;">{sev_icon}</span>
                <strong style="font-size:0.9rem; color:var(--text);">{title_clean}</strong>
                <span style="font-size:0.72rem; font-weight:700; color:{sev_color}; background:var(--surface2); border:1px solid var(--border); padding:0.15rem 0.5rem; border-radius:4px; margin-left:auto;">{dev_label}</span>
            </div>
            <div style="font-size:0.82rem; color:var(--muted); margin-left:1.4rem;" contenteditable="true">{obs_clean}</div>
        </div>
        '''

    if not key_findings_html:
        key_findings_html = '<div style="font-size:0.85rem; color:var(--muted); padding:0.5rem 0;">✅ All transactions performed within expected baseline and SLA targets.</div>'

    # 3. Root-Cause Confidence Table
    confidence_table_rows = ""
    confidence_areas = [
        ("Transaction bottleneck identification", "High confidence" if any(f["category"] == "latency_bottleneck" for f in all_findings) else "No bottleneck detected"),
        ("SLA violation detection", "High confidence" if any(f["category"] == "sla_breach" for f in all_findings) else "All within SLA"),
        ("Error occurrence", "High confidence" if any(f["category"] == "error_anomaly" for f in all_findings) else "No significant errors"),
        ("Specific backend root cause", "Requires server telemetry" if not infra else "Medium confidence"),
        ("Capacity saturation limit", "Requires additional load" if summary.get("throughput", 0) > 0 else "Insufficient data"),
    ]
    for area, assessment in confidence_areas:
        color = "var(--green)" if "High" in assessment else "var(--yellow)" if "Medium" in assessment else "var(--muted)"
        confidence_table_rows += f'<tr><td style="font-weight:600;">{area}</td><td style="color:{color}; font-weight:600;">{assessment}</td></tr>'

    # 4. Recommendations
    linked_recs_html = ""
    for rec in all_recommendations:
        pri = rec.get("priority", "Medium")
        pri_class = "critical" if pri == "Critical" else "warning" if pri == "High" else "info"
        
        why_text = rec.get("why", "")
        why_html = f'<div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">Why:</strong> <span style="font-size:0.82rem;" contenteditable="true">{why_text}</span></div>' if why_text else ""
        
        actions = rec.get("action", [])
        if isinstance(actions, list) and actions:
            action_items = "<ul style='margin:0.3rem 0 0 1rem; font-size:0.82rem;'>" + "".join([f"<li contenteditable='true'>{a}</li>" for a in actions]) + "</ul>"
            action_html = f'<div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">Action:</strong>{action_items}</div>'
        elif isinstance(actions, str) and actions.strip():
            action_html = f'<div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">Action:</strong> <span style="font-size:0.82rem;" contenteditable="true">{actions}</span></div>'
        else:
            action_html = ""

        impact_text = rec.get("expected_impact", "")
        impact_html = f'<div class="rec-impact">Expected Impact: <span contenteditable="true">{impact_text}</span></div>' if impact_text else ""
        
        val_text = rec.get("validation", "")
        val_html = f'<div style="margin-top:0.4rem; font-size:0.78rem; color:var(--muted);"><strong>Validation:</strong> <span contenteditable="true">{val_text}</span></div>' if val_text else ""

        linked_recs_html += f'''
        <div class="rec-card {pri_class}" style="margin-bottom: 1rem; position: relative;">
            <button class="delete-rec-btn" onclick="if(confirm('Remove this recommendation?')) this.closest('.rec-card').remove();" title="Delete Recommendation" style="position:absolute; top:0.8rem; right:0.8rem; background:rgba(239,68,68,0.1); color:#ef4444; border:1px solid rgba(239,68,68,0.3); border-radius:4px; padding:0.15rem 0.4rem; font-size:0.7rem; cursor:pointer;">🗑️ Delete</button>
            <div class="rec-header">
                <span class="rec-priority" contenteditable="true">{pri}</span>
                <span class="rec-category" contenteditable="true">{rec.get('category', 'General')}</span>
            </div>
            <div class="rec-title" contenteditable="true">{rec.get('title', '')}</div>
            {why_html}
            {action_html}
            {impact_html}
            {val_html}
        </div>
        '''

    # 5. Priority Actions
    priority_actions_html = ""
    for i, f in enumerate(all_findings[:5], start=1):
        sev_icon, _ = SEVERITY_BADGES.get(f["severity"], ("⚪", ""))
        title_clean = _clean_client_text(f.get("title", ""))
        priority_actions_html += f'<div class="roadmap-step"><span class="step-num">{i}</span><span>{sev_icon} Investigate <strong>{title_clean}</strong></span></div>'

    if not priority_actions_html:
        priority_actions_html = '<div class="roadmap-step"><span class="step-num">1</span><span>🟢 No critical findings — maintain current performance baseline.</span></div>'

    # ── 6. Build Performance Intelligence Sections (Executive Summary & Tab-wise) ─
    perf_intel = findings_result.get("performance_intelligence", {})
    exec_intel = perf_intel.get("executive_summary", {})
    tab_tx_intel = perf_intel.get("tab_tx_stats", {})
    tab_rt_intel = perf_intel.get("tab_rt_stats", {})
    tab_error_intel = perf_intel.get("tab_error_stats", {})
    tab_infra_intel = perf_intel.get("tab_infra_stats", {})

    # Standardized Tab Insight Panel Helper with Human Validation Checkbox & Contextual AI Chat
    def _build_tab_insight_panel(intel_data: dict, tab_title: str, section_id: str = "tab_tx_stats") -> str:
        override = ai_insights.get(section_id) if ai_insights else None
        effective_data = override if (isinstance(override, dict) and (override.get("observations") or override.get("recommendations"))) else intel_data
        if not effective_data:
            return ""
        obs_list = [_clean_client_text(obs) for obs in effective_data.get("observations", []) if _clean_client_text(obs)]
        rec_list = [_clean_client_text(rec) for rec in effective_data.get("recommendations", []) if _clean_client_text(rec)]
        if not obs_list and not rec_list:
            return ""
        obs_items = "".join([f'<li style="margin-bottom:0.35rem;">{obs}</li>' for obs in obs_list])
        rec_items = "".join([f'<li style="margin-bottom:0.35rem;">{rec}</li>' for rec in rec_list])
        safe_key = "tab_" + re.sub(r'[^a-zA-Z0-9_]', '_', tab_title.lower()).strip('_')
        return f"""
        <div class="section glass-panel ai-sub-card" style="margin-bottom: 1.25rem; padding: 1.2rem 1.5rem 3rem 1.5rem; position: relative;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.75rem; flex-wrap:wrap; gap:0.5rem;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <h3 style="margin:0; font-size:0.95rem; font-weight:700; color:var(--text);">🧠 {tab_title} AI Insights &amp; Recommendations</h3>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                    <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.2rem 0.6rem; border-radius:12px;">AI Generated</span>
                    {_build_validation_badge(safe_key)}
                </div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem;">
                    <div style="font-size:0.8rem; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.5rem;">🔍 Key Observations</div>
                    <ul id="content_obs_{section_id}" style="margin:0; padding-left:1.2rem; font-size:0.84rem; line-height:1.55; color:var(--text);" contenteditable="true">
                        {obs_items if obs_items else '<li style="color:var(--muted);">No AI observations generated</li>'}
                    </ul>
                </div>
                <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem;">
                    <div style="font-size:0.8rem; font-weight:700; color:var(--green); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.5rem;">💡 Recommendations</div>
                    <ul id="content_recs_{section_id}" style="margin:0; padding-left:1.2rem; font-size:0.84rem; line-height:1.55; color:var(--text);" contenteditable="true">
                        {rec_items if rec_items else '<li style="color:var(--muted);">No AI recommendations generated</li>'}
                    </ul>
                </div>

            </div>

            <!-- Contextual Section AI Chat FAB & Drawer -->
            <button class="ai-chat-fab" onclick="toggleAiChat('{section_id}')" title="Ask AI about {tab_title}">
                <span>💬 Ask AI</span>
            </button>
            <div id="aiChatDrawer_{section_id}" class="ai-chat-drawer" data-section-id="{section_id}">
                <div class="ai-chat-resize-handle-nw" title="Drag corner to resize"></div>
                <div class="ai-chat-resize-edge-n" title="Drag edge to resize height"></div>
                <div class="ai-chat-resize-edge-w" title="Drag edge to resize width"></div>
                <div class="ai-chat-resize-handle-se" title="Drag corner to resize"></div>
                <div class="ai-chat-resize-edge-s" title="Drag edge to resize height"></div>
                <div class="ai-chat-resize-edge-e" title="Drag edge to resize width"></div>
                <div class="ai-chat-header">
                    <div class="ai-chat-title-wrap">
                        <div class="ai-chat-title-icon">⚡</div>
                        <div>
                            <div class="ai-chat-title-text">
                                <span>{tab_title} AI Agent</span>
                                <span class="ai-chat-status-dot"></span>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.4rem;">
                        <button class="ai-chat-hdr-btn" onclick="toggleAiChatMaximize('{section_id}')" title="Maximize / Restore" id="aiChatMaxBtn_{section_id}">⛶</button>
                        <button class="ai-chat-hdr-btn" onclick="clearAiChat('{section_id}')" title="Clear Chat History">🗑️</button>
                        <button class="ai-chat-hdr-btn" onclick="toggleAiChat('{section_id}')" title="Close">✕</button>
                    </div>
                </div>
                <div id="aiChatMessages_{section_id}" class="ai-chat-messages">
                    <div class="ai-chat-welcome">
                        <div class="ai-welcome-avatar">🤖</div>
                        <div class="ai-welcome-title">{tab_title} AI Agent</div>
                        <div class="ai-welcome-sub">Ask questions or prompt the agent to rewrite and update this section live.</div>
                        <div class="ai-quick-prompts">
                            <button class="ai-quick-chip" onclick="quickAiPrompt('{section_id}', 'Summarize key bottlenecks and outliers in this section')">🔍 Summarize key bottlenecks</button>
                            <button class="ai-quick-chip" onclick="quickAiPrompt('{section_id}', 'Rewrite observations and recommendations with concise client-facing points')">✍️ Rewrite observations &amp; recommendations</button>
                        </div>
                    </div>
                </div>
                <div class="ai-chat-input-box">
                    <input type="text" id="aiChatInput_{section_id}" class="ai-chat-input" placeholder="Ask questions or ask to rewrite..." onkeydown="handleAiChatKey(event, '{section_id}')" />
                    <button id="aiChatSendBtn_{section_id}" class="ai-chat-send-btn" onclick="sendAiChatMessage('{section_id}')">Send ➤</button>
                </div>
            </div>
        </div>
        """

    tab_tx_panel_html = _build_tab_insight_panel(tab_tx_intel, "Transaction Performance", "tab_tx_stats")
    tab_rt_panel_html = _build_tab_insight_panel(tab_rt_intel, "Response Time & SLA", "tab_rt_stats")
    tab_error_panel_html = _build_tab_insight_panel(tab_error_intel, "Reliability & Errors", "tab_error_stats")
    tab_infra_panel_html = _build_tab_insight_panel(tab_infra_intel, "Infrastructure Monitoring", "tab_infra_stats")


    # Executive Summary Sub-sections (Under AI Augmented Analysis)
    exec_assessment_badge = exec_intel.get("assessment_badge", "")
    exec_assessment_color = exec_intel.get("assessment_color", "var(--accent)")
    exec_raw_overview = (ai_insights.get("exec_overview") if ai_insights else None) or exec_intel.get("assessment_bullets") or exec_intel.get("assessment_text", "")
    exec_overview_pointers_html = _format_as_pointers(exec_raw_overview)
    
    exec_assessment_html = f"""
    <div class="ai-sub-card" style="margin-bottom: 1.25rem; position: relative; padding-bottom: 3rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.75rem; flex-wrap:wrap; gap:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="font-size:1.05rem;">🎯</span>
                <strong style="font-size:0.95rem; font-weight:700; color:var(--text);">AI Powered Executive Overview</strong>
                {f'<span style="font-size:0.72rem; font-weight:700; color:{exec_assessment_color}; background:var(--surface); border:1px solid var(--border); padding:0.15rem 0.5rem; border-radius:4px;">{exec_assessment_badge}</span>' if exec_assessment_badge else ''}
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                {_build_validation_badge('exec_overview')}
            </div>
        </div>
        <ul id="content_exec_overview" style="margin:0; padding-left:1.25rem; font-size:0.86rem; line-height:1.65; color:var(--text);" contenteditable="true">
            {exec_overview_pointers_html}
        </ul>

        <!-- Chat FAB & Drawer for Executive Overview -->
        <button class="ai-chat-fab" onclick="toggleAiChat('exec_overview')" title="Open PerfAgent for Executive Overview">
            <span>💬 PerfAgent</span>
        </button>
        <div id="aiChatDrawer_exec_overview" class="ai-chat-drawer" data-section-id="exec_overview">
            <div class="ai-chat-resize-handle-nw" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-n" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-w" title="Drag edge to resize width"></div>
            <div class="ai-chat-resize-handle-se" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-s" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-e" title="Drag edge to resize width"></div>
            <div class="ai-chat-header">
                <div class="ai-chat-title-wrap">
                    <div class="ai-chat-title-icon">🎯</div>
                    <div>
                        <div class="ai-chat-title-text">
                            <span>Executive Overview — PerfAgent</span>
                            <span class="ai-chat-status-dot"></span>
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChatMaximize('exec_overview')" title="Maximize / Restore" id="aiChatMaxBtn_exec_overview">⛶</button>
                    <button class="ai-chat-hdr-btn" onclick="clearAiChat('exec_overview')" title="Clear Chat History">🗑️</button>
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChat('exec_overview')" title="Close">✕</button>
                </div>
            </div>
            <div id="aiChatMessages_exec_overview" class="ai-chat-messages">
                <div class="ai-chat-welcome">
                    <div class="ai-welcome-avatar">🎯</div>
                    <div class="ai-welcome-title">Executive Overview — PerfAgent</div>
                    <div class="ai-welcome-sub">Ask questions or prompt PerfAgent to rewrite executive summary bullets with specific facts.</div>
                    <div class="ai-quick-prompts">
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_overview', 'Summarize high-level test stability and primary bottlenecks')">🎯 Summarize test stability</button>
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_overview', 'Rewrite executive overview adding specific details on 5xx errors and SLA breaches')">✍️ Rewrite with SLA &amp; error facts</button>
                    </div>
                </div>
            </div>
            <div class="ai-chat-input-box">
                <input type="text" id="aiChatInput_exec_overview" class="ai-chat-input" placeholder="Ask PerfAgent or prompt to rewrite overview..." onkeydown="handleAiChatKey(event, 'exec_overview')" />
                <button id="aiChatSendBtn_exec_overview" class="ai-chat-send-btn" onclick="sendAiChatMessage('exec_overview')">Send ➤</button>
            </div>
        </div>
    </div>
    """ if exec_raw_overview else ""

    kpis_dict = exec_intel.get("kpis", {})
    exec_kpi_strip_html = f"""
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1.25rem;">
        <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1.1rem;">
            <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">{kpis_dict.get('sla', {}).get('title', 'SLA COMPLIANCE')}</div>
            <div class="kpi-value" style="font-size:1.75rem; font-weight:800; color:{'var(--green)' if kpis_dict.get('sla',{}).get('status')=='pass' else 'var(--yellow)' if kpis_dict.get('sla',{}).get('status')=='warning' else 'var(--red)'}; margin:0.2rem 0;">{kpis_dict.get('sla', {}).get('value', '-')}</div>
            <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">{kpis_dict.get('sla', {}).get('sub', '')}</div>
        </div>
        <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1.1rem;">
            <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">{kpis_dict.get('error_rate', {}).get('title', 'ERROR RATE')}</div>
            <div class="kpi-value" style="font-size:1.75rem; font-weight:800; color:{'var(--green)' if kpis_dict.get('error_rate',{}).get('status')=='pass' else 'var(--red)'}; margin:0.2rem 0;">{kpis_dict.get('error_rate', {}).get('value', '-')}</div>
            <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">{kpis_dict.get('error_rate', {}).get('sub', '')}</div>
        </div>
        <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1.1rem;">
            <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">{kpis_dict.get('throughput', {}).get('title', 'THROUGHPUT')}</div>
            <div class="kpi-value" style="font-size:1.75rem; font-weight:800; color:var(--text); margin:0.2rem 0;">{kpis_dict.get('throughput', {}).get('value', '-')}</div>
            <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">{kpis_dict.get('throughput', {}).get('sub', '')}</div>
        </div>
        <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1.1rem;">
            <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">{kpis_dict.get('infra', {}).get('title', 'INFRASTRUCTURE')}</div>
            <div class="kpi-value" style="font-size:1.75rem; font-weight:800; color:{'var(--green)' if kpis_dict.get('infra',{}).get('status')=='pass' else 'var(--yellow)'}; margin:0.2rem 0;">{kpis_dict.get('infra', {}).get('value', '-')}</div>
            <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">{kpis_dict.get('infra', {}).get('sub', '')}</div>
        </div>
    </div>
    """

    # Sub-section 2: Observations Table with Human Validation Badge & Chat Drawer
    obs_source = (ai_insights.get("exec_observations") if ai_insights else None) or exec_intel.get("observations_table", [])
    obs_rows = ""
    for row in obs_source:
        obs_text = str(row.get('observation', '')).replace('\n', '<br>')
        obs_rows += f"""
        <tr style="border-bottom:1px solid var(--border);">
            <td style="font-weight:700; width:26%; vertical-align:top; font-size:0.84rem; color:var(--text); padding:0.75rem 0.9rem;">{row.get('category', '')}</td>
            <td style="width:74%; vertical-align:top; font-size:0.84rem; line-height:1.6; color:var(--text); padding:0.75rem 0.9rem;" contenteditable="true">{obs_text}</td>
        </tr>
        """
    exec_obs_table_html = f"""
    <div class="ai-sub-card" style="margin-bottom: 1.25rem; position: relative; padding-bottom: 3rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="font-size:1.05rem;">📋</span>
                <strong style="font-size:0.95rem; font-weight:700; color:var(--text);">High-Level Performance Observations</strong>
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface); border:1px solid var(--border); padding:0.2rem 0.65rem; border-radius:12px;">AI Assessment</span>
                {_build_validation_badge('exec_observations')}
            </div>
        </div>
        <div style="overflow-x:auto; margin-top:0.35rem;">
            <table style="width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--border); border-radius:8px; overflow:hidden;">
                <thead>
                    <tr style="background:var(--surface2); text-align:left;">
                        <th style="padding:0.65rem 0.9rem; font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); width:26%; border-bottom:1px solid var(--border);">Category</th>
                        <th style="padding:0.65rem 0.9rem; font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); width:74%; border-bottom:1px solid var(--border);">Key Observation with Embedded Evidence</th>
                    </tr>
                </thead>
                <tbody id="content_exec_observations">
                    {obs_rows}
                </tbody>
            </table>
        </div>

        <!-- Chat FAB & Drawer for High-Level Observations -->
        <button class="ai-chat-fab" onclick="toggleAiChat('exec_observations')" title="Open PerfAgent for Observations">
            <span>💬 PerfAgent</span>
        </button>
        <div id="aiChatDrawer_exec_observations" class="ai-chat-drawer" data-section-id="exec_observations">
            <div class="ai-chat-resize-handle-nw" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-n" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-w" title="Drag edge to resize width"></div>
            <div class="ai-chat-resize-handle-se" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-s" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-e" title="Drag edge to resize width"></div>
            <div class="ai-chat-header">
                <div class="ai-chat-title-wrap">
                    <div class="ai-chat-title-icon">📋</div>
                    <div>
                        <div class="ai-chat-title-text">
                            <span>Observations — PerfAgent</span>
                            <span class="ai-chat-status-dot"></span>
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChatMaximize('exec_observations')" title="Maximize / Restore" id="aiChatMaxBtn_exec_observations">⛶</button>
                    <button class="ai-chat-hdr-btn" onclick="clearAiChat('exec_observations')" title="Clear Chat History">🗑️</button>
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChat('exec_observations')" title="Close">✕</button>
                </div>
            </div>
            <div id="aiChatMessages_exec_observations" class="ai-chat-messages">
                <div class="ai-chat-welcome">
                    <div class="ai-welcome-avatar">📋</div>
                    <div class="ai-welcome-title">Observations — PerfAgent</div>
                    <div class="ai-welcome-sub">Ask questions or prompt PerfAgent to rewrite table rows with specific evidence.</div>
                    <div class="ai-quick-prompts">
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_observations', 'Highlight the top 3 transaction degradation observations')">🔍 Highlight top degradations</button>
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_observations', 'Rewrite category observations table focusing on server compute and errors')">✍️ Rewrite observation rows</button>
                    </div>
                </div>
            </div>
            <div class="ai-chat-input-box">
                <input type="text" id="aiChatInput_exec_observations" class="ai-chat-input" placeholder="Ask PerfAgent or prompt to update observations..." onkeydown="handleAiChatKey(event, 'exec_observations')" />
                <button id="aiChatSendBtn_exec_observations" class="ai-chat-send-btn" onclick="sendAiChatMessage('exec_observations')">Send ➤</button>
            </div>
        </div>
    </div>
    """ if obs_rows else ""

    # Sub-section 3: Key Conclusions with Human Validation Badge & Chat Drawer
    concl_source = (ai_insights.get("exec_conclusions") if ai_insights else None) or exec_intel.get("conclusions", [])
    concl_items = "".join([f'<li style="margin-bottom:0.4rem; line-height:1.65;">{c}</li>' for c in concl_source])
    exec_conclusions_html = f"""
    <div class="ai-sub-card" style="margin-bottom: 1.25rem; position: relative; padding-bottom: 3rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; flex-wrap:gap; gap:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="font-size:1.05rem;">📌</span>
                <strong style="font-size:0.95rem; font-weight:700; color:var(--text);">Key Conclusions</strong>
            </div>
            {_build_validation_badge('exec_conclusions')}
        </div>
        <ul id="content_exec_conclusions" style="margin:0; padding-left:1.25rem; font-size:0.86rem; line-height:1.65; color:var(--text);" contenteditable="true">
            {concl_items}
        </ul>

        <!-- Chat FAB & Drawer for Key Conclusions -->
        <button class="ai-chat-fab" onclick="toggleAiChat('exec_conclusions')" title="Open PerfAgent for Conclusions">
            <span>💬 PerfAgent</span>
        </button>
        <div id="aiChatDrawer_exec_conclusions" class="ai-chat-drawer" data-section-id="exec_conclusions">
            <div class="ai-chat-resize-handle-nw" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-n" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-w" title="Drag edge to resize width"></div>
            <div class="ai-chat-resize-handle-se" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-s" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-e" title="Drag edge to resize width"></div>
            <div class="ai-chat-header">
                <div class="ai-chat-title-wrap">
                    <div class="ai-chat-title-icon">📌</div>
                    <div>
                        <div class="ai-chat-title-text">
                            <span>Key Conclusions — PerfAgent</span>
                            <span class="ai-chat-status-dot"></span>
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChatMaximize('exec_conclusions')" title="Maximize / Restore" id="aiChatMaxBtn_exec_conclusions">⛶</button>
                    <button class="ai-chat-hdr-btn" onclick="clearAiChat('exec_conclusions')" title="Clear Chat History">🗑️</button>
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChat('exec_conclusions')" title="Close">✕</button>
                </div>
            </div>
            <div id="aiChatMessages_exec_conclusions" class="ai-chat-messages">
                <div class="ai-chat-welcome">
                    <div class="ai-welcome-avatar">📌</div>
                    <div class="ai-welcome-title">Key Conclusions — PerfAgent</div>
                    <div class="ai-welcome-sub">Ask questions or prompt PerfAgent to refine conclusions or add readiness verdicts.</div>
                    <div class="ai-quick-prompts">
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_conclusions', 'What is the final release readiness verdict based on test data?')">🚦 Release readiness verdict</button>
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_conclusions', 'Rewrite key conclusions citing exact CPU peaks and transaction error counts')">✍️ Rewrite conclusions with facts</button>
                    </div>
                </div>
            </div>
            <div class="ai-chat-input-box">
                <input type="text" id="aiChatInput_exec_conclusions" class="ai-chat-input" placeholder="Ask PerfAgent or prompt to rewrite conclusions..." onkeydown="handleAiChatKey(event, 'exec_conclusions')" />
                <button id="aiChatSendBtn_exec_conclusions" class="ai-chat-send-btn" onclick="sendAiChatMessage('exec_conclusions')">Send ➤</button>
            </div>
        </div>
    </div>
    """ if concl_items else ""

    # Sub-section 4: Recommendations with Chat Drawer
    recs_source = (ai_insights.get("exec_recommendations") if ai_insights else None) or exec_intel.get("priority_recommendations", [])
    p_recs_html = ""
    for r in recs_source:
        r_badge = r.get("badge", "💡")
        r_title = _clean_client_text(r.get("title", ""))
        r_detail = _clean_client_text(r.get("detail", ""))
        r_priority = r.get("priority", "Medium")
        r_impact = _clean_client_text(r.get("business_impact") or r.get("impact") or r.get("expected_impact") or "")
        if not r_impact:
            r_impact = "Mitigates transaction latency spikes, protects end-user conversion rates, and ensures SLA compliance under peak load."
        
        p_recs_html += f"""
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:0.95rem 1.15rem; margin-bottom:0.85rem;">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem; flex-wrap:wrap;">
                <span style="font-size:1.05rem;">{r_badge}</span>
                <strong style="font-size:0.92rem; font-weight:700; color:var(--text);" contenteditable="true">{r_title}</strong>
                <span style="font-size:0.7rem; font-weight:700; text-transform:uppercase; padding:0.15rem 0.5rem; border-radius:4px; background:var(--surface2); border:1px solid var(--border); color:var(--muted); margin-left:auto;">{r_priority}</span>
            </div>
            <p style="margin:0 0 0.55rem 0; font-size:0.86rem; line-height:1.55; color:var(--text);" contenteditable="true"><strong>Technical Action:</strong> {r_detail}</p>
            <div style="background:var(--accent-bg); border-left:3px solid var(--accent); padding:0.5rem 0.8rem; border-radius:4px; font-size:0.83rem; line-height:1.5; color:var(--text);">
                <strong style="color:var(--accent);">💼 Business Impact:</strong> <span contenteditable="true">{r_impact}</span>
            </div>
        </div>
        """

    exec_recs_html = f"""
    <div class="ai-sub-card" style="margin-bottom: 0; position: relative; padding-bottom: 3rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="font-size:1.05rem;">💡</span>
                <strong style="font-size:0.95rem; font-weight:700; color:var(--text);">Recommendations</strong>
            </div>
            {_build_validation_badge('exec_recommendations')}
        </div>
        <div id="content_exec_recommendations" contenteditable="true">
            {p_recs_html}
        </div>

        <!-- Chat FAB & Drawer for Recommendations -->
        <button class="ai-chat-fab" onclick="toggleAiChat('exec_recommendations')" title="Open PerfAgent for Recommendations">
            <span>💬 PerfAgent</span>
        </button>
        <div id="aiChatDrawer_exec_recommendations" class="ai-chat-drawer" data-section-id="exec_recommendations">
            <div class="ai-chat-resize-handle-nw" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-n" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-w" title="Drag edge to resize width"></div>
            <div class="ai-chat-resize-handle-se" title="Drag corner to resize"></div>
            <div class="ai-chat-resize-edge-s" title="Drag edge to resize height"></div>
            <div class="ai-chat-resize-edge-e" title="Drag edge to resize width"></div>
            <div class="ai-chat-header">
                <div class="ai-chat-title-wrap">
                    <div class="ai-chat-title-icon">💡</div>
                    <div>
                        <div class="ai-chat-title-text">
                            <span>Recommendations — PerfAgent</span>
                            <span class="ai-chat-status-dot"></span>
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChatMaximize('exec_recommendations')" title="Maximize / Restore" id="aiChatMaxBtn_exec_recommendations">⛶</button>
                    <button class="ai-chat-hdr-btn" onclick="clearAiChat('exec_recommendations')" title="Clear Chat History">🗑️</button>
                    <button class="ai-chat-hdr-btn" onclick="toggleAiChat('exec_recommendations')" title="Close">✕</button>
                </div>
            </div>
            <div id="aiChatMessages_exec_recommendations" class="ai-chat-messages">
                <div class="ai-chat-welcome">
                    <div class="ai-welcome-avatar">💡</div>
                    <div class="ai-welcome-title">Recommendations — PerfAgent</div>
                    <div class="ai-welcome-sub">Ask for technical remediation strategies or prompt PerfAgent to add tailored recommendations.</div>
                    <div class="ai-quick-prompts">
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_recommendations', 'Add a high priority recommendation for database indexing and connection pooling')">➕ Add database recommendation</button>
                        <button class="ai-quick-chip" onclick="quickAiPrompt('exec_recommendations', 'Rewrite priority recommendations linking actions to business revenue impact')">💼 Link actions to business impact</button>
                    </div>
                </div>
            </div>
            <div class="ai-chat-input-box">
                <input type="text" id="aiChatInput_exec_recommendations" class="ai-chat-input" placeholder="Ask PerfAgent or prompt to add recommendations..." onkeydown="handleAiChatKey(event, 'exec_recommendations')" />
                <button id="aiChatSendBtn_exec_recommendations" class="ai-chat-send-btn" onclick="sendAiChatMessage('exec_recommendations')">Send ➤</button>
            </div>
        </div>
    </div>
    """ if p_recs_html else ""


    # Major Section: AI Augmented Analysis (Enclosing Overview, Observations, Conclusions, Recommendations)
    exec_ai_augmented_html = f"""
    <div class="section glass-panel ai-augmented-section" style="position: relative;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom: 1.25rem; padding-bottom: 0.85rem; border-bottom: 1px solid var(--border);">
            <div style="display:flex; align-items:center; gap:0.65rem;">
                <span style="font-size:1.35rem;">🧠</span>
                <div>
                    <h2 style="margin:0; font-size:1.15rem; font-weight:800; color:var(--text);">AI Augmented Analysis</h2>
                    <p style="margin:0.2rem 0 0 0; font-size:0.8rem; color:var(--muted);"></p>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                <span style="font-size:0.75rem; font-weight:700; color:var(--accent); background:var(--accent-bg); border:1px solid var(--accent); padding:0.25rem 0.75rem; border-radius:14px; display:inline-flex; align-items:center; gap:0.35rem;"> AI Generated</span>
                {_build_validation_badge('major_ai_augmented', 'Validate All Augmented Analysis')}
            </div>
        </div>

        {exec_assessment_html}
        {exec_obs_table_html}
        {exec_conclusions_html}
        {exec_recs_html}
    </div>
    """ if (exec_assessment_html or exec_obs_table_html or exec_conclusions_html or exec_recs_html) else ""



    # Build list of critical transactions for initial chart render
    critical_tx_list = [
        lname for lname, target in sla_targets.items()
        if target.get("is_critical") in (1, True, "1", "true") and lname in display_labels
    ]
    # If no transaction is explicitly marked critical yet, default to top 3 slowest transactions
    if not critical_tx_list:
        critical_tx_list = [k for k, v in sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:3]]

    critical_tx_list_json = json.dumps(critical_tx_list)

    # Mini KPIs for Critical Transactions Header Summary
    crit_tx_count = len(critical_tx_list)
    crit_avg_rt = round(sum(display_labels[t].get('avg_rt', 0) for t in critical_tx_list if t in display_labels) / crit_tx_count) if crit_tx_count else 0
    crit_p95_rt = max((display_labels[t].get('p95', 0) for t in critical_tx_list if t in display_labels), default=0)
    crit_max_rt = max((display_labels[t].get('max_rt', 0) for t in critical_tx_list if t in display_labels), default=0)
    crit_breaches = sum(1 for t in critical_tx_list if t in display_labels and (display_labels[t].get('p90', 0) > sla_targets.get(t, {}).get('rt', default_rt) or display_labels[t].get('error_rate', 0) > sla_targets.get(t, {}).get('err', default_err)))
    target_sla_val = int(min((sla_targets.get(t, {}).get('rt', default_rt) for t in critical_tx_list if t in sla_targets), default=default_rt))

    # SLA Compliance Percentages for Hero Metrics Grid
    sla_compliance_pct = round((tx_under_sla / total_tx_count * 100), 1) if total_tx_count else 100.0
    passed_pct = round((tx_under_sla / total_tx_count * 100), 1) if total_tx_count else 0.0
    minor_pct  = round((sla_minor_count / total_tx_count * 100), 1) if total_tx_count else 0.0
    mod_pct    = round((sla_mod_count / total_tx_count * 100), 1) if total_tx_count else 0.0
    crit_pct   = round((sla_crit_count / total_tx_count * 100), 1) if total_tx_count else 0.0

    # Label time series map for per-transaction chart toggling
    label_ts_map = ts.get("label_ts_map", {})
    if not label_ts_map and "label_series" in ts:
        raw_ls = ts.get("label_series", {})
        label_ts_map = {
            k: {
                "ts_avg_rt": v.get("avg_rt", []) if isinstance(v, dict) else getattr(v, "avg_rt", []),
                "ts_p95_rt": v.get("p95_rt", []) if isinstance(v, dict) else getattr(v, "p95_rt", []),
                "ts_p99_rt": v.get("p99_rt", []) if isinstance(v, dict) else getattr(v, "p99_rt", []),
                "ts_throughput": v.get("throughput", []) if isinstance(v, dict) else getattr(v, "throughput", []),
                "ts_errors": v.get("errors", []) if isinstance(v, dict) else getattr(v, "errors", []),
            }
            for k, v in raw_ls.items()
        }
    if not label_ts_map and run_id and run_id != "unknown":
        norm_ts_path = STORAGE_NORMALIZED_DIR / f"{run_id}_timeseries.json"
        if not norm_ts_path.exists():
            norm_ts_path = RESULTS_DIR / "normalized" / f"{run_id}_timeseries.json"
        if norm_ts_path.exists():
            try:
                norm_ts_data = json.loads(norm_ts_path.read_text(encoding="utf-8"))
                norm_ls = norm_ts_data.get("label_series", {})
                label_ts_map = {
                    k: {
                        "ts_avg_rt": v.get("avg_rt", []),
                        "ts_p95_rt": v.get("p95_rt", []),
                        "ts_p99_rt": v.get("p99_rt", []),
                        "ts_throughput": v.get("throughput", []),
                        "ts_errors": v.get("errors", []),
                    }
                    for k, v in norm_ls.items()
                }
            except Exception:
                pass
    
    # Filter labels for dropdown: prioritize Transaction Controllers from JMX
    tc_keys = set(tc_to_samplers.keys()) if tc_to_samplers else set()
    display_label_names = [l for l in sorted(labels.keys()) if (not tc_keys or l in tc_keys)]
    if not display_label_names:
        display_label_names = sorted(labels.keys())

    # Build map of per-transaction target SLA values for JS chart rendering
    tx_sla_map = {k: v.get("rt", default_rt) for k, v in sla_targets.items()}
    for k in display_labels.keys():
        if k not in tx_sla_map:
            tx_sla_map[k] = default_rt
    tx_sla_json = json.dumps(tx_sla_map)

    # Build comprehensive label time-series map: keyed by integer index AND string label name
    display_ts_map = {}
    for idx_i, l_name in enumerate(display_label_names):
        if l_name in label_ts_map:
            entry = dict(label_ts_map[l_name])
            entry["label"] = l_name
            display_ts_map[idx_i] = entry
            display_ts_map[l_name] = entry
    for l_name, l_ts in label_ts_map.items():
        if l_name not in display_ts_map:
            entry = dict(l_ts)
            entry["label"] = l_name
            display_ts_map[l_name] = entry
    label_ts_json = json.dumps(display_ts_map)

    # Build dropdown HTML options using numeric index values
    tx_options_html = ""
    tx_options_data = []
    for idx_i, l_name in enumerate(display_label_names):
        short_display = l_name if len(l_name) <= 50 else f"{l_name[:47]}..."
        # Use json.dumps to safely escape the display name for the title attribute
        safe_title = short_display.replace('"', '&quot;')
        tx_options_html += f'<option value="{idx_i}" title="{safe_title}">{short_display}</option>'
        tx_options_data.append({
            "id": str(idx_i),
            "name": l_name,
            "shortName": short_display,
            "sla": tx_sla_map.get(l_name, "")
        })
    tx_options_json = json.dumps(tx_options_data)

    # Transaction chart data
    top_labels = sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:8]
    tx_chart_labels = json.dumps([l[0][:30] for l in top_labels])
    tx_chart_values = json.dumps([l[1].get("avg_rt", 0) for l in top_labels])

    # Calculate scorecard metrics for Executive Summary (Wireframe Tab 1)
    apdex_below_50_count = 0
    apdex_below_25_count = 0
    sla_breach_100_count = 0
    sla_breach_50_count  = 0
    sla_breach_20_count  = 0

    for tx_name, metrics in display_labels.items():
        tx_apdex = metrics.get("apdex", 1.0)
        if tx_apdex < 0.25:
            apdex_below_25_count += 1
            apdex_below_50_count += 1
        elif tx_apdex < 0.50:
            apdex_below_50_count += 1

        target_rt_val = sla_targets.get(tx_name, {}).get("rt", default_rt)
        p90_val = metrics.get("p90", metrics.get("avg_rt", 0))
        
        if target_rt_val > 0:
            dev_pct = ((p90_val - target_rt_val) / target_rt_val) * 100.0
            if dev_pct > 100.0:
                sla_breach_100_count += 1
                sla_breach_50_count += 1
                sla_breach_20_count += 1
            elif dev_pct > 50.0:
                sla_breach_50_count += 1
                sla_breach_20_count += 1
            elif dev_pct > 20.0:
                sla_breach_20_count += 1

    # Calculate SLA Deviation Data for Diverging Horizontal Bar Chart (Sorted by worst SLA deviation %)
    dev_items = []
    tx_dev_map = {}
    for tx_name, metrics in display_labels.items():
        target_rt_val = sla_targets.get(tx_name, {}).get("rt", default_rt)
        p90_val = metrics.get("p90", metrics.get("avg_rt", 0))
        if target_rt_val > 0:
            dev_pct = round(((p90_val - target_rt_val) / target_rt_val) * 100.0, 1)
        else:
            dev_pct = 0.0
        item = {"label": tx_name, "dev_pct": dev_pct, "p90": p90_val, "target": target_rt_val}
        dev_items.append(item)
        tx_dev_map[tx_name] = item

    # Sort by worst breach first (highest positive % to lowest negative %)
    dev_items.sort(key=lambda x: x["dev_pct"], reverse=True)

    deviation_chart_labels = [item["label"][:35] for item in dev_items]
    deviation_chart_values = [item["dev_pct"] for item in dev_items]

    deviation_chart_labels_json = json.dumps(deviation_chart_labels)
    deviation_chart_values_json = json.dumps(deviation_chart_values)
    tx_dev_map_json = json.dumps(tx_dev_map)

    # Build Transaction Statistics Table & Chart Data for Iteration Statistics Section (Thread Group Level)
    # Each row = one Thread Group (user story). Child TCs are aggregated into a single row.
    tx_stat_rows_html = ""
    total_duration_min = round(summary.get("duration_sec", 0) / 60.0, 1) if summary.get("duration_sec") else 0
    if total_duration_min == 0:
        total_duration_min = round(parsed.get("duration", 0) / 60.0, 1)

    overall_users = users
    overall_samples = 0
    overall_pass = 0
    overall_fail = 0

    tx_chart_labels = []
    tx_chart_pass = []
    tx_chart_fail = []

    # Try to get Thread Group → TC mapping from JMX
    tg_configs = []
    try:
        from app.services.analytics.sla_manager import parse_jmx_thread_groups
        tg_configs = parse_jmx_thread_groups(jmx_name)
    except Exception as _tg_err:
        print(f"[Report] Thread group parse warning: {_tg_err}", flush=True)

    if tg_configs:
        # Thread Group level: use wrapper_tc as the unique JTL match key
        # The wrapper TC (e.g. "T-1_Overall Iteration") is the first TC inside each
        # ThreadGroup's hashTree — it's unique across TGs and appears directly in JTL.
        # Display label = Thread Group name (human readable).
        all_labels = {**labels}  # full label map (unfiltered) to resolve wrapper TCs

        for tg in tg_configs:
            tg_name_str  = tg["name"]
            tg_enabled   = tg.get("enabled", True)
            tg_users     = tg.get("users", users)
            wrapper_tc   = tg.get("wrapper_tc")    # Primary JTL match key
            child_tcs    = tg.get("child_tcs", []) # Step-level TCs (for fallback)

            tg_total = 0
            tg_fail  = 0
            matched_any = False

            # Strategy 1: match by wrapper TC (e.g. "T-1_Overall Iteration")
            # This is the most reliable — unique per TG, direct JTL label
            if wrapper_tc and wrapper_tc in all_labels:
                tg_total = all_labels[wrapper_tc].get("count", 0)
                tg_fail  = all_labels[wrapper_tc].get("errors", 0)
                matched_any = True

            # Strategy 2: if no wrapper TC in JTL, aggregate named child step TCs
            # (Only works if child TC names are unique across TGs)
            if not matched_any and child_tcs:
                for tc_name in child_tcs:
                    if tc_name in all_labels:
                        tg_total += all_labels[tc_name].get("count", 0)
                        tg_fail  += all_labels[tc_name].get("errors", 0)
                        matched_any = True

            # Strategy 3: fallback — TG name itself appears as JTL label
            if not matched_any and tg_name_str in all_labels:
                tg_total = all_labels[tg_name_str].get("count", 0)
                tg_fail  = all_labels[tg_name_str].get("errors", 0)
                matched_any = True

            if not matched_any:
                continue  # No JTL data for this TG — skip row

            tg_pass = max(0, tg_total - tg_fail)
            err_pct = (tg_fail / tg_total * 100.0) if tg_total > 0 else 0.0

            overall_samples += tg_total
            overall_pass    += tg_pass
            overall_fail    += tg_fail

            tx_chart_labels.append(tg_name_str[:35])
            tx_chart_pass.append(tg_pass)
            tx_chart_fail.append(tg_fail)

            tx_stat_rows_html += f'''
        <tr style="border-bottom:1px solid var(--border);">
            <td style="font-weight:600; text-align:left; padding:0.5rem 0.6rem;">{tg_name_str}</td>
            <td style="text-align:center; padding:0.5rem;">{total_duration_min}</td>
            <td style="text-align:center; padding:0.5rem;">{tg_users}</td>
            <td style="text-align:center; font-weight:700; padding:0.5rem;">{tg_total:,}</td>
            <td style="text-align:center; color:var(--green); font-weight:700; padding:0.5rem;">{tg_pass:,}</td>
            <td style="text-align:center; color:var(--red); font-weight:700; padding:0.5rem;">{tg_fail:,}</td>
            <td style="text-align:center; font-weight:700; color:{'var(--red)' if err_pct > 1.0 else 'var(--green)'}; padding:0.5rem;">{err_pct:.2f}%</td>
        </tr>
        '''


    else:
        # Fallback: no JMX available — use display_labels (TC level) as-is
        for lname, ldata in sorted(display_labels.items(), key=lambda x: x[0]):
            sample_tot = ldata.get("count", 0)
            sample_fail = ldata.get("errors", 0)
            sample_pass = max(0, sample_tot - sample_fail)
            err_pct = (sample_fail / sample_tot * 100.0) if sample_tot > 0 else 0.0
            script_users = ldata.get("users", users)

            overall_samples += sample_tot
            overall_pass += sample_pass
            overall_fail += sample_fail
            tx_chart_labels.append(lname[:35])
            tx_chart_pass.append(sample_pass)
            tx_chart_fail.append(sample_fail)

            tx_stat_rows_html += f'''
        <tr style="border-bottom:1px solid var(--border);">
            <td style="font-weight:600; text-align:left; padding:0.5rem 0.6rem;">{lname}</td>
            <td style="text-align:center; padding:0.5rem;">{total_duration_min}</td>
            <td style="text-align:center; padding:0.5rem;">{script_users}</td>
            <td style="text-align:center; font-weight:700; padding:0.5rem;">{sample_tot:,}</td>
            <td style="text-align:center; color:var(--green); font-weight:700; padding:0.5rem;">{sample_pass:,}</td>
            <td style="text-align:center; color:var(--red); font-weight:700; padding:0.5rem;">{sample_fail:,}</td>
            <td style="text-align:center; font-weight:700; color:{'var(--red)' if err_pct > 1.0 else 'var(--green)'}; padding:0.5rem;">{err_pct:.2f}%</td>
        </tr>
        '''

    overall_err_pct = (overall_fail / overall_samples * 100.0) if overall_samples > 0 else 0.0
    tx_stat_rows_html += f'''
    <tr style="border-top:2px solid var(--accent); background:var(--surface2); font-weight:800;">
        <td style="text-align:left; padding:0.6rem;">Overall</td>
        <td style="text-align:center; padding:0.6rem;">{total_duration_min}</td>
        <td style="text-align:center; padding:0.6rem;">{overall_users}</td>
        <td style="text-align:center; padding:0.6rem;">{overall_samples:,}</td>
        <td style="text-align:center; color:var(--green); padding:0.6rem;">{overall_pass:,}</td>
        <td style="text-align:center; color:var(--red); padding:0.6rem;">{overall_fail:,}</td>
        <td style="text-align:center; color:{'var(--red)' if overall_err_pct > 1.0 else 'var(--green)'}; padding:0.6rem;">{overall_err_pct:.2f}%</td>
    </tr>
    '''

    tx_chart_labels_json = json.dumps(tx_chart_labels)
    tx_chart_pass_json   = json.dumps(tx_chart_pass)
    tx_chart_fail_json   = json.dumps(tx_chart_fail)

    # Build bottom data table for Transaction Summary chart (matching screenshot)
    tx_summary_bottom_table_cols = "".join(f'<th style="padding:0.4rem 0.5rem; font-weight:600; text-align:center;">{lbl}</th>' for lbl in tx_chart_labels)
    tx_summary_bottom_pass_cells = "".join(f'<td style="padding:0.35rem 0.5rem; font-weight:700; color:var(--green); text-align:center;">{p:,}</td>' for p in tx_chart_pass)
    tx_summary_bottom_fail_cells = "".join(f'<td style="padding:0.35rem 0.5rem; font-weight:700; color:{"var(--red)" if f > 0 else "var(--muted)"}; text-align:center;">{f:,}</td>' for f in tx_chart_fail)

    tx_summary_bottom_table_html = f'''
    <div style="overflow-x:auto; margin-top:0.75rem; border-top:1px solid var(--border); padding-top:0.6rem;">
        <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
            <thead>
                <tr style="background:var(--surface2);">
                    <th style="text-align:left; padding:0.4rem 0.6rem; width:100px; font-weight:700;">Metric</th>
                    {tx_summary_bottom_table_cols}
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="text-align:left; font-weight:700; color:var(--green); padding:0.35rem 0.6rem;">
                        <span style="display:inline-block; width:10px; height:10px; background:#10b981; border-radius:2px; margin-right:4px;"></span>Pass
                    </td>
                    {tx_summary_bottom_pass_cells}
                </tr>
                <tr>
                    <td style="text-align:left; font-weight:700; color:var(--red); padding:0.35rem 0.6rem;">
                        <span style="display:inline-block; width:10px; height:10px; background:#ef4444; border-radius:2px; margin-right:4px;"></span>Fail
                    </td>
                    {tx_summary_bottom_fail_cells}
                </tr>
            </tbody>
        </table>
    </div>
    '''

    tx_stats_table_html = f'''
    <div class="section glass-panel" style="margin-bottom:1.5rem; position:relative;">
        <button class="chart-info-btn" onclick="openGraphModal('tx-stats-table')" title="How to read Transaction Statistics">ℹ️</button>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:0.5rem; padding-right:2.5rem;">
            <div>
                <h2 style="margin:0; font-size:1.15rem; font-weight:800; color:var(--accent);">📋 Transaction Statistics</h2>
                <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Execution duration, allocated users, pass/fail sample counts and failure percentages</p>
            </div>
            <div style="display:flex; gap:0.6rem; align-items:center; flex-wrap:wrap;">
                <span style="font-size:0.75rem; font-weight:700; background:var(--surface2); border:1px solid var(--border); padding:0.3rem 0.75rem; border-radius:12px; color:var(--text);">Total Samples: <strong style="color:var(--accent);">{overall_samples:,}</strong></span>
                <span style="font-size:0.75rem; font-weight:700; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:0.3rem 0.75rem; border-radius:12px; color:#10b981;">Pass: <strong>{overall_pass:,}</strong></span>
                <span style="font-size:0.75rem; font-weight:700; background:{'rgba(239,68,68,0.1)' if overall_fail > 0 else 'var(--surface2)'}; border:1px solid {'rgba(239,68,68,0.3)' if overall_fail > 0 else 'var(--border)'}; padding:0.3rem 0.75rem; border-radius:12px; color:{'#ef4444' if overall_fail > 0 else 'var(--muted)'};">Fail: <strong>{overall_fail:,}</strong></span>
            </div>
        </div>
        <div style="overflow-x:auto; border-radius:8px; border:1px solid var(--border);">
            <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                <thead>
                    <tr style="background:#2b579a; color:#ffffff;">
                        <th rowspan="2" style="text-align:left; vertical-align:middle; padding:0.65rem 0.8rem; font-weight:700; font-size:0.8rem; color:#ffffff; border-right:1px solid rgba(255,255,255,0.2);">Scripts Name</th>
                        <th rowspan="2" style="text-align:center; vertical-align:middle; padding:0.65rem 0.8rem; font-weight:700; font-size:0.8rem; color:#ffffff; border-right:1px solid rgba(255,255,255,0.2);">Duration of Run (Min)</th>
                        <th rowspan="2" style="text-align:center; vertical-align:middle; padding:0.65rem 0.8rem; font-weight:700; font-size:0.8rem; color:#ffffff; border-right:1px solid rgba(255,255,255,0.2);">Users</th>
                        <th colspan="3" style="text-align:center; padding:0.45rem 0.8rem; font-weight:700; font-size:0.8rem; color:#ffffff; border-bottom:1px solid rgba(255,255,255,0.2); border-right:1px solid rgba(255,255,255,0.2);">Samples</th>
                        <th rowspan="2" style="text-align:center; vertical-align:middle; padding:0.65rem 0.8rem; font-weight:700; font-size:0.8rem; color:#ffffff;">Error Percentage (%)</th>
                    </tr>
                    <tr style="background:#3b6cb5; color:#ffffff;">
                        <th style="text-align:center; padding:0.4rem 0.6rem; font-weight:700; font-size:0.78rem; color:#ffffff; border-right:1px solid rgba(255,255,255,0.15);">Total</th>
                        <th style="text-align:center; padding:0.4rem 0.6rem; font-weight:700; font-size:0.78rem; color:#a7f3d0; border-right:1px solid rgba(255,255,255,0.15);">Pass</th>
                        <th style="text-align:center; padding:0.4rem 0.6rem; font-weight:700; font-size:0.78rem; color:#fecaca; border-right:1px solid rgba(255,255,255,0.15);">Fail</th>
                    </tr>
                </thead>
                <tbody>
                    {tx_stat_rows_html}
                </tbody>
            </table>
        </div>
    </div>
    '''

    # Build Thread Group -> Child TCs JSON mapping for User Story dropdown filter
    tg_to_tcs_map = {}
    if tg_configs:
        for tg in tg_configs:
            name = tg["name"]
            tcs = tg.get("child_tcs", [])
            # Also include wrapper_tc if present
            if tg.get("wrapper_tc") and tg["wrapper_tc"] not in tcs:
                tcs = [tg["wrapper_tc"]] + tcs
            tg_to_tcs_map[name] = tcs
    tg_to_tcs_json = json.dumps(tg_to_tcs_map)

    # Build User Story dropdown HTML options for Section 5
    us_options_data = []
    us_select_options_html = '<option value="ALL">All User Journeys</option>'
    if tg_to_tcs_map:
        for tg_name in tg_to_tcs_map.keys():
            us_select_options_html += f'<option value="{tg_name}">{tg_name}</option>'
            us_options_data.append({"id": tg_name, "name": tg_name, "shortName": tg_name})
    us_options_json = json.dumps(us_options_data)

    # Build hierarchical transaction & sub-transaction/request data for Interactive Breakdown Bar Chart
    def _build_tx_hierarchy_data():
        user_stories_list = []
        all_tx_list = []
        seen_all_tx = set()

        def _extract_tcs(node):
            tcs = []
            n_name = node.get("name", "")
            n_type = node.get("type", "transaction")
            
            # Check if this node is a step transaction (not a top-level wrapper like T-US01_Overall_Iteration)
            is_step_tc = (n_type == "transaction") and (not n_name.startswith("T-") or "Overall" not in n_name)
            
            if is_step_tc:
                child_items = []
                def _collect_sub_items(ch_node):
                    for c in ch_node.get("children", []):
                        c_name = c.get("name", "")
                        c_data = labels.get(c_name, {})
                        child_items.append({
                            "name": c_name,
                            "type": c.get("type", "request"),
                            "avg_rt": round(c_data.get("avg_rt", 0), 1),
                            "p90": c_data.get("p90", 0),
                            "p95": c_data.get("p95", 0),
                            "min_rt": c_data.get("min_rt", 0),
                            "max_rt": c_data.get("max_rt", 0),
                            "count": c_data.get("count", 0),
                            "errors": c_data.get("errors", 0),
                            "error_rate": round(c_data.get("error_rate", 0), 2)
                        })
                        _collect_sub_items(c)
                _collect_sub_items(node)

                # If no child items found via XML tree but tc_to_samplers has entries
                if not child_items and n_name in tc_to_samplers:
                    for c_name in tc_to_samplers[n_name]:
                        if c_name in labels and c_name != n_name:
                            c_data = labels[c_name]
                            child_items.append({
                                "name": c_name,
                                "type": "request",
                                "avg_rt": round(c_data.get("avg_rt", 0), 1),
                                "p90": c_data.get("p90", 0),
                                "p95": c_data.get("p95", 0),
                                "min_rt": c_data.get("min_rt", 0),
                                "max_rt": c_data.get("max_rt", 0),
                                "count": c_data.get("count", 0),
                                "errors": c_data.get("errors", 0),
                                "error_rate": round(c_data.get("error_rate", 0), 2)
                            })

                tc_data = labels.get(n_name, {})
                t_entry = {
                    "name": n_name,
                    "avg_rt": round(tc_data.get("avg_rt", 0), 1),
                    "p90": tc_data.get("p90", 0),
                    "p95": tc_data.get("p95", 0),
                    "min_rt": tc_data.get("min_rt", 0),
                    "max_rt": tc_data.get("max_rt", 0),
                    "count": tc_data.get("count", 0),
                    "errors": tc_data.get("errors", 0),
                    "error_rate": round(tc_data.get("error_rate", 0), 2),
                    "target_rt": sla_targets.get(n_name, {}).get("rt", default_rt),
                    "children": child_items
                }
                tcs.append(t_entry)
                if n_name not in seen_all_tx:
                    seen_all_tx.add(n_name)
                    all_tx_list.append(t_entry)
            else:
                for c in node.get("children", []):
                    tcs.extend(_extract_tcs(c))
            return tcs

        if jmx_full_tree:
            for tg in jmx_full_tree:
                tg_tcs = []
                for c in tg.get("children", []):
                    tg_tcs.extend(_extract_tcs(c))
                user_stories_list.append({
                    "name": tg["name"],
                    "transactions": tg_tcs
                })
        else:
            # Fallback if no tree parsed: group by display_labels
            fallback_tcs = []
            for lname, ldata in display_labels.items():
                c_items = []
                for c_name in tc_to_samplers.get(lname, []):
                    if c_name in labels and c_name != lname:
                        c_data = labels[c_name]
                        c_items.append({
                            "name": c_name,
                            "type": "request",
                            "avg_rt": round(c_data.get("avg_rt", 0), 1),
                            "p90": c_data.get("p90", 0),
                            "p95": c_data.get("p95", 0),
                            "min_rt": c_data.get("min_rt", 0),
                            "max_rt": c_data.get("max_rt", 0),
                            "count": c_data.get("count", 0),
                            "errors": c_data.get("errors", 0),
                            "error_rate": round(c_data.get("error_rate", 0), 2)
                        })
                t_entry = {
                    "name": lname,
                    "avg_rt": round(ldata.get("avg_rt", 0), 1),
                    "p90": ldata.get("p90", 0),
                    "p95": ldata.get("p95", 0),
                    "min_rt": ldata.get("min_rt", 0),
                    "max_rt": ldata.get("max_rt", 0),
                    "count": ldata.get("count", 0),
                    "errors": ldata.get("errors", 0),
                    "error_rate": round(ldata.get("error_rate", 0), 2),
                    "target_rt": sla_targets.get(lname, {}).get("rt", default_rt),
                    "children": c_items
                }
                fallback_tcs.append(t_entry)
                if lname not in seen_all_tx:
                    seen_all_tx.add(lname)
                    all_tx_list.append(t_entry)

            user_stories_list.append({
                "name": "All User Journeys",
                "transactions": fallback_tcs
            })

        return {
            "user_stories": user_stories_list,
            "all_transactions": all_tx_list
        }

    tx_rt_hierarchy_data = _build_tx_hierarchy_data()
    tx_rt_hierarchy_json = json.dumps(tx_rt_hierarchy_data)

    # Serialize findings and recommendations for JS Findings Drawer
    findings_json = json.dumps(all_findings).replace("</script>", "<\\/script>")
    recs_json = json.dumps(ai_insights.get("recommendations", [])).replace("</script>", "<\\/script>")

    # Load comparison draft if available
    comparison_draft = parsed.get("comparison_draft")
    if not comparison_draft:
        root_dir = Path(__file__).parent.parent.parent.resolve()
        draft_file = root_dir / "Results" / "json" / f"{run_id}_comparison_draft.json"
        if not draft_file.exists():
            draft_file = root_dir / "Results" / f"{run_id}_comparison_draft.json"
        if draft_file.exists():
            try:
                comparison_draft = json.loads(draft_file.read_text(encoding="utf-8"))
            except Exception:
                comparison_draft = None
    comparison_draft_json = json.dumps(comparison_draft or {}).replace("</script>", "<\\/script>")


    # ── Build and return the complete report context ──
    # All local variables computed above become ctx entries
    ctx = {k: v for k, v in locals().items() if (not k.startswith('_') or k in ('_build_validation_badge', '_clean_client_text', '_format_as_pointers')) and k not in ('parsed_orig',)}
    # Ensure critical keys are present
    ctx["parsed"] = parsed
    ctx["ai_insights"] = ai_insights
    effective_users = max(users, total_tg_users) if total_tg_users > 0 else (users or 1)
    ctx["users"] = effective_users
    return ctx
