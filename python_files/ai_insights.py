#!/usr/bin/env python3
"""
ai_insights.py — AI-Powered Performance Analysis for JmeterAI.

Uses Gemini API to generate deep performance optimization insights
from combined client-side and server-side metrics.

Falls back to rule-based system-calculated insights if Gemini is unavailable.
"""

import os
import json
from pathlib import Path

_ROOT_DIR = Path(__file__).parent.parent.resolve()


def _load_env():
    env_path = _ROOT_DIR / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key and val and key not in os.environ:
                    os.environ[key] = val


def generate_insights(test_name: str, summary: dict, labels: dict,
                      time_series: dict, infra: dict, correlation: dict) -> dict:
    """
    Generate AI-powered performance insights.
    Tries Gemini API first, then GitHub Models API if GITHUB_TOKEN present, falls back to rule-based.
    """
    _load_env()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    if gemini_key:
        try:
            return _generate_gemini_insights(
                gemini_key, test_name, summary, labels, time_series, infra, correlation
            )
        except Exception as e:
            print(f"[AI] Gemini API error: {e}. Trying fallback AI providers...", flush=True)

    if github_token:
        try:
            return _generate_github_models_insights(
                github_token, test_name, summary, labels, time_series, infra, correlation
            )
        except Exception as e:
            print(f"[AI] GitHub AI error: {e}. Falling back to rule-based analysis.", flush=True)

    return _generate_rule_based_insights(test_name, summary, labels, infra, correlation)


def calculate_performance_score(summary: dict, infra: dict = None) -> tuple[int, str]:
    """Deterministically calculate performance score based on rigid thresholds."""
    avg_rt = summary.get("avg_rt", 0)
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    error_rate = summary.get("error_rate", 0)

    score = 100
    if avg_rt > 2000: score -= 30
    elif avg_rt > 1000: score -= 20
    elif avg_rt > 500: score -= 10
    
    if error_rate > 5: score -= 30
    elif error_rate > 1: score -= 15
    elif error_rate > 0: score -= 5
    
    if p95 > avg_rt * 4: score -= 10
    if p99 > avg_rt * 6: score -= 10
    
    score = max(0, min(100, score))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    return score, grade


