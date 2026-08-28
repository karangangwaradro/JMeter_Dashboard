#!/usr/bin/env python3
"""
findings_engine.py — Structured Performance Findings Generator for PerfPilot.

Produces structured Finding objects (F-001, F-002, ...) with evidence chains,
interpretations, and linked Recommendations (R-001 → F-001) from test data.

This module is the core "intelligence layer" that drives inline AI observations
throughout the report. It operates deterministically (rule-based) and can be
enriched by AI (Gemini/GitHub) for deeper interpretations.
"""

from typing import Dict, List, Optional, Tuple


# ── Severity Constants (Deviation Terminology) ─────────────────────────────────
SEV_CRITICAL = "Critical Deviation"
SEV_HIGH = "Slightly Deviated"
SEV_MEDIUM = "Acceptable Deviation"
SEV_LOW = "No Deviation"

# Severity → badge mapping for report rendering
SEVERITY_BADGES = {
    SEV_CRITICAL: ("🔴", "var(--red)"),
    SEV_HIGH:     ("🟠", "var(--yellow)"),
    SEV_MEDIUM:   ("🟡", "#f59e0b"),
    SEV_LOW:      ("🟢", "var(--green)"),
}

# ── Category Constants ───────────────────────────────────────────────────────────
CAT_LATENCY_BOTTLENECK = "latency_bottleneck"
CAT_SLA_BREACH = "sla_breach"
CAT_ERROR_ANOMALY = "error_anomaly"
CAT_TAIL_LATENCY = "tail_latency"
CAT_THROUGHPUT_DEGRADATION = "throughput_degradation"
CAT_INFRA_CORRELATION = "infrastructure_correlation"
CAT_CAPACITY_CONCERN = "capacity_concern"
CAT_STABILITY = "stability"


