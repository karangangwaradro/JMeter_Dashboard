#!/usr/bin/env python3
"""
correlation_engine.py — Client ↔ Server Metric Correlation for PerfPilot.

Correlates JMeter client-side metrics (response times, throughput, errors)
with Azure Monitor server-side metrics (CPU, memory, network) to identify
performance bottlenecks and patterns.
"""

import json


def correlate_metrics(parsed: dict, azure_data: dict) -> dict:
    """
    Correlate client-side JMeter metrics with server-side Azure Monitor data.

    Returns a dict with correlation findings, patterns, and bottleneck markers.
    """
    if not azure_data or not azure_data.get("infra_summary"):
        return _client_only_analysis(parsed)

    summary = parsed.get("summary", {})
    infra = azure_data.get("infra_summary", {})
    ts = parsed.get("time_series", {})
    azure_ts = azure_data.get("time_series", {})
    labels = parsed.get("labels", {})

    findings = []
    bottleneck_type = "none"
    severity = "healthy"

    # ── CPU Correlation ──
    avg_cpu = infra.get("avg_cpu", 0)
    max_cpu = infra.get("max_cpu", 0)
    avg_rt = summary.get("avg_rt", 0)

    if max_cpu > 90:
        findings.append({
            "type": "cpu_saturation",
            "severity": "critical",
            "message": f"CPU peaked at {max_cpu:.1f}% — server is CPU-saturated. Response times will degrade under further load.",
            "metric": "cpu", "value": max_cpu, "threshold": 90
        })
        bottleneck_type = "cpu"
        severity = "critical"
    elif avg_cpu > 70:
        findings.append({
            "type": "cpu_elevated",
            "severity": "warning",
            "message": f"Average CPU at {avg_cpu:.1f}% — approaching saturation point. Consider scaling before increasing load.",
            "metric": "cpu", "value": avg_cpu, "threshold": 70
        })
        if severity != "critical":
            severity = "warning"

    # ── Memory Correlation ──
    avg_memory = infra.get("avg_memory", 0)
    max_memory = infra.get("max_memory", 0)

    if max_memory > 90:
        findings.append({
            "type": "memory_pressure",
            "severity": "critical",
            "message": f"Memory utilization peaked at {max_memory:.1f}% — potential OOM risk. Heap/memory leaks may be present.",
            "metric": "memory", "value": max_memory, "threshold": 90
        })
        if bottleneck_type == "none":
            bottleneck_type = "memory"
        severity = "critical"
    elif avg_memory > 75:
        findings.append({
            "type": "memory_elevated",
            "severity": "warning",
            "message": f"Average memory at {avg_memory:.1f}% — monitor for memory leaks during sustained load.",
            "metric": "memory", "value": avg_memory, "threshold": 75
        })

    # ── Network Correlation ──
    avg_net_in = infra.get("avg_network_in_mbps", 0)
    if avg_net_in > 100:  # 100 MB/min is high
        findings.append({
            "type": "network_high",
            "severity": "info",
            "message": f"Network ingress averaging {avg_net_in:.1f} MB — check for large payload responses.",
            "metric": "network", "value": avg_net_in
        })

    # ── Response Time vs CPU Correlation ──
    ts_cpu = azure_ts.get("cpu", [])
    ts_avg_rt = ts.get("ts_avg_rt", [])

    if ts_cpu and ts_avg_rt:
        # Check if high CPU periods correlate with high response times
        min_len = min(len(ts_cpu), len(ts_avg_rt))
        high_cpu_high_rt = 0
        for i in range(min_len):
            if ts_cpu[i] > 70 and ts_avg_rt[i] > avg_rt * 1.5:
                high_cpu_high_rt += 1

        if high_cpu_high_rt > min_len * 0.3:  # More than 30% of time
            findings.append({
                "type": "cpu_rt_correlation",
                "severity": "warning",
                "message": f"Strong correlation detected: {high_cpu_high_rt}/{min_len} intervals show both high CPU (>70%) and elevated response times (>1.5x average). Server compute is the bottleneck.",
                "correlation_strength": round(high_cpu_high_rt / max(1, min_len) * 100, 1)
            })

    # ── Error Rate Analysis ──
    error_rate = summary.get("error_rate", 0)
    if error_rate > 5:
        findings.append({
            "type": "high_error_rate",
            "severity": "critical",
            "message": f"Error rate at {error_rate:.2f}% — exceeds acceptable threshold. Check server logs for connection timeouts or application exceptions.",
            "metric": "error_rate", "value": error_rate, "threshold": 5
        })
        severity = "critical"
    elif error_rate > 1:
        findings.append({
            "type": "elevated_errors",
            "severity": "warning",
            "message": f"Error rate at {error_rate:.2f}% — minor but present. Monitor for patterns during peak load windows.",
            "metric": "error_rate", "value": error_rate, "threshold": 1
        })

    # ── Throughput Analysis ──
    throughput = summary.get("throughput", 0)
    ts_throughput = ts.get("ts_throughput", [])
    if ts_throughput and len(ts_throughput) > 2:
        # Check for throughput degradation over time
        first_third = ts_throughput[:len(ts_throughput)//3]
        last_third = ts_throughput[-len(ts_throughput)//3:]
        if first_third and last_third:
            avg_first = sum(first_third) / len(first_third)
            avg_last = sum(last_third) / len(last_third)
            if avg_first > 0 and avg_last < avg_first * 0.7:
                findings.append({
                    "type": "throughput_degradation",
                    "severity": "warning",
                    "message": f"Throughput degraded by {round((1 - avg_last/avg_first) * 100)}% over the test duration. Possible resource exhaustion or connection pool depletion.",
                    "first_third_avg": round(avg_first, 2),
                    "last_third_avg": round(avg_last, 2)
                })

    # ── Per-Transaction Hotspots ──
    slow_transactions = []
    for lname, ldata in labels.items():
        if ldata.get("avg_rt", 0) > avg_rt * 2 and ldata.get("count", 0) > 5:
            slow_transactions.append({
                "label": lname,
                "avg_rt": ldata["avg_rt"],
                "p95": ldata.get("p95", 0),
                "error_rate": ldata.get("error_rate", 0),
                "ratio_to_avg": round(ldata["avg_rt"] / max(1, avg_rt), 2)
            })

    if slow_transactions:
        slow_transactions.sort(key=lambda x: x["avg_rt"], reverse=True)
        top = slow_transactions[0]
        findings.append({
            "type": "slow_transaction",
            "severity": "warning",
            "message": f"Transaction '{top['label']}' is {top['ratio_to_avg']}x slower than average ({top['avg_rt']:.0f}ms vs {avg_rt:.0f}ms). Priority optimization target.",
            "transactions": slow_transactions[:5]
        })

    # ── App Service HTTP codes ──
    app_service = azure_data.get("app_service", {})
    if app_service.get("http_5xx", 0) > 0:
        findings.append({
            "type": "server_5xx",
            "severity": "critical",
            "message": f"Azure App Service returned {app_service['http_5xx']} 5xx errors during the test window. Server-side failures detected.",
            "metric": "http_5xx", "value": app_service["http_5xx"]
        })

    return {
        "findings": findings,
        "bottleneck_type": bottleneck_type,
        "severity": severity,
        "slow_transactions": slow_transactions[:5],
        "summary": {
            "total_findings": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "warnings": sum(1 for f in findings if f.get("severity") == "warning"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        }
    }


def _client_only_analysis(parsed: dict) -> dict:
    """Provide basic analysis when Azure data is not available."""
    summary = parsed.get("summary", {})
    labels = parsed.get("labels", {})
    findings = []

    error_rate = summary.get("error_rate", 0)
    avg_rt = summary.get("avg_rt", 0)
    p95 = summary.get("p95", 0)

    if error_rate > 5:
        findings.append({
            "type": "high_error_rate", "severity": "critical",
            "message": f"Error rate at {error_rate:.2f}% — investigate server-side logs for root cause."
        })
    elif error_rate > 1:
        findings.append({
            "type": "elevated_errors", "severity": "warning",
            "message": f"Error rate at {error_rate:.2f}% — minor but should be investigated."
        })

    if p95 > avg_rt * 3 and p95 > 1000:
        findings.append({
            "type": "tail_latency", "severity": "warning",
            "message": f"P95 ({p95}ms) is {round(p95/max(1,avg_rt), 1)}x the average ({avg_rt:.0f}ms). Significant tail latency detected."
        })

    # Find slowest transaction
    if labels:
        sorted_labels = sorted(labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)
        if sorted_labels and sorted_labels[0][1].get("avg_rt", 0) > avg_rt * 2:
            lname, ldata = sorted_labels[0]
            findings.append({
                "type": "slow_transaction", "severity": "warning",
                "message": f"'{lname}' is the slowest transaction at {ldata['avg_rt']:.0f}ms (vs {avg_rt:.0f}ms average)."
            })

    return {
        "findings": findings,
        "bottleneck_type": "unknown",
        "severity": "critical" if any(f["severity"] == "critical" for f in findings) else "warning" if findings else "healthy",
        "slow_transactions": [],
        "summary": {
            "total_findings": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "warnings": sum(1 for f in findings if f.get("severity") == "warning"),
            "info": 0,
        },
        "note": "Azure Monitor not configured — server-side correlation unavailable"
    }
