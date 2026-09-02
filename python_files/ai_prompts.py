#!/usr/bin/env python3
"""
ai_prompts.py — Standardized Prompt Engineering & Templates for PerfPilot AI Engine.

Centralizes prompt definitions, JSON schema specifications, and dynamic context assembly
to keep core AI service logic concise and modular.
"""

import json
from typing import Dict, Any, List, Optional


def build_insights_prompt(test_name: str, summary: dict, labels: dict,
                          time_series: dict, infra: dict, correlation: dict,
                          sla_targets: dict = None, default_rt: float = 500.0,
                          default_err: float = 1.0) -> str:
    """Construct the standardized, high-discipline AI performance prompt matching executive format with SLA awareness."""
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

    # Calculate SLA compliance facts
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
        f"  Overall SLA Compliance: {sla_compliance_pct:.1f}% ({len(met_txs)} of {total_tx} transactions met SLA targets)",
        f"  Global Default Response Time SLA Target: {default_rt:.0f} ms | Default Error Rate Target: {default_err:.2f}%",
        f"  Total SLA-Breaching Transactions: {len(breached_txs)}"
    ]
    if breached_txs:
        sla_overview_lines.append("  Key SLA Violations (Actual vs Defined Target):")
        sorted_breaches = sorted(breached_txs, key=lambda x: max(x["rt_dev_pct"], x["err"] * 10), reverse=True)
        for b in sorted_breaches[:12]:
            parts = []
            if b["rt_breach"]:
                parts.append(f"P90={b['p90']:.0f}ms vs SLA Target={b['target_rt']:.0f}ms ({b['rt_dev_pct']:+.1f}% deviation)")
            if b["err_breach"]:
                parts.append(f"Error Rate={b['err']:.2f}% vs SLA Target={b['target_err']:.2f}%")
            sla_overview_lines.append(f"    - {b['name']}: {', '.join(parts)}")
    else:
        sla_overview_lines.append("  All transactions met their defined SLA thresholds.")
    sla_text = "\n".join(sla_overview_lines)

    top_labels = sorted(labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:15]
    labels_text = "\n".join([
        f"  - {name}: {data.get('count',0)} samples, avg={data.get('avg_rt',0):.1f}ms, "
        f"p90={data.get('p90',0)}ms (SLA target: {sla_targets.get(name,{}).get('rt', default_rt):.0f}ms | {'🔴 BREACHED' if data.get('p90',0) > sla_targets.get(name,{}).get('rt', default_rt) else '🟢 MET'}), "
        f"p95={data.get('p95',0)}ms, min={data.get('min_rt',0)}ms, max={data.get('max_rt',0)}ms, "
        f"errors={data.get('errors', 0)} ({data.get('error_rate',0):.2f}%, SLA max: {sla_targets.get(name,{}).get('err', default_err):.2f}%)"
        for name, data in top_labels
    ]) or "  - No transaction data recorded"

    infra_text = "Not available (Azure Monitor not configured)"
    if infra:
        infra_text = (
            f"  CPU: avg={infra.get('avg_cpu',0):.1f}%, max_peak={infra.get('max_cpu',0):.1f}%\n"
            f"  Memory: avg={infra.get('avg_memory',0):.1f}%, max_peak={infra.get('max_memory',0):.1f}%\n"
            f"  Network In: {infra.get('avg_network_in_mbps',0):.1f} MB/min\n"
            f"  Network Out: {infra.get('avg_network_out_mbps',0):.1f} MB/min\n"
            f"  Disk Read IOPS: {infra.get('avg_disk_read_iops',0):.0f}\n"
            f"  Disk Write IOPS: {infra.get('avg_disk_write_iops',0):.0f}"
        )

    corr_findings = ""
    if correlation and correlation.get("findings"):
        corr_findings = "\n".join([
            f"  - [{f.get('severity','info').upper()}] {f.get('message','')}"
            for f in correlation.get("findings", [])
        ])
    else:
        corr_findings = "  No correlation data available"

    try:
        from python_files.findings_engine import generate_findings
        findings_result = generate_findings(
            summary=summary, labels=labels, display_labels=dict(top_labels),
            time_series={}, infra=infra if infra else {},
            correlation={}, sla_targets=sla_targets, default_rt=default_rt, default_err=default_err,
            auto_ai=False
        )
        findings_text = "\n".join([
            f"  - [{f['severity'].upper()}] {f['title']}"
            for f in findings_result.get("findings", [])
        ])
        findings_ids = [f["id"] for f in findings_result.get("findings", [])]
    except Exception:
        findings_text = "  (Findings engine not available — generate your own analysis)"
        findings_ids = []

    return f"""You are a Senior Performance Engineer and Performance Analysis Engine.

Your responsibility is to analyze the performance test results and produce clean, professional engineering observations in the exact requested format.

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

TEST: {test_name}
═══════════════════════════════════════════

WORKLOAD PROFILE:
  Total Samples: {summary.get('total', 0):,}
  Duration: {summary.get('duration_sec', 0):.0f} seconds
  Throughput: {summary.get('throughput', 0):.2f} req/s

DEFINED SLA TARGETS & COMPLIANCE STATUS:
{sla_text}

CLIENT-SIDE RESPONSE TIME & ERROR METRICS:
  Average Response Time: {summary.get('avg_rt', 0):.2f} ms
  Min: {summary.get('min_rt', 0)} ms | Max: {summary.get('max_rt', 0)} ms
  P50: {summary.get('p50', 0)} ms | P90: {summary.get('p90', 0)} ms
  P95: {summary.get('p95', 0)} ms | P99: {summary.get('p99', 0)} ms
  Error Rate: {summary.get('error_rate', 0):.2f}%

PER-TRANSACTION BREAKDOWN (top by response time / count vs Defined SLA):
{labels_text}

SERVER-SIDE INFRASTRUCTURE (Azure Monitor):
{infra_text}

CORRELATION ANALYSIS FINDINGS:
{corr_findings}

EXISTING STRUCTURED FINDINGS (enrich these):
{findings_text}

═══════════════════════════════════════════

Respond ONLY with a valid JSON object (no markdown, no code fences) with exactly these keys:
{{
  "executive_summary": "2-3 sentence concise executive assessment citing key test facts",
  "data_quality_findings": [
    {{
      "severity": "<Critical/Warning/Info>",
      "issue": "Description of data gap, missing dimension, or observation limit",
      "evidence": "What telemetry is absent or conflicting",
      "impact": "How this affects confidence",
      "action": "Recommended next step"
    }}
  ],
  "finding_enrichments": {{
    {', '.join(['"' + fid + '": {"finding": "...", "observation": "...", "interpretation": "...", "evidence": [{"metric": "...", "value": "...", "source": "client/server/derived"}], "likely_cause": "...", "confidence": "Low/Medium/High/Confirmed", "impact": "...", "recommendation": "...", "validation": "..."}' for fid in findings_ids[:6]]) if findings_ids else '"F-001": {"finding": "...", "observation": "...", "interpretation": "...", "evidence": [{"metric": "...", "value": "...", "source": "client"}], "likely_cause": "...", "confidence": "Medium", "impact": "...", "recommendation": "...", "validation": "..."}'}
  }},
  "capacity_planning": {{
    "observed_concurrency": null,
    "estimated_max_users": null,
    "saturation_point": null,
    "safe_concurrency": null,
    "capacity_confidence": "Unknown",
    "analysis": "Explanation of capacity status or why it cannot be reliably estimated from aggregate data"
  }},
  "root_cause_assessment": [
    {{
      "finding": "Primary bottleneck or observed degradation",
      "evidence": "Citing specific measured values and sources",
      "likely_cause": "Direct technical cause without overclaiming",
      "confidence": "Low/Medium/High/Confirmed",
      "recommended_investigation": "Specific telemetry or profiling steps needed"
    }}
  ],
  "bottleneck_analysis": "Detailed analysis of where time is spent across transactions and infrastructure",
  "tail_latency_analysis": "Assessment of P95/P99 outliers, variability, and potential causes",
  "infra_analysis": "Server resource utilization assessment with clear distinction between headroom and saturation",
  "correlation_insights": "Synthesized relationship between client-side latency and server-side metrics",
  "recommendations": [
    {{
      "id": "R-001",
      "priority": "<Critical/High/Medium/Low>",
      "category": "<Backend/Frontend/Infrastructure/Database/Network/Configuration>",
      "title": "Short title",
      "why": "Why this recommendation matters based on evidence",
      "action": ["Step 1", "Step 2"],
      "expected_impact": "Expected qualitative improvement",
      "validation": "How to verify the fix",
      "confidence": "High/Medium/Low/Confirmed"
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
