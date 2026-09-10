"""
ai_studio.py — AI Studio prompt preview, custom generation, chat, and report section patching.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.constants import RESULTS_JSON_DIR, RESULTS_DIR, STORAGE_NORMALIZED_DIR, DATA_DIR
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["AI Studio & Interactive Chat"])


def _load_run_data(run_id: str) -> Dict[str, Any]:
    """
    Loads performance data for a run, prioritizing the new normalized JSON schema contracts
    (Results/normalized/*_aggregate.json, *_timeseries.json, *_server_metrics.json, *_metadata.json)
    with backward-compatible fallback to Results/json/*_result.json.
    """
    clean_id = run_id.replace(".json", "")
    agg_file = STORAGE_NORMALIZED_DIR / f"{clean_id}_aggregate.json"
    ts_file = STORAGE_NORMALIZED_DIR / f"{clean_id}_timeseries.json"
    srv_file = STORAGE_NORMALIZED_DIR / f"{clean_id}_server_metrics.json"
    meta_file = STORAGE_NORMALIZED_DIR / f"{clean_id}_metadata.json"

    legacy_file = RESULTS_JSON_DIR / f"{clean_id}_result.json"
    if not legacy_file.exists():
        legacy_file = RESULTS_DIR / f"{clean_id}_result.json"
    legacy_data = json.loads(legacy_file.read_text(encoding="utf-8")) if legacy_file.exists() else {}

    if agg_file.exists():
        try:
            from app.serialization.serializer import load_aggregate, load_timeseries, load_server_metrics
            agg = load_aggregate(agg_file)
            ts = load_timeseries(ts_file) if ts_file.exists() else None
            srv = load_server_metrics(srv_file) if srv_file.exists() else None

            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            all_lbls = agg.all_labels if agg.all_labels else agg.transactions
            labels_by_tg = (
                {tg: {k: v.model_dump() for k, v in lbls.items()} for tg, lbls in agg.transactions_by_thread_group.items()}
                if agg.transactions_by_thread_group
                else legacy_data.get("labels_by_tg", {})
            )

            return {
                "run_id": clean_id,
                "jmx_name": meta.get("jmx_name", legacy_data.get("jmx_name", agg.test_id)),
                "users": meta.get("users", legacy_data.get("users", 1)),
                "rampup": meta.get("rampup", legacy_data.get("rampup", "0")),
                "summary": {
                    **agg.model_dump(),
                    "total": agg.total_requests,
                    "errors": agg.failed_requests,
                    "avg_rt": agg.avg_response_time,
                    "duration_sec": agg.duration_seconds,
                },
                "labels": {k: v.model_dump() for k, v in all_lbls.items()},
                "labels_by_tg": labels_by_tg,
                "time_series": {
                    "ts_labels": ts.bucket_labels if ts else legacy_data.get("time_series", {}).get("ts_labels", []),
                    "ts_avg_rt": ts.avg_response_time if ts else legacy_data.get("time_series", {}).get("ts_avg_rt", []),
                    "ts_p95_rt": ts.p95_response_time if ts else legacy_data.get("time_series", {}).get("ts_p95_rt", []),
                    "ts_p99_rt": ts.p99_response_time if ts else legacy_data.get("time_series", {}).get("ts_p99_rt", []),
                    "ts_throughput": ts.throughput if ts else legacy_data.get("time_series", {}).get("ts_throughput", []),
                    "ts_errors": ts.errors if ts else legacy_data.get("time_series", {}).get("ts_errors", []),
                    "ts_active_threads": ts.active_threads if ts else legacy_data.get("time_series", {}).get("ts_active_threads", []),
                },
                "infra": srv.infra_summary.model_dump() if srv and srv.infra_summary else legacy_data.get("azure", {}),
                "error_details": {k: v.model_dump() for k, v in agg.errors_breakdown.items()} if agg.errors_breakdown else legacy_data.get("summary", {}).get("errors_breakdown", {}),
                "correlation": legacy_data.get("correlation", {}),
                "ai_insights": legacy_data.get("ai_insights", {}),
                "schema_backed": True,
            }
        except Exception as e:
            logger.warning(f"Could not parse normalized schema models for {clean_id}: {e}; falling back to legacy JSON")

    if not legacy_file.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found in normalized or legacy JSON storage")

    data = json.loads(legacy_file.read_text(encoding="utf-8"))
    data["schema_backed"] = False
    s = data.setdefault("summary", {})
    s.setdefault("total", s.get("total_requests", 0))
    s.setdefault("avg_rt", s.get("avg_response_time", 0))
    s.setdefault("duration_sec", s.get("duration_seconds", 0))
    if "error_details" not in data and "errors_breakdown" in s:
        data["error_details"] = s["errors_breakdown"]
    return data


class GenerateAIRequest(BaseModel):
    run_id: str
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.2
    summary: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    infra: Optional[Dict[str, Any]] = None


class SaveAIRequest(BaseModel):
    run_id: str
    insights: Dict[str, Any]


class ChatMessageRequest(BaseModel):
    run_id: str
    section_id: str = "general"
    message: str
    history: Optional[List[Dict[str, str]]] = None
    baseline_id: Optional[str] = None


class PatchSectionRequest(BaseModel):
    run_id: str
    section_id: str
    content: Any


@router.get("/ai-studio/runs")
def get_ai_studio_runs() -> Dict[str, Any]:
    """Lists runs available for AI Studio analysis from both normalized schema storage and legacy catalog."""
    runs = []
    seen = set()

    # 1. From normalized schema storage
    for p in sorted(STORAGE_NORMALIZED_DIR.glob("*_aggregate.json"), reverse=True):
        rid = p.name.replace("_aggregate.json", "")
        seen.add(rid)
        meta_file = STORAGE_NORMALIZED_DIR / f"{rid}_metadata.json"
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        total = meta.get("total_samples", 0)
        avg_rt = meta.get("avg_rt", 0.0)
        error_rate = meta.get("error_rate", 0.0)
        p95 = meta.get("p95_rt", 0.0)

        if not total:
            try:
                agg_data = json.loads(p.read_text(encoding="utf-8"))
                total = agg_data.get("total_requests", 0)
                avg_rt = agg_data.get("avg_response_time", 0.0)
                error_rate = agg_data.get("error_rate", 0.0)
                p95 = agg_data.get("p95", 0.0)
            except Exception:
                pass

        runs.append({
            "id": rid,
            "jmx_name": meta.get("jmx_name", rid),
            "timestamp": meta.get("timestamp", ""),
            "has_ai": bool(meta.get("has_ai_insights")),
            "has_ai_insights": bool(meta.get("has_ai_insights")),
            "ai_grade": meta.get("status", "Ready"),
            "summary": {
                "total": total,
                "avg_rt": avg_rt,
                "error_rate": error_rate,
                "p95": p95,
            },
            "schema_backed": True,
        })

    # 2. From unified legacy storage
    for p in sorted(RESULTS_JSON_DIR.glob("*_result.json"), reverse=True):
        rid = p.name.replace("_result.json", "")
        if rid in seen:
            continue
        seen.add(rid)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            s = data.get("summary", {})
            total = s.get("total") or s.get("total_requests", 0)
            avg_rt = s.get("avg_rt") or s.get("avg_response_time", 0.0)
            err_rate = s.get("error_rate", 0.0)
            p95 = s.get("p95", 0.0)
            ai_insights = data.get("ai_insights", {})
            has_ai = bool(ai_insights and ai_insights.get("source") != "none")

            runs.append({
                "id": data.get("run_id", rid),
                "jmx_name": data.get("jmx_name", "Scenario"),
                "timestamp": data.get("execution_time", ""),
                "has_ai": has_ai,
                "has_ai_insights": has_ai,
                "ai_grade": ai_insights.get("performance_grade", "Ready"),
                "summary": {
                    "total": total,
                    "avg_rt": avg_rt,
                    "error_rate": err_rate,
                    "p95": p95,
                },
                "schema_backed": False,
            })
        except Exception:
            pass

    return {"success": True, "runs": runs}


@router.get("/ai-studio/prompt-preview")
def get_prompt_preview(run_id: str = Query(...)) -> Dict[str, Any]:
    """Generates prompt preview for a run prioritizing normalized schema data."""
    try:
        from app.services.ai.prompts import build_insights_prompt
        from app.services.analytics.sla_manager import load_sla_targets

        data = _load_run_data(run_id)
        summary = data.get("summary", {})
        labels = data.get("labels", {})
        time_series = data.get("time_series", {})
        users = data.get("users", 1)
        sla_targets, default_rt, default_err = load_sla_targets(data.get("jmx_name", ""), actual_users=users)

        infra = data.get("infra", {})
        if not infra:
            az_file = RESULTS_JSON_DIR / f"azure_{run_id.replace('run_', '')}.json"
            infra = json.loads(az_file.read_text(encoding="utf-8")) if az_file.exists() else {}

        error_details = data.get("error_details", {})
        labels_by_tg = data.get("labels_by_tg", {})

        prompt = build_insights_prompt(
            test_name=data.get("jmx_name", "Scenario"),
            summary=summary,
            labels=labels,
            time_series=time_series,
            infra=infra,
            correlation=data.get("correlation", {}),
            sla_targets=sla_targets,
            default_rt=default_rt,
            default_err=default_err,
            error_details=error_details,
            users=users,
            rampup=int(data.get("rampup", "0") if str(data.get("rampup", "0")).isdigit() else 0),
            labels_by_tg=labels_by_tg,
        )

        return {
            "success": True,
            "prompt": prompt,
            "summary": summary,
            "infra": infra,
            "existing_insights": data.get("ai_insights", {}),
            "labels": labels,
            "schema_backed": data.get("schema_backed", False),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building prompt preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-studio/generate")
def generate_ai_insights_studio(req: GenerateAIRequest) -> Dict[str, Any]:
    """Generates insights via AI provider using custom studio parameters and normalized schema data."""
    try:
        import time
        import os
        from app.services.ai.insights import (
            _load_env,
            execute_openrouter_prompt,
            execute_gemini_prompt,
            execute_github_prompt,
            generate_insights,
            _normalize_model_for_provider
        )

        _load_env()
        data = _load_run_data(req.run_id)
        summary = req.summary or data.get("summary", {})
        infra = req.infra or data.get("infra", {})

        chosen_prompt = (req.prompt or req.user_prompt or "").strip()
        pref_provider = (req.provider or "").strip().lower()
        pref_model = (req.model or "").strip()

        start_time = time.time()
        insights = {}
        used_model = pref_model
        used_provider = pref_provider

        # If the user supplied a custom/refined prompt from the AI Studio editor
        if chosen_prompt:
            openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
            github_token = os.environ.get("GITHUB_TOKEN", "").strip()

            if not pref_provider:
                if "/" in pref_model or "free" in pref_model or "nemotron" in pref_model:
                    pref_provider = "openrouter"
                elif "gemini" in pref_model.lower():
                    pref_provider = "gemini"
                elif "gpt" in pref_model.lower():
                    pref_provider = "github"
                else:
                    pref_provider = "openrouter" if openrouter_key else "gemini" if gemini_key else "github"

            if pref_provider == "openrouter" and openrouter_key:
                norm_m = _normalize_model_for_provider("openrouter", pref_model or "openrouter/free")
                used_model = norm_m
                used_provider = "openrouter"
                insights = execute_openrouter_prompt(chosen_prompt, api_key=openrouter_key, model=norm_m, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
            elif pref_provider == "gemini" and gemini_key:
                norm_m = _normalize_model_for_provider("gemini", pref_model or "gemini-2.5-flash")
                used_model = norm_m
                used_provider = "gemini"
                insights = execute_gemini_prompt(chosen_prompt, api_key=gemini_key, model=norm_m, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
            elif pref_provider == "github" and github_token:
                norm_m = _normalize_model_for_provider("github", pref_model or "gpt-4o-mini")
                used_model = norm_m
                used_provider = "github"
                insights = execute_github_prompt(chosen_prompt, github_token=github_token, model=norm_m, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
            else:
                if openrouter_key:
                    norm_m = _normalize_model_for_provider("openrouter", pref_model or "openrouter/free")
                    used_model = norm_m
                    used_provider = "openrouter"
                    insights = execute_openrouter_prompt(chosen_prompt, api_key=openrouter_key, model=norm_m, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
                elif gemini_key:
                    used_model = "gemini-2.5-flash"
                    used_provider = "gemini"
                    insights = execute_gemini_prompt(chosen_prompt, api_key=gemini_key, model=used_model, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
                elif github_token:
                    used_model = "gpt-4o-mini"
                    used_provider = "github"
                    insights = execute_github_prompt(chosen_prompt, github_token=github_token, model=used_model, summary=summary, infra=infra, temperature=req.temperature or 0.2)[0]
        else:
            from app.services.analytics.sla_manager import load_sla_targets
            users = data.get("users", 1)
            sla_targets, default_rt, default_err = load_sla_targets(data.get("jmx_name", ""), actual_users=users)
            insights = generate_insights(
                test_name=data.get("jmx_name", "Scenario"),
                summary=summary,
                labels=data.get("labels", {}),
                time_series=data.get("time_series", {}),
                infra=infra,
                correlation=data.get("correlation", {}),
                sla_targets=sla_targets,
                default_rt=default_rt,
                default_err=default_err,
                error_details=data.get("error_details", {}),
                users=users,
                rampup=int(data.get("rampup", "0") if str(data.get("rampup", "0")).isdigit() else 0),
                labels_by_tg=data.get("labels_by_tg", {}),
            )
            used_model = insights.get("model", "auto")
            used_provider = insights.get("source", "auto")

        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "success": bool(insights),
            "insights": insights,
            "elapsed_ms": elapsed_ms,
            "model": used_model,
            "provider": used_provider,
            "schema_backed": data.get("schema_backed", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI insights in studio: {e}")
        return {
            "success": False,
            "message": str(e),
            "insights": None,
            "elapsed_ms": int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
        }


@router.post("/ai-studio/save")
def save_ai_insights_studio(req: SaveAIRequest) -> Dict[str, Any]:
    """Persists edited AI insights back into both normalized metadata and unified result JSON and recompiles HTML report."""
    clean_id = req.run_id.replace(".json", "")
    res_path = RESULTS_JSON_DIR / f"{clean_id}_result.json"
    if not res_path.exists():
        res_path = RESULTS_DIR / f"{clean_id}_result.json"

    try:
        data = json.loads(res_path.read_text(encoding="utf-8")) if res_path.exists() else {}
        data["ai_insights"] = req.insights
        res_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Also update metadata file in normalized storage if present
        meta_path = STORAGE_NORMALIZED_DIR / f"{clean_id}_metadata.json"
        if meta_path.exists():
            try:
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                m["has_ai_insights"] = True
                meta_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
            except Exception:
                pass

        # Update data/runs.json catalog
        runs_file = DATA_DIR / "runs.json"
        if runs_file.exists():
            try:
                cat = json.loads(runs_file.read_text(encoding="utf-8"))
                for r in cat.get("runs", []):
                    if r.get("id") == clean_id or r.get("id") == req.run_id:
                        r["has_ai_insights"] = True
                runs_file.write_text(json.dumps(cat, indent=2), encoding="utf-8")
            except Exception:
                pass

        # Automatically recompile the HTML report
        try:
            from app.services.reporting.engine.generator import generate_report
            from app.core.constants import RESULTS_HTML_DIR
            out_html = RESULTS_HTML_DIR / f"{clean_id}_report.html"
            az_file = RESULTS_JSON_DIR / f"azure_{clean_id.replace('run_', '')}.json"
            azure_data = json.loads(az_file.read_text(encoding="utf-8")) if az_file.exists() else {}
            generate_report(
                parsed=data,
                azure_data=azure_data,
                ai_insights=req.insights,
                report_path=out_html,
                jmx_name=data.get("jmx_name", "Scenario"),
                users=data.get("users", 1),
            )
        except Exception as rep_err:
            logger.warning(f"Could not recompile report after saving studio insights: {rep_err}")

        return {"success": True, "message": f"Saved AI insights and recompiled report for {clean_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-chat/message")
def ai_chat_message(req: ChatMessageRequest) -> Dict[str, Any]:
    """Processes interactive AI report copilot chat messages backed by real LLM inference and normalized schema contracts."""
    from app.services.ai.insights import execute_chat_completion

    try:
        data = _load_run_data(req.run_id)
    except Exception:
        data = {}

    summary = data.get("summary", {})
    labels = data.get("labels", {})
    infra = data.get("infra", {})
    error_details = data.get("error_details", {})
    ai_insights = data.get("ai_insights", {})
    jmx_name = data.get("jmx_name", req.run_id)
    users = data.get("users", 1)
    rampup = data.get("rampup", "0")

    # Format top transactions
    sorted_tx = sorted(
        labels.items(),
        key=lambda item: item[1].get("avg_rt", item[1].get("avg", item[1].get("avg_response_time", 0))),
        reverse=True
    )
    tx_lines = []
    for name, m in sorted_tx[:6]:
        tx_lines.append(
            f"  - {name}: Samples={m.get('count', m.get('samples', 0))}, "
            f"Avg={m.get('avg_rt', m.get('avg', 0))}ms, "
            f"P90={m.get('p90', 0)}ms, P95={m.get('p95', 0)}ms, "
            f"Errors={m.get('errors', 0)} ({m.get('error_rate', 0)}%)"
        )
    top_tx_str = "\n".join(tx_lines) if tx_lines else "  No transaction breakdown available."

    # Identify section context and existing findings
    section_label_map = {
        "exec_overview": "Executive Overview / Summary",
        "exec_observations": "Executive Observations by Category",
        "exec_conclusions": "Conclusions & Verdict",
        "exec_recommendations": "Actionable Technical Recommendations",
        "tab_tx_stats": "Transaction Response Times & Throughput",
        "tab_rt_stats": "Response Time Distribution & Percentiles",
        "tab_error_stats": "Error Analysis & Breakdowns",
        "tab_infra_stats": "Server Infrastructure (Azure/Host)",
        "tab_comparison": "Run-to-Run Comparison",
        "compare": "Run-to-Run Comparison",
    }
    section_title = section_label_map.get(req.section_id, req.section_id)

    # Extract existing AI section content if already present
    existing_content = None
    if req.section_id in ai_insights:
        existing_content = ai_insights[req.section_id]
    elif "performance_intelligence" in ai_insights and isinstance(ai_insights["performance_intelligence"], dict):
        pi = ai_insights["performance_intelligence"]
        if req.section_id == "exec_overview":
            existing_content = pi.get("executive_summary")
        elif req.section_id == "exec_observations":
            existing_content = pi.get("observations")
        elif req.section_id == "exec_recommendations":
            existing_content = pi.get("recommendations")
        elif req.section_id == "exec_conclusions":
            existing_content = pi.get("conclusions")
    elif "tab_insights" in ai_insights and isinstance(ai_insights["tab_insights"], dict):
        existing_content = ai_insights["tab_insights"].get(req.section_id)

    # Baseline comparison context if provided
    baseline_ctx_str = ""
    if req.baseline_id:
        try:
            base_data = _load_run_data(req.baseline_id)
            bsum = base_data.get("summary", {})
            baseline_ctx_str = f"""
BASELINE RUN COMPARISON:
- Baseline Run ID: {req.baseline_id} ({base_data.get('jmx_name', 'Baseline')})
- Baseline Users: {base_data.get('users', 'N/A')}
- Baseline Throughput: {bsum.get('throughput', 0):.2f} TPS
- Baseline Avg RT: {bsum.get('avg_rt', bsum.get('avg_response_time', 0)):.1f} ms
- Baseline Error Rate: {bsum.get('error_rate', 0):.2f}%
"""
        except Exception:
            baseline_ctx_str = f"\nBASELINE RUN: {req.baseline_id} (metrics could not be loaded)\n"

    # Build system prompt for PerfAgent
    system_prompt = f"""You are PerfAgent, an elite Performance Engineering AI Assistant integrated directly into an interactive performance test dashboard.
You have full access to performance telemetry for test run '{req.run_id}'.

TEST RUN PROFILE:
- Test Scenario: {jmx_name}
- Virtual Concurrent Users: {users}
- Duration: {summary.get('duration_sec', summary.get('duration', 'N/A'))} seconds | Ramp-up: {rampup}s
- Total Requests / Samples: {summary.get('total', summary.get('total_requests', 0)):,}
- Error Rate: {summary.get('error_rate', 0):.2f}% ({summary.get('errors', summary.get('failed_requests', 0)):,} failed requests)
- Overall Throughput: {summary.get('throughput', 0):.2f} TPS
- Latencies: Avg = {summary.get('avg_rt', summary.get('avg_response_time', 0)):.1f} ms | P90 = {summary.get('p90', 0):.1f} ms | P95 = {summary.get('p95', 0):.1f} ms | P99 = {summary.get('p99', 0):.1f} ms | Max = {summary.get('max_rt', summary.get('max', 0))} ms
- Server Infra: Max CPU = {infra.get('max_cpu', 'N/A')}%, Max Memory = {infra.get('max_memory', 'N/A')}%
{baseline_ctx_str}
TOP TRANSACTIONS:
{top_tx_str}

ERROR DETAILS:
{json.dumps(error_details, indent=2) if error_details else "No errors detected."}

CURRENT ACTIVE SECTION IN DASHBOARD:
Section ID: '{req.section_id}' ({section_title})
Existing Content for this section:
{json.dumps(existing_content, indent=2) if existing_content else "None generated yet."}

INSTRUCTIONS FOR PERFAGENT:
1. Ground your answers directly in the empirical telemetry above. Cite specific numbers (TPS, Avg/P90/P95 latencies, failure counts, transaction names).
2. Maintain an executive, highly technical, performance-engineering tone.
3. If the user asks a question or asks for explanation, answer directly in markdown with bullet points and bold metrics.
4. If the user asks you to rewrite, revise, update, draft, optimize, or change the report section ('{req.section_id}'), you MUST:
   a) Provide a 1-2 sentence conversational explanation of what you improved.
   b) Provide an actionable patch code block formatted EXACTLY as:
```action:patch_section
{{
  "section_id": "{req.section_id}",
  "content": <PATCH_CONTENT>
}}
```
Format rules for <PATCH_CONTENT>:
- For 'exec_overview' or 'exec_conclusions':
  "content": ["Executive takeaway 1...", "Takeaway 2...", "Takeaway 3..."] (JSON array of strings/bullet points).
- For 'exec_observations':
  "content": [
    {{"category": "Throughput & Scalability", "observation": "Detailed technical observation..."}},
    {{"category": "Response Time Degradation", "observation": "Detailed technical observation..."}}
  ]
- For 'exec_recommendations':
  "content": [
    {{
      "badge": "🚀",
      "title": "Recommendation Title",
      "priority": "High",
      "detail": "Actionable technical instructions...",
      "business_impact": "Direct business impact and expected latency reduction..."
    }}
  ]
- For 'tab_tx_stats', 'tab_rt_stats', 'tab_error_stats', 'tab_infra_stats', 'tab_comparison', or 'compare':
  "content": {{
    "summary": "Executive summary paragraph...",
    "observations": ["Obs 1", "Obs 2"],
    "recommendations": ["Rec 1", "Rec 2"]
  }}
"""

    messages = []
    if req.history:
        for h in req.history:
            if isinstance(h, dict) and h.get("content"):
                role = "user" if h.get("role") in ("user", "human") else "assistant"
                messages.append({"role": role, "content": str(h.get("content"))})
    messages.append({"role": "user", "content": req.message})

    try:
        reply, provider, elapsed_ms = execute_chat_completion(
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.3
        )
        return {
            "success": True,
            "reply": reply,
            "provider": provider,
            "elapsed_ms": elapsed_ms,
            "schema_backed": data.get("schema_backed", False)
        }
    except Exception as e:
        logger.error(f"Error executing AI chat for run {req.run_id}: {e}")
        return {
            "success": False,
            "reply": f"Sorry, I encountered an issue contacting the AI provider: {str(e)}. Please check your AI API key configuration in Settings.",
            "message": str(e),
            "schema_backed": data.get("schema_backed", False)
        }


@router.post("/ai-chat/patch-section")
def ai_chat_patch_section(req: PatchSectionRequest) -> Dict[str, Any]:
    """In-place section modification from AI chat suggestion with dual-write persistence."""
    clean_id = req.run_id.replace(".json", "")
    res_path = RESULTS_JSON_DIR / f"{clean_id}_result.json"
    if not res_path.exists():
        res_path = RESULTS_DIR / f"{clean_id}_result.json"

    try:
        data = json.loads(res_path.read_text(encoding="utf-8")) if res_path.exists() else {}
        insights = data.setdefault("ai_insights", {})
        insights[req.section_id] = req.content
        res_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Update metadata in normalized schema storage
        meta_path = STORAGE_NORMALIZED_DIR / f"{clean_id}_metadata.json"
        if meta_path.exists():
            try:
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                m["has_ai_insights"] = True
                meta_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
            except Exception:
                pass

        # Update data/runs.json catalog
        runs_file = DATA_DIR / "runs.json"
        if runs_file.exists():
            try:
                cat = json.loads(runs_file.read_text(encoding="utf-8"))
                for r in cat.get("runs", []):
                    if r.get("id") == clean_id or r.get("id") == req.run_id:
                        r["has_ai_insights"] = True
                runs_file.write_text(json.dumps(cat, indent=2), encoding="utf-8")
            except Exception:
                pass

        return {"success": True, "message": f"Updated section {req.section_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-chat/clear")
def ai_chat_clear(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Clears conversational history for a report."""
    return {"success": True, "message": "Chat history cleared"}