def _generate_gemini_insights(api_key: str, test_name: str, summary: dict,
                              labels: dict, time_series: dict, infra: dict,
                              correlation: dict) -> dict:
    """Generate insights using Google Gemini REST API (no external SDK required)."""
    import urllib.request
    import urllib.error

    # Build context for the AI
    top_labels = sorted(labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:10]
    labels_text = "\n".join([
        f"  - {name}: {data.get('count',0)} samples, avg={data.get('avg_rt',0):.0f}ms, "
        f"p95={data.get('p95',0)}ms, errors={data.get('error_rate',0):.2f}%"
        for name, data in top_labels
    ])

    infra_text = "Not available (Azure Monitor not configured)"
    if infra:
        infra_text = (
            f"  CPU: avg={infra.get('avg_cpu',0):.1f}%, max={infra.get('max_cpu',0):.1f}%\n"
            f"  Memory: avg={infra.get('avg_memory',0):.1f}%, max={infra.get('max_memory',0):.1f}%\n"
            f"  Network In: {infra.get('avg_network_in_mbps',0):.1f} MB/min\n"
            f"  Disk Read IOPS: {infra.get('avg_disk_read_iops',0):.0f}"
        )

    corr_findings = ""
    if correlation and correlation.get("findings"):
        corr_findings = "\n".join([
            f"  - [{f.get('severity','info').upper()}] {f.get('message','')}"
            for f in correlation.get("findings", [])
        ])
    else:
        corr_findings = "  No correlation data available"

    # Build findings context for AI enrichment
    # Import findings engine to generate the deterministic findings list
    try:
        from python_files.findings_engine import generate_findings
        # We need display_labels and sla_targets — approximate from labels for prompt context
        findings_result = generate_findings(
            summary=summary, labels=labels, display_labels=dict(top_labels),
            time_series=time_series, infra=infra if infra else {},
            correlation={}, sla_targets={}, default_rt=500.0, default_err=1.0
        )
        findings_text = "\n".join([
            f"  {f['id']}: [{f['severity'].upper()}] {f['title']} — {f['observation']}"
            for f in findings_result.get("findings", [])
        ])
        findings_ids = [f["id"] for f in findings_result.get("findings", [])]
    except Exception:
        findings_text = "  (Findings engine not available — generate your own analysis)"
        findings_ids = []

    prompt = f"""You are a Senior Performance Engineer and Performance Analysis Engine.

Your responsibility is to enrich structured performance findings using ONLY the supplied test evidence.

OBJECTIVE
Transform raw performance measurements into:
1. Evidence-backed observations
2. Technical interpretations
3. Root-cause assessments
4. Business/engineering impact
5. Actionable recommendations
6. Validation criteria
7. Capacity assessment where data permits

EVIDENCE RULES
- Treat supplied measurements as authoritative.
- Never invent missing metrics.
- Never infer infrastructure behavior that is not supported by telemetry.
- Distinguish confirmed facts from hypotheses.
- A peak resource value does not by itself prove saturation.
- A transaction being slow does not prove the database is the cause.
- A correlation does not prove causation.
- Do not estimate maximum capacity without sufficient concurrency/load data.
- If capacity cannot be determined, return null and explain why.
- If client-side and server-side metrics conflict, explicitly flag the discrepancy.
- Every finding must reference the evidence supporting it.
- Every recommendation must reference the finding(s) that triggered it.
- Expected improvement must be qualitative unless historical/benchmark data supports a quantitative estimate.

ROOT CAUSE CONFIDENCE
Use:
- Confirmed: directly supported by telemetry
- High: strong evidence, but not directly proven
- Medium: plausible explanation with partial evidence
- Low: technically plausible but insufficient evidence
- Unknown: insufficient data

IMPORTANT DISTINCTION
Observation = directly measured fact.
Interpretation = meaning derived from one or more observations.
Root cause assessment = evidence-based explanation or hypothesis.
Recommendation = action derived from the finding.
Validation = how the recommendation should be verified.

DATA QUALITY
Check for: conflicting metrics, inconsistent time windows, client/server error-count mismatches, missing telemetry, insufficient concurrency information.
Do not silently reconcile contradictory values.

ANALYSIS RULES:
1. Use only the supplied test data.
2. Do not invent metrics, transactions, infrastructure behavior, database behavior, or user counts.
3. Never state a suspected root cause as confirmed without direct supporting telemetry.
4. Distinguish measured facts, derived metrics, hypotheses, and unknowns.
5. Every finding must cite the metric(s) that support it.
6. Every recommendation must reference one or more findings.
7. Do not calculate maximum capacity unless the data contains sufficient concurrency/load information. NEVER estimate maximum capacity solely from throughput × average response time. Little's Law may be used to estimate observed concurrency only when workload assumptions are valid; it must not be presented as maximum or safe capacity.
8. Do not classify a resource as saturated from a single peak value.
9. Detect contradictions between client-side and server-side telemetry.
10. If data is insufficient, return null or "Not determinable" rather than inventing a value.
11. Do not repeat the same observation across multiple sections unless the additional section adds a different interpretation.
12. Recommendations must be technically actionable and include a validation method.
16. Expected impact must describe the direction of improvement; NEVER use quantitative percentages or multipliers (e.g., 40%, 2x) unless present in the raw data.
17. Do not confidently claim CPU/Memory contention as the direct cause of latency without thread-pool, database, or GC telemetry.

TEST: {test_name}
═══════════════════════════════════════════

CLIENT-SIDE METRICS:
  Total Samples: {summary.get('total', 0):,}
  Average Response Time: {summary.get('avg_rt', 0):.2f} ms
  P50: {summary.get('p50', 0)} ms | P90: {summary.get('p90', 0)} ms
  P95: {summary.get('p95', 0)} ms | P99: {summary.get('p99', 0)} ms
  Min: {summary.get('min_rt', 0)} ms | Max: {summary.get('max_rt', 0)} ms
  Throughput: {summary.get('throughput', 0):.2f} req/s
  Error Rate: {summary.get('error_rate', 0):.2f}%
  Duration: {summary.get('duration_sec', 0):.0f} seconds

PER-TRANSACTION BREAKDOWN (top by response time):
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
  "executive_summary": "2-3 sentence high-level assessment of the test results",
  "data_quality_findings": [
    {{
      "severity": "<Critical/Warning/Info>",
      "issue": "Description of the data contradiction or missing data",
      "evidence": "What metrics conflict",
      "impact": "How this affects the analysis",
      "action": "What the engineer should do"
    }}
  ],
  "finding_enrichments": {{
    {', '.join(['"' + fid + '": {"finding": "...", "evidence": "...", "likely_cause": "...", "confidence": "Low/Medium/High/Confirmed", "recommended_investigation": "..."}' for fid in findings_ids[:6]]) if findings_ids else '"F-001": {"finding": "...", "evidence": "...", "likely_cause": "...", "confidence": "...", "recommended_investigation": "..."}'} 
  }},
  "capacity_planning": {{
    "estimated_max_users": null,
    "saturation_point": null,
    "safe_concurrency": null,
    "analysis": "Explanation of capacity estimates or why they cannot be reliably determined"
  }},
  "root_cause_assessment": [
    {{
      "finding": "Checkout P95 increased by 84%.",
      "evidence": "Response-time degradation begins after 70% concurrency while error rate remains below 1%.",
      "likely_cause": "Backend saturation.",
      "confidence": "Medium",
      "recommended_investigation": "Review CPU, memory, thread pool, and DB connection pool latency."
    }}
  ],
  "bottleneck_analysis": "Detailed analysis of where time is spent and why",
  "tail_latency_analysis": "Deep dive into P95/P99 outliers and their likely causes",
  "infra_analysis": "Server resource utilization assessment with Azure data correlation",
  "correlation_insights": "Key patterns found between client-side and server-side metrics",
  "recommendations": [
    {{
      "id": "R-001",
      "triggered_by": ["F-001"],
      "priority": "<Critical/High/Medium/Low>",
      "category": "<Backend/Frontend/Infrastructure/Database/Network/Configuration>",
      "title": "Short title",
      "why": "Why this recommendation matters",
      "action": ["Step 1", "Step 2"],
      "expected_impact": "Expected qualitative improvement",
      "validation": "How to verify the fix",
      "confidence": "High/Medium/Low/Confirmed"
    }}
  ]
}}"""

    res_text = None
    last_err = None
    model_candidate = "gemini-2.5-flash"

    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_candidate}:generateContent?key={api_key}"
        )

        payload = json.dumps({
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])

            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    res_text = parts[0].get("text", "")
    except urllib.error.HTTPError as e:
        print(f"Status: {e.code}")
        print(e.read().decode())
        raise
    if not res_text:
        raise Exception(f"Gemini API REST request failed: {last_err}")

    text = res_text.strip()
    # Clean markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    if text.startswith("json"):
        text = text[4:]
    text = text.strip()

    try:
        result = json.loads(text)
        result["source"] = "gemini"
        
        # Inject deterministic performance score
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade
        
        return result
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                result["source"] = "gemini"
                
                # Inject deterministic performance score
                score, grade = calculate_performance_score(summary, infra)
                result["performance_score"] = score
                result["performance_grade"] = grade
                
                return result
            except json.JSONDecodeError:
                pass
        print(f"[AI] Failed to parse Gemini response as JSON", flush=True)
        return _generate_rule_based_insights("", summary, labels, infra, {})


