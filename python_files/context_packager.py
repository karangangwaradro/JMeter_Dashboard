#!/usr/bin/env python3
"""
context_packager.py — Scoped Context Packager for Section-Level AI Chat & Agentic Editing in PerfPilot.

Extracts targeted, compact micro-digests (~300-600 tokens) from result data
for section-specific AI Q&A and empowers the AI to propose in-place report updates.
"""

import json
from typing import Dict, Any


def build_section_digest(result_data: Dict[str, Any], azure_data: Dict[str, Any], section_id: str) -> Dict[str, Any]:
    """
    Builds a compact ~300-600 token micro-digest tailored specifically for the requested subsection or tab.
    
    Supported Section IDs:
      - 'exec_overview': AI Powered Executive Overview (summary bullets, key KPIs, top bottlenecks)
      - 'exec_observations': High-Level Observations Table (category breakdown & embedded evidence)
      - 'exec_conclusions': Key Conclusions (verdict on stability, NFR compliance, compute headroom)
      - 'exec_recommendations': Priority Recommendations & Business Impact
      - 'executive': Full executive overview fallback
      - 'tab_tx_stats': Transaction counts, iterations, volume share, pass/fail status
      - 'tab_rt_stats': Response times (avg, p90, p95, p99), SLA targets, SLA breaches with deviation %
      - 'tab_error_stats': Error rates, error types, failing transactions, error concentration
      - 'tab_infra_stats': CPU/Memory/Disk/Network metrics, Azure Monitor findings, correlation insights
    """
    summary = result_data.get("summary", {})
    labels = result_data.get("labels", {})
    jmx_name = result_data.get("jmx_name", "Performance Test")
    users = result_data.get("users", 1)
    duration_sec = summary.get("duration_sec", 0)

    ai_intel = result_data.get("ai_insights", {}).get("performance_intelligence", {})
    exec_intel = ai_intel.get("executive_summary", {}) if isinstance(ai_intel, dict) else {}

    # ── 1. Executive Overview Sub-section ──
    if section_id in ("exec_overview", "executive", "major_ai_augmented"):
        top_slow = sorted(labels.items(), key=lambda x: x[1].get("p90", x[1].get("avg_rt", 0)), reverse=True)[:5]
        top_err = sorted([l for l in labels.items() if l[1].get("errors", 0) > 0], key=lambda x: x[1].get("error_rate", 0), reverse=True)[:5]
        
        current_bullets = exec_intel.get("assessment_bullets") or [exec_intel.get("assessment_text", "")]
        if isinstance(current_bullets, str):
            current_bullets = [current_bullets]

        return {
            "section_id": "exec_overview",
            "section_name": "AI Powered Executive Overview",
            "current_content": [b for b in current_bullets if b],
            "test_scenario": jmx_name,
            "target_concurrency": users,
            "duration_sec": round(duration_sec, 1),
            "total_requests": summary.get("total", 0),
            "total_iterations": summary.get("total_iterations", 0),
            "throughput_rps": round(summary.get("throughput", 0), 2),
            "overall_avg_rt_ms": round(summary.get("avg_rt", 0), 1),
            "overall_p90_rt_ms": round(summary.get("p90", 0), 1),
            "overall_error_rate_pct": round(summary.get("error_rate", 0), 2),
            "top_slowest_transactions": [
                {"name": name, "p90_ms": round(d.get("p90", 0), 1), "avg_ms": round(d.get("avg_rt", 0), 1), "count": d.get("count", 0)}
                for name, d in top_slow
            ],
            "top_failing_transactions": [
                {"name": name, "errors": d.get("errors", 0), "error_rate_pct": round(d.get("error_rate", 0), 2)}
                for name, d in top_err
            ]
        }

    # ── 2. High-Level Observations Sub-section ──
    elif section_id == "exec_observations":
        return {
            "section_id": "exec_observations",
            "section_name": "High-Level Performance Observations",
            "current_content": exec_intel.get("observations_table", []),
            "workload": {
                "total_samples": summary.get("total", 0),
                "duration_sec": round(duration_sec, 1),
                "throughput_rps": round(summary.get("throughput", 0), 2),
                "avg_rt_ms": round(summary.get("avg_rt", 0), 1),
                "error_rate_pct": round(summary.get("error_rate", 0), 2)
            }
        }

    # ── 3. Key Conclusions Sub-section ──
    elif section_id == "exec_conclusions":
        return {
            "section_id": "exec_conclusions",
            "section_name": "Key Conclusions",
            "current_content": exec_intel.get("conclusions", []),
            "summary_facts": {
                "total_samples": summary.get("total", 0),
                "avg_rt_ms": round(summary.get("avg_rt", 0), 1),
                "p90_ms": round(summary.get("p90", 0), 1),
                "error_rate_pct": round(summary.get("error_rate", 0), 2),
                "total_failing_requests": summary.get("errors", 0)
            }
        }

    # ── 4. Priority Recommendations Sub-section ──
    elif section_id == "exec_recommendations":
        return {
            "section_id": "exec_recommendations",
            "section_name": "Priority Recommendations",
            "current_content": exec_intel.get("priority_recommendations", []),
            "bottleneck_context": {
                "overall_error_rate_pct": round(summary.get("error_rate", 0), 2),
                "overall_p90_ms": round(summary.get("p90", 0), 1)
            }
        }

    # ── 5. Transaction Performance Tab Digest ──
    elif section_id == "tab_tx_stats":
        sorted_by_count = sorted(labels.items(), key=lambda x: x[1].get("count", 0), reverse=True)
        tab_intel = ai_intel.get("tab_tx_stats", {}) if isinstance(ai_intel, dict) else {}
        return {
            "section_id": "tab_tx_stats",
            "section_name": "Transaction Performance & Volume Statistics",
            "current_content": tab_intel,
            "test_scenario": jmx_name,
            "total_transactions_defined": len(labels),
            "total_samples": summary.get("total", 0),
            "total_iterations": summary.get("total_iterations", 0),
            "throughput_rps": round(summary.get("throughput", 0), 2),
            "duration_sec": round(duration_sec, 1),
            "transaction_breakdown": [
                {
                    "transaction": name,
                    "samples": d.get("count", 0),
                    "iterations": d.get("iterations", 0),
                    "passed": d.get("count", 0) - d.get("errors", 0),
                    "failed": d.get("errors", 0),
                    "tps": round(d.get("count", 0) / max(1, duration_sec), 2)
                }
                for name, d in sorted_by_count[:20]
            ]
        }

    # ── 6. Response Time & SLA Tab Digest ──
    elif section_id == "tab_rt_stats":
        sla_targets = {}
        default_rt = 500.0
        try:
            from python_files.sla_manager import load_sla_targets
            sla_targets, default_rt, _ = load_sla_targets(jmx_name, actual_users=users)
            sla_targets = sla_targets or {}
        except Exception:
            pass

        breaches = []
        rt_list = []
        for name, d in labels.items():
            p90 = d.get("p90", d.get("avg_rt", 0))
            tgt = sla_targets.get(name, {}).get("rt", default_rt)
            dev_pct = ((p90 - tgt) / max(1, tgt) * 100) if tgt > 0 else 0
            is_breached = p90 > tgt
            item = {
                "transaction": name,
                "avg_ms": round(d.get("avg_rt", 0), 1),
                "p50_ms": round(d.get("p50", 0), 1),
                "p90_ms": round(p90, 1),
                "p95_ms": round(d.get("p95", 0), 1),
                "p99_ms": round(d.get("p99", 0), 1),
                "sla_target_rt_ms": round(tgt, 1),
                "sla_status": "BREACHED" if is_breached else "MET",
                "sla_dev_pct": round(dev_pct, 1)
            }
            rt_list.append(item)
            if is_breached:
                breaches.append(item)

        sorted_breaches = sorted(breaches, key=lambda x: x["sla_dev_pct"], reverse=True)
        sorted_slowest = sorted(rt_list, key=lambda x: x["p90_ms"], reverse=True)
        tab_intel = ai_intel.get("tab_rt_stats", {}) if isinstance(ai_intel, dict) else {}

        return {
            "section_id": "tab_rt_stats",
            "section_name": "Response Time & SLA Adherence",
            "current_content": tab_intel,
            "global_default_sla_ms": default_rt,
            "overall_avg_rt_ms": round(summary.get("avg_rt", 0), 1),
            "overall_p90_rt_ms": round(summary.get("p90", 0), 1),
            "total_transactions": len(labels),
            "breached_transactions_count": len(breaches),
            "sla_compliance_pct": round(((len(labels) - len(breaches)) / max(1, len(labels))) * 100, 1),
            "sla_breached_transactions": sorted_breaches[:15],
            "slowest_transactions": sorted_slowest[:10]
        }

    # ── 7. Reliability & Error Stats Tab Digest ──
    elif section_id == "tab_error_stats":
        error_details = result_data.get("error_details", {})
        compact_errors = []
        if isinstance(error_details, dict):
            for code, edata in error_details.items():
                if isinstance(edata, dict):
                    compact_errors.append({
                        "http_code": code,
                        "total_errors": edata.get("count", 0),
                        "message": edata.get("failure_message") or edata.get("message", "HTTP Error")
                    })
        
        err_txs = []
        for name, d in labels.items():
            if d.get("errors", 0) > 0:
                err_txs.append({
                    "transaction": name,
                    "total_samples": d.get("count", 0),
                    "error_count": d.get("errors", 0),
                    "error_rate_pct": round(d.get("error_rate", 0), 2)
                })
        sorted_err_txs = sorted(err_txs, key=lambda x: x["error_count"], reverse=True)
        tab_intel = ai_intel.get("tab_error_stats", {}) if isinstance(ai_intel, dict) else {}

        return {
            "section_id": "tab_error_stats",
            "section_name": "Reliability & Error Distribution",
            "current_content": tab_intel,
            "overall_error_count": summary.get("errors", 0),
            "overall_error_rate_pct": round(summary.get("error_rate", 0), 2),
            "total_samples": summary.get("total", 0),
            "failing_transactions_count": len(err_txs),
            "failing_transactions": sorted_err_txs[:15],
            "error_code_summary": compact_errors if compact_errors else "No detailed HTTP error codes reported"
        }

    # ── 8. Infrastructure Monitoring Tab Digest ──
    elif section_id == "tab_infra_stats":
        infra = azure_data.get("infra_summary", {}) if isinstance(azure_data, dict) else {}
        correlation = result_data.get("correlation", {})
        corr_findings = correlation.get("findings", []) if isinstance(correlation, dict) else []
        tab_intel = ai_intel.get("tab_infra_stats", {}) if isinstance(ai_intel, dict) else {}

        return {
            "section_id": "tab_infra_stats",
            "section_name": "Infrastructure & Server-Side Monitoring",
            "current_content": tab_intel,
            "azure_metrics": {
                "avg_cpu_pct": infra.get("avg_cpu", 0),
                "max_cpu_peak_pct": infra.get("max_cpu", 0),
                "avg_memory_pct": infra.get("avg_memory", 0),
                "max_memory_peak_pct": infra.get("max_memory", 0),
                "network_in_mb_min": infra.get("avg_network_in_mbps", 0),
                "network_out_mb_min": infra.get("avg_network_out_mbps", 0),
                "disk_read_iops": infra.get("avg_disk_read_iops", 0),
                "disk_write_iops": infra.get("avg_disk_write_iops", 0),
            } if infra else "Azure Monitor metrics not configured or recorded for this run.",
            "correlation_findings": corr_findings[:10] if corr_findings else "No infrastructure correlation anomalies detected."
        }

    # Default fallback
    return {
        "section_id": section_id,
        "section_name": section_id,
        "summary": summary
    }


