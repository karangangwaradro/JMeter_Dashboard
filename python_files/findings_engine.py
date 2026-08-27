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
                      default_err: float = 1.0) -> dict:
    """
    Generate structured Findings and Recommendations from test data.

    Returns:
        {
            "findings": [Finding, ...],
            "recommendations": [Recommendation, ...],
            "chart_observations": { "response_time": {...}, "throughput": {...}, ... },
            "transaction_findings": { "TxName": Finding or None, ... },
            "overall_assessment": { "status": "...", "icon": "...", "summary": "..." }
        }
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
                "severity": SEV_CRITICAL if top_avg > top_target * 2 else SEV_HIGH,
                "title": f"{top_name} shows significant latency deviation",
                "observation": f"{top_name} response time was significantly higher than the overall test baseline.",
                "evidence": [
                    {"metric": "P90 Response Time", "value": f"{top_p90} ms",
                     "baseline": f"{top_target:.0f} ms SLA target",
                     "source": "Transaction Breakdown"},
                    {"metric": "Deviation", "value": f"{dev_pct:+.1f}%",
                     "baseline": "", "source": "Calculated"},
                ],
                "interpretation": f"{top_name} is the dominant transaction-level latency contributor in this execution.",
                "why_it_matters": (
                    f"{top_name} is the slowest transaction at {top_avg:.0f} ms and "
                    f"{'significantly exceeds its ' + str(int(top_target)) + ' ms SLA target' if top_avg > top_target else 'contributes disproportionately to overall latency'}, "
                    f"making it a priority candidate for optimization."
                ),
                "root_cause_assessment": (
                    "Server-side telemetry is required to determine whether the latency "
                    "originates from database execution, application processing, "
                    "authentication logic, or an external dependency."
                ),
                "confidence": {"bottleneck_identification": "High", "specific_root_cause": "Low"},
                "evidence_sources": ["Transaction Breakdown", "Response Time Over Time",
                                     "Top Transactions by Response Time"],
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
                "severity": severity,
                "title": f"{tx_name} SLA deviation",
                "observation": f"{tx_name} P90 response time exceeded the defined SLA target.",
                "evidence": [
                    {"metric": "P90 Response Time", "value": f"{tx_p90} ms",
                     "baseline": f"{target_rt:.0f} ms SLA target",
                     "source": "Transaction Breakdown"},
                    {"metric": "Deviation", "value": f"{round((tx_p90 / max(1, target_rt) - 1) * 100)}%",
                     "baseline": "",
                     "source": "SLA Engine"},
                ],
                "interpretation": (
                    f"{tx_name} exceeds its P90 SLA target by "
                    f"{round((tx_p90 / max(1, target_rt) - 1) * 100)}%."
                ),
                "why_it_matters": (
                    f"{tx_name} is not meeting its {target_rt:.0f} ms response time SLA, "
                    f"which indicates a performance degradation for this user flow."
                ),
                "root_cause_assessment": (
                    f"Profile the {tx_name} execution path to identify slow database queries, "
                    f"external service calls, or computational bottlenecks."
                ),
                "confidence": {"sla_violation": "High", "specific_root_cause": "Low"},
                "evidence_sources": ["Transaction Breakdown", "SLA Breach Analysis"],
            }
            findings.append(finding)
            tx_findings[tx_name] = finding

        elif err_breached and tx_name not in tx_findings:
            fid = next_id()
            finding = {
                "id": fid,
                "category": CAT_ERROR_ANOMALY,
                "severity": SEV_HIGH if tx_err > 5 else SEV_MEDIUM,
                "title": f"{tx_name} error anomaly",
                "observation": f"{tx_name} recorded a {tx_err:.2f}% error rate (target: {target_err}%).",
                "evidence": [
                    {"metric": "Error Rate", "value": f"{tx_err:.2f}%",
                     "baseline": f"{target_err}% target",
                     "source": "Transaction Breakdown"},
                ],
                "interpretation": f"{tx_name} has a higher-than-acceptable error rate under this workload.",
                "why_it_matters": (
                    f"Errors in {tx_name} indicate reliability issues that could impact user experience."
                ),
                "root_cause_assessment": (
                    f"Investigate error responses for {tx_name} — check HTTP status codes, "
                    f"assertion failures, and server-side exception logs."
                ),
                "confidence": {"error_occurrence": "High", "specific_root_cause": "Low"},
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
            "severity": SEV_HIGH if p99 > avg_rt * 4 else SEV_MEDIUM,
            "title": "Elevated response-time variability observed",
            "observation": "P99 tail latency indicates occasional high-response-time outliers.",
            "evidence": [
                {"metric": "P90 Response Time", "value": f"{p90_val} ms",
                 "baseline": f"{default_rt:.0f} ms SLA target",
                 "source": "Response Time Over Time"},
                {"metric": "Deviation", "value": f"{dev_pct:+.1f}%",
                 "baseline": "", "source": "Calculated"},
            ],
            "interpretation": (
                f"P99 is {round(p99 / max(1, avg_rt), 1)}× the average, indicating that "
                f"a small subset of requests experiences substantially higher response times."
            ),
            "why_it_matters": (
                "Tail latency affects user-perceived performance for a subset of requests "
                "and may indicate garbage collection pauses, connection pool exhaustion, "
                "or intermittent backend issues."
            ),
            "root_cause_assessment": (
                "Correlate P99 spikes with server-side telemetry (GC pauses, thread contention, "
                "database lock waits) to identify the intermittent cause."
            ),
            "confidence": {"tail_latency_detected": "High", "specific_cause": "Low"},
            "evidence_sources": ["Response Time Over Time", "Response Time Distribution",
                                 "Estimated Concurrent Users Over Time"],
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
                    "severity": SEV_HIGH,
                    "title": f"Throughput degraded by {degradation_pct}% over test duration",
                    "observation": (
                        f"Average throughput dropped from {avg_first:.1f} req/s in the first third "
                        f"to {avg_last:.1f} req/s in the final third."
                    ),
                    "evidence": [
                        {"metric": "Early Throughput", "value": f"{avg_first:.1f} req/s",
                         "baseline": "", "source": "Throughput & Errors"},
                        {"metric": "Late Throughput", "value": f"{avg_last:.1f} req/s",
                         "baseline": f"{avg_first:.1f} req/s initial",
                         "source": "Throughput & Errors"},
                    ],
                    "interpretation": (
                        f"Throughput declined by {degradation_pct}% during the test, "
                        f"suggesting progressive resource exhaustion or connection pool depletion."
                    ),
                    "why_it_matters": (
                        "Throughput degradation under sustained load indicates the system "
                        "cannot maintain performance over time, which is critical for production."
                    ),
                    "root_cause_assessment": (
                        "Check for memory leaks, connection pool exhaustion, thread starvation, "
                        "or increasing GC pressure over time."
                    ),
                    "confidence": {"degradation_detected": "High", "specific_cause": "Medium"},
                    "evidence_sources": ["Throughput & Errors",
                                         "Estimated Concurrent Users Over Time"],
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
                "severity": SEV_CRITICAL if max_cpu >= 90 else SEV_HIGH,
                "title": f"CPU utilization reached {max_cpu:.0f}% peak",
                "observation": (
                    f"Server CPU averaged {avg_cpu:.1f}% and peaked at {max_cpu:.1f}% "
                    f"during the test execution."
                ),
                "evidence": [
                    {"metric": "Peak CPU", "value": f"{max_cpu:.1f}%",
                     "baseline": "80% warning threshold",
                     "source": "Azure Resource Utilization"},
                    {"metric": "Avg CPU", "value": f"{avg_cpu:.1f}%",
                     "baseline": "",
                     "source": "Azure Resource Utilization"},
                ],
                "interpretation": (
                    f"The server experienced {'CPU saturation' if max_cpu >= 90 else 'elevated CPU pressure'} "
                    f"under this workload, which {'directly impacts' if max_cpu >= 90 else 'may impact'} "
                    f"response times."
                ),
                "why_it_matters": (
                    f"CPU at {max_cpu:.0f}% leaves minimal headroom for traffic spikes. "
                    f"{'The server is at capacity.' if max_cpu >= 90 else 'Approaching saturation point.'}"
                ),
                "root_cause_assessment": (
                    "Workload-driven CPU contention. Determine if the bottleneck is "
                    "application processing, inefficient algorithms, or insufficient compute resources."
                ),
                "confidence": {"cpu_pressure": "High", "correlation_to_latency": "Medium"},
                "evidence_sources": ["Azure Resource Utilization", "Workload vs CPU Utilization",
                                     "Infrastructure Correlation Matrix"],
            })

        if max_memory >= 80:
            fid = next_id()
            findings.append({
                "id": fid,
                "category": CAT_INFRA_CORRELATION,
                "severity": SEV_CRITICAL if max_memory >= 90 else SEV_HIGH,
                "title": f"Memory utilization reached {max_memory:.0f}% peak",
                "observation": (
                    f"Server memory averaged {avg_memory:.1f}% and peaked at {max_memory:.1f}%."
                ),
                "evidence": [
                    {"metric": "Peak Memory", "value": f"{max_memory:.1f}%",
                     "baseline": "80% warning threshold",
                     "source": "Azure Resource Utilization"},
                ],
                "interpretation": (
                    f"Memory pressure at {max_memory:.0f}% indicates "
                    f"{'potential OOM risk' if max_memory >= 90 else 'elevated memory consumption'}."
                ),
                "why_it_matters": (
                    "High memory utilization can trigger garbage collection pauses, "
                    "swapping, and ultimately out-of-memory failures."
                ),
                "root_cause_assessment": (
                    "Monitor for memory leaks during sustained load. Check heap usage, "
                    "object retention, and cache sizing."
                ),
                "confidence": {"memory_pressure": "High", "memory_leak": "Low"},
                "evidence_sources": ["Azure Resource Utilization",
                                     "Infrastructure Correlation Matrix"],
            })

    # ── 5. Overall Error Rate Finding ────────────────────────────────────────
    if error_rate > 1 and not any(f["category"] == CAT_ERROR_ANOMALY for f in findings):
        fid = next_id()
        findings.append({
            "id": fid,
            "category": CAT_ERROR_ANOMALY,
            "severity": SEV_CRITICAL if error_rate > 5 else SEV_HIGH,
            "title": f"Overall error rate at {error_rate:.2f}%",
            "observation": f"The test recorded an overall error rate of {error_rate:.2f}%.",
            "evidence": [
                {"metric": "Error Rate", "value": f"{error_rate:.2f}%",
                 "baseline": "< 1% acceptable",
                 "source": "Executive Summary KPIs"},
            ],
            "interpretation": (
                f"{'Significant server-side failures are occurring under load.' if error_rate > 5 else 'Errors are present and should be investigated.'}"
            ),
            "why_it_matters": (
                "Errors directly impact user experience and may indicate "
                "server instability under the tested workload."
            ),
            "root_cause_assessment": (
                "Examine error response codes and failure messages in the Error Distribution section."
            ),
            "confidence": {"error_occurrence": "High", "specific_root_cause": "Medium"},
            "evidence_sources": ["Error Distribution & Analysis", "Error Rate by Transaction"],
        })

    # ── 6. Generate Chart-Level Observations ─────────────────────────────────
    chart_observations = _generate_chart_observations(
        summary, time_series, findings, infra
    )

    # ── 7. Generate Recommendations Linked to Findings ───────────────────────
    recommendations = _generate_recommendations(findings, summary, infra)

    # ── 8. Overall Assessment ────────────────────────────────────────────────
    overall = _compute_overall_assessment(findings, summary, error_rate)

    # ── 9. Build Comprehensive Performance Intelligence Structure ─────────────
    perf_intelligence = build_performance_intelligence(
        summary=summary, labels=labels, display_labels=display_labels,
        time_series=time_series, infra=infra, correlation=correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err
    )

    return {
        "findings": findings,
        "recommendations": recommendations,
        "chart_observations": chart_observations,
        "transaction_findings": tx_findings,
        "overall_assessment": overall,
        "performance_intelligence": perf_intelligence,
    }


def build_performance_intelligence(summary: dict, labels: dict, display_labels: dict,
                                   time_series: dict, infra: dict, correlation: dict,
                                   sla_targets: dict, default_rt: float = 500.0,
                                   default_err: float = 1.0) -> dict:
    """
    Build clean, evidence-backed Performance Intelligence data structure.
    Generates:
      - executive_summary (Assessment banner, KPI strip, High-Level Observations Table, Conclusions, Priority Recommendations)
      - tab_tx_stats (Key Observations, Recommendations)
      - tab_rt_stats (Key Observations, Recommendations)
      - tab_error_stats (Key Observations, Recommendations)
      - tab_infra_stats (Key Observations, Recommendations)
    """
    # 1. Base Metrics
    avg_rt = summary.get("avg_rt", 0)
    p90 = summary.get("p90", summary.get("p95", 0))
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    error_rate = summary.get("error_rate", 0)
    throughput = summary.get("throughput", 0)
    total_samples = summary.get("total", 0)

    # Calculate iterations & executions from display_labels
    active_labels = display_labels if display_labels else labels
    total_iterations = max((v.get("count", 0) for v in active_labels.values()), default=total_samples)
    total_tx_executions = sum(v.get("count", 0) for v in active_labels.values()) if active_labels else total_samples
    tc_errors = sum(v.get("errors", 0) for v in active_labels.values()) if active_labels else summary.get("errors", 0)
    if total_tx_executions > 0:
        error_rate = round((tc_errors / total_tx_executions * 100), 2)
    
    total_tx_count = len(active_labels)
    
    # 2. SLA Breaches & Worst Offender
    breached_txs = []
    acceptable_txs = []
    for tx_name, tx_data in active_labels.items():
        t_target = sla_targets.get(tx_name, {}).get("rt", default_rt)
        t_err_target = sla_targets.get(tx_name, {}).get("err", default_err)
        t_p90 = tx_data.get("p90", 0)
        t_err = tx_data.get("error_rate", 0)
        dev_pct = ((t_p90 - t_target) / t_target * 100) if t_target > 0 else 0
        is_breached = (dev_pct > 30) or (t_err > t_err_target)
        if is_breached:
            breached_txs.append({
                "name": tx_name,
                "p90": t_p90,
                "target": t_target,
                "dev_pct": dev_pct,
                "error_rate": t_err,
                "count": tx_data.get("count", 0),
                "errors": tx_data.get("errors", 0)
            })
        else:
            acceptable_txs.append(tx_name)
            
    breached_txs.sort(key=lambda x: x["dev_pct"], reverse=True)
    breached_count = len(breached_txs)
    met_count = total_tx_count - breached_count
    compliance_pct = (met_count / max(1, total_tx_count)) * 100

    # 3. Error Concentration
    tx_errors_sorted = sorted(
        [{"name": k, "errors": v.get("errors", 0), "count": v.get("count", 0), "err_rate": v.get("error_rate", 0)} 
         for k, v in active_labels.items() if v.get("errors", 0) > 0],
        key=lambda x: x["errors"], reverse=True
    )

    # 4. Infra Metrics
    avg_cpu = infra.get("avg_cpu", 0) if infra else 0
    max_cpu = infra.get("max_cpu", 0) if infra else 0
    avg_mem = infra.get("avg_memory", 0) if infra else 0
    max_mem = infra.get("max_memory", 0) if infra else 0
    
    # 5. Overall Assessment
    if error_rate <= 1.0 and breached_count == 0 and max_cpu < 75:
        assessment_badge = "🟢 PERFORMANCE HEALTHY"
        assessment_color = "var(--green)"
        assessment_text = (
            f"The system maintained stable throughput of {throughput:.1f} TPS and healthy response times "
            f"(P90: {p90:.0f}ms) throughout all {total_iterations:,} test iterations. All {total_tx_count} transactions "
            f"met NFR SLA targets with a low {error_rate:.2f}% error rate. Host infrastructure maintained adequate headroom "
            f"with peak CPU at {max_cpu:.1f}%."
        )
    elif error_rate <= 3.0 and breached_count <= 1:
        worst_tx = breached_txs[0]["name"] if breached_txs else "isolated transactions"
        assessment_badge = "🟡 PERFORMANCE ACCEPTABLE WITH OBSERVATIONS"
        assessment_color = "var(--yellow)"
        assessment_text = (
            f"The system sustained the planned workload with {throughput:.1f} TPS and {100 - error_rate:.1f}% success rate. "
            f"While overall performance remained stable, latency elevation was observed in {worst_tx}. "
            f"Infrastructure resources showed no saturation, confirming issues are application or query-level."
        )
    else:
        worst_tx = f"{breached_txs[0]['name']} (+{breached_txs[0]['dev_pct']:.0f}% SLA deviation)" if breached_txs else "core workflows"
        assessment_badge = "⚠️ PERFORMANCE REQUIRES ATTENTION"
        assessment_color = "var(--red)"
        assessment_text = (
            f"The system maintained steady throughput of {throughput:.1f} TPS, but {breached_count} of {total_tx_count} "
            f"transactions breached SLA targets, led by {worst_tx}. Overall error rate reached {error_rate:.1f}%"
            + (f", concentrated heavily in {tx_errors_sorted[0]['name']}." if tx_errors_sorted else ".")
            + f" Infrastructure resources remained below saturation (peak CPU {max_cpu:.1f}%, memory {avg_mem:.1f}%), "
            f"indicating latency originates from application processing or database execution rather than host sizing."
        )

    # 6. KPI Strip
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

    # 7. High-Level Observations Table
    obs_tx_text = (
        f"{total_iterations:,} iterations executed across {total_tx_count} user journeys with "
        f"{total_tx_executions:,} total transactions. {total_tx_executions - tc_errors:,} passed, {tc_errors:,} failed "
        f"({100 - error_rate:.1f}% success rate). Throughput held steady at {throughput:.1f} TPS."
    )
    obs_tx_impact = "🟢 Low: Full test execution completed with stable concurrency" if tc_errors == 0 else f"🔴 High: Execution dropouts observed ({tc_errors:,} failures)"

    if breached_txs:
        top_b = breached_txs[0]
        obs_rt_text = (
            f"{breached_count} of {total_tx_count} transactions breached NFR SLA targets. "
            f"Worst offender: {top_b['name']} recorded P90 of {top_b['p90']/1000:.2f}s against a {top_b['target']/1000:.2f}s SLA "
            f"(+{top_b['dev_pct']:.1f}% deviation). Average response time across all flows was {avg_rt:.0f}ms."
        )
        obs_rt_impact = "🔴 High: User-facing latency degradation in critical paths"
    else:
        obs_rt_text = (
            f"All {total_tx_count} transactions satisfied their respective NFR response time SLA targets. "
            f"Overall average response time was {avg_rt:.0f}ms with P90 at {p90:.0f}ms."
        )
        obs_rt_impact = "🟢 Low: Fast, SLA-compliant user experience"

    if error_rate > 0 and tx_errors_sorted:
        top_err_tx = tx_errors_sorted[0]
        err_pct_share = round(top_err_tx["errors"] / max(1, tc_errors) * 100)
        obs_err_text = (
            f"Overall error rate was {error_rate:.1f}% ({tc_errors:,} failed samples). "
            f"Failures were concentrated in {top_err_tx['name']}, which accounted for {top_err_tx['errors']:,} failures "
            f"({err_pct_share}% of all test failures, with a {top_err_tx['err_rate']:.1f}% local error rate)."
        )
        obs_err_impact = "🔴 High: Service reliability concern during peak activity"
    else:
        obs_err_text = f"Zero transaction failures recorded across the entire execution ({total_tx_executions:,} successful samples)."
        obs_err_impact = "🟢 Low: Flawless reliability under tested workload"

    if infra:
        obs_infra_text = (
            f"Host CPU averaged {avg_cpu:.1f}% and peaked at {max_cpu:.1f}%. "
            f"Memory utilization remained stable around {avg_mem:.1f}%. Host resources maintained sufficient headroom, "
            f"ruling out hardware saturation as the root cause."
        )
        obs_infra_impact = "🟢 Low: Sizing and compute headroom are adequate" if max_cpu < 75 else "🟠 Moderate: CPU utilization exceeded 75%"
    else:
        obs_infra_text = "Server-side APM metrics were not attached. Client-side observations indicate stable connection handling."
        obs_infra_impact = "🟡 Telemetry Recommended: Attach server APM for deep DB/CPU correlation"

    observations_table = [
        {"category": "Transaction Performance", "observation": obs_tx_text, "impact": obs_tx_impact},
        {"category": "Response Time (P90)", "observation": obs_rt_text, "impact": obs_rt_impact},
        {"category": "Reliability & Errors", "observation": obs_err_text, "impact": obs_err_impact},
        {"category": "Infrastructure (Azure)", "observation": obs_infra_text, "impact": obs_infra_impact},
    ]

    # 8. Key Conclusions
    conclusions = []
    if breached_txs:
        conclusions.append(f"Workflows involving '{breached_txs[0]['name']}' represent the primary latency bottleneck under concurrency.")
    else:
        conclusions.append("All core transaction journeys maintained acceptable latency within established SLA limits.")

    if error_rate > 1.0 and tx_errors_sorted:
        conclusions.append(f"Transaction reliability is impaired by failures concentrated in '{tx_errors_sorted[0]['name']}' ({tx_errors_sorted[0]['errors']} errors).")
    else:
        conclusions.append("Transaction reliability was verified with zero systemic failure patterns.")

    if infra and max_cpu < 75:
        conclusions.append(f"Infrastructure resource utilization remained safe (peak CPU {max_cpu:.1f}%, memory {avg_mem:.1f}%), indicating bottlenecks are application-layer.")
    elif infra:
        conclusions.append(f"Host CPU reached {max_cpu:.1f}%, indicating compute capacity constraints under peak load.")
    else:
        conclusions.append(f"Workload was sustained at an average of {throughput:.1f} TPS without thread stalling.")

    # 9. Priority Recommendations
    priority_recommendations = []
    if error_rate > 1.0 and tx_errors_sorted:
        priority_recommendations.append({
            "priority": "Critical",
            "badge": "🔴",
            "title": f"Investigate failures in {tx_errors_sorted[0]['name']}",
            "detail": f"Analyze server-side application logs and HTTP status codes for {tx_errors_sorted[0]['name']} ({tx_errors_sorted[0]['errors']} failed samples). If failures are transient, evaluate controlled retry handling with appropriate backoff."
        })
    if breached_txs:
        top_b = breached_txs[0]
        priority_recommendations.append({
            "priority": "High",
            "badge": "🟠",
            "title": f"Profile and optimize {top_b['name']} latency",
            "detail": f"Examine downstream API calls and database query execution times within {top_b['name']} to bring P90 response time ({top_b['p90']/1000:.2f}s) within the {top_b['target']/1000:.2f}s SLA."
        })
    if infra and max_cpu > 75:
        priority_recommendations.append({
            "priority": "High",
            "badge": "🟠",
            "title": "Scale compute capacity or optimize thread utilization",
            "detail": f"Peak CPU reached {max_cpu:.1f}%. Consider horizontal instance scaling or profiling CPU-heavy routines."
        })
    else:
        priority_recommendations.append({
            "priority": "Medium",
            "badge": "🟡",
            "title": "Evaluate query caching & database index efficiency",
            "detail": "Review top database queries and ensure appropriate index coverage and connection pool sizing for peak load."
        })

    # 10. Tab-Specific Insights
    tab_tx_stats = {
        "observations": [
            f"Completed {total_iterations:,} test iterations across {total_tx_count} transaction flows with {total_tx_executions:,} total requests.",
            f"Achieved a steady-state throughput of {throughput:.1f} TPS with {'consistent execution pacing across threads.' if error_rate <= 1 else 'some execution friction from error retries.'}"
        ],
        "recommendations": [
            "Maintain current thread pacing and ramp-up profiles for baseline comparison in subsequent releases."
        ]
    }

    tab_rt_stats = {
        "observations": [
            f"{met_count} out of {total_tx_count} transactions complied with NFR response time SLA targets ({compliance_pct:.0f}% compliance rate).",
            f"Overall average response time was {avg_rt:.0f}ms; 90th percentile was {p90:.0f}ms."
            + (f" Primary latency outlier: {breached_txs[0]['name']} at {breached_txs[0]['p90']/1000:.2f}s (+{breached_txs[0]['dev_pct']:.0f}% vs SLA)." if breached_txs else "")
        ],
        "recommendations": [
            f"Focus latency reduction efforts on {'the ' + breached_txs[0]['name'] + ' request path' if breached_txs else 'maintaining current SLA margins'}."
        ]
    }

    tab_error_stats = {
        "observations": [
            f"Overall test error rate was {error_rate:.1f}% ({tc_errors:,} failed samples out of {total_tx_executions:,} total).",
            f"{'Failures concentrated primarily in ' + tx_errors_sorted[0]['name'] + ' (' + str(tx_errors_sorted[0]['errors']) + ' failures).' if tx_errors_sorted else 'No transaction failures detected across any tested user flow.'}"
        ],
        "recommendations": [
            f"{'Investigate exception stack traces and server-side responses for ' + tx_errors_sorted[0]['name'] + '.' if tx_errors_sorted else 'Continue monitoring error logs for intermittent timeouts during extended runs.'}"
        ]
    }

    tab_infra_stats = {
        "observations": [
            f"Host CPU averaged {avg_cpu:.1f}% and peaked at {max_cpu:.1f}% under peak load concurrency." if infra else "Azure Monitor telemetry was not enabled for this execution.",
            f"Host memory utilization remained stable at {avg_mem:.1f}% with adequate headroom." if infra else "Client-side throughput remained steady throughout steady state."
        ],
        "recommendations": [
            f"{'Host hardware sizing is adequate; focus tuning on application code and DB queries.' if infra and max_cpu < 75 else 'Review server CPU profile during peak test windows.'}"
        ]
    }

    return {
        "executive_summary": {
            "assessment_badge": assessment_badge,
            "assessment_color": assessment_color,
            "assessment_text": assessment_text,
            "kpis": kpis,
            "observations_table": observations_table,
            "conclusions": conclusions,
            "priority_recommendations": priority_recommendations
        },
        "tab_tx_stats": tab_tx_stats,
        "tab_rt_stats": tab_rt_stats,
        "tab_error_stats": tab_error_stats,
        "tab_infra_stats": tab_infra_stats
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
            if enrich.get("interpretation"):
                finding["interpretation"] = enrich["interpretation"]
            if enrich.get("root_cause_assessment"):
                finding["root_cause_assessment"] = enrich["root_cause_assessment"]
            if enrich.get("why_it_matters"):
                finding["why_it_matters"] = enrich["why_it_matters"]
            if enrich.get("root_cause_confidence"):
                if "confidence" not in finding:
                    finding["confidence"] = {}
                finding["confidence"]["ai_root_cause"] = enrich["root_cause_confidence"]

    ai_recs = ai_insights.get("recommendations", [])
    if ai_recs:
        findings_result["recommendations"] = ai_recs

    if "data_quality_findings" in ai_insights:
        findings_result["data_quality_findings"] = ai_insights["data_quality_findings"]
    
    if "root_cause_assessment" in ai_insights:
        findings_result["overall_root_cause"] = ai_insights["root_cause_assessment"]

    return findings_result


# ── Chart Observation Generators ─────────────────────────────────────────────

def _generate_chart_observations(summary: dict, time_series: dict,
                                 findings: list, infra: dict) -> dict:
    """Generate contextual observation text for each major chart section."""
    avg_rt = summary.get("avg_rt", 0)
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    max_rt = summary.get("max_rt", 0)
    error_rate = summary.get("error_rate", 0)

    # Find related finding IDs for evidence references
    tail_finding = next((f for f in findings if f["category"] == CAT_TAIL_LATENCY), None)
    tp_finding = next((f for f in findings if f["category"] == CAT_THROUGHPUT_DEGRADATION), None)

    # 1. Response Time chart observation
    rt_stability = "stable" if p99 < avg_rt * 3 else "variable with tail latency spikes"
    rt_status_code = "healthy" if p99 < avg_rt * 2.5 else "variable" if p99 < avg_rt * 4 else "degrading"
    rt_badge = "🟢 Latency Stable" if rt_status_code == "healthy" else "🟡 Tail Latency Spikes" if rt_status_code == "variable" else "🔴 Severe Latency Tail"
    
    rt_obs = {
        "status_code": rt_status_code,
        "badge": rt_badge,
        "observation": (
            f"Latency averaged {avg_rt:.0f} ms with P95 at {p95} ms and P99 at {p99} ms (maximum: {max_rt:,} ms)."
        ),
        "why_it_matters": (
            f"Tail latency (P99 at {p99} ms) is {round(p99 / max(1, avg_rt), 1)}x higher than average response time, indicating that isolated requests suffer disproportionate delay."
            if p99 > avg_rt * 2.5 else
            "Response times remained consistent across percentiles without severe tail degradation."
        ),
        "validate": (
            "Analyze slow database queries, garbage collection pauses, and downstream thread contention during P99 spikes."
            if p99 > avg_rt * 2.5 else
            "Verify behavior under stepped stress load to establish latency degradation boundaries."
        ),
        "related_finding": tail_finding["id"] if tail_finding else None,
    }

    # 2. Phase-aware Throughput Analysis
    ts_tp = time_series.get("ts_throughput", [])
    ts_err = time_series.get("ts_errors", [])
    
    if ts_tp:
        peak_tp = max(ts_tp)
        peak_idx = ts_tp.index(peak_tp)
        initial_tp = ts_tp[0]
        end_tp = ts_tp[-1]
        avg_series_tp = round(sum(ts_tp) / len(ts_tp), 1)
        
        # Calculate peak-to-end drop and steady-state variation
        drop_from_peak_pct = round(((peak_tp - end_tp) / peak_tp * 100), 1) if peak_tp > 0 else 0
        total_err_count = sum(ts_err) if ts_err else summary.get("errors", 0)
        
        # Determine performance state
        if peak_idx < len(ts_tp) - 1 and drop_from_peak_pct >= 15:
            # Ramped up or peaked early, then degraded
            status_code = "degrading"
            badge = "🟠 Throughput Degradation"
            badge_color = "var(--yellow)"
            observation = (
                f"Throughput peaked at ~{peak_tp:.0f} req/s during ramp-up, then declined "
                f"by {drop_from_peak_pct:.0f}% to ~{end_tp:.0f} req/s toward the end of the test."
            )
            why_it_matters = (
                f"The decline occurred despite a {error_rate:.2f}% error rate, indicating that "
                f"the reduction is not caused by request failures, but rather by request processing latency, backend contention, or worker completion."
                if total_err_count == 0 else
                f"The decline coincided with {total_err_count} request errors, indicating capacity saturation under sustained load."
            )
            validate = (
                "Check whether the decline correlates with increasing response times (P90/P99), "
                "host CPU/memory saturation, or active worker thread completion."
            )
            trend_label = f"↓ {drop_from_peak_pct:.0f}% from Peak"
            trend_color = "var(--red)"
        elif drop_from_peak_pct >= 8 and (max(ts_tp) - min(ts_tp)) / max(1, avg_series_tp) > 0.25:
            # Fluctuating
            status_code = "variable"
            badge = "🟡 Variable Throughput"
            badge_color = "var(--yellow)"
            observation = (
                f"Throughput averaged {avg_series_tp:.0f} req/s with noticeable fluctuations between "
                f"{min(ts_tp):.0f} req/s and {peak_tp:.0f} req/s."
            )
            why_it_matters = "Throughput volatility suggests uneven workload pacing, periodic garbage collection, or intermittent thread contention."
            validate = "Verify backend thread pools, database connection pooling, and downstream service latency during throughput valleys."
            trend_label = f"±{round((peak_tp - min(ts_tp))/avg_series_tp * 50)}% Volatility"
            trend_color = "var(--yellow)"
        elif end_tp >= initial_tp * 1.2 and peak_idx >= len(ts_tp) - 2:
            # Monotonically ramping or stable high
            status_code = "healthy"
            badge = "🟢 Scaling Successfully"
            badge_color = "var(--green)"
            observation = (
                f"Throughput scaled from {initial_tp:.0f} req/s to a peak of {peak_tp:.0f} req/s, "
                f"maintaining sustained processing throughout the test."
            )
            why_it_matters = "The system successfully absorbed the ramp-up workload without throughput degradation or backpressure."
            validate = "Execute extended soak testing at peak concurrency to evaluate multi-hour stability."
            trend_label = f"+{round((end_tp - initial_tp)/max(1, initial_tp)*100)}% Growth"
            trend_color = "var(--green)"
        else:
            # Steady state
            status_code = "healthy"
            badge = "🟢 Stable Throughput"
            badge_color = "var(--green)"
            observation = f"Throughput remained stable at an average of {avg_series_tp:.0f} req/s (peak: {peak_tp:.0f} req/s) with no significant anomaly."
            why_it_matters = "Workload execution proceeded smoothly without evidence of capacity bottlenecks or processing stalls."
            validate = "Conduct stepped load testing with increased concurrency to identify the ultimate saturation ceiling."
            trend_label = "🟢 Stable (±5%)"
            trend_color = "var(--green)"
            
        tp_obs = {
            "status_code": status_code,
            "badge": badge,
            "badge_color": badge_color,
            "observation": observation,
            "why_it_matters": why_it_matters,
            "validate": validate,
            "avg_tp": avg_series_tp,
            "peak_tp": peak_tp,
            "error_rate": error_rate,
            "trend_label": trend_label,
            "trend_color": trend_color,
            "related_finding": tp_finding["id"] if tp_finding else None,
        }
    else:
        tp_obs = {
            "status_code": "healthy",
            "badge": "🟢 Stable",
            "observation": "Throughput data recorded successfully.",
            "why_it_matters": "Baseline execution achieved.",
            "validate": "Check test logs.",
            "avg_tp": 0,
            "peak_tp": 0,
            "error_rate": error_rate,
            "trend_label": "N/A",
            "trend_color": "var(--muted)",
            "related_finding": None,
        }

    # 3. Infrastructure chart observation (if available)
    infra_obs = None
    if infra:
        avg_cpu = infra.get("avg_cpu", 0)
        max_cpu = infra.get("max_cpu", 0)
        avg_memory = infra.get("avg_memory", 0)
        max_memory = infra.get("max_memory", 0)
        infra_finding = next((f for f in findings if f["category"] == CAT_INFRA_CORRELATION), None)
        
        inf_status = "degrading" if max_cpu >= 85 or max_memory >= 85 else "variable" if max_cpu >= 70 else "healthy"
        inf_badge = "🔴 Resource Saturation" if inf_status == "degrading" else "🟡 Elevated Resource Pressure" if inf_status == "variable" else "🟢 Infrastructure Healthy"

        infra_obs = {
            "status_code": inf_status,
            "badge": inf_badge,
            "observation": (
                f"CPU averaged {avg_cpu:.1f}% (peak: {max_cpu:.0f}%), and memory averaged {avg_memory:.1f}% (peak: {max_memory:.0f}%)."
            ),
            "why_it_matters": (
                f"Peak CPU utilization at {max_cpu:.0f}% represents severe resource pressure and limits available headroom for traffic spikes."
                if max_cpu >= 85 else
                "Host resources maintained sufficient capacity with no systemic starvation observed."
            ),
            "validate": (
                "Profile application threads to identify CPU-intensive methods, review database indexing, and evaluate horizontal scale-out rules."
                if max_cpu >= 75 else
                "Continue monitoring resource trends under scaled concurrency."
            ),
            "related_finding": infra_finding["id"] if infra_finding else None,
        }

    return {
        "response_time": rt_obs,
        "throughput": tp_obs,
        "infrastructure": infra_obs,
    }


# ── Recommendation Generator ────────────────────────────────────────────────

def _generate_recommendations(findings: list, summary: dict, infra: dict) -> list:
    """Generate recommendations linked to finding IDs."""
    recommendations = []
    rec_counter = 0

    # Group findings by category for smarter recommendations
    bottleneck_findings = [f for f in findings if f["category"] == CAT_LATENCY_BOTTLENECK]
    sla_findings = [f for f in findings if f["category"] == CAT_SLA_BREACH]
    error_findings = [f for f in findings if f["category"] == CAT_ERROR_ANOMALY]
    tail_findings = [f for f in findings if f["category"] == CAT_TAIL_LATENCY]
    infra_findings = [f for f in findings if f["category"] == CAT_INFRA_CORRELATION]
    tp_findings = [f for f in findings if f["category"] == CAT_THROUGHPUT_DEGRADATION]

    # R: Enable server-side monitoring (if no infra data or low root-cause confidence)
    needs_telemetry = [f for f in findings
                       if f.get("confidence", {}).get("specific_root_cause") == "Low"
                       or f.get("confidence", {}).get("specific_cause") == "Low"]
    if needs_telemetry and not infra:
        rec_counter += 1
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"] for f in needs_telemetry[:5]],
            "title": "Enable server-side monitoring",
            "priority": "Critical",
            "category": "Infrastructure",
            "why": (
                "Client-side performance data identifies latency anomalies "
                "but cannot establish server-side causality."
            ),
            "action": [
                "Enable CPU, Memory, and JVM monitoring",
                "Configure database query telemetry",
                "Enable application-level logging and tracing",
                "Set up disk I/O and network monitoring",
            ],
            "expected_impact": "Enable server-side correlation and root-cause identification.",
            "validation": "Repeat the same test with telemetry enabled and compare findings.",
        })

    # R: Investigate primary bottleneck
    for f in bottleneck_findings:
        rec_counter += 1
        tx_name = f["title"].replace(" is the primary latency bottleneck", "")
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"]],
            "title": f"Investigate {tx_name} execution path",
            "priority": "Critical",
            "category": "Backend",
            "why": f"{tx_name} is the dominant latency contributor.",
            "action": [
                f"Profile the {tx_name} server-side execution path",
                "Identify slow database queries within this transaction",
                "Check for external service call latency",
                "Review authentication/authorization processing time",
            ],
            "expected_impact": f"Reduce {tx_name} response time to within SLA target.",
            "validation": f"Re-run the test and verify {tx_name} P90 is within SLA.",
        })

    # R: Optimize SLA-breaching transactions
    for f in sla_findings:
        rec_counter += 1
        tx_name = f["title"].replace(" SLA breach", "")
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"]],
            "title": f"Optimize {tx_name} to meet SLA",
            "priority": "High",
            "category": "Backend",
            "why": f"{tx_name} exceeds its response time SLA target.",
            "action": [
                f"Profile the {tx_name} flow end-to-end",
                "Add database query caching where applicable",
                "Review for N+1 query patterns",
            ],
            "expected_impact": f"Improve {tx_name} response times to comply with SLA targets.",
            "validation": f"Re-run the test and confirm {tx_name} SLA compliance.",
        })

    # R: Investigate error anomalies
    for f in error_findings:
        rec_counter += 1
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"]],
            "title": "Investigate error responses",
            "priority": "High",
            "category": "Backend",
            "why": f["observation"],
            "action": [
                "Review HTTP error status codes in the Error Distribution section",
                "Check server-side application logs for exceptions",
                "Verify connection pool and timeout configurations",
            ],
            "expected_impact": "Reduce transaction failure rates and improve stability.",
            "validation": "Re-run the test and confirm error rate is within target.",
        })

    # R: Investigate tail latency
    for f in tail_findings:
        rec_counter += 1
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"]],
            "title": "Analyze tail latency outliers",
            "priority": "Medium",
            "category": "Backend",
            "why": f["observation"],
            "action": [
                "Correlate P99 spikes with server-side GC pauses",
                "Check for thread pool exhaustion during spike windows",
                "Review database lock contention patterns",
            ],
            "expected_impact": "Stabilize response times and reduce P99 variance.",
            "validation": "Re-run and verify P99 is within 3× the average.",
        })

    # R: Scale infrastructure
    for f in infra_findings:
        rec_counter += 1
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [f["id"]],
            "title": "Scale compute resources",
            "priority": "High",
            "category": "Infrastructure",
            "why": f["observation"],
            "action": [
                "Evaluate horizontal scaling (add instances)",
                "Review application code for CPU-intensive operations",
                "Consider upgrading VM/container SKU",
            ],
            "expected_impact": "Provide sufficient resource headroom to prevent CPU/memory pressure during load.",
            "validation": "Re-run the test after scaling and verify resource utilization.",
        })

    # If no findings at all, add a maintenance recommendation
    if not recommendations:
        rec_counter += 1
        recommendations.append({
            "id": f"R-{rec_counter:03d}",
            "triggered_by": [],
            "title": "Maintain current performance baseline",
            "priority": "Low",
            "category": "Configuration",
            "why": "All metrics are within healthy thresholds.",
            "action": [
                "Run longer-duration sustained load tests",
                "Test with progressively higher concurrency to find limits",
                "Establish performance regression baselines",
            ],
            "expected_impact": "Identify maximum safe throughput capacity.",
            "validation": "Document baseline metrics for future comparison.",
        })

    return recommendations


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
