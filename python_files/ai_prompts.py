#!/usr/bin/env python3
"""
ai_prompts.py — Standardized Prompt Engineering & Templates for PerfPilot AI Engine.

Centralizes prompt definitions, JSON schema specifications, and dynamic context assembly
to keep core AI service logic concise and modular.
"""

import json
from typing import Dict, Any, List, Optional


def _format_time_series_progression(time_series: dict) -> str:
    """Format summarized progression table from JMeter time_series data."""
    if not time_series or not isinstance(time_series, dict):
        return "  Time-series telemetry not available"

    labels = time_series.get("ts_labels", [])
    if not labels or not isinstance(labels, list):
        return "  Time-series telemetry not available"

    avg_rts = time_series.get("ts_avg_rt", [])
    p95_rts = time_series.get("ts_p95_rt", [])
    p99_rts = time_series.get("ts_p99_rt", [])
    tps = time_series.get("ts_throughput", [])
    errors = time_series.get("ts_errors", [])
    threads = time_series.get("ts_active_threads", [])

    n = len(labels)
    if n > 16:
        step = max(1, n // 14)
        indices = list(range(0, n, step))
        if (n - 1) not in indices:
            indices.append(n - 1)
    else:
        indices = list(range(n))

    lines = [
        "  Interval | Users/Threads | Throughput (req/s) | Avg RT (ms) | P95 RT (ms) | P99 RT (ms) | Errors",
        "  ---------+---------------+--------------------+-------------+-------------+-------------+-------"
    ]
    for i in indices:
        lbl = str(labels[i]) if i < len(labels) else ""
        th = f"{threads[i]}" if i < len(threads) else "-"
        tp = f"{tps[i]:.1f}" if i < len(tps) and isinstance(tps[i], (int, float)) else "-"
        art = f"{avg_rts[i]:.0f}" if i < len(avg_rts) and isinstance(avg_rts[i], (int, float)) else "-"
        p95 = f"{p95_rts[i]:.0f}" if i < len(p95_rts) and isinstance(p95_rts[i], (int, float)) else "-"
        p99 = f"{p99_rts[i]:.0f}" if i < len(p99_rts) and isinstance(p99_rts[i], (int, float)) else "-"
        err = f"{errors[i]}" if i < len(errors) else "0"
        lines.append(f"  {lbl:<8} | {th:<13} | {tp:<18} | {art:<11} | {p95:<11} | {p99:<11} | {err}")

    return "\n".join(lines)


def _format_azure_infra_telemetry(infra: dict) -> str:
    """Format comprehensive host infrastructure and Azure telemetry."""
    if not infra or not isinstance(infra, dict):
        return "  Server-side infrastructure telemetry not configured / not available."

    lines = []
    infra_sum = infra.get("infra_summary") if "infra_summary" in infra else infra
    if isinstance(infra_sum, dict) and infra_sum:
        cpu_avg = infra_sum.get("avg_cpu", 0)
        cpu_max = infra_sum.get("max_cpu", 0)
        mem_avg = infra_sum.get("avg_memory", 0)
        mem_max = infra_sum.get("max_memory", 0)
        net_in = infra_sum.get("avg_network_in_mbps", 0)
        net_out = infra_sum.get("avg_network_out_mbps", 0)
        disk_r = infra_sum.get("avg_disk_read_iops", 0)
        disk_w = infra_sum.get("avg_disk_write_iops", 0)

        lines.append("  HOST COMPUTE SUMMARY:")
        lines.append(f"    - CPU Utilization: Average={cpu_avg:.1f}%, Peak Maximum={cpu_max:.1f}% {'🔴 SATURATED (>80%)' if cpu_max > 80 else '🟢 HEALTHY'}")
        lines.append(f"    - Memory Utilization: Average={mem_avg:.1f}%, Peak Maximum={mem_max:.1f}% {'🔴 HIGH (>80%)' if mem_max > 80 else '🟢 HEALTHY'}")
        lines.append(f"    - Network Traffic: Inbound={net_in:.1f} MB/min, Outbound={net_out:.1f} MB/min")
        if disk_r > 0 or disk_w > 0:
            lines.append(f"    - Storage IOPS: Read={disk_r:,.0f} IOPS, Write={disk_w:,.0f} IOPS")

    app_svc = infra.get("app_service", {})
    if isinstance(app_svc, dict) and app_svc:
        h2 = app_svc.get("http_2xx", 0)
        h4 = app_svc.get("http_4xx", 0)
        h5 = app_svc.get("http_5xx", 0)
        rt = app_svc.get("avg_response_time_ms", 0)
        lines.append("  AZURE APP SERVICE / APPLICATION GATEWAY STATUS:")
        lines.append(f"    - HTTP Responses: 2xx Success={h2:,}, 4xx Client Errors={h4:,}, 5xx Server Faults={h5:,} {'🔴 SERVER FAILURES PRESENT' if h5 > 0 else '🟢 OK'}")
        if rt:
            lines.append(f"    - Server-Side Average Latency: {rt:.1f} ms")

    az_ts = infra.get("time_series", {})
    if isinstance(az_ts, dict) and az_ts.get("timestamps"):
        timestamps = az_ts.get("timestamps", [])
        cpus = az_ts.get("cpu", [])
        mems = az_ts.get("memory", [])
        nin = az_ts.get("network_in", [])
        nout = az_ts.get("network_out", [])
        
        lines.append("  HOST INFRASTRUCTURE PROGRESSION OVER TIME:")
        lines.append("    Timestamp           | CPU (%) | Memory (%) | Net In (MB/m) | Net Out (MB/m)")
        lines.append("    --------------------+---------+------------+---------------+---------------")
        for idx in range(min(12, len(timestamps))):
            ts_str = str(timestamps[idx])[-8:] if len(str(timestamps[idx])) >= 8 else str(timestamps[idx])
            c_val = f"{cpus[idx]:.1f}%" if idx < len(cpus) and isinstance(cpus[idx], (int, float)) else "-"
            m_val = f"{mems[idx]:.1f}%" if idx < len(mems) and isinstance(mems[idx], (int, float)) else "-"
            ni_val = f"{nin[idx]:.1f}" if idx < len(nin) and isinstance(nin[idx], (int, float)) else "-"
            no_val = f"{nout[idx]:.1f}" if idx < len(nout) and isinstance(nout[idx], (int, float)) else "-"
            lines.append(f"    {ts_str:<19} | {c_val:<7} | {m_val:<10} | {ni_val:<13} | {no_val}")

    return "\n".join(lines) if lines else "  Server-side infrastructure telemetry not configured / not available."


def _format_error_breakdown(error_details: dict) -> str:
    """Format error distribution by HTTP code and affected transactions."""
    if not error_details or not isinstance(error_details, dict):
        return "  No detailed error records captured."

    lines = []
    for code, edata in error_details.items():
        if isinstance(edata, dict):
            cnt = edata.get("count", 0)
            msg = edata.get("message", "") or edata.get("failure_message", "")
            occs = edata.get("occurrences", [])
            label_counts = {}
            for occ in occs:
                if isinstance(occ, dict) and occ.get("label"):
                    lbl = occ["label"]
                    label_counts[lbl] = label_counts.get(lbl, 0) + 1
            
            top_aff = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            aff_str = ", ".join([f"{l} ({c} errors)" for l, c in top_aff]) if top_aff else "N/A"
            
            lines.append(f"  - HTTP {code} ({cnt:,} occurrences): {msg if msg else 'Server Error'}")
            lines.append(f"    Most affected transactions: {aff_str}")
        elif isinstance(edata, list):
            lines.append(f"  - Error Code {code}: {len(edata)} occurrences")

    return "\n".join(lines) if lines else "  No error breakdown details available."


def build_insights_prompt(test_name: str, summary: dict, labels: dict,
                          time_series: dict, infra: dict, correlation: dict = None,
                          sla_targets: dict = None, default_rt: float = 500.0,
                          default_err: float = 1.0, error_details: dict = None,
                          users: int = 1, rampup: int = 0) -> str:
    """Construct prompt passing raw summarized performance, time-series, and Azure telemetry for independent AI findings discovery."""
    if sla_targets is None:
        try:
            from python_files.sla_manager import load_sla_targets
            loaded_targets, d_rt, d_err = load_sla_targets(test_name)
            sla_targets = loaded_targets or {}
            if d_rt: default_rt = d_rt
            if d_err: default_err = d_err
        except Exception:
            sla_targets = {}
    sla_targets = sla_targets or {}

    total_tx = len(labels)
    breached_txs = []
    met_txs = []

    for name, data in labels.items():
        t_conf = sla_targets.get(name, {})
        tgt_rt = t_conf.get("rt", default_rt)
        tgt_err = t_conf.get("err", default_err)
        p90 = data.get("p90", data.get("avg_rt", 0))
        err = data.get("error_rate", 0)

        rt_breached = p90 > tgt_rt
        err_breached = err > tgt_err

        if rt_breached or err_breached:
            rt_dev_pct = ((p90 - tgt_rt) / max(1, tgt_rt) * 100) if tgt_rt > 0 else 0
            breached_txs.append({
                "name": name,
                "p90": p90,
                "target_rt": tgt_rt,
                "rt_dev_pct": rt_dev_pct,
                "err": err,
                "target_err": tgt_err,
                "rt_breach": rt_breached,
                "err_breach": err_breached
            })
        else:
            met_txs.append(name)

    sla_compliance_pct = (len(met_txs) / max(1, total_tx)) * 100 if total_tx > 0 else 100.0

    sla_overview_lines = [
        f"  Overall SLA Compliance: {sla_compliance_pct:.1f}% ({len(met_txs)} of {total_tx} transactions met defined SLA targets)",
        f"  Default Response Time SLA Target: {default_rt:.0f} ms | Default Error Rate Target: {default_err:.2f}%",
        f"  Total SLA-Breaching Transactions: {len(breached_txs)}"
    ]
    if breached_txs:
        sla_overview_lines.append("  Key SLA Violations (Actual vs Defined Target):")
        sorted_breaches = sorted(breached_txs, key=lambda x: max(x["rt_dev_pct"], x["err"] * 10), reverse=True)
        for b in sorted_breaches[:15]:
            parts = []
            if b["rt_breach"]:
                parts.append(f"P90={b['p90']:.0f}ms vs SLA Target={b['target_rt']:.0f}ms ({b['rt_dev_pct']:+.1f}% deviation)")
            if b["err_breach"]:
                parts.append(f"Error Rate={b['err']:.2f}% vs SLA Target={b['target_err']:.2f}%")
            sla_overview_lines.append(f"    - {b['name']}: {', '.join(parts)}")
    else:
        sla_overview_lines.append("  All transactions met their defined SLA thresholds.")
    sla_text = "\n".join(sla_overview_lines)

    top_labels = sorted(labels.items(), key=lambda x: (x[1].get("error_rate", 0), x[1].get("avg_rt", 0)), reverse=True)[:18]
    labels_text = "\n".join([
        f"  - {name}: {data.get('count',0)} samples, avg={data.get('avg_rt',0):.1f}ms, "
        f"p90={data.get('p90',0)}ms (SLA target: {sla_targets.get(name,{}).get('rt', default_rt):.0f}ms | {'🔴 BREACHED' if data.get('p90',0) > sla_targets.get(name,{}).get('rt', default_rt) else '🟢 MET'}), "
        f"p95={data.get('p95',0)}ms, min={data.get('min_rt',0)}ms, max={data.get('max_rt',0)}ms, "
        f"errors={data.get('errors', 0)} ({data.get('error_rate',0):.2f}%, SLA max: {sla_targets.get(name,{}).get('err', default_err):.2f}%)"
        for name, data in top_labels
    ]) or "  - No transaction data recorded"

    timeseries_text = _format_time_series_progression(time_series)
    infra_text = _format_azure_infra_telemetry(infra)
    error_text = _format_error_breakdown(error_details)

    return f"""You are a Principal Performance Engineer and Automated Performance Intelligence Engine.

You must perform INDEPENDENT, DATA-DRIVEN ANALYSIS of the raw summarized performance telemetry below to DISCOVER, DIAGNOSE, AND FORMULATE all engineering findings and observations.

DO NOT simply rephrase canned observations. Use the empirical evidence across workload, time-series progression, error distribution, and host telemetry to determine exactly what occurred.

OUTPUT FORMAT & TONE REQUIREMENTS:
Write observations in a direct, factual, client-facing performance engineering style.
Do not use speculative words like "hypothesis". State direct measured facts, exact iteration counts, response time ranges (in seconds or ms), and error counts.

STRICT CLIENT-FACING LANGUAGE RULES:
- NEVER use or mention internal code tags or IDs such as "F-001", "F-012", "F-014", "R-001", or any "F-xxx" / "R-xxx" tokens anywhere in observations, recommendations, conclusions, or summaries.
- Explain everything in simple, clear, professional client-facing terms (e.g. say "server CPU saturation" instead of "(F-012)", say "application errors and transaction failures" instead of "(F-014)", say "elevated response times").

SLA & NFR COMPLIANCE EVALUATION RULES:
- Explicitly take the DEFINED SLA TARGETS into consideration in all observations and recommendations.
- Cite the overall SLA compliance percentage (e.g., "{sla_compliance_pct:.0f}% SLA compliance") and highlight the number of transactions violating NFR SLAs.
- In `tab_rt_stats`, specifically identify transactions that breached their defined P90 SLA targets and quantify their deviation (e.g., "exceeded the 500 ms SLA target by +335%").
- In `tab_tx_stats` and `recommendations`, focus remediation priorities on transactions failing SLA targets.

FORMAT EXAMPLE FOR HIGH LEVEL OBSERVATIONS:
1. Transaction Statistics:
    a. UC01 New Business: Overall 52 iterations were executed under load out of which 52 passed, 0 failed.
    b. UC05 Add Vessel: Overall 35 iterations were executed under load out of which 35 passed, 0 failed.
    c. UC07 Group Renewal: Overall 39 iterations were executed under load out of which 7 passed, 32 failed.

2. Response Time Statistics (Average / P90 / SLA adherence):
    a. {len(breached_txs)} out of {total_tx} transactions violated the defined NFR SLA ({sla_compliance_pct:.0f}% compliance). Refer Response Time stats tab for details.
    b. The avg response time of Single issue ranges from 59 secs to 67 secs.
    c. The avg response time of Single bind ranges from 12 secs to 20 secs.
    d. The avg response time of Group renewal issue quote and bind quote was observed to be 41 secs and 8 secs respectively.

3. Errors :
    a. UC07 T11 ClickOnIssueQuote: 27 out of 34 Failure i.e., error rate is 79%. These were timeout or server errors observed during peak execution.

4. Server Monitoring:
    a. Server CPU averaged X% (peak Y%) and memory averaged Z%.
    b. (If App Service / Function Apps present): Execution counts, memory usage, and execution durations.

TAB SPECIFIC INSIGHTS:
- tab_tx_stats: 2-3 bullet observations on transactions, iterations, throughput pacing, SLA compliance, and 1-2 actionable recommendations in plain client-facing terms.
- tab_rt_stats: 2-3 bullet observations on response times, P90 outliers, defined SLA deviations / breach percentages, and 1-2 actionable recommendations in plain client-facing terms.
- tab_error_stats: 2-3 bullet observations on error patterns and sample failure rates against error SLA thresholds, and 1-2 actionable recommendations in plain client-facing terms.
- tab_infra_stats: 2-3 bullet observations on host CPU, memory, and resource headroom, and 1-2 actionable recommendations in plain client-facing terms.

TEST SCENARIO: {test_name}
═══════════════════════════════════════════════════════════════════

1. WORKLOAD & CONCURRENCY PROFILE:
  Total Samples Executed: {summary.get('total', 0):,}
  Configured Users / Concurrency: {users} threads | Ramp-up: {rampup}s
  Execution Duration: {summary.get('duration_sec', 0):.0f} seconds ({summary.get('duration_sec', 0)/60:.1f} mins)
  Overall Throughput: {summary.get('throughput', 0):.2f} req/s
  Overall Error Rate: {summary.get('error_rate', 0):.2f}%

2. DEFINED SLA TARGETS & COMPLIANCE STATUS:
{sla_text}

3. CLIENT-SIDE RESPONSE TIME & ERROR OVERVIEW:
  Average Response Time: {summary.get('avg_rt', 0):.2f} ms
  Min: {summary.get('min_rt', 0)} ms | Max: {summary.get('max_rt', 0)} ms
  P50: {summary.get('p50', 0)} ms | P90: {summary.get('p90', 0)} ms
  P95: {summary.get('p95', 0)} ms | P99: {summary.get('p99', 0)} ms

4. RAW SUMMARIZED PER-TRANSACTION METRICS (Sorted by failure rate & response time):
{labels_text}

5. TIME-SERIES RUN PROGRESSION (Concurrency ramp-up, throughput pacing, latency trends over time):
{timeseries_text}

6. SERVER-SIDE INFRASTRUCTURE TELEMETRY (Azure Monitor):
{infra_text}

7. ERROR BREAKDOWN & IMPACTED ENDPOINTS:
{error_text}

═══════════════════════════════════════════════════════════════════

YOUR ANALYSIS TASK:
Discover 3 to 7 primary engineering findings based on the data above.
Correlate the time-series progression (active users vs throughput vs latency) with host infrastructure utilization (CPU peaks, memory, network, 5xx server errors).
Identify whether degradation is caused by server saturation, thread queueing, application failure, or specific transaction bottlenecks.

Respond ONLY with a valid JSON object (no markdown, no code fences) matching this structure:
{{
  "executive_summary": "2-3 sentence concise executive assessment citing key test facts",
  "findings": [
    {{
      "id": "F-001",
      "title": "Concise finding title (e.g. Server CPU Saturation at Peak Concurrency)",
      "severity": "Critical",
      "category": "Infrastructure Saturation",
      "observation": "Factual measured evidence citing exact numbers and intervals",
      "likely_cause": "Direct technical root cause",
      "why_it_matters": "Operational and customer-facing impact",
      "recommendation": "Targeted technical fix or architectural adjustment",
      "validation": "Concrete verification test steps",
      "evidence": [
        {{"metric": "Peak Host CPU", "value": "91.4%", "source": "server"}},
        {{"metric": "P90 Latency", "value": "1166 ms", "source": "client"}}
      ],
      "confidence": "Confirmed"
    }}
  ],
  "capacity_planning": {{
    "observed_concurrency": {users},
    "estimated_max_users": null,
    "saturation_point": "State observed concurrency or inflection point where latency surged or throughput flattened",
    "safe_concurrency": null,
    "capacity_confidence": "High",
    "analysis": "Explanation of capacity limits and scaling behavior based on the time-series data"
  }},
  "root_cause_assessment": [
    {{
      "finding": "Primary bottleneck or observed degradation",
      "evidence": "Citing specific measured values and sources",
      "likely_cause": "Direct technical cause",
      "confidence": "Confirmed",
      "recommended_investigation": "Specific telemetry or profiling steps needed"
    }}
  ],
  "recommendations": [
    {{
      "id": "R-001",
      "priority": "Critical",
      "category": "Infrastructure",
      "title": "Short title",
      "why": "Why this matters based on evidence",
      "action": ["Step 1", "Step 2"],
      "expected_impact": "Expected qualitative improvement",
      "validation": "How to verify the fix",
      "confidence": "High"
    }}
  ],
  "performance_intelligence": {{
    "executive_summary": {{
      "assessment_text": "3-5 high-level executive pointers/bullet statements citing exact measurements, primary bottlenecks, and reliability status.",
      "assessment_bullets": [
        "Executive finding pointer 1 citing measured response time ranges and overall SLA compliance",
        "Executive finding pointer 2 citing peak throughput and concurrency behavior",
        "Executive finding pointer 3 citing primary bottlenecks or error patterns"
      ],
      "conclusions": [
        "Concise conclusion bullet 1 citing exact numbers",
        "Concise conclusion bullet 2 citing exact numbers",
        "Concise conclusion bullet 3 citing exact numbers"
      ],
      "observations_table": [
        {{
          "category": "1. Transaction Statistics",
          "observation": "a. UC01 New Business: Overall X iterations were executed under load out of which Y passed, Z failed.\\nb. ..."
        }},
        {{
          "category": "2. Response Time Statistics",
          "observation": "a. X transactions violated the NFR SLA.\\nb. The avg response time of ... ranges from ... to ...\\nc. ..."
        }},
        {{
          "category": "3. Errors",
          "observation": "a. Transaction Name: X out of Y failures (Z% error rate). Observed failure reasons..."
        }},
        {{
          "category": "4. Server Monitoring",
          "observation": "a. Server CPU averaged X% (peak Y%) and memory averaged Z%.\\nb. ..."
        }}
      ],
      "priority_recommendations": [
        {{"priority": "High", "badge": "🟠", "title": "Short recommendation title", "detail": "Actionable, evidence-backed technical remediation advice", "business_impact": "Direct operational or business impact, e.g. Eliminates checkout delays, protecting customer conversion during peak sales windows."}}
      ]
    }},
    "tab_tx_stats": {{
      "observations": [
        "Bullet 1 on transaction execution counts, pass/fail iterations, and pacing",
        "Bullet 2 on dominant transaction throughput share"
      ],
      "recommendations": [
        "Actionable recommendation on transaction pacing or workload distribution"
      ]
    }},
    "tab_rt_stats": {{
      "observations": [
        "Bullet 1 on response time ranges and SLA breach counts",
        "Bullet 2 on P90/P95 tail latency variations"
      ],
      "recommendations": [
        "Actionable recommendation on latency optimization"
      ]
    }},
    "tab_error_stats": {{
      "observations": [
        "Bullet 1 on exact failure counts, error percentages, and error types",
        "Bullet 2 on timeout or HTTP failure concentration"
      ],
      "recommendations": [
        "Actionable recommendation on error resolution and resilience"
      ]
    }},
    "tab_infra_stats": {{
      "observations": [
        "Bullet 1 on server CPU & memory utilization headroom",
        "Bullet 2 on Azure monitor / compute metrics"
      ],
      "recommendations": [
        "Actionable recommendation on compute sizing or scaling"
      ]
    }}
  }}
}}"""


def build_comparison_prompt(comparison_facts: dict) -> str:
    """Constructs prompt for synthesizing release-over-release performance comparison insights."""
    return f"""You are a Lead Performance Engineer. Analyze these calculated release comparison facts and generate factual summary observations in JSON format.

RULES:
1. Ground every sentence strictly in the provided numbers.
2. DO NOT invent speculative causes like "database contention", "thread pool exhaustion", or "network latency" unless provided in facts.
3. Keep observations concise, direct, and actionable.

Calculated Facts:
{json.dumps(comparison_facts, indent=2)}

Return JSON with exact keys:
{{
  "executive_bullets": ["5-7 factual bullet points"],
  "trend_observation": "One sentence describing overall response time direction across releases",
  "sla_observation": "One sentence describing SLA compliance progression",
  "degradation_observation": "One sentence identifying the most degraded transaction and its largest step",
  "improvement_observation": "One sentence identifying the most improved transaction",
  "risk_observation": "One sentence summarizing high/critical breach evolution"
}}
"""


def build_2run_comparison_prompt(scorecard: dict, transactions: list, new_breaches: list = None,
                                 resolved_breaches: list = None, current_info: dict = None, baseline_info: dict = None) -> str:
    """Constructs prompt for AI comparative intelligence using raw telemetry only (no pre-computed findings)."""
    
    # Format concise transaction telemetry, prioritizing regressions, improvements, and SLA shifts
    formatted_txs = []
    for t in (transactions or []):
        rt_a = round(float(t.get("rt_a", 0) or 0), 1)
        rt_b = round(float(t.get("rt_b", 0) or 0), 1)
        p95_a = round(float(t.get("p95_a", 0) or 0), 1)
        p95_b = round(float(t.get("p95_b", 0) or 0), 1)
        err_a = round(float(t.get("err_rate_a", 0) or 0), 2)
        err_b = round(float(t.get("err_rate_b", 0) or 0), 2)
        target_rt = round(float(t.get("target_rt", 0) or 0), 1)
        target_err = round(float(t.get("target_err", 0) or 0), 2)
        
        rt_delta = round(rt_b - rt_a, 1)
        err_delta = round(err_b - err_a, 2)
        breach = (rt_b > target_rt > 0) or (err_b > target_err > 0)
        
        # Scoring impact to surface top outliers to LLM
        impact = abs(rt_delta) + (err_delta * 50) + (500 if breach else 0)
        formatted_txs.append({
            "transaction": t.get("label", ""),
            "sla_rt_ms": target_rt,
            "sla_err_pct": target_err,
            "baseline": {"avg_rt_ms": rt_a, "p95_ms": p95_a, "err_pct": err_a},
            "current": {"avg_rt_ms": rt_b, "p95_ms": p95_b, "err_pct": err_b},
            "delta_rt_ms": rt_delta,
            "delta_err_pct": err_delta,
            "sla_breach": breach,
            "_impact": impact
        })

    # Sort by impact and keep top 14 most critical items to maintain compact payload under 1,500 tokens
    formatted_txs.sort(key=lambda x: x["_impact"], reverse=True)
    raw_tx_list = [{k: v for k, v in item.items() if not k.startswith("_")} for item in formatted_txs[:14]]

    raw_comparison_telemetry = {
        "baseline_run": baseline_info or {},
        "current_run": current_info or {},
        "overall_scorecard_metrics": {
            "baseline_users": scorecard.get("run_a_users", 1),
            "current_users": scorecard.get("run_b_users", 1),
            "baseline_avg_rt_ms": scorecard.get("run_a_rt", 0),
            "current_avg_rt_ms": scorecard.get("run_b_rt", 0),
            "baseline_p90_ms": scorecard.get("run_a_p90", 0),
            "current_p90_ms": scorecard.get("run_b_p90", 0),
            "baseline_p95_ms": scorecard.get("run_a_p95", 0),
            "current_p95_ms": scorecard.get("run_b_p95", 0),
            "baseline_p99_ms": scorecard.get("run_a_p99", 0),
            "current_p99_ms": scorecard.get("run_b_p99", 0),
            "baseline_total_requests": scorecard.get("run_a_req", 0),
            "current_total_requests": scorecard.get("run_b_req", 0),
            "baseline_throughput_tps": scorecard.get("run_a_tps", 0),
            "current_throughput_tps": scorecard.get("run_b_tps", 0),
            "baseline_errors": scorecard.get("run_a_err_count", 0),
            "current_errors": scorecard.get("run_b_err_count", 0),
            "baseline_error_rate_pct": scorecard.get("run_a_err_rate", 0),
            "current_error_rate_pct": scorecard.get("run_b_err_rate", 0),
            "baseline_sla_pass_rate_pct": scorecard.get("run_a_sla_pass", 0),
            "current_sla_pass_rate_pct": scorecard.get("run_b_sla_pass", 0)
        },
        "transactions_raw_telemetry": raw_tx_list
    }

    return f"""You are a Principal Performance Engineering Architect and Automated Comparative Intelligence Engine.

Analyze the raw performance metrics below comparing a Baseline Run vs a Current Run.
You must INDEPENDENTLY evaluate the data to DISCOVER and DIAGNOSE all regressions, improvements, and SLA transitions yourself.
DO NOT expect pre-baked findings; calculate the differences, identify outliers, and diagnose root causes from the raw telemetry.

INSIGHT-DRIVEN RULES (CRITICAL):
1. Focus on HIGH-LEVEL ARCHITECTURAL & RELEASE INSIGHTS, NOT low-level raw number repetitions (the user can see raw data in the charts below).
2. Generate between 2 and 4 high-impact, actionable Insights focusing on the primary regression drivers, SLA transitions, or notable improvements.
3. Keep every insight card punchy, crisp, and focused on: What happened -> Why it matters -> What to do about it.
4. Ground all observations in direct facts without verbose filler.

RAW COMPARATIVE TELEMETRY:
{json.dumps(raw_comparison_telemetry, indent=2)}

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact schema:
{{
  "risk_level": "LOW RISK" | "MODERATE RISK" | "HIGH RISK",
  "risk_color": "var(--green)" | "var(--amber)" | "var(--red)",
  "status_badge": "🟢 PERFORMANCE IMPROVED" | "🟢 STABLE PERFORMANCE" | "🟡 MINOR DEGRADATION" | "🔴 REGRESSION DETECTED",
  "status_text": "Short 3-5 word status (e.g., Release Blocker: Error Rate Spike)",
  "executive_summary": "EXACTLY 2 to 3 concise, punchy sentences. State the clear release verdict (GO / NO-GO / CONDITIONAL), the overarching latency & reliability delta, and the single primary bottleneck driver.",
  "highlights": [
    "Punchy 1-2 sentence observation highlighting the primary latency/throughput/SLA shift...",
    "Second distinct 1-2 sentence observation on error distribution or tail latency...",
    "Third 1-2 sentence observation on concurrency scaling or resource efficiency..."
  ],
  "recommendations": [
    "Concise 1-2 sentence technical fix specifying domain (e.g. [Database / Indexing], [Application Gateway / Thread Pool], [Caching])...",
    "Second prioritized 1-2 sentence technical remediation action...",
    "Third prioritized 1-2 sentence technical remediation action..."
  ],
  "findings": [
    {{
      "id": "CI-001",
      "title": "Concise Insight Title (e.g., Checkout Latency Degradation Exceeds SLA Threshold)",
      "severity": "Critical" | "High" | "Medium" | "Low",
      "category": "SLA Breach" | "Latency Drift" | "Reliability Risk" | "Scalability Limit" | "Optimization",
      "observation": "1-2 crisp sentences explaining the behavioral shift and architectural cause.",
      "why_it_matters": "1 concise sentence on user experience or release impact.",
      "recommendation": "1 targeted, actionable engineering takeaway or fix."
    }}
  ]
}}
"""