def _generate_rule_based_insights(test_name: str, summary: dict, labels: dict,
                                  infra: dict, correlation: dict) -> dict:
    """Generate rule-based insights when AI is unavailable."""
    avg_rt = summary.get("avg_rt", 0)
    p95 = summary.get("p95", 0)
    p99 = summary.get("p99", 0)
    error_rate = summary.get("error_rate", 0)
    throughput = summary.get("throughput", 0)
    total = summary.get("total", 0)

    score, grade = calculate_performance_score(summary, infra)

    # Executive summary
    if score >= 80:
        exec_summary = f"Performance test '{test_name}' completed with healthy metrics. Average response time of {avg_rt:.0f}ms and {error_rate:.2f}% error rate are within acceptable thresholds."
    elif score >= 60:
        exec_summary = f"Performance test '{test_name}' shows moderate concerns. Response times averaging {avg_rt:.0f}ms with {error_rate:.2f}% errors indicate optimization opportunities."
    else:
        exec_summary = f"Performance test '{test_name}' reveals significant issues. {avg_rt:.0f}ms average response time and {error_rate:.2f}% error rate require immediate attention."

    # Root cause assessment
    primary_bottleneck = "No critical bottleneck detected"
    assessment = "Metrics are within expected operational bounds."
    confidence = "High"
    if error_rate > 5:
        primary_bottleneck = "Server-side failures"
        assessment = f"High error rate ({error_rate:.2f}%) indicates server-side failures under load."
        confidence = "High"
    elif avg_rt > 2000:
        primary_bottleneck = "Backend processing latency"
        assessment = f"Extremely slow response times ({avg_rt:.0f}ms average) indicate backend processing bottleneck or database contention."
        confidence = "Medium"
    elif p95 > avg_rt * 4:
        primary_bottleneck = "Resource contention"
        assessment = f"Severe tail latency detected — P95 ({p95}ms) is {round(p95/max(1,avg_rt))}x the average."
        confidence = "Medium"

    # Recommendations
    recommendations = []
    if avg_rt > 500:
        recommendations.append({
            "id": "R-1", "triggered_by": [],
            "priority": "High", "category": "Backend",
            "title": "Optimize Response Times",
            "why": f"Average RT of {avg_rt:.0f}ms exceeds the 500ms target.",
            "action": ["Profile the slowest endpoints", "Add database query caching", "Review N+1 query patterns"],
            "expected_impact": "Reduce avg RT by 30-50%",
            "validation": "Monitor average RT on subsequent load test",
            "confidence": "Medium"
        })
    if error_rate > 1:
        recommendations.append({
            "id": "R-2", "triggered_by": [],
            "priority": "Critical", "category": "Backend",
            "title": "Reduce Error Rate",
            "why": f"Error rate of {error_rate:.2f}% indicates server-side failures.",
            "action": ["Check connection pool sizes", "Review timeout configurations", "Check memory allocation"],
            "expected_impact": "Reduce error rate to <0.1%",
            "validation": "Run load test and verify 0% 5xx errors",
            "confidence": "High"
        })
    if p95 > avg_rt * 3:
        recommendations.append({
            "id": "R-3", "triggered_by": [],
            "priority": "Medium", "category": "Database",
            "title": "Address Tail Latency",
            "why": f"P95 ({p95}ms) is significantly higher than average ({avg_rt:.0f}ms).",
            "action": ["Investigate database lock contention", "Profile GC pauses"],
            "expected_impact": "Reduce P95/P99 variance",
            "validation": "Verify P95/Average ratio drops below 2x",
            "confidence": "Low"
        })
    if infra and infra.get("avg_cpu", 0) > 70:
        recommendations.append({
            "id": "R-4", "triggered_by": [],
            "priority": "High", "category": "Infrastructure",
            "title": "Scale Compute Resources",
            "why": f"CPU averaging {infra['avg_cpu']:.1f}% — approaching saturation.",
            "action": ["Implement horizontal scaling", "Perform CPU profiling"],
            "expected_impact": "Increase headroom to handle 2x current load",
            "validation": "CPU should remain below 60% during load test",
            "confidence": "High"
        })
    if not recommendations:
        recommendations.append({
            "id": "R-0", "triggered_by": [],
            "priority": "Low", "category": "Configuration",
            "title": "Maintain Current Performance",
            "why": "All metrics are within healthy thresholds.",
            "action": ["Consider running longer duration tests", "Test at higher concurrency to find limits"],
            "expected_impact": "Identify maximum safe throughput capacity",
            "validation": "N/A",
            "confidence": "High"
        })

    return {
        "source": "rule_based",
        "executive_summary": exec_summary,
        "performance_score": score,
        "performance_grade": grade,
        "data_quality_findings": [],
        "finding_enrichments": {},
        "root_cause_assessment": {
            "primary_bottleneck": primary_bottleneck,
            "assessment": assessment,
            "confidence": confidence,
            "confirmed": False,
            "evidence": []
        },
        "bottleneck_analysis": f"Average response time: {avg_rt:.0f}ms. P95: {p95}ms. Throughput: {throughput:.1f} req/s. Error rate: {error_rate:.2f}%.",
        "tail_latency_analysis": f"P95/P99 ratio to average: {round(p95/max(1,avg_rt), 1)}x / {round(p99/max(1,avg_rt), 1)}x. {'Significant tail latency detected.' if p95 > avg_rt * 3 else 'Tail latency within acceptable bounds.'}",
        "infra_analysis": f"CPU: {infra.get('avg_cpu', 'N/A')}%, Memory: {infra.get('avg_memory', 'N/A')}%" if infra else "Azure Monitor not configured — server-side analysis unavailable.",
        "capacity_planning": {
            "estimated_max_users": None,
            "saturation_point": None,
            "safe_concurrency": None,
            "analysis": "Capacity cannot be reliably determined from this execution because concurrency/ramp data and an observed saturation point are unavailable. Little's Law shouldn't be used to estimate max capacity here."
        },
        "correlation_insights": "Enable Azure Monitor integration for server-side correlation insights." if not infra else "Client-server metric correlation active.",
        "recommendations": recommendations
    }


