#!/usr/bin/env python3
"""
report_generator.py — HTML Performance Report Generator for JmeterAI.

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

    for lname, ldata in sorted(display_labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True):
        target = sla_targets.get(lname, {"rt": default_rt, "err": default_err, "minor_pct": 100.0, "mod_pct": 200.0, "crit_pct": 300.0})
        target_rt = target.get("rt", default_rt)
        target_err = target.get("err", default_err)
        minor_pct  = target.get("minor_pct", 100.0)
        mod_pct    = target.get("mod_pct", 200.0)
        crit_pct   = target.get("crit_pct", 300.0)
        
        p90_val = ldata.get("p90", 0)
        p95_val = ldata.get("p95", 0)
        avg_rt_val = ldata.get("avg_rt", 0)
        err_rate_val = ldata.get("error_rate", 0)

        # Exact Apdex score calculation using raw JTL iteration samples if present, else fallback
        samples = ldata.get("samples")
        success_flags = ldata.get("success_flags")
        if samples:
            apdex_res = calculate_apdex(samples, success_flags, target_t=target_rt)
            apdex_score = apdex_res["apdex"]
        else:
            apdex_score = calculate_apdex_from_summary(avg_rt_val, p90_val, err_rate_val, target_t=target_rt)
            
        all_apdex_scores.append(apdex_score)
        apdex_cls = "pass" if apdex_score >= 0.85 else "fail" if apdex_score < 0.70 else ""
        
        # Calculate Deviation %
        deviation_pct = ((p90_val - target_rt) / target_rt * 100) if target_rt > 0 else 0
        err_breached = err_rate_val > target_err
        
        # Determine classification
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
            is_breached = False # It's a deviation, but "acceptable", so it doesn't fail the transaction overall
        else:
            is_breached = False
        
        p90_breached = deviation_pct > 30 # For CSS styling

        if is_breached or deviation_pct > 30:
            tx_breached_count += 1 if is_breached else 0

            # Collect child HTTP samplers if this is a Transaction Controller
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

        sla_status_html = f'<span style="color: {severity_color}; font-weight:700;">{severity_label}</span>'
        err_cls = "pass" if not err_breached else "fail"
        rt_cls = "pass" if not p90_breached else "fail"

        # Match child samplers / sub-requests for table tree dropdown
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

        child_tbl_rows = ""
        c_cls_id = f"child-row-group-{hash(lname) & 0xffffffff}"
        if matched_table_children:
            for cs_k, cs_v in matched_table_children.items():
                c_err_cls = "pass" if cs_v.get('error_rate', 0) <= 1 else "fail"
                child_tbl_rows += f"""
                <tr class="{c_cls_id}" style="display: none; background: var(--surface2); font-size: 0.76rem;">
                    <td style="padding-left: 2rem;">↳ <code>{cs_k}</code></td>
                    <td>{cs_v.get('count', 0):,}</td>
                    <td>-</td>
                    <td>{cs_v.get('avg_rt', 0):.0f} ms</td>
                    <td><strong>{cs_v.get('p90', 0)} ms</strong></td>
                    <td>{cs_v.get('p95', 0)} ms</td>
                    <td>{cs_v.get('p99', 0)} ms</td>
                    <td>{cs_v.get('min_rt', 0)} ms</td>
                    <td>{cs_v.get('max_rt', 0)} ms</td>
                    <td class="{c_err_cls}">{cs_v.get('error_rate', 0):.2f}%</td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                </tr>"""

        toggle_tbl_btn = f"""<button onclick="var rows=document.getElementsByClassName('{c_cls_id}'); var isHidden=rows[0].style.display==='none'; for(var i=0;i<rows.length;i++){{rows[i].style.display=isHidden?'table-row':'none';}} this.innerText=isHidden?'▲ Hide ({len(matched_table_children)})':'▼ Requests ({len(matched_table_children)})';" style="background:var(--surface2); border:1px solid var(--border); color:var(--accent); border-radius:4px; padding:0.15rem 0.4rem; font-size:0.72rem; cursor:pointer; font-weight:600; margin-left:0.5rem;">▼ Requests ({len(matched_table_children)})</button>""" if child_tbl_rows else ''

        # Store finding badge placeholder — actual badge built after findings_engine runs
        _finding_badge_key = f"__FINDING_BADGE_{lname}__"
        
        dev_color = "var(--red)" if deviation_pct > 90 else "var(--yellow)" if deviation_pct > 30 else "var(--green)"
        deviation_html = f'<span style="color:{dev_color}; font-weight:600;">{deviation_pct:+.1f}%</span>'

        labels_rows += f"""
        <tr>
            <td><strong>{lname}</strong> {toggle_tbl_btn}</td>
            <td>{ldata['count']:,}</td>
            <td class="{apdex_cls}"><strong>{apdex_score:.2f}</strong></td>
            <td class="{rt_cls}">{ldata['avg_rt']:.0f} ms</td>
            <td class="{rt_cls}"><strong>{ldata['p90']} ms</strong></td>
            <td>{ldata['p95']} ms</td>
            <td>{ldata['p99']} ms</td>
            <td>{ldata['min_rt']} ms</td>
            <td>{ldata['max_rt']} ms</td>
            <td class="{err_cls}">{ldata['error_rate']:.2f}%</td>
            <td>{target_rt:.0f} ms</td>
            <td>{deviation_html}</td>
            <td>{sla_status_html}</td>
        </tr>
        {child_tbl_rows}"""

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

    # Error Analysis Donut: per-error-type breakdown from JTL parsing
    error_details_raw = parsed.get("error_details", {})
    # Sort by count descending, take top 10
    error_types_sorted = sorted(error_details_raw.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    total_errors_all = sum(ed["count"] for _, ed in error_types_sorted) if error_types_sorted else 0
    
    summary_errs = summary.get("tc_errors", summary.get("errors", 0))
    display_total_errors = max(total_errors_all, summary_errs)
    
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

    # Concurrency Estimate Over Time using Little's Law: N = throughput × avg_rt/1000
    ts_tp_raw  = ts.get("ts_throughput", [])
    ts_rt_raw  = ts.get("ts_avg_rt", [])
    concurrency_est = json.dumps([
        round(tp * (rt / 1000.0), 1) if (tp and rt) else 0
        for tp, rt in zip(ts_tp_raw, ts_rt_raw)
    ])

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
        rc_ev = ""
        if overall_rc.get("evidence"):
            rc_ev = "<div style='margin-top:0.8rem; font-size:0.8rem; color:var(--muted);'><strong>Evidence:</strong> " + " &middot; ".join(overall_rc["evidence"]) + "</div>"
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
        evidence_chips = " &middot; ".join([f'<span class="evidence-chip">{e}</span>' for e in rt_obs.get("evidence", [])])
        related_badge = f'<span class="finding-badge-inline" onclick="showFinding(\'{rt_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {rt_obs.get("related_finding", "")}</span>' if rt_obs.get("related_finding") else ""
        rt_observation_html = f'''
        <div class="ai-observation-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <h4 style="margin:0; font-size:0.88rem; font-weight:700; color:var(--accent);">🧠 AI Observation</h4>
                {related_badge}
            </div>
            <p style="font-weight:600; font-size:0.85rem; margin-bottom:0.6rem; color:var(--text);">{rt_obs.get("title", "")}</p>
            <div class="evidence-grid">{evidence_chips}</div>
            <blockquote class="ai-interpretation">{rt_obs.get("interpretation", "")}</blockquote>
        </div>
        '''

    tp_obs = chart_observations.get("throughput", {})
    tp_observation_html = ""
    if tp_obs:
        tp_evidence_chips = " &middot; ".join([f'<span class="evidence-chip">{e}</span>' for e in tp_obs.get("evidence", [])])
        tp_related_badge = f'<span class="finding-badge-inline" onclick="showFinding(\'{tp_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {tp_obs.get("related_finding", "")}</span>' if tp_obs.get("related_finding") else ""
        tp_observation_html = f'''
        <div class="ai-observation-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <h4 style="margin:0; font-size:0.88rem; font-weight:700; color:var(--accent);">🧠 AI Observation</h4>
                {tp_related_badge}
            </div>
            <div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">Observation:</strong> <span style="font-size:0.82rem;">{tp_obs.get("observation", "")}</span></div>
            <div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">Interpretation:</strong> <span style="font-size:0.82rem;">{tp_obs.get("interpretation", "")}</span></div>
            <div style="margin-bottom:0.5rem;"><strong style="font-size:0.82rem;">AI Assessment:</strong> <span style="font-size:0.82rem; font-weight:600;">{tp_obs.get("assessment", "")}</span></div>
            <div><strong style="font-size:0.82rem;">Next Validation:</strong> <span style="font-size:0.82rem; color:var(--muted);">{tp_obs.get("next_validation", "")}</span></div>
            <div class="evidence-grid" style="margin-top:0.5rem;">{tp_evidence_chips}</div>
        </div>
        '''

    infra_obs = chart_observations.get("infrastructure")
    infra_observation_html = ""
    if infra_obs:
        infra_related = f'<span class="finding-badge-inline" onclick="showFinding(\'{infra_obs.get("related_finding", "")}\');" style="cursor:pointer;">🔍 {infra_obs.get("related_finding", "")}</span>' if infra_obs.get("related_finding") else ""
        infra_observation_html = f'''
        <div class="ai-observation-panel" style="margin-top:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <h4 style="margin:0; font-size:0.88rem; font-weight:700; color:var(--accent);">🧠 Infrastructure Observation</h4>
                {infra_related}
            </div>
            <div style="margin-bottom:0.4rem;"><strong style="font-size:0.82rem;">Observation:</strong> <span style="font-size:0.82rem;">{infra_obs.get("observation", "")}</span></div>
            <div><strong style="font-size:0.82rem;">Assessment:</strong> <span style="font-size:0.82rem; font-weight:600;">{infra_obs.get("assessment", "")}</span></div>
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

    # Build sub-map only for displayed labels, keyed by numeric index
    display_ts_map = {}
    for idx_i, l_name in enumerate(display_label_names):
        if l_name in label_ts_map:
            entry = dict(label_ts_map[l_name])
            entry["label"] = l_name
            display_ts_map[idx_i] = entry
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


    # Serialize findings and recommendations for JS Findings Drawer
    findings_json = json.dumps(all_findings).replace("</script>", "<\\/script>")
    recs_json = json.dumps(ai_insights.get("recommendations", [])).replace("</script>", "<\\/script>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{jmx_name} — Performance Report | JmeterAI</title>
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
    </style>
</head>
<body>
<div class="report-container">

    <!-- Header -->
    <div class="report-header glass-panel" style="display:flex; justify-content:space-between; align-items:center; padding:1rem 1.5rem; margin-bottom:1rem;">
        <div class="header-left" style="display:flex; align-items:center; gap:1.25rem;">
            <div class="engine-badge" style="font-weight:800; font-size:1.2rem; color:var(--accent);">⚡ JMeter AI</div>
            <div style="border-left:2px solid var(--border); padding-left:1.25rem;">
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em;">Project Details &amp; Execution Time</div>
                <div style="font-size:1rem; font-weight:700; color:var(--text); margin:0.1rem 0;">Application Name: {jmx_name} &nbsp;|&nbsp; Module Executed: <span contenteditable="true">Load Test Module</span></div>
                <div style="font-size:0.78rem; color:var(--muted);">
                    <strong>Start Time:</strong> {summary.get('start_time', execution_time)} &nbsp;|&nbsp; <strong>End Time:</strong> {summary.get('end_time', execution_time)} &nbsp;|&nbsp; <strong>Run ID:</strong> {run_id}
                </div>
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
            <table style="margin-bottom:1rem; font-size:0.85rem;">
                <thead>
                    <tr><th>Parameter</th><th>Value</th><th>Parameter</th><th>Value</th></tr>
                </thead>
                <tbody>
                    <tr><td style="font-weight:700;">Test Name</td><td>{jmx_name}</td><td style="font-weight:700;">Total Iterations</td><td>{summary.get('total_iterations', summary.get('total', 0)):,}</td></tr>
                    <tr><td style="font-weight:700;">Test Type</td><td contenteditable="true">Load Test</td><td style="font-weight:700;">Total Requests</td><td>{summary.get('total', 0):,}</td></tr>
                    <tr><td style="font-weight:700;">Duration</td><td>{summary.get('duration_sec', 0):.0f} seconds</td><td style="font-weight:700;">Total Transactions</td><td>{total_tx_count}</td></tr>
                    <tr><td style="font-weight:700;">Peak Users</td><td>{users} users</td><td style="font-weight:700;">Failed Transactions</td><td>{summary.get('tc_errors', summary.get('errors', 0)):,}</td></tr>
                    <tr><td style="font-weight:700;">Ramp-up / Down</td><td contenteditable="true">Manual Input</td><td style="font-weight:700;">Environment</td><td contenteditable="true">Staging</td></tr>
                </tbody>
            </table>
        </div>

        <!-- 2. Test Objective -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <h2>🎯 Test Objective</h2>
            <div style="font-size:0.88rem; line-height:1.6; padding:0.4rem 0;" contenteditable="true">
                Validate system performance, throughput stability, response time SLA compliance, and error rates of {jmx_name} under peak load conditions.
            </div>
        </div>

        <!-- 3. Performance Scorecard & SLA Violation Grid (Grouped 3x3 Layout) -->
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

        <!-- 4. Iteration Statistics & Transaction Statistics Table/Chart (Exact Wireframe Format) -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <h2>📊 Transaction Statistics &amp; Iteration Summary</h2>
            
            <div style="overflow-x:auto; margin-bottom:1.5rem;">
                <table style="width:100%; border-collapse:collapse; font-size:0.83rem; border:1px solid var(--border);">
                    <thead>
                        <tr style="background:var(--surface2); border-bottom:1px solid var(--border);">
                            <th rowspan="2" style="text-align:left; padding:0.6rem; border-right:1px solid var(--border);">Scripts Name</th>
                            <th rowspan="2" style="text-align:center; padding:0.6rem; border-right:1px solid var(--border);">Duration of Run (Min)</th>
                            <th rowspan="2" style="text-align:center; padding:0.6rem; border-right:1px solid var(--border);">Users</th>
                            <th colspan="3" style="text-align:center; padding:0.4rem; border-bottom:1px solid var(--border); border-right:1px solid var(--border);">Samples</th>
                            <th rowspan="2" style="text-align:center; padding:0.6rem;">Error Percentage (%)</th>
                        </tr>
                        <tr style="background:var(--surface2); border-bottom:2px solid var(--border);">
                            <th style="text-align:center; padding:0.4rem; border-right:1px solid var(--border);">Total</th>
                            <th style="text-align:center; padding:0.4rem; color:var(--green); border-right:1px solid var(--border);">Pass</th>
                            <th style="text-align:center; padding:0.4rem; color:var(--red); border-right:1px solid var(--border);">Fail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tx_stat_rows_html}
                    </tbody>
                </table>
            </div>

            <h3 style="margin:1.2rem 0 0.6rem 0; font-size:1.05rem; font-weight:700; text-align:center;">Transaction Summary</h3>
            <div style="position:relative; height:340px; width:100%;">
                <canvas id="chart-tx-summary-bar"></canvas>
            </div>
        </div>

        <!-- 5. SLA Deviation by Transaction (Executive Diagnostic Diverging Chart) -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom:0.75rem;">
                <div>
                    <h2 style="margin:0;">🎯 SLA Deviation by Transaction (% from Target SLA)</h2>
                    <div style="font-size:0.78rem; color:var(--muted); margin-top:0.2rem;">Diverging diagnostic chart normalized as (P90 Response Time &divide; Target SLA - 1) &times; 100%. Sorted by worst breach.</div>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
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

        <!-- 6. Error Stats Graph -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <h2>🔴 Error Stats Graph</h2>
            <div style="position:relative; height:260px; width:100%; margin-top:0.75rem;">
                <canvas id="chart-errors-exec"></canvas>
            </div>
        </div>

        <!-- 7. Server Side Graphs -->
        <div class="section glass-panel" style="margin-top:1.25rem;">
            <h2>🖥️ Server Side Graphs</h2>
            <div style="position:relative; height:260px; width:100%; margin-top:0.75rem;">
                <canvas id="chart-infra-exec"></canvas>
            </div>
        </div>

    </div>


        <!-- Recommendations -->
        <div class="section glass-panel" style="margin-top: 1.5rem; border-left: 4px solid var(--green);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <h2 style="margin:0;" contenteditable="true">💡 Recommendations</h2>
                <button class="delete-rec-btn" onclick="if(confirm('Delete Recommendations section?')) this.closest('.section').remove();" style="background:rgba(239,68,68,0.1); color:#ef4444; border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:0.25rem 0.6rem; font-size:0.75rem; cursor:pointer; font-weight:600;">🗑️ Delete Section</button>
            </div>
            <div class="rec-grid" contenteditable="true">{linked_recs_html if linked_recs_html else recs_html}</div>
        </div>
        
        <!-- Limitations Disclaimer -->
        <div style="font-size:0.75rem; color:var(--muted); margin-top: 1.5rem; text-align:center;">
            <strong>Test Limitations:</strong> Capacity estimates and performance thresholds are extrapolated from a single load profile. They represent observed pressure points, not certified maximums. Validated root-cause analysis requires infrastructure telemetry alignment.
        </div>
    </div>

    <!-- TAB 2: User Load Distribution -->
    <div id="rpt-load" class="tab-pane hidden">
        <div class="section glass-panel" style="margin-bottom: 1.5rem;">
            <h2>📐 Capacity Planning</h2>
            <table style="font-size: 0.85rem;">
                <thead>
                    <tr><th>Metric</th><th>Status</th><th>Notes</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Observed Concurrency</strong></td><td>{users} users</td><td>Tested concurrency level.</td></tr>
                    <tr><td><strong>Safe Concurrency</strong></td><td>Not determined</td><td>Cannot be established without stepped load testing.</td></tr>
                    <tr><td><strong>Saturation Point</strong></td><td>Not determined</td><td>System saturation was not strictly observed.</td></tr>
                </tbody>
            </table>
            <p style="font-size: 0.82rem; color: var(--muted); margin-top: 0.5rem;">Capacity boundaries require incremental stress testing.</p>
        </div>
        <div class="chart-box glass-panel" style="position: relative; min-height: 280px;">
            <h3>👥 Estimated Concurrent Users Over Time <small style="font-size:0.7rem; color:var(--muted); font-weight:400;">(Little's Law)</small></h3>
            <div style="position: relative; height: 260px; width: 100%;">
                <canvas id="concChart"></canvas>
            </div>
        </div>
    </div>

    <!-- TAB 3: Transaction Stats -->
    <div id="rpt-tx" class="tab-pane hidden">
        <div class="kpi-grid">
            <div class="kpi-card glass-panel"><div class="kpi-label">Total Iterations</div><div class="kpi-value">{summary.get('total_iterations', summary.get('total', 0)):,}</div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">Total Transactions</div><div class="kpi-value">{total_tx_count}</div></div>
        </div>
        
        <div class="chart-box glass-panel" style="margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.8rem; gap: 0.5rem;">
                <h3 style="margin:0; white-space: nowrap;">📊 Throughput & Errors</h3>
                <select id="tpSelect" onchange="updateTpChart(this.value)" style="max-width: 240px; background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.3rem 0.6rem; font-size:0.78rem; outline:none; cursor:pointer; text-overflow: ellipsis; overflow: hidden;">
                    <option value="ALL">All Transactions (Overall)</option>
                    {tx_options_html}
                </select>
            </div>
            <div style="position: relative; height: 260px; width: 100%;">
                <canvas id="tpChart"></canvas>
            </div>
            {tp_observation_html}
        </div>

        <div class="section glass-panel">
            <h2>📋 Per-Transaction Breakdown &amp; SLA Targets</h2>
            <table>
                <thead><tr>
                    <th>Transaction / Request</th><th>Samples</th><th>Apdex</th><th>Avg RT</th>
                   <th>P90</th><th>P95</th><th>P99</th>
                    <th>Min</th><th>Max</th><th>Error Rate</th><th>RT SLA</th><th>Deviation %</th><th>SLA Status</th>
                </tr></thead>
                <tbody>{labels_rows}</tbody>
            </table>
        </div>
    </div>

    <!-- TAB 4: Response Time Stats -->
    <div id="rpt-rt" class="tab-pane hidden">
        <div class="kpi-grid">
            <div class="kpi-card glass-panel"><div class="kpi-label">Avg Response Time</div><div class="kpi-value {'pass' if avg_rt <= 500 else 'warn' if avg_rt <= 2000 else 'fail'}">{avg_rt:.0f}<span style="font-size:0.9rem"> ms</span></div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">P95 Response</div><div class="kpi-value">{summary.get('p95', 0)}<span style="font-size:0.9rem"> ms</span></div></div>
            <div class="kpi-card glass-panel"><div class="kpi-label">P99 Response</div><div class="kpi-value">{summary.get('p99', 0)}<span style="font-size:0.9rem"> ms</span></div></div>
        </div>

        <div class="chart-box glass-panel" style="margin-bottom: 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.8rem; gap: 0.5rem;">
                <h3 style="margin:0; white-space: nowrap;">📈 Response Time Over Time</h3>
                <select id="rtSelect" onchange="updateRtChart(this.value)" style="max-width: 240px; background:var(--surface2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.3rem 0.6rem; font-size:0.78rem; outline:none; cursor:pointer; text-overflow: ellipsis; overflow: hidden;">
                    <option value="ALL">All Transactions (Overall)</option>
                    {tx_options_html}
                </select>
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
                <div>
                    <a href="#" onclick="switchReportTab('rpt-tx', document.querySelectorAll('.nav-btn')[2]); return false;" style="font-size:0.78rem; font-weight:600; color:var(--accent); text-decoration:none;">Manage Critical Transactions →</a>
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
                <h3>📊 Response Time Distribution</h3>
                <div style="position: relative; height: 220px; width: 100%;">
                    <canvas id="histChart"></canvas>
                </div>
            </div>
            <div class="chart-box glass-panel" style="position: relative; min-height: 280px;">
                <h3>🏷️ Top Transactions by Response Time</h3>
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
                <span style="font-size:0.78rem; font-weight:700; background:var(--surface2); border:1px solid var(--border); padding:0.3rem 0.75rem; border-radius:12px; color:var(--text);">{total_tx_count} Transactions</span>
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
            <h3>🔴 Error Rate by Transaction (%)</h3>
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
                <span style="font-size:0.78rem; font-weight:700; background:{'rgba(239,68,68,0.12)' if display_total_errors > 0 else 'rgba(16,185,129,0.12)'}; border:1px solid {'rgba(239,68,68,0.3)' if display_total_errors > 0 else 'rgba(16,185,129,0.3)'}; padding:0.3rem 0.75rem; border-radius:12px; color:{'#ef4444' if display_total_errors > 0 else '#10b981'};">{display_total_errors} Total Errors</span>
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
                <span style="font-size:0.75rem; font-weight:600; background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); padding:0.25rem 0.6rem; border-radius:12px;">Threshold Bands: 80% / 90%</span>
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
                <h3 style="margin:0; font-size:1rem; font-weight:700;">📈 Workload vs CPU Utilization</h3>
                <p style="margin:0.2rem 0 0.75rem 0; font-size:0.75rem; color:var(--muted);">Aligning JMeter request throughput against Azure host CPU %</p>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="workloadCpuChart"></canvas>
                </div>
            </div>

            <!-- Performance Impact (Throughput vs Response Time) -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <h3 style="margin:0; font-size:1rem; font-weight:700;">⚡ Throughput vs Response Time</h3>
                <p style="margin:0.2rem 0 0.75rem 0; font-size:0.75rem; color:var(--muted);">Analyzing capacity limits as request load increases</p>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="tpRtChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 4. Storage & Network Subsystem Grid -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Storage I/O & Queue Depth -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <h3 style="margin:0; font-size:1rem; font-weight:700;">💾 Disk I/O &amp; Queue Contention</h3>
                <p style="margin:0.2rem 0 0.75rem 0; font-size:0.75rem; color:var(--muted);">Disk Read/Write throughput (MB/s) vs Disk Queue Depth</p>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="diskChart"></canvas>
                </div>
            </div>

            <!-- Network Throughput -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <h3 style="margin:0; font-size:1rem; font-weight:700;">🌐 Network Throughput (In/Out)</h3>
                <p style="margin:0.2rem 0 0.75rem 0; font-size:0.75rem; color:var(--muted);">Inbound and Outbound network data transfer rate</p>
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
        ⚡ Generated by <strong>JmeterAI</strong> &nbsp;|&nbsp; {execution_time} &nbsp;|&nbsp; Run ID: {run_id}
    </div>
    <!-- Finding Drawer -->
    <div id="findingDrawerOverlay" onclick="closeFinding()"></div>
    <div id="findingDrawer">
        <button class="drawer-close" onclick="closeFinding()" style="position:absolute; top:1rem; right:1rem;">&times;</button>
        <div id="drawerContent"></div>
    </div>
</div>

<script>
    function switchReportTab(tabId, btn) {{
        document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
        const pane = document.getElementById(tabId);
        if (pane) pane.classList.remove('hidden');
        if (btn) btn.classList.add('active');
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

    // Executive Summary Tab 1 Critical Transactions Response Time Chart
    let critTxChartObj = null;
    const critCanvas = document.getElementById('chart-rt-exec');
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
            const shortName = txName.length > 25 ? txName.substring(0, 22) + '...' : txName;

            const chip = document.createElement('button');
            chip.type = 'button';
            chip.title = txName;
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
        
        // Render individual SLA target lines if single/few transactions are selected, or distinct targets exist
        const selectedTxs = Array.from(criticalTxSet);
        const uniqueSlaTargets = new Set(selectedTxs.map(t => txSlaMap[t] || {default_rt}));

        if (uniqueSlaTargets.size === 1) {{
            // All selected transactions share the same target value
            const targetVal = Array.from(uniqueSlaTargets)[0];
            const slaData = new Array({ts_labels}.length).fill(targetVal);
            datasets.push({{
                label: 'SLA Target (' + targetVal + ' ms)',
                data: slaData,
                borderColor: 'rgba(239, 68, 68, 0.85)',
                backgroundColor: 'rgba(239, 68, 68, 0.05)',
                borderWidth: 2,
                borderDash: [6, 6],
                pointRadius: 0,
                fill: true
            }});
        }} else {{
            // Render individual dashed target line per distinct SLA threshold
            uniqueSlaTargets.forEach(targetVal => {{
                if (targetVal) {{
                    const slaData = new Array({ts_labels}.length).fill(targetVal);
                    datasets.push({{
                        label: 'SLA Target (' + targetVal + ' ms)',
                        data: slaData,
                        borderColor: 'rgba(239, 68, 68, 0.75)',
                        borderWidth: 1.8,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }});
                }}
            }});
        }}

        // 2. Transaction Lines
        criticalTxSet.forEach(txName => {{
            let tsData = null;
            Object.values(labelTsMap).forEach(entry => {{
                if (entry.label === txName) tsData = entry.ts_avg_rt;
            }});
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
                    pointRadius: 2.5
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

    // Throughput Chart Instance
    const tpChartObj = new Chart(document.getElementById('tpChart'), {{
        type: 'bar',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'Throughput (req/s)', data: overallTs.throughput, backgroundColor: 'rgba(99,102,241,0.6)', borderRadius: 4 }},
                {{ label: 'Errors', data: overallTs.errors, backgroundColor: 'rgba(239,68,68,0.6)', borderRadius: 4 }}
            ]
        }},
        options: {{ responsive: true, scales: {{ y: {{ grid: {{ color: gridColor }} }}, x: {{ grid: {{ 'display': false }} }} }} }}
    }});

    function updateTpChart(val) {{
        let d = overallTs;
        if (val !== 'ALL') {{
            const idx = parseInt(val, 10);
            const entry = labelTsMap[idx];
            if (entry) d = {{ throughput: entry.ts_throughput, errors: entry.ts_errors }};
        }}
        tpChartObj.data.datasets[0].data = [...d.throughput];
        tpChartObj.data.datasets[1].data = [...d.errors];
        tpChartObj.update('active');
    }}

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

    // Transaction Summary Grouped Bar Chart (Pass vs Fail with Data Labels)
    new Chart(document.getElementById('chart-tx-summary-bar'), {{
        type: 'bar',
        data: {{
            labels: {tx_chart_labels_json},
            datasets: [
                {{
                    label: 'Pass',
                    data: {tx_chart_pass_json},
                    backgroundColor: '#10b981',
                    borderColor: '#059669',
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.6
                }},
                {{
                    label: 'Fail',
                    data: {tx_chart_fail_json},
                    backgroundColor: '#ef4444',
                    borderColor: '#dc2626',
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.6
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ font: {{ weight: 'bold' }} }} }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 25, font: {{ size: 10 }} }} }},
                y: {{ grid: {{ color: gridColor }}, beginAtZero: true, title: {{ display: true, text: 'Sample Count' }} }}
            }}
        }}
    }});



    new Chart(document.getElementById('chart-errors-exec'), {{
        type: 'bar',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'Error Count', data: overallTs.errors, backgroundColor: 'rgba(239,68,68,0.75)', borderRadius: 4 }}
            ]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: gridColor }} }}, x: {{ grid: {{ display: false }} }} }} }}
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

    // ── Error Distribution Donut Chart with Interactive Drill-Down ──
    const errDonutLabels = {error_donut_labels};
    const errDonutCounts = {error_donut_counts};
    const errDrillData = {error_drill_json};
    const errDonutColors = ['#ef4444','#f97316','#f59e0b','#8b5cf6','#3b82f6','#06b6d4','#10b981','#ec4899','#84cc16','#64748b'];
    const startEpochMs = {start_epoch_ms};
    const displayTotalErrors = {display_total_errors};

    if (errDonutLabels.length > 0) {{
        const errorDonutCtx = document.getElementById('errorDonutChart');
        const errorDonutObj = new Chart(errorDonutCtx, {{
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
        const legendEl = document.getElementById('errorDonutLegend');
        if (legendEl) {{
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
        // Legacy fallback - we have errors, but no granular details
        const errorDonutEl = document.getElementById('errorDonutChart');
        if (errorDonutEl) {{
            errorDonutEl.parentElement.parentElement.parentElement.parentElement.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1.05rem; font-weight:700;">Error Distribution &amp; Analysis</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Granular error data unavailable (legacy run)</p>
                    </div>
                    <span style="font-size:0.78rem; font-weight:700; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); padding:0.3rem 0.75rem; border-radius:12px; color:#f59e0b;">${{displayTotalErrors}} Total Errors</span>
                </div>
                <div style="text-align:center; padding:2.5rem 1rem; color:var(--muted);">
                    <div style="font-size:3rem; margin-bottom:0.5rem; opacity:0.7;">⚠️</div>
                    <div style="font-size:1.1rem; font-weight:700; color:var(--text);">${{displayTotalErrors}} Errors Detected</div>
                    <div style="font-size:0.82rem; margin-top:0.3rem;">Granular error distribution is not available for this run.<br>Please re-execute the test to capture detailed error analytics.</div>
                </div>`;
        }}
    }} else {{
        // No errors - show success state
        const errorDonutEl = document.getElementById('errorDonutChart');
        if (errorDonutEl) {{
            errorDonutEl.parentElement.parentElement.parentElement.parentElement.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1.05rem; font-weight:700;">Error Distribution &amp; Analysis</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">No errors detected during test execution</p>
                    </div>
                    <span style="font-size:0.78rem; font-weight:700; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:0.3rem 0.75rem; border-radius:12px; color:#10b981;">0 Errors</span>
                </div>
                <div style="text-align:center; padding:2.5rem 1rem; color:var(--muted);">
                    <div style="font-size:3rem; margin-bottom:0.5rem;">✅</div>
                    <div style="font-size:1.1rem; font-weight:700; color:#10b981;">Zero Errors Detected</div>
                    <div style="font-size:0.82rem; margin-top:0.3rem;">All requests completed successfully during this test execution.</div>
                </div>`;
        }}
    }}

    function showErrorDrillDown(errorKey, accentColor) {{
        const panel = document.getElementById('errorDrillPanel');
        if (!panel) return;
        const data = errDrillData[errorKey];
        if (!data) {{ panel.innerHTML = '<p style="color:var(--muted); text-align:center;">No drill-down data available for this error.</p>'; return; }}

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
                ${{data.code ? '<strong>HTTP Code:</strong> ' + data.code + ' &nbsp;|&nbsp; ' : ''}}<strong>Affected Transactions:</strong> ${{txEntries.length}}
            </div>
            <div style="overflow-x:auto; border-radius:6px; border:1px solid var(--border);">
                <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                    <thead>
                        <tr style="background:var(--bg); border-bottom:2px solid var(--border);">
                            <th style="padding:0.45rem 0.5rem; text-align:left; font-weight:700; font-size:0.75rem; color:var(--muted);">Transaction</th>
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
    }}

    // 5. Concurrency Estimate Over Time (Little's Law)
    const concData = {concurrency_est};
    if (concData.some(v => v > 0)) {{
        new Chart(document.getElementById('concChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels},
                datasets: [{{
                    label: 'Est. Concurrent Users',
                    data: concData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139,92,246,0.12)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                    pointBackgroundColor: '#8b5cf6'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ labels: {{ color: textColor }} }} }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: textColor }} }},
                    y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Users', color: textColor }}, beginAtZero: true }}
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
</script>
</body>
</html>"""

    report_path.write_text(html, encoding="utf-8")
    return report_path