def generate_findings(summary: dict, labels: dict, display_labels: dict,
                      time_series: dict, infra: dict, correlation: dict,
                      sla_targets: dict, default_rt: float = 500.0,
                      default_err: float = 1.0, test_name: str = "Scenario",
                      ai_insights: dict = None, auto_ai: bool = True) -> dict:
    """
    Generate structured Findings from test data and natively enrich with AI if available.
    Strictly AI-based: Rule-based text observations and fallback narratives have been removed.
    """
    findings = []
    finding_counter = [0]  # mutable counter for closure

    def next_id():
        finding_counter[0] += 1
        return f"F-{finding_counter[0]:03d}"

    # ── 1. Transaction-Level Findings ────────────────────────────────────────
    avg_rt = summary.get("avg_rt", 0)
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    error_rate = summary.get("error_rate", 0)
    throughput = summary.get("throughput", 0)
    max_rt = summary.get("max_rt", 0)

    # Sort transactions by avg RT descending to identify bottleneck
    sorted_txns = sorted(display_labels.items(),
                         key=lambda x: x[1].get("avg_rt", 0), reverse=True)

    # Map: transaction name → finding (for table column rendering)
    tx_findings = {}

    # Primary latency bottleneck: slowest transaction that is > 1.5x overall average
    if sorted_txns:
        top_name, top_data = sorted_txns[0]
        top_avg = top_data.get("avg_rt", 0)
        top_p95 = top_data.get("p95", 0)
        top_target = sla_targets.get(top_name, {}).get("rt", default_rt)
        deviation = round(top_avg / max(1, avg_rt), 1)

        if top_avg > avg_rt * 1.5 and top_avg > 200:
            fid = next_id()
            top_p90 = top_data.get("p90", 0)
            dev_pct = ((top_p90 - top_target) / max(1, top_target)) * 100 if top_target > 0 else 0
            finding = {
                "id": fid,
                "category": CAT_LATENCY_BOTTLENECK,
                "evidence_class": "DERIVED",
                "severity": SEV_CRITICAL if top_avg > top_target * 2 else SEV_HIGH,
                "title": f"{top_name} latency deviation ({top_p90:.0f} ms)",
                "observation": "",
                "evidence": [
                    {"metric": "P90 Response Time", "value": f"{top_p90} ms",
                     "baseline": f"{top_target:.0f} ms SLA target",
                     "source": "Transaction Breakdown"},
                    {"metric": "Deviation", "value": f"{dev_pct:+.1f}%",
                     "baseline": "", "source": "Calculated"},
                ],
                "interpretation": "",
                "why_it_matters": "",
                "root_cause_assessment": "",
                "confidence": {},
                "evidence_sources": ["Transaction Breakdown", "Response Time Over Time"],
            }
            findings.append(finding)
            tx_findings[top_name] = finding

    # SLA breach findings for each breaching transaction
    for tx_name, tx_data in sorted_txns:
        if tx_name in tx_findings:
            continue  # Already captured as primary bottleneck

        target = sla_targets.get(tx_name, {"rt": default_rt, "err": default_err})
        target_rt = target.get("rt", default_rt)
        target_err = target.get("err", default_err)
        tx_p90 = tx_data.get("p90", 0)
        tx_avg = tx_data.get("avg_rt", 0)
        tx_err = tx_data.get("error_rate", 0)

        p90_breached = tx_p90 > target_rt
        err_breached = tx_err > target_err

        if p90_breached and tx_name not in tx_findings:
            fid = next_id()
            severity = SEV_CRITICAL if tx_p90 > target_rt * 3 else SEV_HIGH if tx_p90 > target_rt * 2 else SEV_MEDIUM
            finding = {
                "id": fid,
                "category": CAT_SLA_BREACH,
                "evidence_class": "DERIVED",
                "severity": severity,
                "title": f"{tx_name} SLA deviation ({tx_p90:.0f} ms)",
                "observation": "",
                "evidence": [
                    {"metric": "P90 Response Time", "value": f"{tx_p90} ms",
                     "baseline": f"{target_rt:.0f} ms SLA target",
                     "source": "Transaction Breakdown"},
                    {"metric": "Deviation", "value": f"{round((tx_p90 / max(1, target_rt) - 1) * 100)}%",
                     "baseline": "",
                     "source": "SLA Engine"},
                ],
                "interpretation": "",
                "why_it_matters": "",
                "root_cause_assessment": "",
                "confidence": {},
                "evidence_sources": ["Transaction Breakdown", "SLA Breach Analysis"],
            }
            findings.append(finding)
            tx_findings[tx_name] = finding

        elif err_breached and tx_name not in tx_findings:
            fid = next_id()
            finding = {
                "id": fid,
                "category": CAT_ERROR_ANOMALY,
                "evidence_class": "MEASURED",
                "severity": SEV_HIGH if tx_err > 5 else SEV_MEDIUM,
                "title": f"{tx_name} error anomaly ({tx_err:.2f}%)",
                "observation": "",
                "evidence": [
                    {"metric": "Error Rate", "value": f"{tx_err:.2f}%",
                     "baseline": f"{target_err}% target",
                     "source": "Transaction Breakdown"},
                ],
                "interpretation": "",
                "why_it_matters": "",
                "root_cause_assessment": "",
                "confidence": {},
                "evidence_sources": ["Transaction Breakdown", "Error Distribution & Analysis"],
            }
            findings.append(finding)
            tx_findings[tx_name] = finding

    # ── 2. Tail Latency Finding ──────────────────────────────────────────────
    if p99 > avg_rt * 2.5 and p99 > 200:
        fid = next_id()
        p90_val = summary.get("p90", p95)
        dev_pct = ((p99 - max(1, p90_val)) / max(1, p90_val)) * 100
        tail_finding = {
            "id": fid,
            "category": CAT_TAIL_LATENCY,
            "evidence_class": "DERIVED",
            "severity": SEV_HIGH if p99 > avg_rt * 4 else SEV_MEDIUM,
            "title": f"Elevated tail latency (P99: {p99:.0f} ms)",
            "observation": "",
            "evidence": [
                {"metric": "P99 Response Time", "value": f"{p99:.0f} ms",
                 "baseline": f"{avg_rt:.0f} ms Avg RT",
                 "source": "Response Time Distribution"},
                {"metric": "P90 Response Time", "value": f"{p90_val} ms",
                 "baseline": f"{default_rt:.0f} ms SLA target",
                 "source": "Response Time Over Time"},
            ],
            "interpretation": "",
            "why_it_matters": "",
            "root_cause_assessment": "",
            "confidence": {},
            "evidence_sources": ["Response Time Over Time", "Response Time Distribution"],
        }
        findings.append(tail_finding)

    # ── 3. Throughput Degradation Finding ─────────────────────────────────────
    ts_throughput = time_series.get("ts_throughput", [])
    if ts_throughput and len(ts_throughput) > 4:
        first_third = ts_throughput[:len(ts_throughput) // 3]
        last_third = ts_throughput[-len(ts_throughput) // 3:]
        if first_third and last_third:
            avg_first = sum(first_third) / len(first_third)
            avg_last = sum(last_third) / len(last_third)
            if avg_first > 0 and avg_last < avg_first * 0.7:
                degradation_pct = round((1 - avg_last / avg_first) * 100)
                fid = next_id()
                findings.append({
                    "id": fid,
                    "category": CAT_THROUGHPUT_DEGRADATION,
                    "evidence_class": "CORRELATED",
                    "severity": SEV_HIGH,
                    "title": f"Throughput degraded by {degradation_pct}%",
                    "observation": "",
                    "evidence": [
                        {"metric": "Early Throughput", "value": f"{avg_first:.1f} req/s",
                         "baseline": "", "source": "Throughput & Errors"},
                        {"metric": "Late Throughput", "value": f"{avg_last:.1f} req/s",
                         "baseline": f"{avg_first:.1f} req/s initial",
                         "source": "Throughput & Errors"},
                    ],
                    "interpretation": "",
                    "why_it_matters": "",
                    "root_cause_assessment": "",
                    "confidence": {},
                    "evidence_sources": ["Throughput & Errors"],
                })

    # ── 4. Infrastructure Correlation Findings ───────────────────────────────
    if infra:
        avg_cpu = infra.get("avg_cpu", 0)
        max_cpu = infra.get("max_cpu", 0)
        avg_memory = infra.get("avg_memory", 0)
        max_memory = infra.get("max_memory", 0)

        if max_cpu >= 80:
            fid = next_id()
            findings.append({
                "id": fid,
                "category": CAT_INFRA_CORRELATION,
                "evidence_class": "MEASURED",
                "severity": SEV_HIGH if max_cpu >= 90 else SEV_MEDIUM,
                "title": f"Server CPU peak at {max_cpu:.0f}%",
                "observation": "",
                "evidence": [
                    {"metric": "Peak CPU", "value": f"{max_cpu:.1f}%",
                     "baseline": "80% warning threshold",
                     "source": "Azure Resource Utilization"},
                    {"metric": "Avg CPU", "value": f"{avg_cpu:.1f}%",
                     "baseline": "",
                     "source": "Azure Resource Utilization"},
                ],
                "interpretation": "",
                "why_it_matters": "",
                "root_cause_assessment": "",
                "confidence": {},
                "evidence_sources": ["Azure Resource Utilization"],
            })

        if max_memory >= 80:
            fid = next_id()
            findings.append({
                "id": fid,
                "category": CAT_INFRA_CORRELATION,
                "evidence_class": "MEASURED",
                "severity": SEV_HIGH if max_memory >= 90 else SEV_MEDIUM,
                "title": f"Server Memory peak at {max_memory:.0f}%",
                "observation": "",
                "evidence": [
                    {"metric": "Peak Memory", "value": f"{max_memory:.1f}%",
                     "baseline": "80% warning threshold",
                     "source": "Azure Resource Utilization"},
                    {"metric": "Avg Memory", "value": f"{avg_memory:.1f}%",
                     "baseline": "",
                     "source": "Azure Resource Utilization"},
                ],
                "interpretation": "",
                "why_it_matters": "",
                "root_cause_assessment": "",
                "confidence": {},
                "evidence_sources": ["Azure Resource Utilization"],
            })

    # ── 5. Overall Error Rate Finding ────────────────────────────────────────
    if error_rate > 1 and not any(f["category"] == CAT_ERROR_ANOMALY for f in findings):
        fid = next_id()
        findings.append({
            "id": fid,
            "category": CAT_ERROR_ANOMALY,
            "evidence_class": "MEASURED",
            "severity": SEV_CRITICAL if error_rate > 5 else SEV_HIGH,
            "title": f"Overall error rate at {error_rate:.2f}%",
            "observation": "",
            "evidence": [
                {"metric": "Error Rate", "value": f"{error_rate:.2f}%",
                 "baseline": "< 1% acceptable",
                 "source": "Executive Summary KPIs"},
            ],
            "interpretation": "",
            "why_it_matters": "",
            "root_cause_assessment": "",
            "confidence": {},
            "evidence_sources": ["Error Distribution & Analysis", "Overall Summary"],
        })

    # ── 6. Chart Observations (Strictly AI-based) ────────────────────────────
    chart_observations = {}

    # ── 7. Recommendations (Strictly AI-based) ───────────────────────────────
    recommendations = []

    # ── 8. Overall Assessment ────────────────────────────────────────────────
    overall = _compute_overall_assessment(findings, summary, error_rate)

    # ── 9. Base Performance Intelligence (Strictly metrics, no rule-based text) ─
    perf_intelligence = build_performance_intelligence(
        summary=summary, labels=labels, display_labels=display_labels,
        time_series=time_series, infra=infra, correlation=correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err
    )

    findings_result = {
        "findings": findings,
        "recommendations": recommendations,
        "chart_observations": chart_observations,
        "transaction_findings": tx_findings,
        "overall_assessment": overall,
        "performance_intelligence": perf_intelligence,
    }

    # ── 10. Native AI Execution & Enrichment ──────────────────────────────────
    if ai_insights is None and auto_ai:
        try:
            from python_files.ai_insights import generate_insights
            ai_insights = generate_insights(
                test_name=test_name,
                summary=summary,
                labels=labels,
                time_series={},
                infra=infra if infra else {},
                correlation=correlation if correlation else {},
                sla_targets=sla_targets,
                default_rt=default_rt,
                default_err=default_err
            )
        except Exception as e:
            print(f"[FindingsEngine] Native AI execution skipped: {e}", flush=True)

    if ai_insights and ai_insights.get("source") != "none":
        findings_result = enrich_findings_with_ai(findings_result, ai_insights)

    return findings_result


def build_performance_intelligence(summary: dict, labels: dict, display_labels: dict,
                                   time_series: dict, infra: dict, correlation: dict,
                                   sla_targets: dict, default_rt: float = 500.0,
                                   default_err: float = 1.0) -> dict:
    """
    Build clean, metric-driven Performance Intelligence data structure.
    Strictly AI-based: Does NOT inject hardcoded or rule-based fallback narratives.
    """
    avg_rt = summary.get("avg_rt", 0)
    p90 = summary.get("p90", summary.get("p95", 0))
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    error_rate = summary.get("error_rate", 0)
    throughput = summary.get("throughput", 0)
    total_samples = summary.get("total", 0)

    active_labels = display_labels if display_labels else labels
    total_iterations = max((v.get("count", 0) for v in active_labels.values()), default=total_samples)
    total_tx_executions = sum(v.get("count", 0) for v in active_labels.values()) if active_labels else total_samples
    tc_errors = sum(v.get("errors", 0) for v in active_labels.values()) if active_labels else summary.get("errors", 0)
    if total_tx_executions > 0:
        error_rate = round((tc_errors / total_tx_executions * 100), 2)
    
    total_tx_count = len(active_labels)
    
    breached_count = 0
    for tx_name, tx_data in active_labels.items():
        t_target = sla_targets.get(tx_name, {}).get("rt", default_rt)
        t_err_target = sla_targets.get(tx_name, {}).get("err", default_err)
        t_p90 = tx_data.get("p90", 0)
        t_err = tx_data.get("error_rate", 0)
        dev_pct = ((t_p90 - t_target) / t_target * 100) if t_target > 0 else 0
        if (dev_pct > 30) or (t_err > t_err_target):
            breached_count += 1
            
    met_count = total_tx_count - breached_count
    compliance_pct = (met_count / max(1, total_tx_count)) * 100

    avg_cpu = infra.get("avg_cpu", 0) if infra else 0
    max_cpu = infra.get("max_cpu", 0) if infra else 0
    avg_mem = infra.get("avg_memory", 0) if infra else 0
    max_mem = infra.get("max_memory", 0) if infra else 0
    
    kpis = {
        "sla": {
            "title": "SLA Compliance",
            "value": f"{compliance_pct:.0f}%",
            "sub": f"{met_count}/{total_tx_count} Transactions Met",
            "status": "pass" if compliance_pct >= 90 else "warning" if compliance_pct >= 70 else "fail",
            "badge": "🟢 Passed" if compliance_pct >= 90 else "⚠️ Warning" if compliance_pct >= 70 else "🔴 Breached"
        },
        "error_rate": {
            "title": "Error Rate",
            "value": f"{error_rate:.1f}%",
            "sub": f"{tc_errors:,} failed samples",
            "status": "pass" if error_rate <= 1.0 else "fail",
            "badge": "🟢 Stable" if error_rate <= 1.0 else "🔴 Elevated"
        },
        "throughput": {
            "title": "Throughput",
            "value": f"{throughput:.1f} TPS",
            "sub": f"{total_tx_executions:,} total executions",
            "status": "pass",
            "badge": "🟢 Steady"
        },
        "infra": {
            "title": "Infrastructure",
            "value": "HEALTHY" if max_cpu < 75 else "SATURATED",
            "sub": f"Peak CPU {max_cpu:.0f}% · Mem {avg_mem:.0f}%" if infra else "Telemetry Adequate",
            "status": "pass" if max_cpu < 75 else "warning",
            "badge": "🟢 Adequate" if max_cpu < 75 else "⚠️ High Load"
        }
    }

    return {
        "executive_summary": {
            "assessment_badge": "",
            "assessment_color": "",
            "assessment_text": "",
            "kpis": kpis,
            "observations_table": [],
            "conclusions": [],
            "priority_recommendations": []
        },
        "tab_tx_stats": {
            "observations": [],
            "recommendations": []
        },
        "tab_rt_stats": {
            "observations": [],
            "recommendations": []
        },
        "tab_error_stats": {
            "observations": [],
            "recommendations": []
        },
        "tab_infra_stats": {
            "observations": [],
            "recommendations": []
        }
    }


def enrich_findings_with_ai(findings_result: dict, ai_insights: dict) -> dict:
    """
    Merge AI-generated enrichments into the deterministic findings and performance intelligence.
    """
    if not ai_insights:
        return findings_result

    # Merge into performance intelligence if present
    if "performance_intelligence" in findings_result and "performance_intelligence" in ai_insights:
        ai_perf = ai_insights["performance_intelligence"]
        base_perf = findings_result["performance_intelligence"]
        
        # Overlay executive summary fields if provided
        if "executive_summary" in ai_perf:
            ai_exec = ai_perf["executive_summary"]
            if "assessment_text" in ai_exec and ai_exec["assessment_text"]:
                base_perf["executive_summary"]["assessment_text"] = ai_exec["assessment_text"]
            if "conclusions" in ai_exec and ai_exec["conclusions"]:
                base_perf["executive_summary"]["conclusions"] = ai_exec["conclusions"]
            if "priority_recommendations" in ai_exec and ai_exec["priority_recommendations"]:
                base_perf["executive_summary"]["priority_recommendations"] = ai_exec["priority_recommendations"]
            if "observations_table" in ai_exec and ai_exec["observations_table"]:
                base_perf["executive_summary"]["observations_table"] = ai_exec["observations_table"]

        # Overlay tab insights
        for tab_key in ["tab_tx_stats", "tab_rt_stats", "tab_error_stats", "tab_infra_stats"]:
            if tab_key in ai_perf:
                if "observations" in ai_perf[tab_key] and ai_perf[tab_key]["observations"]:
                    base_perf[tab_key]["observations"] = ai_perf[tab_key]["observations"]
                if "recommendations" in ai_perf[tab_key] and ai_perf[tab_key]["recommendations"]:
                    base_perf[tab_key]["recommendations"] = ai_perf[tab_key]["recommendations"]

    enrichments = ai_insights.get("finding_enrichments", {})
    for finding in findings_result.get("findings", []):
        fid = finding["id"]
        if fid in enrichments:
            enrich = enrichments[fid]
            if enrich.get("evidence_class"):
                finding["evidence_class"] = enrich["evidence_class"]
            if enrich.get("observation"):
                finding["observation"] = enrich["observation"]
            if enrich.get("interpretation"):
                finding["interpretation"] = enrich["interpretation"]
            if enrich.get("likely_cause"):
                finding["likely_cause"] = enrich["likely_cause"]
                finding["root_cause_assessment"] = enrich["likely_cause"]
            elif enrich.get("root_cause_assessment"):
                finding["root_cause_assessment"] = enrich["root_cause_assessment"]
            if enrich.get("impact"):
                finding["why_it_matters"] = enrich["impact"]
            elif enrich.get("why_it_matters"):
                finding["why_it_matters"] = enrich["why_it_matters"]
            if enrich.get("recommendation"):
                finding["recommendation"] = enrich["recommendation"]
            if enrich.get("validation"):
                finding["validation"] = enrich["validation"]
            if enrich.get("limitations"):
                finding["limitations"] = enrich["limitations"]
            if enrich.get("confidence"):
                if "confidence" not in finding or not isinstance(finding["confidence"], dict):
                    finding["confidence"] = {}
                finding["confidence"]["ai_confidence"] = enrich["confidence"]
            if enrich.get("evidence") and isinstance(enrich["evidence"], list):
                finding["evidence"] = [
                    {
                        "metric": ev.get("metric", "Metric"),
                        "value": str(ev.get("value", "")),
                        "source": ev.get("source", "Telemetry"),
                        "baseline": ev.get("baseline", "")
                    }
                    for ev in enrich["evidence"] if isinstance(ev, dict)
                ]

    ai_recs = ai_insights.get("recommendations", [])
    if ai_recs:
        findings_result["recommendations"] = ai_recs

    if "data_quality_findings" in ai_insights:
        findings_result["data_quality_findings"] = ai_insights["data_quality_findings"]
    
    if "root_cause_assessment" in ai_insights:
        findings_result["overall_root_cause"] = ai_insights["root_cause_assessment"]

    if "capacity_planning" in ai_insights:
        findings_result["capacity_planning"] = ai_insights["capacity_planning"]

    return findings_result


# ── Chart Observation Generators ─────────────────────────────────────────────

def _generate_chart_observations(summary: dict, time_series: dict,
                                 findings: list, infra: dict) -> dict:
    """Rule-based chart observations removed. Observations must come strictly from AI."""
    return {}


# ── Recommendation Generator ────────────────────────────────────────────────

def _generate_recommendations(findings: list, summary: dict, infra: dict) -> list:
    """Rule-based recommendations removed. Recommendations must come strictly from AI."""
    return []


# ── Overall Assessment ───────────────────────────────────────────────────────

def _compute_overall_assessment(findings: list, summary: dict,
                                error_rate: float) -> dict:
    """Compute the overall performance assessment status."""
    critical_count = sum(1 for f in findings if f["severity"] == SEV_CRITICAL)
    high_count = sum(1 for f in findings if f["severity"] == SEV_HIGH)

    if critical_count > 0:
        status = "Performance requires immediate attention"
        icon = "🔴"
        color = "var(--red)"
    elif high_count > 0:
        status = "Performance requires optimization"
        icon = "🟠"
        color = "var(--yellow)"
    elif findings:
        status = "Performance is acceptable with minor observations"
        icon = "🟡"
        color = "#f59e0b"
    else:
        status = "Performance meets all targets"
        icon = "🟢"
        color = "var(--green)"

    return {
        "status": status,
        "icon": icon,
        "color": color,
        "total_findings": len(findings),
        "critical": critical_count,
        "high": high_count,
        "medium": sum(1 for f in findings if f["severity"] == SEV_MEDIUM),
        "low": sum(1 for f in findings if f["severity"] == SEV_LOW),
    }
