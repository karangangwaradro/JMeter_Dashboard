#!/usr/bin/env python3
"""
context_packager.py — Scoped Context Packager for Section-Level AI Chat & Agentic Editing in PerfPilot.

Extracts targeted, compact micro-digests (~400-800 tokens) combining BOTH the current
AI section content AND structured raw performance metrics (time-series, peak timestamps,
SLA breaches, errors, and throughput).
"""

import json
from typing import Dict, Any


def _extract_server_monitoring_context(result_data: Dict[str, Any], azure_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts structured server infrastructure metrics, time-series progression, peak timestamps,
    and user-load vs server degradation correlation.
    """
    infra_src = {}
    ts_src = {}
    app_src = {}

    if isinstance(azure_data, dict) and azure_data.get("infra_summary"):
        infra_src = azure_data.get("infra_summary", {})
        ts_src = azure_data.get("time_series", {})
        app_src = azure_data.get("app_service", {})
    elif isinstance(result_data.get("azure"), dict) and result_data["azure"].get("infra_summary"):
        infra_src = result_data["azure"].get("infra_summary", {})
        ts_src = result_data["azure"].get("time_series", {})
        app_src = result_data["azure"].get("app_service", {})

    if not infra_src:
        return {}

    timestamps = ts_src.get("timestamps", [])
    cpu_list = ts_src.get("cpu", [])
    mem_list = ts_src.get("memory", [])
    net_in_list = ts_src.get("network_in", [])
    net_out_list = ts_src.get("network_out", [])

    # Identify exact peak values and peak timestamps
    peak_cpu_val = max(cpu_list) if cpu_list else infra_src.get("max_cpu", 0)
    peak_mem_val = max(mem_list) if mem_list else infra_src.get("max_memory", 0)

    peak_cpu_ts = None
    if cpu_list and timestamps and len(cpu_list) == len(timestamps) and peak_cpu_val in cpu_list:
        peak_cpu_ts = timestamps[cpu_list.index(peak_cpu_val)]

    peak_mem_ts = None
    if mem_list and timestamps and len(mem_list) == len(timestamps) and peak_mem_val in mem_list:
        peak_mem_ts = timestamps[mem_list.index(peak_mem_val)]

    # Detailed timeline progression
    timeline = []
    if timestamps:
        for i, ts in enumerate(timestamps):
            entry = {"timestamp": ts}
            if i < len(cpu_list):
                entry["cpu_pct"] = round(cpu_list[i], 1)
            if i < len(mem_list):
                entry["memory_pct"] = round(mem_list[i], 1)
            if i < len(net_in_list):
                entry["network_in_mbps"] = round(net_in_list[i], 2)
            if i < len(net_out_list):
                entry["network_out_mbps"] = round(net_out_list[i], 2)
            timeline.append(entry)

    # Progression trend & load correlation
    start_cpu = cpu_list[0] if cpu_list else None
    start_mem = mem_list[0] if mem_list else None
    users = result_data.get("users", 1)

    degradation_summary = None
    if start_cpu is not None and peak_cpu_val is not None:
        cpu_growth = round(peak_cpu_val - start_cpu, 1)
        mem_growth = round(peak_mem_val - start_mem, 1) if start_mem is not None and peak_mem_val is not None else 0
        degradation_summary = (
            f"Server CPU ramped up by +{cpu_growth}% (from {start_cpu:.1f}% to peak {peak_cpu_val:.1f}% at timestamp {peak_cpu_ts or 'peak window'}) "
            f"and Memory increased by +{mem_growth}% (from {start_mem:.1f}% to peak {peak_mem_val:.1f}% at timestamp {peak_mem_ts or 'peak window'}) "
            f"as concurrent user load scaled to {users} users."
        )

    return {
        "summary": {
            "avg_cpu_pct": infra_src.get("avg_cpu", 0),
            "max_cpu_peak_pct": peak_cpu_val,
            "avg_memory_pct": infra_src.get("avg_memory", 0),
            "max_memory_peak_pct": peak_mem_val,
            "avg_network_in_mbps": infra_src.get("avg_network_in_mbps", 0),
            "avg_network_out_mbps": infra_src.get("avg_network_out_mbps", 0),
            "avg_disk_read_iops": infra_src.get("avg_disk_read_iops", 0),
            "avg_disk_write_iops": infra_src.get("avg_disk_write_iops", 0),
            "http_5xx_server_errors": app_src.get("http_5xx", 0),
            "server_avg_response_time_ms": app_src.get("avg_response_time_ms", 0)
        },
        "peak_events_with_timestamps": {
            "peak_cpu": {
                "value_pct": peak_cpu_val,
                "timestamp": peak_cpu_ts,
                "assessment": "Critical Saturation" if peak_cpu_val >= 90 else ("Elevated" if peak_cpu_val >= 75 else "Healthy")
            },
            "peak_memory": {
                "value_pct": peak_mem_val,
                "timestamp": peak_mem_ts,
                "assessment": "High Memory Pressure" if peak_mem_val >= 85 else "Acceptable"
            }
        },
        "server_degradation_over_time": degradation_summary,
        "timeline_progression": timeline
    }


def _build_raw_data_summary(result_data: Dict[str, Any], azure_data: Dict[str, Any], server_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a complete, categorized raw performance data summary spanning workload,
    transaction statistics, response times & SLA adherence, reliability & errors,
    and server infrastructure monitoring.
    """
    summary = result_data.get("summary", {})
    labels = result_data.get("labels", {})
    jmx_name = result_data.get("jmx_name", "Performance Test")
    users = result_data.get("users", 1)
    duration_sec = summary.get("duration_sec", 0)

    # 1. SLA Targets & Calculations
    sla_targets = {}
    default_rt = 500.0
    default_err = 1.0
    try:
        from python_files.sla_manager import load_sla_targets
        sla_targets, default_rt, default_err = load_sla_targets(jmx_name, actual_users=users)
        sla_targets = sla_targets or {}
    except Exception:
        pass

    breaches = []
    tx_list = []
    for name, d in labels.items():
        p90 = d.get("p90", d.get("avg_rt", 0))
        tgt_rt = sla_targets.get(name, {}).get("rt", default_rt)
        tgt_err = sla_targets.get(name, {}).get("err", default_err)
        err_rate = d.get("error_rate", 0)
        
        is_rt_breached = p90 > tgt_rt if tgt_rt > 0 else False
        is_err_breached = err_rate > tgt_err if tgt_err > 0 else False
        is_breached = is_rt_breached or is_err_breached
        dev_pct = ((p90 - tgt_rt) / max(1, tgt_rt) * 100) if tgt_rt > 0 else 0

        item = {
            "transaction": name,
            "samples": d.get("count", 0),
            "iterations": d.get("iterations", 0),
            "passed": d.get("count", 0) - d.get("errors", 0),
            "failed": d.get("errors", 0),
            "error_rate_pct": round(err_rate, 2),
            "avg_ms": round(d.get("avg_rt", 0), 1),
            "p50_ms": round(d.get("p50", 0), 1),
            "p90_ms": round(p90, 1),
            "p95_ms": round(d.get("p95", 0), 1),
            "p99_ms": round(d.get("p99", 0), 1),
            "min_ms": round(d.get("min_rt", 0), 1),
            "max_ms": round(d.get("max_rt", 0), 1),
            "tps": round(d.get("count", 0) / max(1, duration_sec), 2),
            "sla_target_rt_ms": round(tgt_rt, 1),
            "sla_target_err_pct": round(tgt_err, 2),
            "sla_status": "BREACHED" if is_breached else "MET",
            "sla_dev_pct": round(dev_pct, 1)
        }
        tx_list.append(item)
        if is_breached:
            breaches.append(item)

    sorted_by_samples = sorted(tx_list, key=lambda x: x["samples"], reverse=True)
    sorted_by_p90 = sorted(tx_list, key=lambda x: x["p90_ms"], reverse=True)
    sorted_breaches = sorted(breaches, key=lambda x: x["sla_dev_pct"], reverse=True)

    # 2. Error Breakdown
    error_details = result_data.get("error_details", {})
    compact_errors = []
    if isinstance(error_details, dict):
        for code, edata in error_details.items():
            if isinstance(edata, dict):
                compact_errors.append({
                    "error_key": code,
                    "http_code": edata.get("code") or code,
                    "total_occurrences": edata.get("count", 0),
                    "error_message": edata.get("failure_message") or edata.get("message", "Error")
                })
    failing_txs = [t for t in sorted_by_samples if t["failed"] > 0]

    return {
        "workload_execution_raw": {
            "test_scenario": jmx_name,
            "target_concurrency_users": users,
            "duration_sec": round(duration_sec, 1),
            "duration_min": round(duration_sec / 60, 2),
            "start_epoch": summary.get("start_epoch"),
            "end_epoch": summary.get("end_epoch"),
            "total_requests": summary.get("total", 0),
            "total_iterations": summary.get("total_iterations", 0),
            "throughput_tps": round(summary.get("throughput", 0), 2),
            "overall_avg_rt_ms": round(summary.get("avg_rt", 0), 1),
            "overall_p50_ms": round(summary.get("p50", 0), 1),
            "overall_p90_ms": round(summary.get("p90", 0), 1),
            "overall_p95_ms": round(summary.get("p95", 0), 1),
            "overall_p99_ms": round(summary.get("p99", 0), 1),
            "overall_min_rt_ms": round(summary.get("min_rt", 0), 1),
            "overall_max_rt_ms": round(summary.get("max_rt", 0), 1),
            "total_errors": summary.get("errors", 0),
            "overall_error_rate_pct": round(summary.get("error_rate", 0), 2)
        },
        "transaction_breakdown_raw": sorted_by_samples[:25],
        "slowest_transactions_raw": sorted_by_p90[:10],
        "reliability_and_errors_raw": {
            "total_errors": summary.get("errors", 0),
            "overall_error_rate_pct": round(summary.get("error_rate", 0), 2),
            "error_types": compact_errors,
            "failing_endpoints": failing_txs[:15]
        },
        "sla_compliance_raw": {
            "total_transactions": len(labels),
            "met_transactions_count": len(labels) - len(breaches),
            "breached_transactions_count": len(breaches),
            "overall_compliance_pct": round(((len(labels) - len(breaches)) / max(1, len(labels))) * 100, 1) if labels else 100.0,
            "default_sla_target_rt_ms": default_rt,
            "breached_transactions": sorted_breaches[:15]
        },
        "server_infrastructure_raw": server_ctx if server_ctx else "Server monitoring not configured"
    }


def build_section_digest(result_data: Dict[str, Any], azure_data: Dict[str, Any], section_id: str) -> Dict[str, Any]:
    """
    Builds a comprehensive micro-digest tailored specifically for the requested subsection or tab,
    providing BOTH the existing AI observations AND structured raw performance metrics.
    """
    summary = result_data.get("summary", {})
    labels = result_data.get("labels", {})
    jmx_name = result_data.get("jmx_name", "Performance Test")
    users = result_data.get("users", 1)
    duration_sec = summary.get("duration_sec", 0)

    ai_intel = result_data.get("ai_insights", {}).get("performance_intelligence", {})
    exec_intel = ai_intel.get("executive_summary", {}) if isinstance(ai_intel, dict) else {}
    server_ctx = _extract_server_monitoring_context(result_data, azure_data)
    raw_summary = _build_raw_data_summary(result_data, azure_data, server_ctx)

    # ── 1. Executive Overview Sub-section ──
    if section_id in ("exec_overview", "executive", "major_ai_augmented"):
        current_bullets = exec_intel.get("assessment_bullets") or [exec_intel.get("assessment_text", "")]
        if isinstance(current_bullets, str):
            current_bullets = [current_bullets]

        return {
            "section_id": "exec_overview",
            "section_name": "AI Powered Executive Overview",
            "current_content": [b for b in current_bullets if b],
            "raw_performance_data": {
                "workload_execution": raw_summary["workload_execution_raw"],
                "slowest_transactions": raw_summary["slowest_transactions_raw"][:5],
                "failing_transactions": raw_summary["reliability_and_errors_raw"]["failing_endpoints"][:5],
                "server_highlights": server_ctx.get("peak_events_with_timestamps", {}) if server_ctx else "N/A",
                "server_degradation_trend": server_ctx.get("server_degradation_over_time") if server_ctx else "N/A",
                "server_timeline_sample": server_ctx.get("timeline_progression", []) if server_ctx else []
            }
        }

    # ── 2. High-Level Observations Sub-section ──
    elif section_id == "exec_observations":
        return {
            "section_id": "exec_observations",
            "section_name": "High-Level Performance Observations",
            "current_content": exec_intel.get("observations_table", []),
            "raw_performance_data": {
                "category_1_transaction_statistics_raw": {
                    "workload_summary": raw_summary["workload_execution_raw"],
                    "transactions_sample_and_tps": [
                        {"name": t["transaction"], "samples": t["samples"], "iterations": t["iterations"], "tps": t["tps"], "passed": t["passed"], "failed": t["failed"]}
                        for t in raw_summary["transaction_breakdown_raw"][:15]
                    ]
                },
                "category_2_response_time_statistics_raw": {
                    "overall_latencies": {
                        "avg_ms": raw_summary["workload_execution_raw"]["overall_avg_rt_ms"],
                        "p50_ms": raw_summary["workload_execution_raw"]["overall_p50_ms"],
                        "p90_ms": raw_summary["workload_execution_raw"]["overall_p90_ms"],
                        "p95_ms": raw_summary["workload_execution_raw"]["overall_p95_ms"],
                        "p99_ms": raw_summary["workload_execution_raw"]["overall_p99_ms"],
                        "min_ms": raw_summary["workload_execution_raw"]["overall_min_rt_ms"],
                        "max_ms": raw_summary["workload_execution_raw"]["overall_max_rt_ms"]
                    },
                    "sla_compliance": raw_summary["sla_compliance_raw"],
                    "slowest_and_breached_transactions": raw_summary["sla_compliance_raw"]["breached_transactions"]
                },
                "category_3_error_statistics_raw": raw_summary["reliability_and_errors_raw"],
                "category_4_server_monitoring_raw": server_ctx if server_ctx else "Server monitoring data not configured or recorded for this run."
            }
        }

    # ── 3. Key Conclusions Sub-section ──
    elif section_id == "exec_conclusions":
        return {
            "section_id": "exec_conclusions",
            "section_name": "Key Conclusions",
            "current_content": exec_intel.get("conclusions", []),
            "raw_performance_data": {
                "workload_execution": raw_summary["workload_execution_raw"],
                "sla_compliance": raw_summary["sla_compliance_raw"],
                "server_peak_events": server_ctx.get("peak_events_with_timestamps", {}) if server_ctx else "N/A",
                "server_degradation_trend": server_ctx.get("server_degradation_over_time") if server_ctx else "N/A"
            }
        }

    # ── 4. Priority Recommendations Sub-section ──
    elif section_id == "exec_recommendations":
        return {
            "section_id": "exec_recommendations",
            "section_name": "Priority Recommendations",
            "current_content": exec_intel.get("priority_recommendations", []),
            "raw_performance_data": {
                "top_latency_bottlenecks": raw_summary["slowest_transactions_raw"][:5],
                "top_failing_endpoints": raw_summary["reliability_and_errors_raw"]["failing_endpoints"][:5],
                "sla_breaches": raw_summary["sla_compliance_raw"]["breached_transactions"][:5],
                "server_peak_events": server_ctx.get("peak_events_with_timestamps", {}) if server_ctx else "N/A",
                "server_degradation_trend": server_ctx.get("server_degradation_over_time") if server_ctx else "N/A"
            }
        }

    # ── 5. Transaction Statistics Tab Digest ──
    elif section_id == "tab_tx_stats":
        tab_intel = ai_intel.get("tab_tx_stats", {}) if isinstance(ai_intel, dict) else {}
        return {
            "section_id": "tab_tx_stats",
            "section_name": "Transaction Performance Breakdown",
            "current_content": tab_intel,
            "raw_performance_data": {
                "workload_summary": raw_summary["workload_execution_raw"],
                "transactions": raw_summary["transaction_breakdown_raw"]
            }
        }

    # ── 6. Response Time & SLA Tab Digest ──
    elif section_id == "tab_rt_stats":
        tab_intel = ai_intel.get("tab_rt_stats", {}) if isinstance(ai_intel, dict) else {}
        return {
            "section_id": "tab_rt_stats",
            "section_name": "Response Time & SLA Adherence",
            "current_content": tab_intel,
            "raw_performance_data": {
                "sla_compliance_overview": raw_summary["sla_compliance_raw"],
                "slowest_transactions": raw_summary["slowest_transactions_raw"],
                "transaction_percentiles": [
                    {"name": t["transaction"], "avg_ms": t["avg_ms"], "p50_ms": t["p50_ms"], "p90_ms": t["p90_ms"], "p95_ms": t["p95_ms"], "p99_ms": t["p99_ms"], "sla_target_ms": t["sla_target_rt_ms"], "sla_status": t["sla_status"], "sla_dev_pct": t["sla_dev_pct"]}
                    for t in raw_summary["transaction_breakdown_raw"]
                ]
            }
        }

    # ── 7. Reliability & Error Stats Tab Digest ──
    elif section_id == "tab_error_stats":
        tab_intel = ai_intel.get("tab_error_stats", {}) if isinstance(ai_intel, dict) else {}
        return {
            "section_id": "tab_error_stats",
            "section_name": "Reliability & Error Distribution",
            "current_content": tab_intel,
            "raw_performance_data": raw_summary["reliability_and_errors_raw"]
        }

    # ── 8. Infrastructure Monitoring Tab Digest ──
    elif section_id == "tab_infra_stats":
        correlation = result_data.get("correlation", {})
        corr_findings = correlation.get("findings", []) if isinstance(correlation, dict) else []
        tab_intel = ai_intel.get("tab_infra_stats", {}) if isinstance(ai_intel, dict) else {}

        return {
            "section_id": "tab_infra_stats",
            "section_name": "Infrastructure & Server-Side Monitoring",
            "current_content": tab_intel,
            "raw_performance_data": {
                "server_monitoring": server_ctx if server_ctx else "Azure Monitor metrics not configured or recorded for this run.",
                "correlation_findings": corr_findings[:10] if corr_findings else "No infrastructure correlation anomalies detected."
            }
        }

    # Default fallback
    return {
        "section_id": section_id,
        "section_name": section_id,
        "summary": summary,
        "raw_performance_data": raw_summary
    }


def build_chat_system_prompt(section_id: str, section_digest: Dict[str, Any]) -> str:
    """
    Constructs a disciplined system prompt for section Q&A with agentic section-patching abilities.
    """
    section_name = section_digest.get("section_name", section_id)
    digest_json = json.dumps(section_digest, indent=2)

    return f"""You are PerfAgent, a Senior Performance Engineering AI Assistant embedded inside the PerfPilot report for the section: "{section_name}".

STRICT BEHAVIOR & SCOPE RULES:
1. Ground all answers and edits in BOTH the existing AI content (`current_content`) AND the provided comprehensive raw metrics (`raw_performance_data`).
2. When answering questions or writing/updating observations across the 4 core categories:
   - "1. Transaction Statistics": Reference exact sample counts, iterations, volume share, and throughput TPS from `category_1_transaction_statistics_raw` / `workload_execution_raw`.
   - "2. Response Time Statistics": Reference exact avg, p90, p95, p99 response times and SLA breaches/deviations from `category_2_response_time_statistics_raw` / `sla_compliance_raw`.
   - "3. Error Statistics": Reference exact error counts, error rates %, HTTP status codes (e.g. 500, 503, 404), failure messages, and failing endpoints from `category_3_error_statistics_raw`.
   - "4. Server Monitoring": Reference exact CPU/Memory averages, peak values, EXACT peak duration timestamps (e.g. "2026-08-10T00:20:00Z"), IOPS, App Service 5xx errors, and degradation trends from `category_4_server_monitoring_raw` / `server_infrastructure_raw`.
3. NEVER make up numbers or guess values not present in the data. Cite exact response times, error counts, percentages, and transaction names.
4. Tone: Professional, objective, direct, factual, client-ready performance engineering. Keep answers concise.
5. DO NOT use internal code tags like F-001 or R-001.

AGENTIC REPORT EDITING / REWRITING INSTRUCTIONS:
If the user asks you to rewrite, update, refine, replace, or add content to this section (e.g. "in server monitoring add how server degraded over time", "update conclusions with Y", "add a recommendation for Z"):
1. Provide a brief 1-2 sentence conversational summary explaining the updates made.
2. ALWAYS append an actionable JSON patch block at the very end of your response using this exact format:

```action:patch_section
{{
  "section_id": "{section_id}",
  "content": <NEW_CONTENT_STRUCTURE>
}}
```

Format of "content" depends on the current section:
- For "exec_overview" or "exec_conclusions": JSON array of string bullets: ["Bullet 1 with exact numbers", "Bullet 2..."]
- For "exec_observations": JSON array of observation objects: [{{"category": "1. Transaction Statistics", "observation": "a. Detail...\nb. Detail..."}}, {{"category": "2. Response Time Statistics", "observation": "..."}}, {{"category": "3. Error Statistics", "observation": "..."}}, {{"category": "4. Server Monitoring", "observation": "a. CPU peaked at 91.4% at timestamp 2026-08-10T00:20:00Z as user concurrency reached peak load...\nb. Memory increased from 52.4% to 89.3%..."}}]
- For "exec_recommendations": JSON array of recommendation objects: [{{"badge": "🟠", "title": "Short Title", "priority": "High", "detail": "Technical action detail...", "business_impact": "Direct revenue or user impact..."}}]
- For "tab_tx_stats", "tab_rt_stats", "tab_error_stats", "tab_infra_stats": JSON object: {{"observations": ["Observation 1", "Observation 2"], "recommendations": ["Recommendation 1"]}}

CURRENT SECTION CONTEXT DATA (AI OBSERVATIONS + COMPLETE SUMMARIZED RAW DATA):
{digest_json}
"""
