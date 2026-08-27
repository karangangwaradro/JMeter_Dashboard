#!/usr/bin/env python3
"""
report_generator.py — HTML Performance Report Generator for PerfPilot.

Generates a premium standalone HTML performance report with:
  - KPI cards, per-transaction breakdown
  - Time-series charts (Chart.js)
  - Azure Monitor server-side metrics overlay
  - AI-powered insights panel
  - Dark/light mode toggle
"""

import json
from pathlib import Path
from datetime import datetime


def generate_report(parsed: dict, azure_data: dict, ai_insights: dict,
                    report_path: Path, jmx_name: str, users: int):
    """Generate a standalone HTML performance report."""
    summary = parsed.get("summary", {})
    labels = parsed.get("labels", {})
    ts = parsed.get("time_series", {})
    correlation = parsed.get("correlation", {})
    execution_time = parsed.get("execution_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    run_id = parsed.get("run_id", "unknown")

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

    try:
        from python_files.sla_manager import load_sla_targets, parse_jmx_hierarchy
        sla_targets, default_rt, default_err = load_sla_targets(jmx_name)
    except Exception as sla_err:
        print(f"[Report] SLA targets load warning: {sla_err}", flush=True)

    try:
        from python_files.sla_manager import parse_jmx_hierarchy
        tc_ordered, tc_to_samplers = parse_jmx_hierarchy(jmx_name)
    except Exception as hier_err:
        print(f"[Report] Hierarchy parse warning: {hier_err}", flush=True)

    # Parse full tree structure for hierarchical table display
    jmx_full_tree = []
    tg_to_transactions = {}
    try:
        from python_files.sla_manager import parse_jmx_full_tree
        jmx_full_tree, tg_to_transactions = parse_jmx_full_tree(jmx_name)
    except Exception as tree_err:
        print(f"[Report] Full tree parse warning: {tree_err}", flush=True)

    # Filter for main report display: if Transaction Controllers exist, only show TCs in main tables/charts
    tc_set = set(tc_ordered) if tc_ordered else set()
    display_labels = {k: v for k, v in labels.items() if k in tc_set} if tc_set else {k: v for k, v in labels.items() if k.upper().startswith("TC")}
    if not display_labels:
        display_labels = labels

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
    
    from python_files.apdex_calculator import calculate_apdex, calculate_apdex_from_summary

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
        if not name:
            return None, name
        if name in tg_specific:
            return tg_specific[name], name
        if name in all_lbls:
            return all_lbls[name], name

        import re
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
        # TREE MODE: Thread Group -> Overall Transaction -> Main Transactions -> All Requests (flattening sub-transactions)
        tg_filter_options = '<option value="ALL">All Thread Groups</option>'
        for tg_node in jmx_full_tree:
            tg_name = tg_node["name"]
            tg_filter_options += f'<option value="{tg_name}">{tg_name}</option>'

        for tg_node in jmx_full_tree:
            tg_name = tg_node["name"]
            tg_specific_labels = labels_by_tg.get(tg_name, {})

            # Thread group header row
            labels_rows += f"""
            <tr class="tg-header-row" data-tg="{tg_name}" style="background: linear-gradient(135deg, var(--accent-bg), var(--surface2)); border-top: 2px solid var(--accent);">
                <td colspan="11" style="padding: 0.6rem 1rem; font-weight: 700; font-size: 0.88rem; color: var(--accent);">
                    <span style="display:inline-flex; align-items:center; gap:0.4rem;">🔧 Thread Group: <span style="color:var(--text);">{tg_name}</span></span>
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
        # FLAT MODE (fallback): No JMX tree available, use original flat rendering
        tg_filter_options = ''
        for lname, ldata in sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True):
            labels_rows += _build_tx_row(lname, ldata, depth=0, node_type="transaction", tg_name="")

            # Also build flat child rows for fallback mode (original behavior)
            c_samplers_table = tc_to_samplers.get(lname, [])
            matched_table_children = {}
            for c_spec in c_samplers_table:
                if c_spec in labels and c_spec != lname:
                    matched_table_children[c_spec] = labels[c_spec]

            if not matched_table_children:
                import re
                clean_name_t = re.sub(r'TC\d+|_|T\d+', ' ', lname)
                split_words_t = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', clean_name_t)
                keywords_t = [w.lower() for w in split_words_t if len(w) >= 3 and w.lower() not in ("tc01", "tc02", "tc03", "t01", "t02", "t03", "t04")]
                for l_key, l_val in labels.items():
                    if l_key != lname and not l_key.upper().startswith("TC0") and not l_key.upper().startswith("TC1"):
                        if any(kw in l_key.lower() for kw in keywords_t):
                            matched_table_children[l_key] = l_val

            c_cls_id = f"child-row-group-{hash(lname) & 0xffffffff}"
            if matched_table_children:
                for cs_k, cs_v in matched_table_children.items():
                    c_err_cls = "pass" if cs_v.get('error_rate', 0) <= 1 else "fail"
                    labels_rows += f"""
                    <tr class="{c_cls_id}" style="display: none; background: var(--surface2); font-size: 0.76rem;">
                        <td style="padding-left: 2rem;">↳ <code>{cs_k}</code></td>
                        <td>{cs_v.get('count', 0):,}</td>
                        <td>-</td>
                        <td class="tx-rt-cell" data-ms="{cs_v.get('avg_rt', 0):.1f}"><span class="tx-rt-val">{cs_v.get('avg_rt', 0):.0f}</span></td>
                        <td class="tx-rt-cell" data-ms="{cs_v.get('p90', 0)}"><strong class="tx-rt-val">{cs_v.get('p90', 0)}</strong></td>
                        <td class="tx-rt-cell" data-ms="{cs_v.get('min_rt', 0)}"><span class="tx-rt-val">{cs_v.get('min_rt', 0)}</span></td>
                        <td class="tx-rt-cell" data-ms="{cs_v.get('max_rt', 0)}"><span class="tx-rt-val">{cs_v.get('max_rt', 0)}</span></td>
                        <td class="{c_err_cls}">{cs_v.get('error_rate', 0):.2f}%</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>"""

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
        
        sev_label = "Critical Deviation" if dev_pct > 90 else "Slightly Deviated" if dev_pct > 60 else "Acceptable Deviation"
        sev_color = "var(--red)" if dev_pct > 90 else "var(--yellow)"
        if err_val > t_err_target:
            sev_label = "Critical Deviation"
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
    for err_k, err_v in error_details_raw.items():
        k_lower = err_k.lower()
        msg_lower = (err_v.get("message") or "").lower()
        fmsg_lower = (err_v.get("failure_message") or "").lower()
        if any(w in k_lower or w in msg_lower or w in fmsg_lower for w in [
            "samples in transaction", "failed samples", "failing samples", "transaction failed", "transaction controller"
        ]):
            continue
        
        filtered_occs = [
            occ for occ in err_v.get("occurrences", [])
            if not (occ.get("label", "").lower().startswith("tc") or 
                    occ.get("label", "").lower().startswith("t-") or 
                    "transaction controller" in occ.get("label", "").lower() or 
                    "overall_iteration" in occ.get("label", "").lower() or
                    "controller" in occ.get("label", "").lower())
        ]
        
        cleaned_entry = dict(err_v)
        if filtered_occs:
            cleaned_entry["occurrences"] = filtered_occs
            cleaned_entry["count"] = len(filtered_occs) if len(err_v.get("occurrences", [])) == err_v.get("count", 0) else err_v.get("count", len(filtered_occs))
        elif err_v.get("occurrences") and not filtered_occs:
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
        from python_files.sla_manager import parse_jmx_thread_groups
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

    total_tg_users = sum(tg.get("users", 1) for tg in tg_configs) if tg_configs else users
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

    # Compute Throughput Scaling Efficiency
    first_tp = ts_tp_raw[0] if ts_tp_raw and ts_tp_raw[0] > 0 else (ts_tp_raw[1] if len(ts_tp_raw) > 1 else cap_peak_tps)
    tp_growth_pct = round(((cap_peak_tps - first_tp) / first_tp * 100), 1) if first_tp > 0 else 0.0
    tp_scaling_text = f"+{tp_growth_pct:.1f}%" if tp_growth_pct > 0 else "0.0%"
    tp_scaling_eval = "🟢 Linear Scaling" if tp_growth_pct >= 20 else ("🟡 Steady Load" if tp_growth_pct >= 0 else "🔴 Degrading")

    # ── Load vs Throughput and Load vs RT Data Series for Charts ──
    # Map time points with VUs, TPS, P95, and Avg RT
    ts_lbls_list = json.loads(ts_labels)
    ts_vus_list = json.loads(concurrency_est) if concurrency_est else [total_tg_users] * len(ts_lbls_list)
    
    # Combined labels showing interval + active VUs (e.g., "10s (11 VUs)")
    load_chart_labels = [f"{lbl} ({vu} VUs)" for lbl, vu in zip(ts_lbls_list, ts_vus_list)]
    load_chart_labels_json = json.dumps(load_chart_labels)
    
    # Expected linear scaling reference line
    max_vu_val = max(ts_vus_list, default=total_tg_users) or 1
    expected_tp_series = [round((vu / max_vu_val) * cap_peak_tps, 1) for vu in ts_vus_list]
    expected_tp_json = json.dumps(expected_tp_series)
    
    # Global SLA threshold reference array for chart
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
            <td style="padding:0.75rem 0.8rem; text-align:center; vertical-align:middle;">
                {capacity_rating}
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

    # Azure data
    azure_configured = azure_data and azure_data.get("configured", False)
    infra = azure_data.get("infra_summary", {}) if azure_data else {}
    azure_ts = azure_data.get("time_series", {}) if azure_data else {}

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

    raw_cpu = azure_ts.get("cpu", [])
    raw_mem = azure_ts.get("memory", [])
    raw_disk_q = azure_ts.get("disk_queue", [])
    raw_disk_read = azure_ts.get("disk_read_mb", [])
    raw_disk_write = azure_ts.get("disk_write_mb", [])
    raw_net_in = azure_ts.get("net_in_mb", [])
    raw_net_out = azure_ts.get("net_out_mb", [])
    raw_avail = azure_ts.get("availability", [])

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
    # AI Insights
    ai_source = ai_insights.get("source", "none") if ai_insights else "none"
    ai_badge = "🤖 AI Generated" if ai_source == "gemini" else "📊 System Calculated" if ai_source == "rule_based" else "⚠️ No Analysis"
    ai_badge_color = "#3b82f6" if ai_source == "gemini" else "#6b7280"

    exec_summary = ai_insights.get("executive_summary", "No analysis available.") if ai_insights else "AI insights not generated."
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
        recs_html = '<div class="rec-card info"><div class="rec-title" contenteditable="true">No specific recommendations</div><div class="rec-desc" contenteditable="true">Test metrics are within healthy thresholds.</div></div>'

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
    from python_files.findings_engine import generate_findings, enrich_findings_with_ai, SEVERITY_BADGES
    findings_result = generate_findings(
        summary=summary, labels=labels, display_labels=display_labels,
        time_series=ts, infra=infra, correlation=correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err
    )
    # Enrich with AI interpretations if available
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
        <div class="glass-panel" style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Performance Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    {related_badge}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{badge_text}</span>
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
        <div class="glass-panel" style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Performance Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    {tp_related_badge}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{badge_text}</span>
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
        <div class="glass-panel" style="border-left: 4px solid {inf_border}; background: {inf_bg}; padding: 1rem 1.25rem; border-radius: 8px; margin-top: 1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <div style="font-weight:800; font-size:0.92rem; color:var(--text); display:flex; align-items:center; gap:0.4rem;">
                    <span>🧠 Infrastructure Observation</span>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    {infra_related}
                    <span style="font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; background:var(--surface); border:1px solid var(--border); color:var(--text);">{inf_badge}</span>
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
        priority_actions_html += f'<div class="roadmap-step"><span class="step-num">{i}</span><span>{sev_icon} Investigate <strong>{f["id"]}</strong> — {f["title"]}</span></div>'

    if not priority_actions_html:
        priority_actions_html = '<div class="roadmap-step"><span class="step-num">1</span><span>🟢 No critical findings — maintain current performance baseline.</span></div>'

    # ── 6. Build Performance Intelligence Sections (Executive Summary & Tab-wise) ─
    perf_intel = findings_result.get("performance_intelligence", {})
    exec_intel = perf_intel.get("executive_summary", {})
    tab_tx_intel = perf_intel.get("tab_tx_stats", {})
    tab_rt_intel = perf_intel.get("tab_rt_stats", {})
    tab_error_intel = perf_intel.get("tab_error_stats", {})
    tab_infra_intel = perf_intel.get("tab_infra_stats", {})

    # Standardized Tab Insight Panel Helper
    def _build_tab_insight_panel(intel_data: dict, tab_title: str) -> str:
        if not intel_data:
            return ""
        obs_items = "".join([f'<li style="margin-bottom:0.35rem;">{obs}</li>' for obs in intel_data.get("observations", [])])
        rec_items = "".join([f'<li style="margin-bottom:0.35rem;">{rec}</li>' for rec in intel_data.get("recommendations", [])])
        return f"""
        <div class="section glass-panel" style="margin-bottom: 1.25rem; padding: 1.2rem 1.5rem; border-left: 4px solid var(--accent);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.75rem;">
                <h3 style="margin:0; font-size:0.95rem; font-weight:700; color:var(--text);">🧠 {tab_title} Insights &amp; Recommendations</h3>
                <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.2rem 0.6rem; border-radius:12px;">Evidence-Backed</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem;">
                    <div style="font-size:0.8rem; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.5rem;">🔍 Key Observations</div>
                    <ul style="margin:0; padding-left:1.2rem; font-size:0.84rem; line-height:1.55; color:var(--text);" contenteditable="true">
                        {obs_items}
                    </ul>
                </div>
                <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem;">
                    <div style="font-size:0.8rem; font-weight:700; color:var(--green); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.5rem;">💡 Recommendations</div>
                    <ul style="margin:0; padding-left:1.2rem; font-size:0.84rem; line-height:1.55; color:var(--text);" contenteditable="true">
                        {rec_items}
                    </ul>
                </div>
            </div>
        </div>
        """

    tab_tx_panel_html = _build_tab_insight_panel(tab_tx_intel, "Transaction Performance")
    tab_rt_panel_html = _build_tab_insight_panel(tab_rt_intel, "Response Time & SLA")
    tab_error_panel_html = _build_tab_insight_panel(tab_error_intel, "Reliability & Errors")
    tab_infra_panel_html = _build_tab_insight_panel(tab_infra_intel, "Infrastructure Monitoring")

    # Executive Summary Blocks
    exec_assessment_badge = exec_intel.get("assessment_badge", "⚠️ PERFORMANCE REQUIRES ATTENTION")
    exec_assessment_color = exec_intel.get("assessment_color", "var(--red)")
    exec_assessment_text = exec_intel.get("assessment_text", "")
    
    exec_assessment_html = f"""
    <div class="section glass-panel" style="margin-top:1.25rem; border-left: 5px solid {exec_assessment_color}; padding: 1.25rem 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
            <div style="font-size:0.92rem; font-weight:800; color:{exec_assessment_color}; letter-spacing:0.04em;">{exec_assessment_badge}</div>
            <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.2rem 0.6rem; border-radius:12px;">Executive Overview</span>
        </div>
        <p style="font-size:0.92rem; line-height:1.65; margin:0; color:var(--text);" contenteditable="true">{exec_assessment_text}</p>
    </div>
    """

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

    # Observations Table
    obs_rows = ""
    for row in exec_intel.get("observations_table", []):
        obs_rows += f"""
        <tr style="border-bottom:1px solid var(--border);">
            <td style="font-weight:700; width:24%; vertical-align:top; font-size:0.85rem; color:var(--text);">{row.get('category', '')}</td>
            <td style="width:76%; vertical-align:top; font-size:0.85rem; line-height:1.55; color:var(--text);" contenteditable="true">{row.get('observation', '')}</td>
        </tr>
        """
    exec_obs_table_html = f"""
    <div class="section glass-panel" style="margin-top:1.25rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <h2 style="margin:0;">📋 High-Level Performance Observations</h2>
            <span style="font-size:0.75rem; font-weight:600; color:var(--muted);">Factual Assessment</span>
        </div>
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr style="background:var(--surface2); text-align:left;">
                    <th style="padding:0.6rem 0.8rem; font-size:0.78rem; font-weight:700; width:24%;">Category</th>
                    <th style="padding:0.6rem 0.8rem; font-size:0.78rem; font-weight:700; width:76%;">Key Observation with Embedded Evidence</th>
                </tr>
            </thead>
            <tbody>
                {obs_rows}
            </tbody>
        </table>
    </div>
    """

    # Conclusions & Priority Recommendations
    concl_items = "".join([f'<li style="margin-bottom:0.45rem;">{c}</li>' for c in exec_intel.get("conclusions", [])])
    exec_conclusions_html = f"""
    <div class="section glass-panel" style="margin-top:1.25rem; border-left: 4px solid var(--accent);">
        <h2 style="margin:0 0 0.6rem 0;">📌 Key Conclusions</h2>
        <ul style="margin:0; padding-left:1.3rem; font-size:0.88rem; line-height:1.65; color:var(--text);" contenteditable="true">
            {concl_items}
        </ul>
    </div>
    """

    p_recs_html = ""
    for r in exec_intel.get("priority_recommendations", []):
        r_badge = r.get("badge", "💡")
        r_title = r.get("title", "")
        r_detail = r.get("detail", "")
        r_priority = r.get("priority", "Medium")
        p_recs_html += f"""
        <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem;">
                <span style="font-size:1rem;">{r_badge}</span>
                <strong style="font-size:0.9rem; color:var(--text);" contenteditable="true">{r_title}</strong>
                <span style="font-size:0.7rem; font-weight:700; text-transform:uppercase; padding:0.15rem 0.5rem; border-radius:4px; background:var(--surface); border:1px solid var(--border); color:var(--muted); margin-left:auto;">{r_priority}</span>
            </div>
            <p style="margin:0; font-size:0.85rem; line-height:1.55; color:var(--muted);" contenteditable="true">{r_detail}</p>
        </div>
        """

    exec_priority_recs_html = f"""
    <div class="section glass-panel" style="margin-top:1.25rem; border-left: 4px solid var(--green);">
        <h2 style="margin:0 0 0.8rem 0;">💡 Priority Recommendations</h2>
        <div contenteditable="true">
            {p_recs_html}
        </div>
    </div>
    """

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
    for idx_i, l_name in enumerate(display_label_names):
        short_display = l_name if len(l_name) <= 50 else f"{l_name[:47]}..."
        # Use json.dumps to safely escape the display name for the title attribute
        safe_title = short_display.replace('"', '&quot;')
        tx_options_html += f'<option value="{idx_i}" title="{safe_title}">{short_display}</option>'

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
        from python_files.sla_manager import parse_jmx_thread_groups
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
    us_select_options_html = '<option value="ALL">All User Stories / Thread Groups</option>'
    if tg_to_tcs_map:
        for tg_name in tg_to_tcs_map.keys():
            us_select_options_html += f'<option value="{tg_name}">{tg_name}</option>'

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
                "name": "All User Stories",
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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{jmx_name} — Performance Report | PerfPilot</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-grad: linear-gradient(135deg, #e0e7ff 0%, #f3f4f6 50%, #dbeafe 100%);
            --surface: rgba(255, 255, 255, 0.65);
            --surface2: rgba(255, 255, 255, 0.4);
            --border: rgba(255, 255, 255, 0.6);
            --text: #1f2328; --muted: #4b5563;
            --accent: #2563eb; --accent2: #1d4ed8;
            --accent-bg: rgba(37, 99, 235, 0.06);
            --green: #059669; --yellow: #d97706; --red: #dc2626; --blue: #2563eb;
            --green-bg: rgba(16, 185, 129, 0.15); --yellow-bg: rgba(245, 158, 11, 0.15);
            --red-bg: rgba(239, 68, 68, 0.15); --blue-bg: rgba(59, 130, 246, 0.15);
            --shadow-sm: 0 4px 16px rgba(0, 0, 0, 0.04);
            --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.06);
        }}
        html.dark {{
            --bg-grad: linear-gradient(135deg, #0f172a 0%, #020617 50%, #1e1b4b 100%);
            --surface: rgba(30, 41, 59, 0.65);
            --surface2: rgba(30, 41, 59, 0.4);
            --border: rgba(255, 255, 255, 0.08);
            --text: #f1f5f9; --muted: #94a3b8;
            --accent: #3b82f6; --accent2: #60a5fa;
            --accent-bg: rgba(59, 130, 246, 0.08);
            --green: #10b981; --yellow: #f59e0b; --red: #ef4444; --blue: #3b82f6;
            --shadow-sm: 0 4px 16px rgba(0, 0, 0, 0.2);
            --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: var(--bg-grad); background-attachment: fixed; color: var(--text); font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 2rem; line-height: 1.5; }}
        .report-container {{ max-width: 1300px; margin: 0 auto; }}

        /* Glassmorphism Base for Containers */
        .glass-panel {{
            background: var(--surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }}

        /* Tree hierarchy styles */
        .tg-header-row td {{ border-bottom: 1px solid var(--accent) !important; }}
        .tree-row[data-type="request"] td {{ padding-top: 0.35rem; padding-bottom: 0.35rem; }}
        .tree-toggle-btn {{
            background: transparent;
            border: none;
            color: var(--accent);
            cursor: pointer;
            font-size: 0.72rem;
            padding: 0.1rem 0.25rem;
            margin-right: 0.25rem;
            line-height: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
            user-select: none;
        }}
        .tree-toggle-btn:hover {{
            color: var(--text);
            transform: scale(1.3);
        }}
        .tree-toggle-spacer {{
            display: inline-block;
            width: 0.95rem;
            margin-right: 0.25rem;
        }}

        /* Header */
        .report-header {{ display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 1.75rem; border-radius: 12px; margin-bottom: 1.5rem; transition: box-shadow 0.2s; }}
        .report-header:hover {{ box-shadow: var(--shadow-md); }}
        .header-left {{ display: flex; align-items: center; gap: 1.25rem; }}
        .engine-badge {{ background: var(--surface2); border: 1px solid var(--border); padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; letter-spacing: 0; }}
        .report-title h1 {{ font-size: 1.35rem; font-weight: 700; color: var(--text); }}
        .report-title p {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.25rem; }}
        .header-right {{ display: flex; align-items: center; gap: 1rem; }}
        .score-circle {{ width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; font-weight: 800; border: 2px solid {score_color}; color: {score_color}; background: var(--surface2); }}
        .status-pill {{ padding: 0.35rem 0.85rem; border-radius: 12px; font-size: 0.78rem; font-weight: 700; color: #fff; background: {status_color}; text-shadow: 0 1px 2px rgba(0,0,0,0.1); }}
        .theme-toggle {{ cursor: pointer; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 0.45rem 0.8rem; color: var(--text); font-size: 0.82rem; font-weight: 600; transition: all 0.2s; }}
        .theme-toggle:hover {{ background: var(--border); }}

        /* Nav Tabs */
        .report-nav {{ display: flex; gap: 0.35rem; padding: 0.4rem; border-radius: 10px; margin-bottom: 1.5rem; }}
        .nav-btn {{ flex: 1; padding: 0.6rem 1rem; text-align: center; border: none; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.85rem; border-radius: 8px; cursor: pointer; transition: all 0.2s; }}
        .nav-btn:hover {{ color: var(--text); background: var(--surface2); }}
        .nav-btn.active {{ color: #ffffff; background: var(--accent); font-weight: 700; box-shadow: var(--shadow-sm); }}
        .tab-pane {{ display: block; animation: fadeIn 0.3s ease-in-out; }}
        .tab-pane.hidden {{ display: none !important; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        /* KPI Grid */
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem; }}
        .kpi-card {{ border-radius: 12px; padding: 1.25rem 1.5rem; transition: all 0.2s; }}
        .kpi-card:hover {{ border-color: var(--accent); box-shadow: var(--shadow-md); transform: translateY(-2px); }}
        .kpi-label {{ color: var(--muted); font-size: 0.78rem; margin-bottom: 0.4rem; font-weight: 600; }}
        .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: var(--text); }}
        .kpi-sub {{ font-size: 0.75rem; color: var(--muted); margin-top: 0.2rem; }}
        .pass {{ color: var(--green); }} .warn {{ color: var(--yellow); }} .fail {{ color: var(--red); }}

        /* Sections */
        .section {{ border-radius: 12px; padding: 1.75rem; margin-bottom: 1.5rem; overflow: auto; }}
        .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; }}
        .section h2 {{ font-size: 1.1rem; font-weight: 700; color: var(--text); margin-bottom: 1.25rem; }}
        .ai-badge {{ display: inline-flex; align-items: center; gap: 0.4rem; background: var(--surface2); color: var(--text); border: 1px solid var(--border); padding: 0.3rem 0.8rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; }}

        /* Tables */
        table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.85rem; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
        th {{ background: var(--surface2); color: var(--muted); text-align: left; padding: 0.75rem 1rem; font-size: 0.78rem; border-bottom: 1px solid var(--border); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); background: rgba(255, 255, 255, 0.1); }}
        tr:hover td {{ background: var(--surface2); }}
        tr:last-child td {{ border-bottom: none; }}

        /* Charts */
        .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }}
        @media (max-width: 900px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
        .chart-box {{ border-radius: 12px; padding: 1.5rem; }}
        .chart-box h3 {{ font-size: 0.95rem; font-weight: 700; margin-bottom: 1rem; color: var(--text); }}

        /* AI Insights & Recs */
        .insight-card {{ background: var(--surface2); border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; border-left: 4px solid var(--accent); }}
        .insight-card h4 {{ font-size: 0.9rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--accent); }}
        .insight-card p {{ font-size: 0.88rem; line-height: 1.7; }}
        .rec-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }}
        @media (max-width: 900px) {{ .rec-grid {{ grid-template-columns: 1fr; }} }}
        .rec-card {{ border-radius: 10px; padding: 1.25rem; border: 1px solid var(--border); background: var(--surface2); }}
        .rec-card.critical {{ border-left: 4px solid var(--red); }}
        .rec-card.warning {{ border-left: 4px solid var(--yellow); }}
        .rec-card.info {{ border-left: 4px solid var(--blue); }}
        .rec-header {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }}
        .rec-priority {{ font-size: 0.72rem; font-weight: 700; text-transform: uppercase; padding: 0.2rem 0.6rem; border-radius: 6px; }}
        .rec-card.critical .rec-priority {{ background: var(--red); color: #fff; }}
        .rec-card.warning .rec-priority {{ background: var(--yellow); color: #000; }}
        .rec-card.info .rec-priority {{ background: var(--blue); color: #fff; }}
        .rec-category {{ font-size: 0.72rem; color: var(--muted); padding: 0.2rem 0.6rem; border: 1px solid var(--border); border-radius: 6px; }}
        .rec-title {{ font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; }}
        .rec-desc {{ font-size: 0.85rem; color: var(--muted); line-height: 1.6; }}
        .rec-impact {{ font-size: 0.78rem; color: var(--green); margin-top: 0.75rem; font-weight: 600; }}

        /* Capacity */
        .capacity-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-bottom: 1.25rem; }}
        .cap-card {{ background: var(--surface2); border-radius: 10px; padding: 1.25rem; text-align: center; border: 1px solid var(--border); }}
        .cap-label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; font-weight: 600; }}
        .cap-value {{ font-size: 1.75rem; font-weight: 800; color: var(--accent); }}
        .cap-analysis {{ font-size: 0.85rem; color: var(--muted); }}

        /* Editable */
        [contenteditable="true"] {{ outline: 2px dashed rgba(139, 92, 246, 0.4); outline-offset: 3px; border-radius: 4px; transition: outline-color 0.2s; }}
        [contenteditable="true"]:hover {{ outline-color: var(--accent); }}
        [contenteditable="true"]:focus {{ outline: 2px solid var(--accent); background: var(--surface2); }}
        .published-mode [contenteditable="true"] {{ outline: none !important; background: transparent !important; }}

        /* AI Observation Panels — inline below charts */
        .ai-observation-panel {{ background: var(--surface2); border-radius: 10px; padding: 1rem 1.25rem; margin-top: 1rem; border-left: 4px solid var(--accent); border: 1px solid var(--border); border-left: 4px solid var(--accent); }}
        .ai-observation-panel h4 {{ font-size: 0.88rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--accent); }}
        .ai-interpretation {{ font-size: 0.82rem; color: var(--muted); border-left: 3px solid var(--accent); padding: 0.4rem 0.8rem; margin: 0.5rem 0 0 0; background: rgba(37, 99, 235, 0.04); border-radius: 0 6px 6px 0; font-style: italic; }}
        .evidence-grid {{ display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: var(--text); }}
        .evidence-chip {{ background: var(--surface); border: 1px solid var(--border); padding: 0.2rem 0.5rem; border-radius: 5px; font-weight: 600; font-size: 0.78rem; }}

        /* Finding Badges — used in tables and inline references */
        .finding-badge {{ display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.72rem; font-weight: 700; border: 1.5px solid; background: transparent; white-space: nowrap; }}
        .finding-badge-inline {{ display: inline-flex; align-items: center; gap: 0.2rem; padding: 0.15rem 0.45rem; border-radius: 5px; font-size: 0.7rem; font-weight: 700; background: var(--surface); border: 1px solid var(--border); color: var(--accent); }}

        /* Finding Detail Cards — in AI Summary tab */
        .finding-detail {{ background: var(--surface2); border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; border: 1px solid var(--border); border-left: 4px solid var(--accent); scroll-margin-top: 2rem; }}

        /* Evidence Source References */
        .evidence-ref {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 5px; font-size: 0.72rem; font-weight: 600; background: var(--surface); border: 1px solid var(--border); color: var(--accent); margin: 0.1rem 0; }}

        /* Confidence Badges */
        .confidence-badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 5px; font-size: 0.7rem; font-weight: 600; margin-right: 0.4rem; }}
        .confidence-badge.confidence-high {{ background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }}
        .confidence-badge.confidence-medium {{ background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }}
        .confidence-badge.confidence-low {{ background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }}

        .report-footer {{ text-align: center; color: var(--muted); font-size: 0.82rem; padding: 2.5rem 0; font-weight: 500; }}

        /* --- Edit Mode Styles --- */
        [contenteditable="true"] {{ outline: none !important; background: transparent !important; border: none !important; transition: all 0.2s; }}
        body.edit-mode-active [contenteditable="true"] {{ outline: 1px dashed var(--accent) !important; background: rgba(99, 102, 241, 0.05) !important; cursor: text; }}
        .delete-rec-btn {{ display: none; position: absolute; right: 0.5rem; top: 0.5rem; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; color: #ef4444; padding: 0.2rem 0.5rem; font-size: 0.75rem; cursor: pointer; font-weight: 700; transition: all 0.2s; z-index: 10; }}
        .delete-rec-btn:hover {{ background: #ef4444; color: #fff; }}
        body.edit-mode-active .delete-rec-btn {{ display: block !important; }}

        /* Print & PDF Export Styles */
        @media print {{
            body {{ background: #ffffff !important; color: #000000 !important; padding: 0 !important; font-size: 10pt !important; }}
            * {{ overflow: visible !important; }}
            .report-container {{ max-width: 100% !important; margin: 0 !important; padding: 0 !important; }}
            .glass-panel {{ background: #ffffff !important; box-shadow: none !important; border: 1px solid #ddd !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; border-radius: 6px !important; padding: 1rem !important; margin-bottom: 1.5rem !important; }}
            .report-nav, .theme-toggle, #publishBtn, #pdfBtn, #editModeBadge, .delete-rec-btn {{ display: none !important; }}
            .tab-pane, .tab-pane.hidden {{ display: block !important; opacity: 1 !important; visibility: visible !important; height: auto !important; position: static !important; margin-bottom: 1rem !important; animation: none !important; }}
            .chart-box, .section, .kpi-card, .rec-card, table, tr, img {{ page-break-inside: avoid !important; }}
            .report-header {{ border: none !important; box-shadow: none !important; padding: 0 0 1rem 0 !important; margin-bottom: 1.5rem !important; border-bottom: 2px solid #e1e4e8 !important; border-radius: 0 !important; }}
            
            /* Fixes for specific elements to fit PDF A4 perfectly */
            .chart-box {{ width: 100% !important; padding: 0.5rem !important; page-break-inside: avoid !important; }}
            table {{ width: 100% !important; border-collapse: collapse !important; font-size: 9pt !important; page-break-inside: auto !important; }}
            tr {{ page-break-inside: avoid !important; page-break-after: auto !important; }}
            th, td {{ border: 1px solid #e1e4e8 !important; padding: 0.4rem !important; background: none !important; }}
            
            /* Typography scaling for print */
            h1 {{ font-size: 16pt !important; }}
            h2 {{ font-size: 13pt !important; margin-bottom: 0.75rem !important; margin-top: 0 !important; }}
            h3 {{ font-size: 11pt !important; margin-bottom: 0.5rem !important; }}
            p, span, div {{ font-size: 9.5pt !important; line-height: 1.4 !important; }}
            .kpi-value {{ font-size: 18pt !important; }}
            .kpi-label {{ font-size: 8pt !important; }}
            .kpi-card {{ padding: 0.75rem !important; }}
            .rec-card {{ padding: 0.75rem !important; border-width: 1px !important; border-left-width: 4px !important; margin-bottom: 0.5rem !important; }}
            .rec-desc {{ font-size: 9pt !important; }}
            .insight-card p {{  font-size: 9.5pt !important; }}
            .insight-card {{ border-width: 1px !important; border-left-width: 4px !important; padding: 1rem !important; }}
        }}

        /* --- Drawer Overlay & Panel --- */
        #findingDrawerOverlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 9998; backdrop-filter: blur(2px);
        }}
        #findingDrawer {{
            display: none; position: fixed; top: 0; right: -450px; width: 450px; height: 100%; background: var(--surface); box-shadow: -4px 0 15px rgba(0,0,0,0.15); z-index: 9999; border-left: 1px solid var(--border); overflow-y: auto; transition: right 0.3s ease; padding: 1.5rem;
        }}
        #findingDrawer.open {{ right: 0; }}
        .drawer-close {{ font-size: 1.5rem; cursor: pointer; color: var(--muted); background: transparent; border: none; outline: none; }}
        .drawer-section {{ margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
        .drawer-section:last-child {{ border-bottom: none; }}
        .drawer-h {{ font-size: 0.85rem; font-weight: 700; color: var(--accent); margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.5px; }}

        /* --- Graph Info Button & Modal --- */
        .chart-info-btn {{
            position: absolute;
            top: 1rem;
            right: 1.1rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--surface2);
            border: 1.5px solid var(--border);
            color: var(--accent);
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            flex-shrink: 0;
            user-select: none;
            z-index: 15;
        }}
        .chart-info-btn:hover {{
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
            transform: translateY(-2px) scale(1.1);
            box-shadow: 0 4px 14px rgba(99,102,241,0.35);
        }}
        #graphModalOverlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}
        #graphModalOverlay.open {{
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 1;
        }}
        #graphInfoModal {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
            width: 90%;
            max-width: 540px;
            max-height: 85vh;
            overflow-y: auto;
            padding: 1.5rem;
            transform: scale(0.95);
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 10001;
        }}
        #graphModalOverlay.open #graphInfoModal {{
            transform: scale(1);
        }}
        .graph-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.8rem;
            margin-bottom: 1rem;
        }}
        .graph-modal-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .graph-modal-close {{
            font-size: 1.5rem;
            line-height: 1;
            color: var(--muted);
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 0 0.3rem;
            border-radius: 4px;
            transition: color 0.15s;
        }}
        .graph-modal-close:hover {{
            color: var(--text);
        }}
        .graph-modal-section {{
            margin-bottom: 1rem;
        }}
        .graph-modal-section:last-child {{
            margin-bottom: 0;
        }}
        .graph-modal-section-title {{
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--accent);
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }}
        .graph-modal-text {{
            font-size: 0.86rem;
            color: var(--text);
            line-height: 1.5;
            margin: 0;
        }}
        .graph-modal-list {{
            margin: 0.3rem 0 0 1.2rem;
            padding: 0;
            font-size: 0.86rem;
            color: var(--text);
            line-height: 1.5;
        }}
        .graph-modal-list li {{
            margin-bottom: 0.3rem;
        }}
    </style>
</head>
<body>
<div class="report-container">

    <!-- Header -->
    <div class="report-header glass-panel" style="display:flex; justify-content:space-between; align-items:center; padding:1rem 1.5rem; margin-bottom:1rem;">
        <div class="header-left" style="display:flex; align-items:center; gap:1.25rem;">
            <div class="engine-badge" style="font-weight:800; font-size:1.2rem; color:var(--accent);">⚡ PerfPilot</div>
            <div style="border-left:2px solid var(--border); padding-left:1.25rem;">
                <div style="font-size:1.15rem; font-weight:700; color:var(--text);" contenteditable="true">Performance Test Report - {jmx_name}</div>
            </div>
        </div>
        <div class="header-right" style="display:flex; align-items:center; gap:0.6rem;">
            <span id="editModeBadge" class="status-pill" style="background:#8b5cf6; font-size:0.75rem; display:none;">✏️ EDIT MODE</span>
            <button id="editBtn" class="theme-toggle" onclick="toggleEditMode()" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.45rem 1rem; cursor:pointer; font-weight:600;">✏️ Edit Report</button>
            <button id="pdfBtn" class="theme-toggle" onclick="exportToPDF()" style="background: linear-gradient(135deg, #f43f5e, #e11d48); color: #fff; border: none; font-weight:700; padding:0.45rem 1rem; box-shadow: 0 4px 12px rgba(225,29,72,0.3); border-radius:6px; cursor:pointer;">📄 Export Report</button>
            <button id="publishBtn" class="theme-toggle" onclick="publishReport()" style="background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none; font-weight:700; padding:0.45rem 1rem; box-shadow: 0 4px 12px rgba(16,185,129,0.3); border-radius:6px; cursor:pointer;">🚀 Publish Report</button>
        </div>
    </div>

    <!-- Report Tab Navigation Header -->
    <nav class="report-nav glass-panel">
        <button class="nav-btn active" onclick="switchReportTab('rpt-summary', this)">📊 Executive Summary</button>
        <button class="nav-btn" onclick="switchReportTab('rpt-load', this)">👥 Load &amp; Capacity</button>
        <button class="nav-btn" onclick="switchReportTab('rpt-tx', this)">📋 Transaction Stats</button>
        <button class="nav-btn" onclick="switchReportTab('rpt-rt', this)">⏱️ Response Time Stats</button>
        <button class="nav-btn" onclick="switchReportTab('rpt-error', this)">🔴 SLA &amp; Errors</button>
        <button class="nav-btn" onclick="switchReportTab('rpt-infra', this)">🖥️ Infrastructure Monitoring</button>
    </nav>

    <!-- TAB 1: Executive Summary -->
    <div id="rpt-summary" class="tab-pane">
        
        <!-- 1. Test Config / Details -->
        <div class="section glass-panel">
            <h2>📋 Test Config / Details</h2>
            <table style="margin-bottom:1rem; font-size:0.85rem; width:100%;">
                <tbody>
                    <tr>
                        <td style="font-weight:700; width:18%;">Start Time</td>
                        <td style="width:32%;" contenteditable="true">{summary.get('start_time', execution_time)}</td>
                        <td style="font-weight:700; width:18%;">End Time</td>
                        <td style="width:32%;" contenteditable="true">{summary.get('end_time', execution_time)}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:700;">Test Name</td>
                        <td contenteditable="true">{jmx_name}</td>
                        <td style="font-weight:700;">Environment</td>
                        <td contenteditable="true">Staging</td>
                    </tr>
                    <tr>
                        <td style="font-weight:700;">Total Concurrent Users</td>
                        <td contenteditable="true">{users} users</td>
                        <td style="font-weight:700;">Duration</td>
                        <td contenteditable="true">{summary.get('duration_sec', 0):.0f} seconds</td>
                    </tr>
                    <tr>
                        <td style="font-weight:700;">Ramp-up</td>
                        <td contenteditable="true">Manual Input</td>
                        <td style="font-weight:700;">Release</td>
                        <td contenteditable="true">Release 1.0</td>
                    </tr>
                    <tr>
                        <td style="font-weight:700; vertical-align:top;">Test Objective</td>
                        <td colspan="3" contenteditable="true" style="line-height:1.5;">Validate system performance, throughput stability, response time SLA compliance, and error rates of {jmx_name} under peak load conditions.</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 2. Performance Scorecard & SLA Violation Grid (Grouped 3x3 Layout) -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <h2>📈 Performance Scorecard &amp; SLA Violation Summary</h2>
            
            <!-- Group 1: APDEX & User Experience Health (3 Cards) -->
            <div style="font-size:0.8rem; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; margin:0.8rem 0 0.5rem 0;">APDEX &amp; User Experience Health</div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem;">
                
                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">Overall APDEX Score</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{score_color}; margin:0.3rem 0;">{apdex_score_str}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">Target &ge; 0.85</div>
                </div>

                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);"># Transactions (Apdex &lt; .50)</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{'var(--red)' if apdex_below_50_count > 0 else 'var(--green)'}; margin:0.3rem 0;">{apdex_below_50_count}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">Poor performance rating</div>
                </div>

                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);"># Transactions (Apdex &lt; .25)</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{'var(--red)' if apdex_below_25_count > 0 else 'var(--green)'}; margin:0.3rem 0;">{apdex_below_25_count}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">Unacceptable rating</div>
                </div>

            </div>

            <!-- Group 2: Response Time SLA Violations (3 Cards) -->
            <div style="font-size:0.8rem; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; margin:1.2rem 0 0.5rem 0;">Response Time SLA Breaches</div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem;">

                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">RT SLA Violated (&gt; 100%)</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{'var(--red)' if sla_breach_100_count > 0 else 'var(--green)'}; margin:0.3rem 0;">{sla_breach_100_count}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">&gt; 2x SLA target</div>
                </div>

                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">RT SLA Violated (&gt; 50%)</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{'var(--red)' if sla_breach_50_count > 0 else 'var(--green)'}; margin:0.3rem 0;">{sla_breach_50_count}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">&gt; 1.5x SLA target</div>
                </div>

                <div class="kpi-card glass-panel" style="background:var(--surface1); border:1px solid var(--border); text-align:center; padding:1rem;">
                    <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted);">RT SLA Violated (&gt; 20%)</div>
                    <div class="kpi-value" style="font-size:1.8rem; font-weight:800; color:{'var(--yellow)' if sla_breach_20_count > 0 else 'var(--green)'}; margin:0.3rem 0;">{sla_breach_20_count}</div>
                    <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">&gt; 1.2x SLA target</div>
                </div>

            </div>
        </div>

        <!-- 3. Overall Performance Assessment Banner -->
        {exec_assessment_html}

        <!-- 4. High-Level Performance Observations Table -->
        {exec_obs_table_html}

        <!-- 6. Key Conclusions -->
        {exec_conclusions_html}

        <!-- 7. Priority Recommendations -->
        {exec_priority_recs_html}

        <!-- 8. Transaction Statistics & Iteration Summary Bar Chart -->
        <div class="section glass-panel" style="margin-top:1.25rem; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('tx-summary')" title="How to read this graph &amp; use filters">ℹ️</button>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; padding-right:2.5rem;">
                <div>
                    <h2 style="margin:0;">📊 Transaction Statistics &amp; Iteration Summary</h2>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Total vs passed and failed request sample counts per test script</p>
                </div>
                <div style="display:flex; gap:0.6rem; align-items:center; flex-wrap:wrap;">
                    <span style="font-size:0.75rem; font-weight:700; background:var(--surface2); border:1px solid var(--border); padding:0.3rem 0.75rem; border-radius:12px; color:var(--text);">Total Samples: <strong style="color:var(--accent);">{overall_samples:,}</strong></span>
                    <span style="font-size:0.75rem; font-weight:700; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:0.3rem 0.75rem; border-radius:12px; color:#10b981;">Pass: <strong>{overall_pass:,}</strong></span>
                    <span style="font-size:0.75rem; font-weight:700; background:{'rgba(239,68,68,0.1)' if overall_fail > 0 else 'var(--surface2)'}; border:1px solid {'rgba(239,68,68,0.3)' if overall_fail > 0 else 'var(--border)'}; padding:0.3rem 0.75rem; border-radius:12px; color:{'#ef4444' if overall_fail > 0 else 'var(--muted)'};">Fail: <strong>{overall_fail:,}</strong></span>
                </div>
            </div>
            
            <div style="position:relative; height:370px; width:100%;">
                <canvas id="chart-tx-summary-bar"></canvas>
            </div>
        </div>

        <!-- 5. Transaction & Sub-Transaction Response Time Breakdown (Hierarchical Multi-View Line Graphs) -->
        <div class="section glass-panel" style="margin-top:1.25rem; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('tx-rt-breakdown')" title="How to read this graph &amp; use filters">ℹ️</button>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; padding-right:2.5rem;">
                <div>
                    <h2 style="margin:0;">📈 Transaction &amp; Sub-Transaction Performance Line Graphs</h2>
                    <div style="font-size:0.78rem; color:var(--muted); margin-top:0.2rem;">
                        Hierarchical multi-metric line analysis. Filter by User Story, drill into child HTTP requests, and duplicate charts to compare different metrics simultaneously.
                    </div>
                </div>
                <div>
                    <button type="button" onclick="addTxRtChartView()" style="background:var(--accent); color:#ffffff; border:none; padding:0.45rem 0.9rem; border-radius:6px; font-size:0.8rem; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:0.4rem; box-shadow: 0 2px 6px rgba(99,102,241,0.3);">
                        <span>➕</span> Add / Duplicate Comparison Chart
                    </button>
                </div>
            </div>

            <!-- Dynamic Multi-Chart Vertical Container -->
            <div id="txRtChartsContainer" style="display:flex; flex-direction:column; gap:1.5rem; width:100%;">
            </div>
        </div>

        <!-- 6. SLA Deviation by Transaction (Executive Diagnostic Diverging Chart) -->
        <div class="section glass-panel" style="margin-top:1.25rem; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('sla-deviation')" title="How to read this graph &amp; use filters">ℹ️</button>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom:0.75rem; padding-right:2.5rem;">
                <div>
                    <h2 style="margin:0;">🎯 SLA Deviation by Transaction (% from Target SLA)</h2>
                    <div style="font-size:0.78rem; color:var(--muted); margin-top:0.2rem;">Diverging diagnostic chart normalized as (P90 Response Time &divide; Target SLA - 1) &times; 100%. Sorted by worst breach.</div>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <label for="usDevFilter" style="font-size:0.78rem; font-weight:700; color:var(--muted);">Filter User Story:</label>
                    <select id="usDevFilter" onchange="filterSlaDevByUs(this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.4rem 0.8rem; border-radius:6px; font-size:0.8rem; font-weight:600;">
                        {us_select_options_html}
                    </select>
                </div>
            </div>
            <div style="position:relative; height:340px; width:100%; margin-top:0.5rem;">
                <canvas id="chart-sla-deviation-exec"></canvas>
            </div>
        </div>

        <!-- 7. Error Distribution & Analysis (Pie/Donut Chart) -->
        <div class="section glass-panel" style="margin-top:1.25rem; border-left: 4px solid #ef4444; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('error-distribution')" title="How to read this graph &amp; use filters">ℹ️</button>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem; flex-wrap:wrap; gap:0.5rem; padding-right:2.5rem;">
                <div>
                    <h2 style="margin:0;">🔴 Error Distribution &amp; Analysis</h2>
                    <div style="font-size:0.78rem; color:var(--muted); margin-top:0.2rem;">Global Acceptable Error Rate Threshold: <strong style="color:var(--text);">{default_err}%</strong>. Distribution of errors by category / response code.</div>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:0.78rem; font-weight:700; background:{'rgba(239,68,68,0.12)' if display_total_errors > 0 else 'rgba(16,185,129,0.12)'}; border:1px solid {'rgba(239,68,68,0.3)' if display_total_errors > 0 else 'rgba(16,185,129,0.3)'}; padding:0.3rem 0.75rem; border-radius:12px; color:{'#ef4444' if display_total_errors > 0 else '#10b981'};">{display_total_errors} Total Errors</span>
                </div>
            </div>

            <div id="execErrorContent">
                <div style="display:flex; gap:1.5rem; align-items:flex-start; flex-wrap:wrap;">
                    <!-- Left: Donut Chart -->
                    <div style="flex-shrink:0; display:flex; flex-direction:column; align-items:center; gap:0.6rem;">
                        <div style="position:relative; width:200px; height:200px; display:flex; align-items:center; justify-content:center;">
                            <canvas id="chart-errors-exec" width="200" height="200"></canvas>
                            <div id="execErrorDonutCenter" style="position:absolute; text-align:center; pointer-events:none; width:100%;">
                                <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1;">{total_errors_all}</div>
                                <div style="font-size:0.65rem; font-weight:700; color:var(--muted); letter-spacing:0.04em; margin-top:0.2rem;">ERRORS</div>
                            </div>
                        </div>
                        <div id="execErrorDonutLegend" style="font-size:0.75rem; display:flex; flex-direction:column; gap:0.3rem; max-width:220px;"></div>
                    </div>

                    <!-- Right: Drill-Down Detail Panel -->
                    <div id="execErrorDrillPanel" style="flex:1; min-width:300px; min-height:200px; background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:1rem; display:flex; align-items:center; justify-content:center;">
                        <div style="text-align:center; color:var(--muted); font-size:0.85rem;">
                            <div style="font-size:2rem; margin-bottom:0.5rem; opacity:0.4;">🔍</div>
                            <div style="font-weight:600;">Click an error slice to view details</div>
                            <div style="font-size:0.75rem; margin-top:0.3rem;">Shows affected transactions, timing, and response data</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 8. Server Side Graphs -->
        <div class="section glass-panel" style="margin-top:1.25rem; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('server-side')" title="How to read this graph &amp; use filters">ℹ️</button>
            <h2 style="margin:0; padding-right:2.5rem;">🖥️ Server Side Graphs</h2>
            <div style="position:relative; height:260px; width:100%; margin-top:0.75rem;">
                <canvas id="chart-infra-exec"></canvas>
            </div>
        </div>

        <!-- Limitations Disclaimer -->
        <div style="font-size:0.75rem; color:var(--muted); margin-top: 1.5rem; text-align:center;">
            <strong>Test Limitations:</strong> Capacity estimates and performance thresholds are extrapolated from a single load profile. They represent observed pressure points, not certified maximums. Validated root-cause analysis requires infrastructure telemetry alignment.
        </div>
    </div>

    <!-- TAB 2: Load & Capacity Analysis -->
    <div id="rpt-load" class="tab-pane hidden">
        <!-- 1. Focused Capacity Summary KPI Strip (3 Cards) -->
        <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 1.25rem;">
            <div class="kpi-card glass-panel" style="text-align:center; padding:1.1rem;">
                <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted); text-transform:uppercase;">Target Concurrency</div>
                <div class="kpi-value" style="font-size:1.65rem; font-weight:800; color:var(--text); margin:0.25rem 0;">{total_tg_users} <small style="font-size:0.75rem; color:var(--muted);">VUs</small></div>
                <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">{len(tg_configs)} Configured User Journeys</div>
            </div>
            <div class="kpi-card glass-panel" style="text-align:center; padding:1.1rem;">
                <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted); text-transform:uppercase;">Peak Throughput</div>
                <div class="kpi-value" style="font-size:1.65rem; font-weight:800; color:var(--accent); margin:0.25rem 0;">{cap_peak_tps:.1f} <small style="font-size:0.75rem; color:var(--muted);">TPS</small></div>
                <div class="kpi-sub" style="font-size:0.75rem; color:var(--muted);">Sustained over {test_dur_sec}s test</div>
            </div>
            <div class="kpi-card glass-panel" style="text-align:center; padding:1.1rem;">
                <div class="kpi-label" style="font-size:0.72rem; font-weight:700; color:var(--muted); text-transform:uppercase;">Scaling Efficiency</div>
                <div class="kpi-value" style="font-size:1.65rem; font-weight:800; color:var(--text); margin:0.25rem 0;">{tp_scaling_text}</div>
                <div class="kpi-sub" style="font-size:0.75rem; font-weight:600;">{tp_scaling_eval}</div>
            </div>
        </div>

        <!-- 2. Hero Visual: Load vs Throughput (TPS vs VUs) -->
        <div class="chart-box glass-panel" style="position: relative; margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.6rem;">
                <div>
                    <h3 style="margin:0; font-size:1rem; font-weight:700;">📈 Load vs Throughput (TPS vs VUs)</h3>
                    <p style="font-size:0.73rem; color:var(--muted); margin:0.15rem 0 0 0;">Evaluates throughput scaling linearity as concurrency scales</p>
                </div>
                <span style="font-size:0.72rem; font-weight:700; background:var(--surface2); border:1px solid var(--border); padding:0.2rem 0.55rem; border-radius:10px; color:var(--accent);">{tp_scaling_text} Scaling</span>
            </div>
            <div style="position: relative; height: 280px; width: 100%;">
                <canvas id="chartLoadVsThroughput"></canvas>
            </div>
            <div style="font-size:0.75rem; color:var(--muted); background:var(--surface2); padding:0.5rem 0.75rem; border-radius:6px; margin-top:0.6rem;">
                💡 <strong>Throughput Evaluation:</strong> Sustained {cap_peak_tps:.1f} TPS at peak {total_tg_users} VUs ({tp_scaling_eval}).
            </div>
        </div>

        <!-- 3. Load Level Progression Matrix -->
        <div class="section glass-panel" style="margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                <div>
                    <h2 style="margin:0; font-size:1.05rem;">📊 Load Level Progression Matrix</h2>
                    <p style="font-size:0.75rem; color:var(--muted); margin:0.2rem 0 0 0;">System performance behavior across test execution stages</p>
                </div>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                <thead>
                    <tr style="background:var(--surface2); text-align:left; font-size:0.75rem; color:var(--muted);">
                        <th style="padding:0.5rem 0.75rem;">Load Stage</th>
                        <th style="text-align:center;">Active VUs</th>
                        <th style="text-align:center;">Throughput (TPS)</th>
                        <th style="text-align:center;">P95 Latency</th>
                        <th style="text-align:center;">Errors</th>
                        <th style="text-align:center;">Assessment</th>
                    </tr>
                </thead>
                <tbody>
                    {staging_rows_html}
                </tbody>
            </table>
        </div>

        <!-- 4. User Journey Concurrency Allocation & Capacity -->
        <div class="section glass-panel" style="margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.85rem;">
                <div>
                    <h2 style="margin:0; font-size:1.15rem; font-weight:800; display:flex; align-items:center; gap:0.5rem;">
                        👥 User Journey Concurrency Allocation &amp; Capacity
                    </h2>
                    <p style="font-size:0.8rem; color:var(--muted); margin:0.25rem 0 0 0;">Journey-level concurrency allocation, throughput generation, and capacity limit classification</p>
                </div>
                <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.25rem 0.65rem; border-radius:12px;">{len(tg_configs)} Configured Journeys</span>
            </div>
            <div style="overflow-x:auto; border-radius:8px; border:1px solid var(--border);">
                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                    <thead>
                        <tr style="background:var(--surface2); text-align:left;">
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem;">User Journey</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; text-align:center; width:13%;">Concurrency Allocation</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; text-align:center; width:12%;">Throughput</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; text-align:center; width:12%;">P90 Latency</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; text-align:center; width:12%;">Error Rate</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; width:22%;">SLA Compliance</th>
                            <th style="padding:0.65rem 0.8rem; font-weight:700; font-size:0.78rem; text-align:center; width:15%;">Capacity Limit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tg_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 3: Transaction Stats -->
    <div id="rpt-tx" class="tab-pane hidden">
        {tab_tx_panel_html}
        
        <div class="chart-box glass-panel" style="margin-bottom: 1.5rem; padding: 1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem; gap: 0.5rem; flex-wrap:wrap;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:800; display:flex; align-items:center; gap:0.4rem;">
                        📊 Throughput &amp; Errors
                    </h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Request execution rate and failure distribution over test timeline</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <select id="tpSelect" onchange="updateTpChart(this.value)" style="max-width: 260px; background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.35rem 0.65rem; font-size:0.78rem; font-weight:600; outline:none; cursor:pointer; text-overflow: ellipsis; overflow: hidden;">
                        <option value="ALL">All Transactions (Overall)</option>
                        {tx_options_html}
                    </select>
                    <button class="chart-info-btn" onclick="openGraphModal('throughput')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>

            <!-- 4 Compact KPI Chips ABOVE the Chart -->
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:0.75rem; margin-bottom:1rem;">
                <div class="glass-panel" style="background:var(--surface1); border:1px solid var(--border); padding:0.75rem; text-align:center; border-radius:8px;">
                    <div style="font-size:0.7rem; font-weight:700; color:var(--muted); text-transform:uppercase;">AVG THROUGHPUT</div>
                    <div id="tpKpiAvg" style="font-size:1.25rem; font-weight:800; color:var(--text); margin-top:0.2rem;">{tp_obs.get('avg_tp', round(summary.get('throughput', 0))):.0f} req/s</div>
                </div>
                <div class="glass-panel" style="background:var(--surface1); border:1px solid var(--border); padding:0.75rem; text-align:center; border-radius:8px;">
                    <div style="font-size:0.7rem; font-weight:700; color:var(--muted); text-transform:uppercase;">PEAK THROUGHPUT</div>
                    <div id="tpKpiPeak" style="font-size:1.25rem; font-weight:800; color:var(--accent); margin-top:0.2rem;">{tp_obs.get('peak_tp', 0):.0f} req/s</div>
                </div>
                <div class="glass-panel" style="background:var(--surface1); border:1px solid var(--border); padding:0.75rem; text-align:center; border-radius:8px;">
                    <div style="font-size:0.7rem; font-weight:700; color:var(--muted); text-transform:uppercase;">ERROR RATE</div>
                    <div id="tpKpiErr" style="font-size:1.25rem; font-weight:800; color:{'var(--green)' if tp_obs.get('error_rate', 0) == 0 else 'var(--red)'}; margin-top:0.2rem;">{tp_obs.get('error_rate', 0):.2f}%</div>
                </div>
                <div class="glass-panel" style="background:var(--surface1); border:1px solid var(--border); padding:0.75rem; text-align:center; border-radius:8px;">
                    <div style="font-size:0.7rem; font-weight:700; color:var(--muted); text-transform:uppercase;">END TREND / VARIATION</div>
                    <div id="tpKpiTrend" style="font-size:1.15rem; font-weight:800; color:{tp_obs.get('trend_color', 'var(--text)')}; margin-top:0.2rem;">{tp_obs.get('trend_label', 'Stable')}</div>
                </div>
            </div>

            <!-- Throughput Chart (Wider, Height 240px) -->
            <div style="position: relative; height: 240px; width: 100%; margin-bottom: 0.5rem;">
                <canvas id="tpChart"></canvas>
            </div>

            <!-- Standardized Contextual AI Performance Observation Card -->
            {tp_observation_html}
        </div>

        <div class="section glass-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8rem; margin-bottom:0.8rem;">
                <h2 style="margin:0;">📋 Per-Transaction Breakdown &amp; SLA Targets</h2>
                <div style="display:flex; align-items:center; gap:0.8rem; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:0.4rem;">
                        <label style="font-size:0.8rem; font-weight:600; color:var(--muted); white-space:nowrap;">⏱️ Unit:</label>
                        <select id="txUnitSelector" onchange="toggleTxTableUnits(this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.35rem 0.6rem; font-size:0.8rem; font-weight:600; outline:none; cursor:pointer;">
                            <option value="ms" selected>Milliseconds (ms)</option>
                            <option value="s">Seconds (s)</option>
                        </select>
                    </div>
                    {'<div style="display:flex; align-items:center; gap:0.4rem;"><label style="font-size:0.8rem; font-weight:600; color:var(--muted); white-space:nowrap;">🔧 Thread Group:</label><select id="tgFilterSelect" onchange="filterByThreadGroup(this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.35rem 0.7rem; font-size:0.8rem; outline:none; cursor:pointer; min-width:200px;">' + tg_filter_options + '</select></div>' if tg_filter_options else ''}
                </div>
            </div>
            <table id="txBreakdownTable">
                <thead><tr>
                    <th>Transaction / Request</th>
                    <th>Samples</th>
                    <th>Apdex</th>
                    <th id="th-tx-avg">Avg RT (ms)</th>
                    <th id="th-tx-p90">P90 (ms)</th>
                    <th id="th-tx-min">Min (ms)</th>
                    <th id="th-tx-max">Max (ms)</th>
                    <th>Error Rate</th>
                    <th id="th-tx-sla">RT SLA (ms)</th>
                    <th>Deviation %</th>
                    <th>SLA Status</th>
                </tr></thead>
                <tbody>{labels_rows}</tbody>
            </table>
            <script>
            function toggleTreeChildren(btn, clsId) {{
                var isExpanded = btn.getAttribute('data-expanded') === 'true';
                if (isExpanded) {{
                    // Collapse: hide all descendants with clsId
                    var rows = document.getElementsByClassName(clsId);
                    for (var i = 0; i < rows.length; i++) {{
                        rows[i].style.display = 'none';
                    }}
                    // Also reset any expanded child buttons within those rows
                    for (var i = 0; i < rows.length; i++) {{
                        var nestedBtns = rows[i].querySelectorAll('.tree-toggle-btn[data-expanded="true"]');
                        nestedBtns.forEach(function(nb) {{
                            nb.setAttribute('data-expanded', 'false');
                            nb.textContent = '▶';
                        }});
                    }}
                    btn.setAttribute('data-expanded', 'false');
                    btn.textContent = '▶';
                }} else {{
                    // Expand: show ONLY direct children (rows with data-parent-cls === clsId)
                    var rows = document.querySelectorAll('tr[data-parent-cls="' + clsId + '"]');
                    for (var i = 0; i < rows.length; i++) {{
                        var currentTgFilter = document.getElementById('tgFilterSelect') ? document.getElementById('tgFilterSelect').value : 'ALL';
                        var rowTg = rows[i].getAttribute('data-tg');
                        if (currentTgFilter === 'ALL' || !rowTg || rowTg === currentTgFilter) {{
                            rows[i].style.display = 'table-row';
                        }}
                    }}
                    btn.setAttribute('data-expanded', 'true');
                    btn.textContent = '▼';
                }}
            }}
            function filterByThreadGroup(val) {{
                var table = document.getElementById('txBreakdownTable');
                if (!table) return;
                var rows = table.querySelectorAll('tbody tr');
                rows.forEach(function(row) {{
                    var tg = row.getAttribute('data-tg');
                    var isTgMatch = (val === 'ALL' || !tg || tg === val);
                    if (!isTgMatch) {{
                        row.style.display = 'none';
                    }} else {{
                        // Show thread group header rows and top-level depth 0 rows
                        if (row.classList.contains('tg-header-row') || row.getAttribute('data-depth') === '0') {{
                            row.style.display = 'table-row';
                        }} else {{
                            // For child rows, keep hidden by default unless parent is expanded
                            row.style.display = 'none';
                        }}
                    }}
                }});
                // Reset all toggle buttons to collapsed (▶)
                var allBtns = table.querySelectorAll('.tree-toggle-btn');
                allBtns.forEach(function(btn) {{
                    btn.setAttribute('data-expanded', 'false');
                    btn.textContent = '▶';
                }});
            }}
            function toggleTxTableUnits(unit) {{
                var isSec = (unit === 's');
                var thAvg = document.getElementById('th-tx-avg');
                var thP90 = document.getElementById('th-tx-p90');
                var thMin = document.getElementById('th-tx-min');
                var thMax = document.getElementById('th-tx-max');
                var thSla = document.getElementById('th-tx-sla');
                if (thAvg) thAvg.textContent = isSec ? 'Avg RT (s)' : 'Avg RT (ms)';
                if (thP90) thP90.textContent = isSec ? 'P90 (s)' : 'P90 (ms)';
                if (thMin) thMin.textContent = isSec ? 'Min (s)' : 'Min (ms)';
                if (thMax) thMax.textContent = isSec ? 'Max (s)' : 'Max (ms)';
                if (thSla) thSla.textContent = isSec ? 'RT SLA (s)' : 'RT SLA (ms)';

                var cells = document.querySelectorAll('#txBreakdownTable .tx-rt-cell');
                cells.forEach(function(cell) {{
                    var rawMs = parseFloat(cell.getAttribute('data-ms'));
                    if (isNaN(rawMs)) return;
                    var valEl = cell.querySelector('.tx-rt-val') || cell;
                    if (isSec) {{
                        var secVal = rawMs / 1000.0;
                        valEl.textContent = secVal >= 10 ? secVal.toFixed(1) : secVal.toFixed(2);
                    }} else {{
                        valEl.textContent = Math.round(rawMs).toString();
                    }}
                }});
            }}
            </script>
        </div>
    </div>

    <!-- TAB 4: Response Time Stats -->
    <div id="rpt-rt" class="tab-pane hidden">
        {tab_rt_panel_html}
        <div class="kpi-grid">
            <div class="kpi-card glass-panel"><div class="kpi-label">Avg Response Time</div><div class="kpi-value {'pass' if avg_rt <= 500 else 'warn' if avg_rt <= 2000 else 'fail'}">{avg_rt:.0f}<span style="font-size:0.9rem"> ms</span></div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">P95 Response</div><div class="kpi-value">{summary.get('p95', 0)}<span style="font-size:0.9rem"> ms</span></div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">P99 Response</div><div class="kpi-value">{summary.get('p99', 0)}<span style="font-size:0.9rem"> ms</span></div></div>
        </div>

        <div class="chart-box glass-panel" style="margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.8rem; gap: 0.5rem;">
                <h3 style="margin:0; white-space: nowrap;">📈 Response Time Over Time</h3>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <select id="rtSelect" onchange="updateRtChart(this.value)" style="max-width: 240px; background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.3rem 0.6rem; font-size:0.78rem; outline:none; cursor:pointer; text-overflow: ellipsis; overflow: hidden;">
                        <option value="ALL">All Transactions (Overall)</option>
                        {tx_options_html}
                    </select>
                    <button class="chart-info-btn" onclick="openGraphModal('rt-over-time')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>
            <div style="position: relative; height: 260px; width: 100%;">
                <canvas id="rtChart"></canvas>
            </div>
            {rt_observation_html}
        </div>

        <!-- Critical Transaction Response Time Card -->
        <div class="chart-box glass-panel" style="position: relative; min-height: 380px; margin-bottom: 1.5rem; border-left: 4px solid var(--red); padding: 1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">🔥 Critical Transaction Response Time</h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Response time trend for transactions marked as critical</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <button class="chart-info-btn" onclick="openGraphModal('critical-tx')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>

            <!-- Mini Summary KPIs -->
            <div style="display:flex; gap:1.25rem; flex-wrap:wrap; background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.6rem 1rem; margin-bottom:0.85rem; font-size:0.8rem;">
                <div><span style="color:var(--muted);">Critical:</span> <strong>{crit_tx_count}</strong></div>
                <div><span style="color:var(--muted);">Avg Response:</span> <strong>{crit_avg_rt} ms</strong></div>
                <div><span style="color:var(--muted);">P95 Response:</span> <strong>{crit_p95_rt} ms</strong></div>
                <div><span style="color:var(--muted);">SLA Breaches:</span> <strong style="color:{'var(--red)' if crit_breaches > 0 else 'var(--green)'};">{crit_breaches}</strong></div>
                <div><span style="color:var(--muted);">Max Response:</span> <strong>{crit_max_rt} ms</strong></div>
            </div>

            <!-- Interactive Transaction Toggle Chips -->
            <div id="crit-tx-chip-container" style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-bottom:0.85rem;"></div>

            <!-- Substantially Wider Canvas Area -->
            <div style="position: relative; height: 320px; width: 100%;">
                <canvas id="critTxChart"></canvas>
            </div>
        </div>

        <div class="chart-grid">
            <div class="chart-box glass-panel" style="position: relative; min-height: 280px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                    <h3 style="margin:0;">📊 Response Time Distribution</h3>
                    <button class="chart-info-btn" onclick="openGraphModal('rt-hist')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 220px; width: 100%;">
                    <canvas id="histChart"></canvas>
                </div>
            </div>
            <div class="chart-box glass-panel" style="position: relative; min-height: 280px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                    <h3 style="margin:0;">🏷️ Top Transactions by Response Time</h3>
                    <button class="chart-info-btn" onclick="openGraphModal('top-tx')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 220px; width: 100%;">
                    <canvas id="txChart"></canvas>
                </div>
            </div>
        </div>

        <div class="section glass-panel" style="margin-top: 1.5rem;">
            <h2>🚨 Critical Transactions & Deviations</h2>
            <p style="font-size:0.8rem; color:var(--muted); margin:-0.5rem 0 1rem 0;"><i>Criteria: Transactions with SLA deviations > 30% or Error SLA breaches.</i></p>
            {crit_tx_table_html}
        </div>
    </div>

    <!-- TAB 5: Error Statistics -->
    <div id="rpt-error" class="tab-pane hidden">
        {tab_error_panel_html}
        <div class="kpi-grid">
            <div class="kpi-card glass-panel"><div class="kpi-label">Error Rate</div><div class="kpi-value {'pass' if error_rate <= 1 else 'warn' if error_rate <= 5 else 'fail'}">{error_rate:.2f}<span style="font-size:0.9rem">%</span></div><div class="kpi-sub">{summary.get('tc_errors', summary.get('errors', 0))} transaction failures</div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">SLA Breaches</div><div class="kpi-value" style="color: {'var(--red)' if tx_breached_count > 0 else 'var(--green)'};">{tx_breached_count}</div><div class="kpi-sub">Breached RT or Error SLA</div></div>
        </div>

        <!-- SLA Deviation & Breach Severity Card -->
        <div class="chart-box glass-panel" style="position: relative; min-height: 300px; margin-bottom: 1.5rem; padding: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 1.25rem;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">SLA Deviation &amp; Breach Severity</h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Distribution of transactions by SLA utilization</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:0.78rem; font-weight:700; background:var(--surface2); border:1px solid var(--border); padding:0.3rem 0.75rem; border-radius:12px; color:var(--text);">{total_tx_count} Transactions</span>
                    <button class="chart-info-btn" onclick="openGraphModal('sla-donut')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>

            <div style="display:flex; align-items:center; gap:2rem; flex-wrap:wrap; margin-bottom: 1rem;">
                <!-- Left Donut with Center Percentage Overlay -->
                <div style="position: relative; width: 160px; height: 160px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                    <canvas id="slaDonut" width="160" height="160"></canvas>
                    <div style="position: absolute; text-align: center; pointer-events: none; width: 100%;">
                        <div style="font-size: 1.4rem; font-weight: 800; color: {'#10b981' if sla_compliance_pct >= 85 else '#f59e0b' if sla_compliance_pct >= 70 else '#ef4444'}; line-height: 1;">{sla_compliance_pct}%</div>
                        <div style="font-size: 0.65rem; font-weight: 700; color: var(--muted); letter-spacing: 0.04em; margin-top: 0.25rem;">SLA COMPLIANCE</div>
                    </div>
                </div>

                <!-- Right Metric Cards Grid -->
                <div style="flex: 1; min-width: 280px; display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.85rem;">
                    <!-- Passed Card -->
                    <div style="background: rgba(16,185,129,0.07); border: 1px solid rgba(16,185,129,0.25); border-radius: 10px; padding: 0.85rem 1rem;">
                        <div style="display:flex; align-items:center; gap:0.4rem; font-size:0.75rem; font-weight:700; color:#10b981; margin-bottom:0.3rem;">● PASSED</div>
                        <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1.1;">{tx_under_sla}</div>
                        <div style="font-size:0.75rem; font-weight:600; color:#10b981; margin-top:0.1rem;">{passed_pct}%</div>
                        <div style="font-size:0.7rem; color:var(--muted); margin-top:0.2rem;">Under SLA</div>
                    </div>

                    <!-- Minor Card -->
                    <div style="background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.25); border-radius: 10px; padding: 0.85rem 1rem;">
                        <div style="display:flex; align-items:center; gap:0.4rem; font-size:0.75rem; font-weight:700; color:#f59e0b; margin-bottom:0.3rem;">● MINOR</div>
                        <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1.1;">{sla_minor_count}</div>
                        <div style="font-size:0.75rem; font-weight:600; color:#f59e0b; margin-top:0.1rem;">{minor_pct}%</div>
                        <div style="font-size:0.7rem; color:var(--muted); margin-top:0.2rem;">{sla_minor_count} breaches</div>
                    </div>

                    <!-- Moderate Card -->
                    <div style="background: rgba(249,115,22,0.07); border: 1px solid rgba(249,115,22,0.25); border-radius: 10px; padding: 0.85rem 1rem;">
                        <div style="display:flex; align-items:center; gap:0.4rem; font-size:0.75rem; font-weight:700; color:#f97316; margin-bottom:0.3rem;">● MODERATE</div>
                        <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1.1;">{sla_mod_count}</div>
                        <div style="font-size:0.75rem; font-weight:600; color:#f97316; margin-top:0.1rem;">{mod_pct}%</div>
                        <div style="font-size:0.7rem; color:var(--muted); margin-top:0.2rem;">{sla_mod_count} breaches</div>
                    </div>

                    <!-- Critical Card -->
                    <div style="background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 0.85rem 1rem;">
                        <div style="display:flex; align-items:center; gap:0.4rem; font-size:0.75rem; font-weight:700; color:#ef4444; margin-bottom:0.3rem;">● CRITICAL</div>
                        <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1.1;">{sla_crit_count}</div>
                        <div style="font-size:0.75rem; font-weight:600; color:#ef4444; margin-top:0.1rem;">{crit_pct}%</div>
                        <div style="font-size:0.7rem; color:var(--muted); margin-top:0.2rem;">{'None' if sla_crit_count == 0 else f'{sla_crit_count} breaches'}</div>
                    </div>
                </div>
            </div>

            <!-- Bottom Threshold Legend -->
            <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap; font-size:0.75rem; color:var(--muted); border-top:1px solid var(--border); padding-top:0.8rem;">
                <span><strong style="color:#10b981;">●</strong> Under SLA</span>
                <span><strong style="color:#f59e0b;">●</strong> &gt;100% SLA</span>
                <span><strong style="color:#f97316;">●</strong> &gt;200% SLA</span>
                <span><strong style="color:#ef4444;">●</strong> &gt;300% SLA</span>
            </div>
        </div>

        <div class="chart-box glass-panel" style="position: relative; min-height: 280px; margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                <h3 style="margin:0;">🔴 Error Rate by Transaction (%)</h3>
                <button class="chart-info-btn" onclick="openGraphModal('error-rate-tx')" title="How to read this graph &amp; use filters">ℹ️</button>
            </div>
            <div style="position: relative; height: 260px; width: 100%;">
                <canvas id="errChart"></canvas>
            </div>
        </div>

        <!-- Row 3: Error Analysis Donut (Interactive Drill-Down) -->
        <div class="chart-box glass-panel" style="position: relative; min-height: 380px; margin-bottom: 1.5rem; padding: 1.25rem; border-left: 4px solid #ef4444;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">Error Distribution &amp; Analysis</h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Global Acceptable Error Rate Threshold: <strong style="color:var(--text);">{default_err}%</strong>. Click any error type in the donut to drill into affected transactions.</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:0.78rem; font-weight:700; background:{'rgba(239,68,68,0.12)' if display_total_errors > 0 else 'rgba(16,185,129,0.12)'}; border:1px solid {'rgba(239,68,68,0.3)' if display_total_errors > 0 else 'rgba(16,185,129,0.3)'}; padding:0.3rem 0.75rem; border-radius:12px; color:{'#ef4444' if display_total_errors > 0 else '#10b981'};">{display_total_errors} Total Errors</span>
                    <button class="chart-info-btn" onclick="openGraphModal('error-distribution')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>

            <div style="display:flex; gap:1.5rem; align-items:flex-start; flex-wrap:wrap;">
                <!-- Left: Donut Chart -->
                <div style="flex-shrink:0; display:flex; flex-direction:column; align-items:center; gap:0.6rem;">
                    <div style="position:relative; width:200px; height:200px; display:flex; align-items:center; justify-content:center;">
                        <canvas id="errorDonutChart" width="200" height="200"></canvas>
                        <div id="errorDonutCenter" style="position:absolute; text-align:center; pointer-events:none; width:100%;">
                            <div style="font-size:1.5rem; font-weight:800; color:var(--text); line-height:1;">{total_errors_all}</div>
                            <div style="font-size:0.65rem; font-weight:700; color:var(--muted); letter-spacing:0.04em; margin-top:0.2rem;">ERRORS</div>
                        </div>
                    </div>
                    <!-- Legend below donut -->
                    <div id="errorDonutLegend" style="font-size:0.75rem; display:flex; flex-direction:column; gap:0.3rem; max-width:220px;"></div>
                </div>

                <!-- Right: Drill-Down Detail Panel -->
                <div id="errorDrillPanel" style="flex:1; min-width:300px; min-height:200px; background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:1rem; display:flex; align-items:center; justify-content:center;">
                    <div style="text-align:center; color:var(--muted); font-size:0.85rem;">
                        <div style="font-size:2rem; margin-bottom:0.5rem; opacity:0.4;">🔍</div>
                        <div style="font-weight:600;">Click an error slice to view details</div>
                        <div style="font-size:0.75rem; margin-top:0.3rem;">Shows affected transactions, timing, and response data</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section glass-panel">
            <h2>🚨 SLA Breach Analysis &amp; Corresponding HTTP Requests</h2>
            {sla_breaches_html}
        </div>
    </div>

    <!-- TAB 6: Infrastructure Monitoring -->
    <div id="rpt-infra" class="tab-pane hidden">
        {tab_infra_panel_html}
        
        <!-- 1. Top Health KPI Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
            <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #f59e0b;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK CPU UTILIZATION</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_cpu_val}%</div>
                <div style="font-size: 0.7rem; color: {'#ef4444' if peak_cpu_val >= 80 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ High CPU Pressure' if peak_cpu_val >= 80 else 'Healthy'}</div>
            </div>

            <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #3b82f6;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK MEMORY UTILIZATION</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_mem_val}%</div>
                <div style="font-size: 0.7rem; color: {'#ef4444' if peak_mem_val >= 80 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ High Memory Pressure' if peak_mem_val >= 80 else 'Healthy'}</div>
            </div>

            <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #8b5cf6;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK DISK QUEUE DEPTH</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_disk_q_val}</div>
                <div style="font-size: 0.7rem; color: {'#ef4444' if peak_disk_q_val >= 5.0 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ Storage Contention' if peak_disk_q_val >= 5.0 else 'Optimal I/O'}</div>
            </div>

            <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #10b981;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">SYSTEM AVAILABILITY</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{min_avail_val}%</div>
                <div style="font-size: 0.7rem; color: {'#10b981' if min_avail_val >= 99.5 else '#ef4444'}; margin-top: 0.2rem;">{'Operational SLA' if min_avail_val >= 99.5 else 'Degraded During Peak'}</div>
            </div>
        </div>

        <!-- 2. Main Resource Utilization (CPU & Memory) - Full Width -->
        <div class="chart-box glass-panel" style="position: relative; min-height: 380px; margin-bottom: 1.5rem; padding: 1.25rem; {azure_section_style}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">🖥️ Azure Resource Utilization (CPU &amp; Memory)</h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Dual-line time series tracking host resource pressure thresholds</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:0.75rem; font-weight:600; background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); padding:0.25rem 0.6rem; border-radius:12px;">Threshold Bands: 80% / 90%</span>
                    <button class="chart-info-btn" onclick="openGraphModal('azure-cpu-mem')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>
            
            <div style="position: relative; height: 310px; width: 100%;">
                <canvas id="azChart"></canvas>
            </div>
            
            <p style="margin-top:0.8rem; font-size:0.78rem; color:var(--muted); background:var(--surface2); padding:0.5rem 0.8rem; border-radius:6px; border-left:3px solid var(--accent);">
                <strong>Conclusion:</strong> The server experienced a significant resource utilization spike, with CPU reaching {peak_cpu_val}% and memory reaching {peak_mem_val}%, indicating elevated host-level contention.
            </p>
            {infra_observation_html}
        </div>

        <!-- 3. Dual Charts Grid: Workload vs Resource & Performance Impact -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Workload vs Resource (Throughput vs CPU) -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">📈 Workload vs CPU Utilization</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Aligning JMeter request throughput against Azure host CPU %</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('workload-cpu')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="workloadCpuChart"></canvas>
                </div>
            </div>

            <!-- Performance Impact (Throughput vs Response Time) -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">⚡ Throughput vs Response Time</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Analyzing capacity limits as request load increases</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('tp-rt-impact')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="tpRtChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 4. Storage & Network Subsystem Grid -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Storage I/O & Queue Depth -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">💾 Disk I/O &amp; Queue Contention</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Disk Read/Write throughput (MB/s) vs Disk Queue Depth</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('disk-io')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="diskChart"></canvas>
                </div>
            </div>

            <!-- Network Throughput -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">🌐 Network Throughput (In/Out)</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Inbound and Outbound network data transfer rate</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('network-tp')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="netChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 5. Correlation Matrix & Event Timeline Grid -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Correlation Matrix Table -->
            <div class="chart-box glass-panel" style="padding: 1.2rem;">
                <h3 style="margin:0; font-size:1rem; font-weight:700; margin-bottom: 0.3rem;">📊 Infrastructure Correlation Matrix</h3>
                <p style="font-size:0.75rem; color:var(--muted); margin-bottom: 0.8rem;">Pearson correlation coefficients (r) dynamically calculated from run telemetry</p>
                
                <table style="width:100%; border-collapse:collapse; font-size:0.78rem; text-align:center;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border); background:var(--surface2);">
                            <th style="padding:0.4rem; text-align:left;">Signal</th>
                            <th style="padding:0.4rem;">CPU</th>
                            <th style="padding:0.4rem;">Memory</th>
                            <th style="padding:0.4rem;">Throughput</th>
                            <th style="padding:0.4rem;">Resp Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">CPU %</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_mem) >= 0.7 else 'var(--text)'};">{r_cpu_mem:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_tp) >= 0.7 else 'var(--text)'};">{r_cpu_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_rt) >= 0.7 else 'var(--text)'};">{r_cpu_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Memory %</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_mem) >= 0.7 else 'var(--text)'};">{r_cpu_mem:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_tp) >= 0.7 else 'var(--text)'};">{r_mem_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_rt) >= 0.7 else 'var(--text)'};">{r_mem_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Throughput</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_tp) >= 0.7 else 'var(--text)'};">{r_cpu_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_tp) >= 0.7 else 'var(--text)'};">{r_mem_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_tp_rt) >= 0.7 else 'var(--text)'}; background:rgba(16,185,129,0.15);">{r_tp_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Resp Time</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_rt) >= 0.7 else 'var(--text)'};">{r_cpu_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_rt) >= 0.7 else 'var(--text)'};">{r_mem_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_tp_rt) >= 0.7 else 'var(--text)'}; background:rgba(16,185,129,0.15);">{r_tp_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                        </tr>
                    </tbody>
                </table>
                <p style="font-size:0.7rem; color:var(--muted); margin-top:0.6rem;">💡 <em>Calculated correlation between request volume and response latency: <strong>r = {r_tp_rt:.2f}</strong>.</em></p>
            </div>

            <!-- Chronological Event Progression Timeline -->
            <div class="chart-box glass-panel" style="padding: 1.2rem;">
                <h3 style="margin:0; font-size:1rem; font-weight:700; margin-bottom: 0.3rem;">⏱️ Performance Incident Timeline</h3>
                <p style="font-size:0.75rem; color:var(--muted); margin-bottom: 0.8rem;">Sequential degradation events during test execution</p>
                
                <div style="display:flex; flex-direction:column; gap:0.6rem; font-size:0.78rem;">
                    {timeline_html}
                </div>
            </div>
        </div>

        <!-- 6. AI Infrastructure Diagnostic Summary Card -->
        <div class="chart-box glass-panel" style="padding: 1.25rem; border-left: 4px solid var(--accent); margin-bottom: 1.5rem;">
            <h3 style="margin:0; font-size:1.05rem; font-weight:700; display:flex; align-items:center; gap:0.5rem;">
                🧠 Infrastructure Diagnostic Analysis
            </h3>
            
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-top:0.85rem; font-size:0.78rem;">
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#ef4444; margin-bottom:0.2rem;">🔴 Primary Signal</div>
                    <p style="margin:0; color:var(--text);">CPU utilization reached <strong>{peak_cpu_val}%</strong> peak pressure during high-throughput interval.</p>
                </div>
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#f59e0b; margin-bottom:0.2rem;">Associated Signals</div>
                    <p style="margin:0; color:var(--text);">Memory reached <strong>{peak_mem_val}%</strong>, Disk Queue depth reached <strong>{peak_disk_q_val}</strong>, and SLA breaches occurred.</p>
                </div>
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#3b82f6; margin-bottom:0.2rem;">🔍 Likely Root Cause</div>
                    <p style="margin:0; color:var(--text);">Workload-driven host CPU &amp; memory contention under concurrent user load.</p>
                </div>
            </div>
        </div>

        <!-- Correlation Findings List -->
        <div class="section glass-panel">
            <h2>🔗 Client ↔ Server Correlation Findings</h2>
            {corr_html}
        </div>
    </div>

    <!-- Methodology -->
    <div class="section glass-panel" style="margin-bottom: 2rem;">
        <h2>📐 Calculation Methodology</h2>
        <div style="font-size: 0.85rem; color: var(--text); display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div>
                <h4 style="margin-bottom:0.3rem;">SLA Deviation %</h4>
                <p style="margin-top:0; color:var(--muted);">Calculates how far actual P90 exceeds target P90. <br/><code>Deviation = ((Actual P90 - Target P90) / Target P90) * 100</code></p>
                
                <h4 style="margin-bottom:0.3rem;">Apdex (Application Performance Index)</h4>
                <p style="margin-top:0; color:var(--muted);">Measures user satisfaction. Evaluates response times against target T and 4T boundaries, deducting for errors. <br/><code>Score = (Satisfied + (Tolerating / 2)) / Total</code></p>
            </div>
            <div>
                <h4 style="margin-bottom:0.3rem;">Response Time Percentiles (P90/P95/P99)</h4>
                <p style="margin-top:0; color:var(--muted);">The time within which N% of requests were completed. Used instead of averages to highlight tail latency and true user experience.</p>
                
                <h4 style="margin-bottom:0.3rem;">Error Rate</h4>
                <p style="margin-top:0; color:var(--muted);">Percentage of total transactions that failed application or HTTP validation assertions.</p>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="report-footer">
        ⚡ Generated by <strong>PerfPilot</strong> &nbsp;|&nbsp; {execution_time} &nbsp;|&nbsp; Run ID: {run_id}
    </div>
    <!-- Finding Drawer -->
    <div id="findingDrawerOverlay" onclick="closeFinding()"></div>
    <div id="findingDrawer">
        <button class="drawer-close" onclick="closeFinding()" style="position:absolute; top:1rem; right:1rem;">&times;</button>
        <div id="drawerContent"></div>
    </div>

    <!-- Graph Info Modal -->
    <div id="graphModalOverlay" onclick="closeGraphModal(event)">
        <div id="graphInfoModal" onclick="event.stopPropagation()">
            <div class="graph-modal-header">
                <h3 class="graph-modal-title" id="graphModalTitle">📊 Graph Guide</h3>
                <button class="graph-modal-close" onclick="closeGraphModal()">&times;</button>
            </div>
            <div id="graphModalBody"></div>
        </div>
    </div>
</div>

<script>
    function switchReportTab(tabId, btn) {{
        document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
        const pane = document.getElementById(tabId);
        if (pane) pane.classList.remove('hidden');
        if (btn) btn.classList.add('active');
        // Force immediate resize on all Chart.js instances so hidden canvases get full 100% width
        for (let id in Chart.instances) {{
            Chart.instances[id].resize();
        }}
        window.dispatchEvent(new Event('resize'));
    }}

    function toggleTheme() {{
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('jmeter_ai_theme', isDark ? 'dark' : 'light');
    }}

    let activeTabBeforePrint = 'rpt-summary';

    function exportToPDF() {{
        // Remember current tab
        const activeNav = document.querySelector('.nav-btn.active');
        if (activeNav) {{
            const match = activeNav.getAttribute('onclick').match(/'([^']+)'/);
            if (match) activeTabBeforePrint = match[1];
        }}

        // Reveal all tabs so Chart.js canvases get real dimensions instead of 0x0
        document.querySelectorAll('.tab-pane').forEach(t => t.classList.remove('hidden'));
        
        // Force Chart.js to immediately resize and redraw on the screen
        for (let id in Chart.instances) {{
            Chart.instances[id].resize();
        }}

        // Wait for rendering frame to complete before launching print dialog
        setTimeout(() => {{
            window.print();
        }}, 400);
    }}

    // Restore original tab state after print dialog closes
    window.addEventListener('afterprint', () => {{
        document.querySelectorAll('.tab-pane').forEach(t => {{
            if (t.id !== activeTabBeforePrint) t.classList.add('hidden');
        }});
    }});

    async function publishReport() {{
        if (!confirm("Are you sure you want to publish this report?\\n\\nThis will remove edit mode and save a permanent, clean, non-editable published report file.")) return;

        const editBadge = document.getElementById('editModeBadge');
        const publishBtn = document.getElementById('publishBtn');
        if (editBadge) editBadge.style.display = 'none';
        if (publishBtn) publishBtn.style.display = 'none';

        // Strip contenteditable attributes for clean non-editable HTML
        document.querySelectorAll('[contenteditable]').forEach(el => {{
            el.removeAttribute('contenteditable');
        }});

        // Clean canvases to prevent Chart.js sizing glitches on reload
        document.querySelectorAll('canvas').forEach(c => {{
            c.removeAttribute('style');
            c.removeAttribute('width');
            c.removeAttribute('height');
            c.className = '';
        }});

        // Mark document container as published
        document.documentElement.classList.add('published-mode');

        const fullHtml = "<!DOCTYPE html>\\n" + document.documentElement.outerHTML;
        const currentPath = window.location.pathname;
        const fileName = currentPath.substring(currentPath.lastIndexOf('/') + 1) || 'report.html';
        const pubFileName = fileName.replace('.html', '_published.html');

        try {{
            const res = await fetch('/api/save-published-report', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ report_name: pubFileName, html_content: fullHtml }})
            }});
            const data = await res.json();
            if (data.success) {{
                alert("🎉 Report Published Successfully!\\n\\nSaved to: Results/Published/" + data.file + "\\n\\nYou will now be redirected to the published non-editable report.");
                window.location.href = data.url || ('/Results/Published/' + data.file);
            }} else {{
                alert("Error publishing report: " + data.message);
                if (editBadge) editBadge.style.display = 'inline-block';
                if (publishBtn) publishBtn.style.display = 'inline-block';
            }}
        }} catch (err) {{
            alert("Failed to reach server: " + err.message);
            if (editBadge) editBadge.style.display = 'inline-block';
            if (publishBtn) publishBtn.style.display = 'inline-block';
        }}
    }}

    if (localStorage.getItem('jmeter_ai_theme') === 'dark') {{
        document.documentElement.classList.add('dark');
    }}

    const chartFont = {{ family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 11 }};
    const gridColor = '#e1e4e8';
    const textColor = '#656d76';
    Chart.defaults.color = textColor;
    Chart.defaults.font = chartFont;

    const overallTs = {{
        avg_rt: {ts_avg_rt},
        p95_rt: {ts_p95_rt},
        p99_rt: {ts_p99_rt},
        throughput: {ts_throughput},
        errors: {ts_errors}
    }};

    const labelTsMap = {label_ts_json};
    
    // Critical Transactions Tracking & Deterministic Colors
    const criticalTxSet = new Set();
    const initialCriticals = {critical_tx_list_json};
    initialCriticals.forEach(t => criticalTxSet.add(t));

    // Critical Transactions Response Time Chart
    let critTxChartObj = null;
    const critCanvas = document.getElementById('critTxChart') || document.getElementById('chart-rt-exec');
    if (critCanvas) {{
        critTxChartObj = new Chart(critCanvas, {{
            type: 'line',
            data: {{
                labels: {ts_labels},
                datasets: []
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ font: {{ weight: '600' }} }} }},
                    tooltip: {{ mode: 'index', intersect: false }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: textColor, maxTicksLimit: 10 }} }},
                    y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Response Time (ms)', color: textColor }} }}
                }}
            }}
        }});
    }}

    const fixedColors = ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444', '#ec4899', '#06b6d4', '#84cc16'];
    function getTxColor(name) {{
        let hash = 0;
        for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
        return fixedColors[Math.abs(hash) % fixedColors.length];
    }}

    const targetSlaVal = {target_sla_val};



    function renderCritTxChips() {{
        const container = document.getElementById('crit-tx-chip-container');
        if (!container) return;
        container.innerHTML = '';

        if (!initialCriticals || initialCriticals.length === 0) return;

        const allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.style.cssText = 'padding:0.25rem 0.6rem; font-size:0.75rem; border-radius:12px; border:1px solid var(--border); background:var(--surface2); color:var(--text); cursor:pointer; font-weight:600;';
        allBtn.innerText = 'Show All';
        allBtn.onclick = (e) => {{
            e.preventDefault();
            initialCriticals.forEach(t => criticalTxSet.add(t));
            renderCritTxChips();
            updateCriticalTxChart();
        }};
        container.appendChild(allBtn);

        initialCriticals.forEach(txName => {{
            const isSelected = criticalTxSet.has(txName);
            const color = getTxColor(txName);
            const txSla = txSlaMap[txName] ? ' (SLA: ' + txSlaMap[txName] + 'ms)' : '';
            const shortName = (txName.length > 25 ? txName.substring(0, 22) + '...' : txName) + txSla;

            const chip = document.createElement('button');
            chip.type = 'button';
            chip.title = txName + txSla;
            chip.style.cssText = `padding:0.25rem 0.65rem; font-size:0.75rem; border-radius:12px; border:1px solid ${{isSelected ? color : 'var(--border)'}}; background:${{isSelected ? color + '22' : 'transparent'}}; color:${{isSelected ? color : 'var(--muted)'}}; cursor:pointer; font-weight:${{isSelected ? '700' : '500'}}; transition:all 0.15s;`;
            chip.innerText = (isSelected ? '● ' : '○ ') + shortName;
            chip.onclick = (e) => {{
                e.preventDefault();
                if (criticalTxSet.has(txName)) {{
                    criticalTxSet.delete(txName);
                }} else {{
                    criticalTxSet.add(txName);
                }}
                renderCritTxChips();
                updateCriticalTxChart();
            }};
            container.appendChild(chip);
        }});
    }}

    const txSlaMap = {tx_sla_json};

    function updateCriticalTxChart() {{
        if (!critTxChartObj) return;
        const datasets = [];

        // Transaction Lines with SLA target embedded in the index/label
        criticalTxSet.forEach(txName => {{
            let tsData = null;
            if (labelTsMap[txName] && labelTsMap[txName].ts_avg_rt) {{
                tsData = labelTsMap[txName].ts_avg_rt;
            }} else {{
                Object.values(labelTsMap).forEach(entry => {{
                    if (entry && (entry.label === txName || entry.name === txName)) {{
                        tsData = entry.ts_avg_rt;
                    }}
                }});
            }}
            if (tsData && tsData.length > 0) {{
                const color = getTxColor(txName);
                const txSla = txSlaMap[txName] ? ' (SLA: ' + txSlaMap[txName] + 'ms)' : '';
                const shortLabel = (txName.length > 25 ? txName.substring(0, 22) + '...' : txName) + txSla;
                datasets.push({{
                    label: shortLabel,
                    data: [...tsData],
                    borderColor: color,
                    backgroundColor: color,
                    borderWidth: 2.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 3.5,
                    pointHoverRadius: 6
                }});
            }}
        }});

        critTxChartObj.data.datasets = datasets;
        critTxChartObj.update('active');
    }}

    renderCritTxChips();

    function toggleCriticalTx(txName, isChecked) {{
        if (isChecked) {{
            criticalTxSet.add(txName);
        }} else {{
            criticalTxSet.delete(txName);
        }}
        updateCriticalTxChart();
    }}

    // Initial render of critical transactions chart
    updateCriticalTxChart();

    // Response Time Chart Instance
    const rtChartObj = new Chart(document.getElementById('rtChart'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'Avg RT', data: overallTs.avg_rt, borderColor: '#6366f1', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'P95 RT', data: overallTs.p95_rt, borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'P99 RT', data: overallTs.p99_rt, borderColor: '#ef4444', borderWidth: 1.5, borderDash: [5,3], fill: false, tension: 0.3, pointRadius: 1 }}
            ]
        }},
        options: {{ responsive: true, scales: {{ y: {{ grid: {{ color: gridColor }}, title: {{ 'display': true, text: 'ms' }} }}, x: {{ grid: {{ 'display': false }} }} }} }}
    }});

    function updateRtChart(val) {{
        let d = overallTs;
        if (val !== 'ALL') {{
            const idx = parseInt(val, 10);
            const entry = labelTsMap[idx];
            if (entry) d = {{ avg_rt: entry.ts_avg_rt, p95_rt: entry.ts_p95_rt, p99_rt: entry.ts_p99_rt }};
        }}
        rtChartObj.data.datasets[0].data = [...d.avg_rt];
        rtChartObj.data.datasets[1].data = [...d.p95_rt];
        rtChartObj.data.datasets[2].data = [...d.p99_rt];
        rtChartObj.update('active');
    }}

    // Throughput Chart Instance (Line Graph)
    const hasInitialErrors = overallTs.errors && overallTs.errors.some(e => e > 0);
    const tpDatasets = [
        {{
            label: 'Throughput (req/s)',
            data: overallTs.throughput,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.12)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#6366f1',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }}
    ];
    if (hasInitialErrors) {{
        tpDatasets.push({{
            label: 'Errors',
            data: overallTs.errors,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.10)',
            fill: true,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }});
    }}

    const tpChartObj = new Chart(document.getElementById('tpChart'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: tpDatasets
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ weight: '600' }} }} }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{ grid: {{ color: 'rgba(255,255,255,0.04)' }}, ticks: {{ color: textColor, font: {{ weight: '600' }} }} }},
                y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Throughput (req/s)', color: textColor }}, beginAtZero: true }}
            }}
        }}
    }});

    function updateTpChart(val) {{
        let d = overallTs;
        if (val !== 'ALL') {{
            const idx = parseInt(val, 10);
            const entry = labelTsMap[idx];
            if (entry) d = {{ throughput: entry.ts_throughput, errors: entry.ts_errors }};
        }}
        tpChartObj.data.datasets[0].data = [...d.throughput];
        if (tpChartObj.data.datasets.length > 1 && d.errors) {{
            tpChartObj.data.datasets[1].data = [...d.errors];
        }}
        tpChartObj.update('active');

        // Dynamically update the 4 KPI chips above the chart
        const tpArr = d.throughput || [];
        const errArr = d.errors || [];
        if (tpArr.length > 0) {{
            const avgVal = Math.round(tpArr.reduce((a,b)=>a+b, 0) / tpArr.length);
            const peakVal = Math.round(Math.max(...tpArr));
            const endVal = Math.round(tpArr[tpArr.length - 1]);
            const totalErrs = errArr.reduce((a,b)=>a+b, 0);
            const totalSamples = tpArr.reduce((a,b)=>a+b, 0) * 10;
            const errRateVal = totalSamples > 0 ? (totalErrs / totalSamples * 100).toFixed(2) : '0.00';

            const kpiAvg = document.getElementById('tpKpiAvg');
            const kpiPeak = document.getElementById('tpKpiPeak');
            const kpiErr = document.getElementById('tpKpiErr');
            const kpiTrend = document.getElementById('tpKpiTrend');
            if (kpiAvg) kpiAvg.innerText = avgVal + ' req/s';
            if (kpiPeak) kpiPeak.innerText = peakVal + ' req/s';
            if (kpiErr) {{
                kpiErr.innerText = errRateVal + '%';
                kpiErr.style.color = parseFloat(errRateVal) > 0 ? 'var(--red)' : 'var(--green)';
            }}
            if (kpiTrend) {{
                const diffPct = peakVal > 0 ? Math.round((peakVal - endVal)/peakVal * 100) : 0;
                if (diffPct >= 10) {{
                    kpiTrend.innerText = '↓ ' + diffPct + '% from Peak';
                    kpiTrend.style.color = 'var(--red)';
                }} else {{
                    kpiTrend.innerText = '🟢 Stable';
                    kpiTrend.style.color = 'var(--green)';
                }}
            }}
        }}
    }}

    // ── Hierarchical Transaction & Sub-Transaction Multi-View Line Chart Manager ──
    const txRtHierarchyData = {tx_rt_hierarchy_json};
    let txRtChartPanels = [];
    let nextTxRtPanelId = 1;

    // Metric visual configuration and styling
    const txRtMetricColorMap = {{
        'avg_rt': {{ line: '#6366f1', fill: 'rgba(99, 102, 241, 0.12)', label: 'Average RT (ms)', unit: 'ms' }},
        'p90': {{ line: '#f59e0b', fill: 'rgba(245, 158, 11, 0.12)', label: '90th Percentile (P90) (ms)', unit: 'ms' }},
        'p95': {{ line: '#ef4444', fill: 'rgba(239, 68, 68, 0.12)', label: '95th Percentile (P95) (ms)', unit: 'ms' }},
        'max_rt': {{ line: '#ec4899', fill: 'rgba(236, 72, 153, 0.12)', label: 'Max Response Time (ms)', unit: 'ms' }},
        'min_rt': {{ line: '#10b981', fill: 'rgba(16, 185, 129, 0.12)', label: 'Min Response Time (ms)', unit: 'ms' }},
        'error_rate': {{ line: '#dc2626', fill: 'rgba(220, 38, 38, 0.12)', label: 'Error Rate (%)', unit: '%' }},
        'count': {{ line: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.12)', label: 'Sample Count', unit: 'samples' }}
    }};

    // Custom Data Labels Plugin for Line Points
    const txRtLineLabelsPlugin = {{
        id: 'txRtLineLabelsPlugin',
        afterDatasetsDraw(chart) {{
            const {{ ctx }} = chart;
            ctx.save();
            const isDark = document.documentElement.classList.contains('dark');
            ctx.font = '600 10.5px Inter, sans-serif';
            ctx.fillStyle = isDark ? '#f1f5f9' : '#1f2328';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            chart.data.datasets.forEach((dataset, datasetIndex) => {{
                const meta = chart.getDatasetMeta(datasetIndex);
                if (!meta.hidden) {{
                    meta.data.forEach((element, index) => {{
                        const val = dataset.data[index];
                        if (val !== null && val !== undefined && !isNaN(val)) {{
                            let formatted = '';
                            const metric = chart.config._metricKey || 'avg_rt';
                            if (metric === 'error_rate') {{
                                formatted = Number(val).toFixed(2) + '%';
                            }} else if (metric === 'count') {{
                                formatted = Math.round(val).toLocaleString();
                            }} else {{
                                formatted = Math.round(val).toLocaleString() + ' ms';
                            }}
                            const x = element.x;
                            const y = element.y - 6;
                            ctx.fillText(formatted, x, y);
                        }}
                    }});
                }}
            }});
            ctx.restore();
        }}
    }};

    function addTxRtChartView(initialMetric) {{
        const container = document.getElementById('txRtChartsContainer');
        if (!container) return;

        const panelId = nextTxRtPanelId++;
        const defaultMetric = initialMetric || (txRtChartPanels.length === 1 ? 'p90' : (txRtChartPanels.length === 2 ? 'max_rt' : 'avg_rt'));

        const cardEl = document.createElement('div');
        cardEl.id = `tx-rt-panel-${{panelId}}`;
        cardEl.className = 'glass-panel';
        cardEl.style.cssText = 'background:var(--surface1); border:1px solid var(--border); border-radius:10px; padding:1.25rem; position:relative; width:100%; box-sizing:border-box;';

        const canRemove = txRtChartPanels.length > 0;

        cardEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.6rem; border-bottom:1px solid var(--border); padding-bottom:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:0.3rem;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">User Story:</label>
                        <select id="txRtUsSelect-${{panelId}}" onchange="onPanelUsChange(${{panelId}}, this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.3rem 0.6rem; border-radius:6px; font-size:0.75rem; font-weight:600; outline:none; cursor:pointer;">
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">Transaction:</label>
                        <select id="txRtTxSelect-${{panelId}}" onchange="onPanelTxChange(${{panelId}}, this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.3rem 0.6rem; border-radius:6px; font-size:0.75rem; font-weight:600; outline:none; cursor:pointer; max-width:260px;">
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">Metric:</label>
                        <select id="txRtMetricSelect-${{panelId}}" onchange="onPanelMetricChange(${{panelId}}, this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.3rem 0.6rem; border-radius:6px; font-size:0.75rem; font-weight:700; outline:none; cursor:pointer;">
                            <option value="avg_rt" ${{defaultMetric === 'avg_rt' ? 'selected' : ''}}>Average RT (ms)</option>
                            <option value="p90" ${{defaultMetric === 'p90' ? 'selected' : ''}}>90th Percentile (P90) (ms)</option>
                            <option value="p95" ${{defaultMetric === 'p95' ? 'selected' : ''}}>95th Percentile (P95) (ms)</option>
                            <option value="max_rt" ${{defaultMetric === 'max_rt' ? 'selected' : ''}}>Max Response Time (ms)</option>
                            <option value="min_rt" ${{defaultMetric === 'min_rt' ? 'selected' : ''}}>Min Response Time (ms)</option>
                            <option value="error_rate" ${{defaultMetric === 'error_rate' ? 'selected' : ''}}>Error Rate (%)</option>
                            <option value="count" ${{defaultMetric === 'count' ? 'selected' : ''}}>Sample Count</option>
                        </select>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button type="button" onclick="duplicateTxRtView(${{panelId}})" title="Duplicate this exact view" style="background:var(--surface2); border:1px solid var(--border); color:var(--text); font-size:0.72rem; font-weight:600; padding:0.25rem 0.55rem; border-radius:4px; cursor:pointer;">⧉ Duplicate</button>
                    ${{canRemove ? `<button type="button" onclick="removeTxRtChartView(${{panelId}})" title="Close this chart view" style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); color:#ef4444; font-size:0.75rem; font-weight:700; padding:0.25rem 0.55rem; border-radius:4px; cursor:pointer;">✕</button>` : ''}}
                </div>
            </div>
            <div id="txRtBreadcrumb-${{panelId}}" style="font-size:0.75rem; font-weight:600; color:var(--muted); margin-bottom:0.5rem; display:flex; align-items:center; gap:0.3rem;">
            </div>
            <div style="position:relative; height:320px; width:100%;">
                <canvas id="chart-tx-rt-canvas-${{panelId}}"></canvas>
            </div>
        `;

        container.appendChild(cardEl);

        const panelObj = {{
            id: panelId,
            us: 'ALL',
            tx: 'ALL',
            metric: defaultMetric,
            chartObj: null
        }};
        txRtChartPanels.push(panelObj);

        // Populate User Stories
        const usSelect = document.getElementById(`txRtUsSelect-${{panelId}}`);
        if (usSelect) {{
            usSelect.innerHTML = '<option value="ALL">All User Stories</option>';
            if (txRtHierarchyData.user_stories) {{
                txRtHierarchyData.user_stories.forEach(us => {{
                    const opt = document.createElement('option');
                    opt.value = us.name;
                    opt.textContent = us.name;
                    usSelect.appendChild(opt);
                }});
            }}
        }}

        populatePanelTxDropdown(panelId);

        // Create Chart.js Line Instance
        const canvas = document.getElementById(`chart-tx-rt-canvas-${{panelId}}`);
        const mInfo = txRtMetricColorMap[defaultMetric] || txRtMetricColorMap['avg_rt'];

        const chartObj = new Chart(canvas, {{
            type: 'line',
            data: {{
                labels: [],
                datasets: [
                    {{
                        label: mInfo.label,
                        data: [],
                        borderColor: mInfo.line,
                        backgroundColor: mInfo.fill,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: mInfo.line,
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                const val = ctx.parsed.y;
                                const curM = panelObj.metric;
                                if (curM === 'error_rate') return `Error Rate: ${{Number(val).toFixed(2)}}%`;
                                if (curM === 'count') return `Count: ${{Math.round(val).toLocaleString()}} samples`;
                                return `${{mInfo.label}}: ${{Math.round(val).toLocaleString()}} ms`;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255,255,255,0.04)' }},
                        ticks: {{
                            color: textColor,
                            font: {{ weight: '600', size: 9.5 }},
                            maxRotation: 25
                        }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        ticks: {{
                            color: textColor,
                            callback: function(val) {{
                                const curM = panelObj.metric;
                                if (curM === 'error_rate') return val + '%';
                                if (curM === 'count') return val.toLocaleString();
                                return val.toLocaleString() + ' ms';
                            }}
                        }},
                        title: {{ display: true, text: mInfo.label, color: textColor }},
                        grace: '18%',
                        beginAtZero: true
                    }}
                }}
            }},
            plugins: [txRtLineLabelsPlugin]
        }});

        chartObj.config._metricKey = defaultMetric;
        panelObj.chartObj = chartObj;

        updatePanelChart(panelId);
    }}

    function populatePanelTxDropdown(panelId) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        const txSelect = document.getElementById(`txRtTxSelect-${{panelId}}`);
        if (!txSelect) return;

        txSelect.innerHTML = '';
        const allOpt = document.createElement('option');
        allOpt.value = 'ALL';
        allOpt.textContent = panel.us === 'ALL' ? 'All Transactions (Overview)' : `All in ${{panel.us}}`;
        txSelect.appendChild(allOpt);

        let txList = [];
        if (panel.us === 'ALL') {{
            txList = txRtHierarchyData.all_transactions || [];
        }} else {{
            const foundUs = (txRtHierarchyData.user_stories || []).find(u => u.name === panel.us);
            if (foundUs) txList = foundUs.transactions || [];
        }}

        txList.forEach(t => {{
            const opt = document.createElement('option');
            opt.value = t.name;
            const subCount = (t.children || []).length;
            const suffix = subCount > 0 ? ` (${{subCount}} sub-req)` : '';
            opt.textContent = (t.name.length > 25 ? t.name.substring(0, 22) + '...' : t.name) + suffix;
            opt.title = t.name;
            txSelect.appendChild(opt);
        }});

        txSelect.value = panel.tx;
        if (txSelect.value !== panel.tx) {{
            panel.tx = 'ALL';
            txSelect.value = 'ALL';
        }}
    }}

    function onPanelUsChange(panelId, val) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        panel.us = val;
        panel.tx = 'ALL';
        populatePanelTxDropdown(panelId);
        updatePanelChart(panelId);
    }}

    function onPanelTxChange(panelId, val) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        panel.tx = val;
        updatePanelChart(panelId);
    }}

    function onPanelMetricChange(panelId, val) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        panel.metric = val;
        updatePanelChart(panelId);
    }}

    function duplicateTxRtView(sourcePanelId) {{
        const src = txRtChartPanels.find(p => p.id === sourcePanelId);
        if (!src) return;
        addTxRtChartView(src.metric);
        const newPanel = txRtChartPanels[txRtChartPanels.length - 1];
        if (newPanel) {{
            newPanel.us = src.us;
            newPanel.tx = src.tx;
            newPanel.metric = src.metric;
            const usSel = document.getElementById(`txRtUsSelect-${{newPanel.id}}`);
            if (usSel) usSel.value = src.us;
            populatePanelTxDropdown(newPanel.id);
            const txSel = document.getElementById(`txRtTxSelect-${{newPanel.id}}`);
            if (txSel) txSel.value = src.tx;
            const mSel = document.getElementById(`txRtMetricSelect-${{newPanel.id}}`);
            if (mSel) mSel.value = src.metric;
            updatePanelChart(newPanel.id);
        }}
    }}

    function removeTxRtChartView(panelId) {{
        const idx = txRtChartPanels.findIndex(p => p.id === panelId);
        if (idx === -1) return;
        const panel = txRtChartPanels[idx];
        if (panel.chartObj) {{
            panel.chartObj.destroy();
        }}
        txRtChartPanels.splice(idx, 1);
        const card = document.getElementById(`tx-rt-panel-${{panelId}}`);
        if (card) card.remove();
    }}

    function updatePanelChart(panelId) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel || !panel.chartObj) return;

        const breadcrumbEl = document.getElementById(`txRtBreadcrumb-${{panelId}}`);
        let items = [];

        if (panel.tx !== 'ALL') {{
            let targetTx = null;
            if (txRtHierarchyData.all_transactions) {{
                targetTx = txRtHierarchyData.all_transactions.find(t => t.name === panel.tx);
            }}
            if (!targetTx && txRtHierarchyData.user_stories) {{
                for (const us of txRtHierarchyData.user_stories) {{
                    const found = (us.transactions || []).find(t => t.name === panel.tx);
                    if (found) {{ targetTx = found; break; }}
                }}
            }}

            if (targetTx && targetTx.children && targetTx.children.length > 0) {{
                items = targetTx.children;
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Context:</span> <span style="color:var(--text);">${{panel.us === 'ALL' ? 'All Stories' : panel.us}}</span> &rarr; <span style="color:var(--accent); font-weight:700;">📂 ${{targetTx.name}}</span> &rarr; <span style="color:var(--text); font-weight:700;">🔍 ${{items.length}} Child Requests</span>`;
                }}
            }} else if (targetTx) {{
                items = [targetTx];
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Context:</span> <span style="color:var(--text);">${{panel.us === 'ALL' ? 'All Stories' : panel.us}}</span> &rarr; <span style="color:var(--accent); font-weight:700;">📂 ${{targetTx.name}}</span> (No child requests)`;
                }}
            }}
        }} else {{
            if (panel.us === 'ALL') {{
                items = txRtHierarchyData.all_transactions || [];
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Showing:</span> <span style="color:var(--accent); font-weight:700;">🌐 All User Stories</span> &rarr; <span style="color:var(--text); font-weight:700;">${{items.length}} Main Transactions</span>`;
                }}
            }} else {{
                const foundUs = (txRtHierarchyData.user_stories || []).find(u => u.name === panel.us);
                items = foundUs ? (foundUs.transactions || []) : [];
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Showing:</span> <span style="color:var(--accent); font-weight:700;">📁 ${{panel.us}}</span> &rarr; <span style="color:var(--text); font-weight:700;">${{items.length}} Transactions</span>`;
                }}
            }}
        }}

        const labels = items.map(item => item.name.length > 28 ? item.name.substring(0, 25) + '...' : item.name);
        const dataValues = items.map(item => {{
            const v = item[panel.metric];
            return v !== undefined && v !== null ? v : 0;
        }});

        const mInfo = txRtMetricColorMap[panel.metric] || txRtMetricColorMap['avg_rt'];

        panel.chartObj.config._metricKey = panel.metric;
        panel.chartObj.data.labels = labels;
        panel.chartObj.data.datasets[0].label = mInfo.label;
        panel.chartObj.data.datasets[0].data = dataValues;
        panel.chartObj.data.datasets[0].borderColor = mInfo.line;
        panel.chartObj.data.datasets[0].backgroundColor = mInfo.fill;
        panel.chartObj.data.datasets[0].pointBackgroundColor = mInfo.line;
        panel.chartObj.options.scales.y.title.text = mInfo.label;

        panel.chartObj.update('active');
    }}

    // Initialize primary line chart view
    addTxRtChartView('avg_rt');

    // SLA Deviation by Transaction Diverging Horizontal Bar Chart
    const tgToTcsMap = {tg_to_tcs_json};
    const txDevMap = {tx_dev_map_json};
    const initialDevLabels = {deviation_chart_labels_json};
    const initialDevVals = {deviation_chart_values_json};

    const slaDevChartObj = new Chart(document.getElementById('chart-sla-deviation-exec'), {{
        type: 'bar',
        data: {{
            labels: initialDevLabels,
            datasets: [
                {{
                    label: 'SLA Deviation (%)',
                    data: initialDevVals,
                    backgroundColor: initialDevVals.map(val => val > 0 ? '#ef4444' : '#10b981'),
                    borderColor: initialDevVals.map(val => val > 0 ? '#dc2626' : '#059669'),
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.65
                }}
            ]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{
                            const val = ctx.parsed.x;
                            return (val > 0 ? '+' : '') + val + '% deviation from SLA';
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ color: gridColor }},
                    ticks: {{
                        color: textColor,
                        callback: function(val) {{ return (val > 0 ? '+' : '') + val + '%'; }}
                    }},
                    title: {{ display: true, text: 'Deviation from SLA Limit (%)', color: textColor }}
                }},
                y: {{
                    grid: {{ display: false }},
                    ticks: {{ color: textColor, font: {{ weight: '600', size: 11 }} }}
                }}
            }}
        }}
    }});

    function filterSlaDevByUs(selectedUs) {{
        if (!slaDevChartObj) return;

        let filteredItems = [];

        if (selectedUs === 'ALL' || !tgToTcsMap[selectedUs]) {{
            // Show all transactions sorted by worst deviation %
            filteredItems = Object.values(txDevMap);
        }} else {{
            // Filter to child transactions belonging to the selected User Story / Thread Group
            const childTcs = tgToTcsMap[selectedUs] || [];
            filteredItems = Object.values(txDevMap).filter(item => childTcs.includes(item.label));
        }}

        filteredItems.sort((a, b) => b.dev_pct - a.dev_pct);

        const newLabels = filteredItems.map(item => item.label.length > 35 ? item.label.substring(0, 32) + '...' : item.label);
        const newVals   = filteredItems.map(item => item.dev_pct);

        slaDevChartObj.data.labels = newLabels;
        slaDevChartObj.data.datasets[0].data = newVals;
        slaDevChartObj.data.datasets[0].backgroundColor = newVals.map(v => v > 0 ? '#ef4444' : '#10b981');
        slaDevChartObj.data.datasets[0].borderColor = newVals.map(v => v > 0 ? '#dc2626' : '#059669');
        slaDevChartObj.update('active');
    }}

    // Chart.js Data Labels Plugin to draw exact sample counts on top of bars
    const txSummaryDataLabelsPlugin = {{
        id: 'txSummaryDataLabelsPlugin',
        afterDatasetsDraw(chart) {{
            const {{ ctx }} = chart;
            ctx.save();
            const isDark = document.documentElement.classList.contains('dark');
            ctx.font = '700 11px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            chart.data.datasets.forEach((dataset, datasetIndex) => {{
                const meta = chart.getDatasetMeta(datasetIndex);
                if (!meta.hidden) {{
                    meta.data.forEach((element, index) => {{
                        const val = dataset.data[index];
                        if (val !== null && val !== undefined && !isNaN(val)) {{
                            if (datasetIndex === 1 && val === 0) return; // Don't draw 0 for Fail
                            const formatted = val.toLocaleString();
                            const x = element.x;
                            const y = element.y - 4;
                            ctx.fillStyle = datasetIndex === 0 
                                ? (isDark ? '#34d399' : '#059669') 
                                : '#ef4444';
                            ctx.fillText(formatted, x, y);
                        }}
                    }});
                }}
            }});
            ctx.restore();
        }}
    }};

    // Transaction Summary Grouped Bar Chart (Pass vs Fail with Numbers on Bars)
    new Chart(document.getElementById('chart-tx-summary-bar'), {{
        type: 'bar',
        data: {{
            labels: {tx_chart_labels_json},
            datasets: [
                {{
                    label: 'Pass Samples',
                    data: {tx_chart_pass_json},
                    backgroundColor: 'rgba(16, 185, 129, 0.85)',
                    borderColor: '#059669',
                    borderWidth: 1.5,
                    borderRadius: 5,
                    barPercentage: 0.62,
                    categoryPercentage: 0.65
                }},
                {{
                    label: 'Fail Samples',
                    data: {tx_chart_fail_json},
                    backgroundColor: 'rgba(239, 68, 68, 0.85)',
                    borderColor: '#dc2626',
                    borderWidth: 1.5,
                    borderRadius: 5,
                    barPercentage: 0.62,
                    categoryPercentage: 0.65
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            layout: {{
                padding: {{
                    top: 25,
                    bottom: 5
                }}
            }},
            plugins: {{
                legend: {{
                    position: 'bottom',
                    labels: {{
                        font: {{ weight: '700', size: 12 }},
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 16,
                        color: textColor
                    }}
                }},
                tooltip: {{
                    mode: 'index',
                    intersect: false,
                    padding: 10,
                    callbacks: {{
                        label: function(ctx) {{
                            const label = ctx.dataset.label || '';
                            const val = ctx.raw || 0;
                            const chart = ctx.chart;
                            const pass = chart.data.datasets[0].data[ctx.dataIndex] || 0;
                            const fail = (chart.data.datasets[1] && chart.data.datasets[1].data[ctx.dataIndex]) || 0;
                            const total = pass + fail;
                            const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0';
                            return `${{label}}: ${{val.toLocaleString()}} (${{pct}}%)`;
                        }},
                        footer: function(tooltipItems) {{
                            if (tooltipItems.length > 0) {{
                                const idx = tooltipItems[0].dataIndex;
                                const chart = tooltipItems[0].chart;
                                const pass = chart.data.datasets[0].data[idx] || 0;
                                const fail = (chart.data.datasets[1] && chart.data.datasets[1].data[idx]) || 0;
                                const total = pass + fail;
                                const errRate = total > 0 ? ((fail / total) * 100).toFixed(2) : '0.00';
                                return `Total: ${{total.toLocaleString()}} samples | Error Rate: ${{errRate}}%`;
                            }}
                            return '';
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ display: false }},
                    ticks: {{ maxRotation: 25, font: {{ weight: '600', size: 11 }}, color: textColor }}
                }},
                y: {{
                    grid: {{ color: gridColor }},
                    beginAtZero: true,
                    grace: '12%',
                    ticks: {{
                        color: textColor,
                        callback: function(val) {{ return val.toLocaleString(); }}
                    }},
                    title: {{ display: true, text: 'Sample Count', color: textColor, font: {{ weight: '700' }} }}
                }}
            }}
        }},
        plugins: [txSummaryDataLabelsPlugin]
    }});



    new Chart(document.getElementById('chart-infra-exec'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'CPU %', data: {ts_cpu}, borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'Memory %', data: {ts_memory}, borderColor: '#3b82f6', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }}
            ]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: gridColor }}, min: 0, max: 100 }}, x: {{ grid: {{ display: false }} }} }} }}
    }});

    // ── Charts & Analytics Tab ─────────────────────────────────────────────────
    // 1. SLA Deviation & Severity Donut Chart
    new Chart(document.getElementById('slaDonut'), {{
        type: 'doughnut',
        data: {{
            labels: ['Passed', 'Minor Breach', 'Moderate Breach', 'Critical Breach'],
            datasets: [{{
                data: [{tx_under_sla}, {sla_minor_count}, {sla_mod_count}, {sla_crit_count}],
                backgroundColor: [
                    '#10b981',  // Passed - Emerald Green
                    '#f59e0b',  // Minor - Amber
                    '#f97316',  // Moderate - Orange
                    '#ef4444'   // Critical - Red
                ],
                borderColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
                borderWidth: 1,
                hoverOffset: 4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            cutout: '76%',
            plugins: {{
                legend: {{ display: false }}
            }}
        }}
    }});

    // 3. Error Rate by Transaction (horizontal bar)
    if ({err_labels_json}.length > 0) {{
        new Chart(document.getElementById('errChart'), {{
            type: 'bar',
            data: {{
                labels: {err_labels_json},
                datasets: [{{
                    label: 'Error Rate (%)',
                    data: {err_rates_json},
                    backgroundColor: 'rgba(239,68,68,0.75)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: '%', color: textColor }} }},
                    y: {{ grid: {{ display: false }}, ticks: {{ color: textColor, font: {{ size: 10 }} }} }}
                }}
            }}
        }});
    }} else {{
        const errEl = document.getElementById('errChart');
        if (errEl) {{ errEl.parentElement.innerHTML += '<p style="color:var(--green);text-align:center;margin-top:2rem;">✅ No transactions with errors</p>'; errEl.style.display='none'; }}
    }}

    // 4. Response Time Histogram
    new Chart(document.getElementById('histChart'), {{
        type: 'bar',
        data: {{
            labels: {rt_hist_labels},
            datasets: [{{
                label: 'Requests',
                data: {rt_hist_counts},
                backgroundColor: [
                    'rgba(16,185,129,0.75)','rgba(59,130,246,0.75)','rgba(139,92,246,0.75)',
                    'rgba(245,158,11,0.75)','rgba(249,115,22,0.75)','rgba(239,68,68,0.75)','rgba(127,29,29,0.75)'
                ],
                borderRadius: 5
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ grid: {{ display: false }}, ticks: {{ color: textColor }} }},
                y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Request Count', color: textColor }} }}
            }}
        }}
    }});

    // 5. Top Transactions by Response Time (Percentile comparison bar chart)
    const elTxChart = document.getElementById('txChart');
    if (elTxChart) {{
        new Chart(elTxChart, {{
            type: 'bar',
            data: {{
                labels: {pct_names},
                datasets: [
                    {{ label: 'P50', data: {pct_p50}, backgroundColor: 'rgba(59,130,246,0.75)', borderRadius: 3 }},
                    {{ label: 'P90', data: {pct_p90}, backgroundColor: 'rgba(245,158,11,0.75)', borderRadius: 3 }},
                    {{ label: 'P95', data: {pct_p95}, backgroundColor: 'rgba(249,115,22,0.75)', borderRadius: 3 }},
                    {{ label: 'P99', data: {pct_p99}, backgroundColor: 'rgba(239,68,68,0.75)', borderRadius: 3 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ weight: '600', size: 10 }}, boxWidth: 10, padding: 6 }} }},
                    tooltip: {{ mode: 'index', intersect: false }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: textColor, font: {{ size: 10 }}, maxRotation: 25 }} }},
                    y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Latency (ms)', color: textColor }} }}
                }}
            }}
        }});
    }}

    // ── Error Distribution Donut / Pie Charts (Executive Summary & Error Tab) ──
    const errDonutLabels = {error_donut_labels};
    const errDonutCounts = {error_donut_counts};
    const errDrillData = {error_drill_json};
    const errDonutColors = ['#ef4444','#f97316','#f59e0b','#8b5cf6','#3b82f6','#06b6d4','#10b981','#ec4899','#84cc16','#64748b'];
    const startEpochMs = {start_epoch_ms};
    const displayTotalErrors = {display_total_errors};

    function initErrorDonutInstances() {{
        const configs = [
            {{ canvasId: 'chart-errors-exec', legendId: 'execErrorDonutLegend', contentId: 'execErrorContent' }},
            {{ canvasId: 'errorDonutChart', legendId: 'errorDonutLegend', contentId: null }}
        ];

        configs.forEach(cfg => {{
            const canvasEl = document.getElementById(cfg.canvasId);
            if (!canvasEl) return;

            if (errDonutLabels.length > 0) {{
                new Chart(canvasEl, {{
                    type: 'doughnut',
                    data: {{
                        labels: errDonutLabels,
                        datasets: [{{
                            data: errDonutCounts,
                            backgroundColor: errDonutColors.slice(0, errDonutLabels.length),
                            borderColor: errDonutColors.slice(0, errDonutLabels.length).map(c => c + '88'),
                            borderWidth: 2,
                            hoverOffset: 8,
                            hoverBorderWidth: 3
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '68%',
                        plugins: {{
                            legend: {{ display: false }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(ctx) {{
                                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                        const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : '0';
                                        return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
                                    }}
                                }}
                            }}
                        }},
                        onClick: function(evt, elements) {{
                            if (elements.length > 0) {{
                                const idx = elements[0].index;
                                const errorKey = errDonutLabels[idx];
                                showErrorDrillDown(errorKey, errDonutColors[idx % errDonutColors.length]);
                            }}
                        }}
                    }}
                }});

                // Build custom legend
                const legendEl = document.getElementById(cfg.legendId);
                if (legendEl) {{
                    legendEl.innerHTML = '';
                    const totalAll = errDonutCounts.reduce((a, b) => a + b, 0);
                    errDonutLabels.forEach((label, i) => {{
                        const pct = totalAll > 0 ? ((errDonutCounts[i] / totalAll) * 100).toFixed(1) : '0';
                        const color = errDonutColors[i % errDonutColors.length];
                        const item = document.createElement('div');
                        item.style.cssText = 'display:flex; align-items:center; gap:0.4rem; cursor:pointer; padding:0.15rem 0; transition:opacity 0.15s;';
                        item.innerHTML = `<span style="width:10px; height:10px; border-radius:50%; background:${{color}}; flex-shrink:0;"></span><span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{label}}">${{label.length > 28 ? label.substring(0,25)+'...' : label}}</span><span style="margin-left:auto; font-weight:700; color:${{color}}; flex-shrink:0;">${{errDonutCounts[i]}}</span>`;
                        item.onclick = () => showErrorDrillDown(label, color);
                        item.onmouseenter = () => {{ item.style.opacity = '0.7'; }};
                        item.onmouseleave = () => {{ item.style.opacity = '1'; }};
                        legendEl.appendChild(item);
                    }});
                }}
            }} else if (displayTotalErrors > 0) {{
                // Legacy fallback
                const parent = cfg.contentId ? document.getElementById(cfg.contentId) : canvasEl.parentElement.parentElement;
                if (parent) {{
                    parent.innerHTML = `
                        <div style="text-align:center; padding:2rem 1rem; color:var(--muted);">
                            <div style="font-size:2.5rem; margin-bottom:0.5rem; opacity:0.7;">⚠️</div>
                            <div style="font-size:1.1rem; font-weight:700; color:var(--text);">${{displayTotalErrors}} Errors Detected</div>
                            <div style="font-size:0.82rem; margin-top:0.3rem;">Granular error distribution is not available for this run.<br>Please re-execute the test to capture detailed error analytics.</div>
                        </div>`;
                }}
            }} else {{
                // Zero errors success state
                const parent = cfg.contentId ? document.getElementById(cfg.contentId) : canvasEl.parentElement.parentElement;
                if (parent) {{
                    parent.innerHTML = `
                        <div style="text-align:center; padding:2rem 1rem; color:var(--muted);">
                            <div style="font-size:2.5rem; margin-bottom:0.5rem;">✅</div>
                            <div style="font-size:1.1rem; font-weight:700; color:#10b981;">Zero Errors Detected</div>
                            <div style="font-size:0.82rem; color:var(--muted); margin-top:0.3rem;">All requests completed successfully during this test execution.</div>
                        </div>`;
                }}
            }}
        }});
    }}

    initErrorDonutInstances();

    function showErrorDrillDown(errorKey, accentColor) {{
        const panels = [document.getElementById('errorDrillPanel'), document.getElementById('execErrorDrillPanel')].filter(Boolean);
        if (panels.length === 0) return;
        const data = errDrillData[errorKey];
        if (!data) {{ panels.forEach(p => p.innerHTML = '<p style="color:var(--muted); text-align:center;">No drill-down data available for this error.</p>'); return; }}

        const txEntries = Object.entries(data.transactions || {{}});
        const failureNote = data.failure_message ? `<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:6px; padding:0.5rem 0.75rem; margin-bottom:0.75rem; font-size:0.78rem; color:#ef4444; word-break:break-word;">⚠️ <strong>Assertion/Failure:</strong> ${{data.failure_message}}</div>` : '';

        let txTableRows = '';
        txEntries.forEach(([txName, info]) => {{
            const firstTime = info.first_ts && startEpochMs ? new Date(info.first_ts).toLocaleTimeString() : '-';
            const lastTime = info.last_ts && startEpochMs ? new Date(info.last_ts).toLocaleTimeString() : '-';
            txTableRows += `
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:0.4rem 0.5rem; font-weight:600; font-size:0.78rem; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{txName}}">${{txName.length > 35 ? txName.substring(0,32)+'...' : txName}}</td>
                    <td style="padding:0.4rem; text-align:center; font-weight:700; color:${{accentColor}};">${{info.count}}</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.avg_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.min_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.max_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center; font-size:0.75rem; color:var(--muted);">${{firstTime}}</td>
                    <td style="padding:0.4rem; text-align:center; font-size:0.75rem; color:var(--muted);">${{lastTime}}</td>
                </tr>`;
        }});

        panels.forEach(panel => {{
            panel.style.display = 'block';
            panel.style.alignItems = 'stretch';
            panel.style.justifyContent = 'flex-start';
            panel.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; gap:0.5rem;">
                    <div style="display:flex; align-items:center; gap:0.5rem; min-width:0;">
                        <span style="width:12px; height:12px; border-radius:50%; background:${{accentColor}}; flex-shrink:0;"></span>
                        <strong style="font-size:0.9rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{errorKey}}">${{errorKey}}</strong>
                    </div>
                    <span style="font-size:0.78rem; font-weight:700; background:${{accentColor}}18; border:1px solid ${{accentColor}}44; padding:0.2rem 0.6rem; border-radius:10px; color:${{accentColor}}; flex-shrink:0;">${{data.total}} occurrences</span>
                </div>
                ${{failureNote}}
                <div style="font-size:0.78rem; color:var(--muted); margin-bottom:0.5rem;">
                    ${{data.code ? '<strong>HTTP Code:</strong> ' + data.code + ' &nbsp;|&nbsp; ' : ''}}<strong>Affected Requests:</strong> ${{txEntries.length}}
                </div>
                <div style="overflow-x:auto; border-radius:6px; border:1px solid var(--border);">
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                        <thead>
                            <tr style="background:var(--bg); border-bottom:2px solid var(--border);">
                                <th style="padding:0.45rem 0.5rem; text-align:left; font-weight:700; font-size:0.75rem; color:var(--muted);">Request / Sampler</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Errors</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Avg RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Min RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Max RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">First</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Last</th>
                            </tr>
                        </thead>
                        <tbody>${{txTableRows}}</tbody>
                    </table>
                </div>
            `;
        }});
    }}

    // ── Load & Capacity Hero Charts ──
    const loadLabels = {load_chart_labels_json};
    const loadTpData = {ts_tp_raw};
    const expectedTpData = {expected_tp_json};
    const loadP95Data = {ts_p95_rt};
    const loadAvgData = {ts_avg_rt};
    const slaRefData = {sla_ref_json};

    // 1. Load vs Throughput (TPS vs VUs)
    const elLoadTp = document.getElementById('chartLoadVsThroughput');
    if (elLoadTp && loadTpData.length > 0) {{
        new Chart(elLoadTp, {{
            type: 'line',
            data: {{
                labels: loadLabels,
                datasets: [
                    {{
                        label: 'Actual Throughput (TPS)',
                        data: loadTpData,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139,92,246,0.15)',
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#8b5cf6'
                    }},
                    {{
                        label: 'Linear Scaling Reference',
                        data: expectedTpData,
                        borderColor: '#94a3b8',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ weight: '600' }} }} }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        callbacks: {{
                            label: function(ctx) {{
                                return ctx.dataset.label + ': ' + ctx.raw + ' TPS';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: textColor, font: {{ weight: '600' }} }},
                        title: {{ display: true, text: 'Active Virtual Users (VUs)', color: textColor }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        ticks: {{ color: textColor }},
                        title: {{ display: true, text: 'Throughput (TPS)', color: textColor }},
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    }}



    // Azure Infrastructure Diagnostic Suite Charts
    const azCpu = {ts_cpu};
    const azMem = {ts_memory};
    const azDiskQ = {ts_disk_q_json};
    const azDiskRead = {ts_disk_read_json};
    const azDiskWrite = {ts_disk_write_json};
    const azNetIn = {ts_net_in_json};
    const azNetOut = {ts_net_out_json};

    if (azCpu.length > 0) {{
        // 1. CPU & Memory Utilization (Full Width)
        new Chart(document.getElementById('azChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'CPU %', data: azCpu, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.12)', borderWidth: 2.5, fill: true, tension: 0.3, pointRadius: 3 }},
                    {{ label: 'Memory %', data: azMem, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.12)', borderWidth: 2.5, fill: true, tension: 0.3, pointRadius: 3 }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ min: 0, max: 100, grid: {{ color: gridColor }}, title: {{ display: true, text: '%' }} }}, x: {{ grid: {{ display: false }} }} }} }}
        }});

        // 2. Workload vs CPU Utilization
        new Chart(document.getElementById('workloadCpuChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Throughput (req/s)', data: overallTs.throughput.slice(0, azCpu.length), borderColor: '#6366f1', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'CPU %', data: azCpu, borderColor: '#ef4444', borderWidth: 2, borderDash: [4,4], fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'req/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', min: 0, max: 100, title: {{ display: true, text: 'CPU %' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 3. Throughput vs Response Time
        new Chart(document.getElementById('tpRtChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Throughput (req/s)', data: overallTs.throughput.slice(0, azCpu.length), borderColor: '#10b981', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'Avg RT (ms)', data: overallTs.avg_rt.slice(0, azCpu.length), borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'req/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Avg RT (ms)' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 4. Disk I/O & Queue Depth
        new Chart(document.getElementById('diskChart'), {{
            type: 'bar',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ type: 'bar', label: 'Disk Read (MB/s)', data: azDiskRead, backgroundColor: 'rgba(59,130,246,0.6)', yAxisID: 'y' }},
                    {{ type: 'bar', label: 'Disk Write (MB/s)', data: azDiskWrite, backgroundColor: 'rgba(16,185,129,0.6)', yAxisID: 'y' }},
                    {{ type: 'line', label: 'Queue Depth', data: azDiskQ, borderColor: '#ef4444', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'MB/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Queue Depth' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 5. Network Throughput
        new Chart(document.getElementById('netChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Network In (MB)', data: azNetIn, borderColor: '#06b6d4', backgroundColor: 'rgba(6,182,212,0.12)', borderWidth: 2, fill: true, tension: 0.3 }},
                    {{ label: 'Network Out (MB)', data: azNetOut, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.12)', borderWidth: 2, fill: true, tension: 0.3 }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ grid: {{ color: gridColor }}, title: {{ display: true, text: 'MB' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    }}
    
    // ── Edit Mode Logic ──
    let editMode = false;
    function toggleEditMode() {{
        editMode = !editMode;
        document.body.classList.toggle('edit-mode-active', editMode);
        const editBtn = document.getElementById('editBtn');
        if (editBtn) editBtn.innerText = editMode ? '💾 Save Edits' : '✏️ Edit Report';
        const badge = document.getElementById('editModeBadge');
        if (badge) badge.style.display = editMode ? 'inline-block' : 'none';
        
        document.querySelectorAll('[data-editable]').forEach(el => {{
            el.setAttribute('contenteditable', editMode ? 'true' : 'false');
        }});
    }}
    
    // Disable contenteditable on load, mark elements
    document.addEventListener("DOMContentLoaded", () => {{
        document.querySelectorAll('[contenteditable="true"]').forEach(el => {{
            el.setAttribute('data-editable', 'true');
            el.setAttribute('contenteditable', 'false');
        }});
    }});

    // ── Finding Drawer Logic ──
    const findingsData = {findings_json};
    const recsData = {recs_json};

    function showFinding(fid) {{
        const finding = findingsData.find(f => f.id === fid);
        if (!finding) return;
        
        let html = `<h2 style="margin-top:0; color:var(--text); font-size:1.4rem;">${{finding.id}}</h2>`;
        html += `<p style="font-size:1.1rem; font-weight:700; margin-bottom:1.5rem; color:var(--text);">${{finding.title}}</p>`;
        
        html += `<div class="drawer-section"><div class="drawer-h">Observation</div><p style="font-size:0.9rem; margin:0;">${{finding.observation}}</p></div>`;
        
        if (finding.evidence && finding.evidence.length > 0) {{
            html += `<div class="drawer-section"><div class="drawer-h">Evidence</div>`;
            finding.evidence.forEach(e => {{
                html += `<div style="background:var(--surface2); padding:0.5rem; border-radius:6px; margin-bottom:0.4rem; font-size:0.85rem;"><strong>${{e.metric}}:</strong> ${{e.value}} <span style="color:var(--muted); font-size:0.8rem; float:right;">${{e.source}}</span></div>`;
            }});
            html += `</div>`;
        }}

        if (finding.interpretation) {{
            html += `<div class="drawer-section"><div class="drawer-h">Interpretation</div><p style="font-size:0.9rem; margin:0;">${{finding.interpretation}}</p></div>`;
        }}
        
        if (finding.root_cause_assessment) {{
            html += `<div class="drawer-section"><div class="drawer-h">Root Cause Assessment</div><p style="font-size:0.9rem; margin:0;">${{finding.root_cause_assessment}}</p>`;
            if (finding.confidence && finding.confidence.specific_root_cause) {{
                html += `<div style="font-size:0.8rem; margin-top:0.3rem; color:var(--muted);"><strong>Confidence:</strong> ${{finding.confidence.specific_root_cause}}</div>`;
            }}
            html += `</div>`;
        }}

        if (finding.impact) {{
            html += `<div class="drawer-section"><div class="drawer-h">Impact</div><p style="font-size:0.9rem; margin:0;">${{finding.impact}}</p></div>`;
        }}

        // Find linked recommendation
        const rec = recsData.find(r => r.triggered_by && r.triggered_by.includes(fid));
        if (rec) {{
            html += `<div class="drawer-section" style="background:rgba(16,185,129,0.1); padding:1rem; border-radius:8px; border-left:4px solid #10b981;">
                <div class="drawer-h" style="color:#10b981;">Recommendation: ${{rec.id}}</div>
                <p style="font-weight:700; margin:0 0 0.5rem 0; font-size:0.9rem;">${{rec.title}}</p>
                <p style="font-size:0.85rem; margin:0 0 0.5rem 0;">${{rec.why}}</p>`;
            if (rec.action && rec.action.length > 0) {{
                html += `<ul style="font-size:0.85rem; padding-left:1.2rem; margin-bottom:0.5rem;">`;
                rec.action.forEach(a => html += `<li>${{a}}</li>`);
                html += `</ul>`;
            }}
            if (rec.validation) {{
                html += `<div style="font-size:0.85rem; margin-top:0.5rem;"><strong>Validation:</strong> ${{rec.validation}}</div>`;
            }}
            html += `</div>`;
        }}

        document.getElementById('drawerContent').innerHTML = html;
        document.getElementById('findingDrawerOverlay').style.display = 'block';
        setTimeout(() => document.getElementById('findingDrawer').classList.add('open'), 10);
    }}

    function closeFinding() {{
        document.getElementById('findingDrawer').classList.remove('open');
        setTimeout(() => document.getElementById('findingDrawerOverlay').style.display = 'none', 300);
    }}

    // ── Graph Guide Modal Logic ──
    const graphGuides = {{
        'tx-summary': {{
            title: '📊 Transaction Statistics &amp; Iteration Summary',
            what: 'Shows total request samples split into Passed (green) and Failed (red) executions for each test script.',
            howToRead: [
                'Taller green bars indicate high execution volume with successful assertions.',
                'Any red bars highlight transaction failures or assertion breaches.',
                'Exact sample counts are printed directly on top of each bar for instant reading.'
            ],
            filters: 'Hover over bars to view percentage breakdown and script error rate. Click "Pass Samples" or "Fail Samples" in the bottom legend to toggle datasets.'
        }},
        'tx-rt-breakdown': {{
            title: '⏱️ Transaction &amp; Sub-Transaction Response Time Breakdown',
            what: 'Hierarchical response time analysis from high-level User Stories down to individual child HTTP requests and sub-transactions.',
            howToRead: [
                'Data labels on top of bars display the exact response time in milliseconds.',
                'Allows pinpointing which sub-request is responsible for overall transaction slowness.'
            ],
            filters: 'Use <strong>User Story</strong> dropdown to isolate a flow, <strong>Transaction</strong> to drill down into child requests, and <strong>Metric</strong> to switch between Average RT, P90, P95, and Max RT.'
        }},
        'sla-deviation': {{
            title: '🎯 SLA Deviation by Transaction (% from Target SLA)',
            what: 'Diverging diagnostic chart measuring percentage deviation of each transaction\\'s P90 latency from its SLA target.',
            howToRead: [
                '<strong>Green bars (left/negative):</strong> Within acceptable SLA target (healthy).',
                '<strong>Red bars (right/positive):</strong> Exceeding SLA threshold (breached).'
            ],
            filters: 'Use the <strong>Filter User Story</strong> dropdown to isolate transactions in a specific user story. Hover over bars to see the exact percentage deviation and target.'
        }},
        'error-distribution': {{
            title: '🔴 Error Distribution &amp; Analysis',
            what: 'Interactive donut chart breaking down all failed requests grouped by HTTP status code, assertion failure message, or error category.',
            howToRead: [
                'Larger slices represent the predominant error types causing test degradation.',
                'Center text shows the total count of errors captured during the test.'
            ],
            filters: '<strong>Click any slice or legend item</strong> to populate the right-hand drill-down panel with affected transactions, timestamps, and assertion details.'
        }},
        'server-side': {{
            title: '🖥️ Server Side CPU &amp; Memory Utilization',
            what: 'Simultaneous dual-line time series tracking host CPU utilization (%) in amber and Memory utilization (%) in blue.',
            howToRead: [
                'Values sustained above 80% indicate high resource pressure.',
                'Spikes aligning with test load indicate infrastructure bottlenecks.'
            ],
            filters: 'Hover along the timeline to inspect synchronized CPU and Memory % at any specific test second.'
        }},
        'concurrency': {{
            title: '👥 Estimated Concurrent Users Over Time',
            what: 'Calculated active concurrent user load across the test duration derived from throughput and response time (Little\\'s Law).',
            howToRead: [
                'Displays ramp-up phase, steady-state plateau, and ramp-down.',
                'Sudden drops or fluctuations highlight client-side or server-side stalls.'
            ],
            filters: 'Hover over data points to check estimated active users at each interval.'
        }},
        'throughput': {{
            title: '📊 Throughput &amp; Errors Over Time',
            what: 'Request throughput (req/sec in blue/indigo) and error occurrences (in red) minute-by-minute throughout the execution.',
            howToRead: [
                'Throughput should remain steady or scale with concurrent user ramp-up.',
                'Red bars indicate the exact timeframe when errors occurred.'
            ],
            filters: 'Use the top-right <strong>Transaction</strong> dropdown to view throughput and error trends for a specific transaction or the entire test.'
        }},
        'rt-over-time': {{
            title: '📈 Response Time Trend Over Time',
            what: 'Multi-line timeline tracking Average RT (indigo), 95th Percentile P95 (amber), and 99th Percentile P99 (red dashed).',
            howToRead: [
                'Flat, low lines indicate stable performance under load.',
                'Rising slopes or sharp spikes reveal latency degradation or server queueing.'
            ],
            filters: 'Use the <strong>Transaction</strong> dropdown to focus on an individual transaction. Click legend items to toggle P95/P99 visibility.'
        }},
        'critical-tx': {{
            title: '🔥 Critical Transaction Response Time',
            what: 'Response time trends for high-priority or slowest transactions plotted alongside dashed red SLA target lines.',
            howToRead: [
                'Lines rising above the dashed red SLA line signify performance SLA breaches.',
                'Summary badges at top show critical count, average, P95, and max response times.'
            ],
            filters: 'Click the <strong>Transaction Chips</strong> above the chart to toggle specific transactions on/off, or click "Show All".'
        }},
        'rt-hist': {{
            title: '📊 Response Time Distribution Histogram',
            what: 'Request count distribution grouped into response time latency buckets (from <500ms up to >5000ms).',
            howToRead: [
                'Skew towards green/blue buckets (<500ms-1s) means fast user experience.',
                'Skew towards amber/red (>2s) shows tail latency delays affecting users.'
            ],
            filters: 'Hover over each latency bucket bar to see exact request volume and distribution.'
        }},
        'top-tx': {{
            title: '🏷️ Top Transactions by Response Time',
            what: 'Horizontal bar ranking of slowest transactions ordered by average response time.',
            howToRead: [
                'Quickly identifies top optimization candidates and slowest user actions in the application.'
            ],
            filters: 'Hover over bars to inspect average response times in milliseconds.'
        }},
        'sla-donut': {{
            title: 'SLA Deviation &amp; Breach Severity Donut',
            what: 'Overall SLA compliance score and distribution of transactions across SLA severity categories (Passed, Minor, Moderate, Critical).',
            howToRead: [
                'Center percentage shows overall SLA compliance (>=85% is passing).',
                'Side cards break down exact transaction counts in each breach tier.'
            ],
            filters: 'Hover over donut segments to inspect individual tier counts.'
        }},
        'error-rate-tx': {{
            title: '🔴 Error Rate by Transaction (%)',
            what: 'Horizontal bar chart showing failure rate percentage for transactions that experienced errors.',
            howToRead: [
                'Highlights which specific transactions suffered the highest failure rates during the test.'
            ],
            filters: 'Hover over bars to view exact failure percentages.'
        }},
        'azure-cpu-mem': {{
            title: '🖥️ Azure Resource Utilization (CPU &amp; Memory)',
            what: 'Full-width dual time series of server CPU % (amber) and Memory % (blue) with threshold bands (80% and 90%).',
            howToRead: [
                'Sustained periods above 80% indicate resource starvation causing response time degradation.'
            ],
            filters: 'Hover across the timeline to see exact CPU and memory % at each sample timestamp.'
        }},
        'workload-cpu': {{
            title: '📈 Workload vs CPU Utilization',
            what: 'Dual-axis chart comparing JMeter request throughput (req/s on left axis) against Azure CPU % (on right axis).',
            howToRead: [
                'Reveals whether CPU utilization scales proportionally with client load or saturates early.'
            ],
            filters: 'Hover across points to compare req/sec against host CPU load simultaneously.'
        }},
        'tp-rt-impact': {{
            title: '⚡ Throughput vs Response Time',
            what: 'Request throughput (req/s) plotted against Average Response Time (ms).',
            howToRead: [
                'If throughput flattens while response time climbs, the application has reached its maximum capacity/saturation point.'
            ],
            filters: 'Hover to inspect throughput and latency correlation at any second.'
        }},
        'disk-io': {{
            title: '💾 Disk I/O &amp; Queue Contention',
            what: 'Disk Read (MB/s) and Write (MB/s) bars alongside Disk Queue Depth line on secondary axis.',
            howToRead: [
                'Queue Depth > 2-5 indicates disk I/O bottlenecks and storage queueing delays.'
            ],
            filters: 'Hover over bars and line to inspect storage transfer rates and queue length.'
        }},
        'network-tp': {{
            title: '🌐 Network Throughput (In/Out)',
            what: 'Inbound (cyan) and Outbound (purple) network transfer volume in megabytes over time.',
            howToRead: [
                'Highlights network bandwidth usage and identifies potential network saturation.'
            ],
            filters: 'Hover across timestamps to check network MB transferred at each point.'
        }}
    }};

    function openGraphModal(key) {{
        const guide = graphGuides[key];
        if (!guide) return;

        document.getElementById('graphModalTitle').innerHTML = guide.title;
        
        let howToReadList = '';
        if (Array.isArray(guide.howToRead)) {{
            howToReadList = '<ul class="graph-modal-list">' + guide.howToRead.map(item => `<li>${{item}}</li>`).join('') + '</ul>';
        }} else {{
            howToReadList = `<p class="graph-modal-text">${{guide.howToRead}}</p>`;
        }}

        let html = `
            <div class="graph-modal-section">
                <div class="graph-modal-section-title">📊 What This Graph Shows</div>
                <p class="graph-modal-text">${{guide.what}}</p>
            </div>
            <div class="graph-modal-section">
                <div class="graph-modal-section-title">🔍 How To Read It</div>
                ${{howToReadList}}
            </div>
        `;

        if (guide.filters) {{
            html += `
                <div class="graph-modal-section">
                    <div class="graph-modal-section-title">🎛️ Filters &amp; Interactions</div>
                    <p class="graph-modal-text">${{guide.filters}}</p>
                </div>
            `;
        }}

        document.getElementById('graphModalBody').innerHTML = html;
        const overlay = document.getElementById('graphModalOverlay');
        overlay.style.display = 'flex';
        setTimeout(() => overlay.classList.add('open'), 10);
    }}

    function closeGraphModal(event) {{
        if (event && event.target && event.target.id !== 'graphModalOverlay' && !event.target.classList.contains('graph-modal-close')) {{
            return;
        }}
        const overlay = document.getElementById('graphModalOverlay');
        overlay.classList.remove('open');
        setTimeout(() => {{ overlay.style.display = 'none'; }}, 200);
    }}

    document.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape') closeGraphModal();
    }});
</script>
</body>
</html>"""

    report_path.write_text(html, encoding="utf-8")
    return report_path