def build_chat_system_prompt(section_id: str, section_digest: Dict[str, Any]) -> str:
    """
    Constructs a disciplined system prompt for section Q&A with agentic section-patching abilities.
    """
    section_name = section_digest.get("section_name", section_id)
    digest_json = json.dumps(section_digest, indent=2)

    return f"""You are an Agentic Senior Performance Engineer AI Assistant embedded inside the PerfPilot report for the section: "{section_name}".

STRICT BEHAVIOR & SCOPE RULES:
1. Ground all answers and edits STRICTLY in the provided JSON metrics and current section content below.
2. NEVER make up numbers or guess values not present in the data. Cite exact response times, error counts, percentages, and transaction names.
3. Tone: Professional, objective, direct, factual, client-ready performance engineering. Keep answers concise.
4. DO NOT use internal code tags like F-001 or R-001.

AGENTIC REPORT EDITING / REWRITING INSTRUCTIONS:
If the user asks you to rewrite, update, refine, replace, or add content to this section (e.g. "rewrite adding X", "update conclusions with Y", "add a recommendation for Z"):
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
- For "exec_observations": JSON array of observation objects: [{{"category": "1. Transaction Statistics", "observation": "a. Detail...\nb. Detail..."}}, {{"category": "2. Response Time Statistics", "observation": "..."}}, ...]
- For "exec_recommendations": JSON array of recommendation objects: [{{"badge": "🟠", "title": "Short Title", "priority": "High", "detail": "Technical action detail...", "business_impact": "Direct revenue or user impact..."}}]
- For "tab_tx_stats", "tab_rt_stats", "tab_error_stats", "tab_infra_stats": JSON object: {{"observations": ["Observation 1", "Observation 2"], "recommendations": ["Recommendation 1"]}}

CURRENT SECTION CONTEXT DATA:
{digest_json}
"""
