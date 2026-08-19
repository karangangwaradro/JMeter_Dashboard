#!/usr/bin/env python3
"""
findings_engine.py — Structured Performance Findings Generator for JmeterAI.

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

    return {
        "findings": findings,
        "recommendations": recommendations,
        "chart_observations": chart_observations,
        "transaction_findings": tx_findings,
        "overall_assessment": overall,
    }


def enrich_findings_with_ai(findings_result: dict, ai_insights: dict) -> dict:
    """
    Merge AI-generated enrichments into the deterministic findings.

    If ai_insights contains a 'finding_enrichments' dict, overlay the AI's
    deeper interpretations onto the corresponding Finding objects.
    """
    if not ai_insights:
        return findings_result

    enrichments = ai_insights.get("finding_enrichments", {})
    for finding in findings_result.get("findings", []):
        fid = finding["id"]
        if fid in enrichments:
            enrich = enrichments[fid]
            # AI enrichments overlay — don't replace, enhance
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

    # Replace deterministic recommendations with AI-generated unified recommendations if present
    ai_recs = ai_insights.get("recommendations", [])
    if ai_recs:
        findings_result["recommendations"] = ai_recs

    # Also capture data quality findings at the root level if present
    if "data_quality_findings" in ai_insights:
        findings_result["data_quality_findings"] = ai_insights["data_quality_findings"]
    
    # And capture the root_cause_assessment object if present
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
    throughput = summary.get("throughput", 0)
    error_rate = summary.get("error_rate", 0)

    # Find related finding IDs for evidence references
    tail_finding = next((f for f in findings if f["category"] == CAT_TAIL_LATENCY), None)
    tp_finding = next((f for f in findings if f["category"] == CAT_THROUGHPUT_DEGRADATION), None)

    # Response Time chart observation
    rt_stability = "stable" if p99 < avg_rt * 3 else "variable with periodic spikes"
    rt_obs = {
        "title": (
            f"Latency remains broadly {rt_stability} during sustained execution"
            + (", but periodic P99 spikes indicate intermittent high-latency requests."
               if p99 > avg_rt * 2.5 else ".")
        ),
        "evidence": [
            f"Avg RT: {avg_rt:.0f} ms",
            f"P95: {p95} ms",
            f"P99: {p99} ms",
            f"Maximum observed: {max_rt:,} ms",
        ],
        "interpretation": (
            f"The average latency is {'relatively stable' if p99 < avg_rt * 3 else 'showing significant variance'}. "
            + ("Tail latency requires investigation because a small subset of requests "
               "experiences substantially higher response times."
               if p99 > avg_rt * 2.5
               else "Response time distribution is within acceptable bounds.")
        ),
        "related_finding": tail_finding["id"] if tail_finding else None,
    }

    # Throughput chart observation
    ts_tp = time_series.get("ts_throughput", [])
    tp_trend = "stable"
    if ts_tp and len(ts_tp) > 4:
        first_q = ts_tp[:len(ts_tp) // 4]
        last_q = ts_tp[-len(ts_tp) // 4:]
        if first_q and last_q:
            avg_fq = sum(first_q) / len(first_q)
            avg_lq = sum(last_q) / len(last_q)
            if avg_fq > 0 and avg_lq < avg_fq * 0.8:
                tp_trend = "declining"
            elif avg_fq > 0 and avg_lq > avg_fq * 1.1:
                tp_trend = "increasing"

    if tp_trend == "stable":
        tp_assessment = "Capacity saturation was not demonstrated by this execution."
        tp_next = "Repeat with progressively higher concurrency to determine whether throughput continues scaling or reaches a saturation point."
    elif tp_trend == "declining":
        tp_assessment = "Throughput degradation suggests the system is approaching or has reached its capacity limit."
        tp_next = "Investigate server resource utilization and connection pool settings."
    else:
        tp_assessment = "Throughput increased over the test, indicating the system is handling ramp-up successfully."
        tp_next = "Validate sustained throughput at peak concurrency for a longer duration."

    tp_obs = {
        "observation": (
            f"Throughput {'remains relatively stable throughout the sustained test period and does not show an obvious collapse' if tp_trend == 'stable' else 'shows ' + tp_trend + ' behavior'} as execution progresses."
        ),
        "interpretation": (
            f"{'No direct evidence of throughput degradation is observed under this workload.' if tp_trend == 'stable' else 'Throughput ' + tp_trend + ' detected.'}"
        ),
        "assessment": tp_assessment,
        "next_validation": tp_next,
        "evidence": [
            f"Avg Throughput: {throughput:.1f} req/s",
            f"Error Rate: {error_rate:.2f}%",
        ],
        "related_finding": tp_finding["id"] if tp_finding else None,
    }

    # Infrastructure chart observation (if available)
    infra_obs = None
    if infra:
        avg_cpu = infra.get("avg_cpu", 0)
        max_cpu = infra.get("max_cpu", 0)
        avg_memory = infra.get("avg_memory", 0)
        max_memory = infra.get("max_memory", 0)
        infra_finding = next((f for f in findings if f["category"] == CAT_INFRA_CORRELATION), None)

        infra_obs = {
            "observation": (
                f"CPU averaged {avg_cpu:.1f}% and peaked at {max_cpu:.0f}%. "
                f"Memory averaged {avg_memory:.1f}% and peaked at {max_memory:.0f}%."
            ),
            "interpretation": (
                f"The server experienced {'significant resource pressure' if max_cpu >= 80 or max_memory >= 80 else 'normal resource utilization'} "
                f"during this test execution."
            ),
            "assessment": (
                f"{'Resource contention was observed — scaling or optimization is recommended.' if max_cpu >= 80 else 'Server resources remained within healthy operating limits.'}"
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