def _generate_github_models_insights(github_token: str, test_name: str, summary: dict,
                                      labels: dict, time_series: dict, infra: dict,
                                      correlation: dict) -> dict:
    """Generate insights using GitHub Models API (e.g. gpt-4o / Llama)."""
    import urllib.request

    url = "https://models.inference.ai.azure.com/chat/completions"
    top_labels = sorted(labels.items(), key=lambda x: x[1].get("avg_rt", 0), reverse=True)[:10]

    prompt = f"""You are a Senior Performance Engineer. Analyze this test result and respond ONLY with JSON:
Test: {test_name}
Summary: {json.dumps(summary)}
Top Slow Transactions: {json.dumps(top_labels)}
Server Infra: {json.dumps(infra)}

Return JSON with exact keys:
"executive_summary",
"data_quality_findings" (array of objects with "severity", "issue", "evidence", "impact", "action"),
"finding_enrichments" (object with "interpretation", "root_cause_assessment", "root_cause_confidence", "why_it_matters", "evidence"),
"root_cause_assessment" (object with "primary_bottleneck", "assessment", "confidence", "confirmed", "evidence"),
"bottleneck_analysis", "tail_latency_analysis", "infra_analysis",
"capacity_planning" (object with "estimated_max_users", "saturation_point", "safe_concurrency", "analysis" - use null for unknown capacity, do NOT invent max users from throughput),
"correlation_insights",
"recommendations" (array of objects with "id", "triggered_by", "priority", "category", "title", "why", "action", "expected_impact", "validation", "confidence")
"""

    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json"
    })

    with urllib.request.urlopen(req, timeout=20) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"]
        insights = json.loads(content)
        insights["source"] = "github_ai"
        
        # Inject deterministic performance score
        score, grade = calculate_performance_score(summary, infra)
        insights["performance_score"] = score
        insights["performance_grade"] = grade
        
        return insights


def generate_comparison_ai_insights(comparison_facts: dict) -> dict:
    """
    Synthesizes factual multi-release comparison observations from calculated deterministic facts.
    Strictly forbids speculative root-cause statements (e.g. database locks).
    """
    _load_env()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = f"""You are a Lead Performance Engineer. Analyze these calculated release comparison facts and generate factual summary observations in JSON format.

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

    if gemini_key:
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                parsed["source"] = "gemini_2.0"
                return parsed
        except Exception as e:
            print(f"[AI Comparison] Gemini API error: {e}", flush=True)

    if github_token:
        try:
            import urllib.request
            url = "https://models.inference.ai.azure.com/chat/completions"
            payload = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {github_token}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(text)
                parsed["source"] = "github_ai"
                return parsed
        except Exception as e:
            print(f"[AI Comparison] GitHub API error: {e}", flush=True)

    # Fallback to deterministic observations already present in comparison_facts
    return {
        "source": "deterministic_facts",
        "executive_bullets": comparison_facts.get("ai_executive_summary", []),
        "trend_observation": comparison_facts.get("graph_insights", {}).get("rt_trend", {}).get("observation", ""),
        "sla_observation": comparison_facts.get("graph_insights", {}).get("sla_trend", {}).get("observation", ""),
        "degradation_observation": f"{comparison_facts.get('executive_kpis', {}).get('most_degraded_tx', 'None')} recorded {comparison_facts.get('executive_kpis', {}).get('most_degraded_pct', 0):+.2f}% degradation.",
        "improvement_observation": f"Most improved transaction: {comparison_facts.get('deterministic_conclusions', {}).get('most_improved', 'None')} (-{comparison_facts.get('deterministic_conclusions', {}).get('most_improved_pct', 0):.2f}%).",
        "risk_observation": f"Critical SLA breaches: {comparison_facts.get('executive_kpis', {}).get('critical_breaches_current', 0)}."
    }

