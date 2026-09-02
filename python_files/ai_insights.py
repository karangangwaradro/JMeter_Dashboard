#!/usr/bin/env python3
"""
ai_insights.py — AI-Powered Performance Analysis for PerfPilot.

Uses Gemini API or GitHub Models to generate deep performance optimization insights,
evidence-backed observations, and actionable recommendations.

Strictly AI-based: Rule-based observation and recommendation fallbacks have been removed.
Supports interactive prompt preview, custom refinement, and live execution.
"""

import os
import json
import time
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
                if key and val:
                    os.environ[key] = val
from python_files.ai_prompts import build_insights_prompt, build_comparison_prompt



def _safe_json_loads(text: str, provider_name: str = "AI") -> dict:
    """Robustly parse JSON response from LLMs, handling markdown fences and unescaped characters."""
    import re
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
    if t.endswith("```"):
        t = t[:-3]
    if t.startswith("json"):
        t = t[4:]
    t = t.strip()

    try:
        return json.loads(t, strict=False)
    except Exception:
        pass

    start = t.find("{")
    end = t.rfind("}") + 1
    if start >= 0 and end > start:
        sub = t[start:end]
        try:
            return json.loads(sub, strict=False)
        except Exception:
            try:
                # Fix unescaped backslashes commonly returned by LLMs in latex or regex patterns
                fixed = re.sub(r'\\(?![/u"bfnrt])', r'\\\\', sub)
                return json.loads(fixed, strict=False)
            except Exception as final_err:
                raise ValueError(f"Failed to parse JSON response from {provider_name}: {final_err}")
    raise ValueError(f"Failed to parse JSON response from {provider_name}: {t[:200]}")


def execute_gemini_prompt(prompt: str, api_key: str = None, model: str = "gemini-2.5-flash",
                          temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against Gemini REST API with performance timing."""
    import urllib.request
    import urllib.error

    _load_env()
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    start_time = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": float(temperature),
            "responseMimeType": "application/json"
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise Exception(f"Gemini returned empty candidates list: {data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            res_text = parts[0].get("text", "") if parts else ""
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"Gemini API Error ({err.code}): {err_msg}")

    elapsed_ms = int((time.time() - start_time) * 1000)

    result = _safe_json_loads(res_text, "Gemini")

    result["source"] = "gemini"
    result["model"] = model
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, res_text, elapsed_ms


def execute_github_prompt(prompt: str, github_token: str = None, model: str = "gpt-4o-mini",
                          temperature: float = 0.3, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against GitHub Models API with performance timing."""
    import urllib.request
    import urllib.error

    _load_env()
    token = github_token or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError("GITHUB_TOKEN is not configured.")

    start_time = time.time()
    url = "https://models.inference.ai.azure.com/chat/completions"

    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
        "temperature": float(temperature),
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"GitHub Models API Error ({err.code}): {err_msg}")

    elapsed_ms = int((time.time() - start_time) * 1000)
    result = _safe_json_loads(content, "GitHub Models")
    result["source"] = "github_ai"
    result["model"] = model
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def execute_openrouter_prompt(prompt: str, api_key: str = None, model: str = "nvidia/nemotron-3-ultra-550b-a55b:free",
                              temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against OpenRouter API with performance timing."""
    import urllib.request
    import urllib.error

    _load_env()
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    start_time = time.time()
    url = "https://openrouter.ai/api/v1/chat/completions"

    model_name = model or "nvidia/nemotron-3-ultra-550b-a55b:free"
    if model_name == "nvidia/llama-3.1-nemotron-70b-instruct":
        model_name = "nvidia/nemotron-3-ultra-550b-a55b:free"

    req_body = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(temperature)
    }
    if "nemotron" in model_name.lower():
        req_body["reasoning"] = {"enabled": True}
    else:
        req_body["response_format"] = {"type": "json_object"}

    payload = json.dumps(req_body).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "PerfPilot",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"OpenRouter returned empty choices list: {res_data}")
            msg = choices[0].get("message", {})
            content = msg.get("content", "") or ""
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"OpenRouter API Error ({err.code}): {err_msg}")

    elapsed_ms = int((time.time() - start_time) * 1000)
    result = _safe_json_loads(content, "OpenRouter")

    result["source"] = "openrouter"
    result["model"] = model_name
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def generate_insights(test_name: str, summary: dict, labels: dict,
                      time_series: dict, infra: dict, correlation: dict,
                      sla_targets: dict = None, default_rt: float = 500.0,
                      default_err: float = 1.0) -> dict:
    """
    Generate AI-powered performance insights taking SLA targets into consideration.
    Supports OpenRouter, Google Gemini, and GitHub Models providers based on configured preference.
    """
    _load_env()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    if preferred_model == "nvidia/llama-3.1-nemotron-70b-instruct":
        preferred_model = "nvidia/nemotron-3-ultra-550b-a55b:free"
    elif preferred_model == "gemini-2.0-flash":
        preferred_model = "gemini-2.5-flash"

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = build_insights_prompt(
        test_name, summary, labels, time_series, infra, correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err
    )

    # 1. Try Preferred Provider First if configured
    if preferred_provider == "openrouter" and openrouter_key:
        try:
            model = preferred_model or "nvidia/nemotron-3-ultra-550b-a55b:free"
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] OpenRouter error: {e}. Trying fallback AI providers...", flush=True)

    elif preferred_provider == "gemini" and gemini_key:
        try:
            model = preferred_model or "gemini-2.5-flash"
            return execute_gemini_prompt(prompt, api_key=gemini_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] Gemini error: {e}. Trying fallback AI providers...", flush=True)

    elif preferred_provider == "github" and github_token:
        try:
            model = preferred_model or "gpt-4o-mini"
            return execute_github_prompt(prompt, github_token=github_token, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] GitHub AI error: {e}. Trying fallback AI providers...", flush=True)

    # 2. General Fallback Chain if preferred not matched or failed
    if openrouter_key and preferred_provider != "openrouter":
        try:
            model = preferred_model if ("nemotron" in preferred_model.lower() or "/" in preferred_model) else "nvidia/nemotron-3-ultra-550b-a55b:free"
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] OpenRouter fallback error: {e}", flush=True)

    if gemini_key and preferred_provider != "gemini":
        try:
            return execute_gemini_prompt(prompt, api_key=gemini_key, model="gemini-2.5-flash", summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] Gemini fallback error: {e}", flush=True)

    if github_token and preferred_provider != "github":
        try:
            return execute_github_prompt(prompt, github_token=github_token, model="gpt-4o-mini", summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] GitHub AI fallback error: {e}", flush=True)

    print("[AI] No AI provider available or request failed. AI insights skipped.", flush=True)
    return _empty_insights(summary, infra)


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


def _empty_insights(summary: dict, infra: dict = None) -> dict:
    """Return an empty insight schema when AI is not run or fails."""
    score, grade = calculate_performance_score(summary, infra)
    return {
        "source": "none",
        "executive_summary": "AI insights not generated. Configure GEMINI_API_KEY or GITHUB_TOKEN to enable AI analysis.",
        "performance_score": score,
        "performance_grade": grade,
        "performance_intelligence": {
            "executive_summary": {
                "assessment_badge": "",
                "assessment_color": "",
                "assessment_text": "",
                "kpis": {},
                "observations_table": [],
                "conclusions": [],
                "priority_recommendations": []
            },
            "tab_tx_stats": {"observations": [], "recommendations": []},
            "tab_rt_stats": {"observations": [], "recommendations": []},
            "tab_error_stats": {"observations": [], "recommendations": []},
            "tab_infra_stats": {"observations": [], "recommendations": []}
        },
        "data_quality_findings": [],
        "finding_enrichments": {},
        "root_cause_assessment": [],
        "bottleneck_analysis": "",
        "tail_latency_analysis": "",
        "infra_analysis": "",
        "capacity_planning": {},
        "correlation_insights": "",
        "recommendations": []
    }


def _ensure_performance_intelligence(insights: dict) -> dict:
    """Ensure structured performance_intelligence has base keys without injecting rule-based text."""
    if "performance_intelligence" not in insights or not isinstance(insights["performance_intelligence"], dict):
        insights["performance_intelligence"] = {}
    
    pi = insights["performance_intelligence"]
    if "executive_summary" not in pi or not isinstance(pi["executive_summary"], dict):
        pi["executive_summary"] = {
            "assessment_badge": "",
            "assessment_color": "",
            "assessment_text": "",
            "kpis": {},
            "observations_table": [],
            "conclusions": [],
            "priority_recommendations": []
        }
    
    for tab in ["tab_tx_stats", "tab_rt_stats", "tab_error_stats", "tab_infra_stats"]:
        if tab not in pi or not isinstance(pi[tab], dict):
            pi[tab] = {"observations": [], "recommendations": []}
        else:
            if "observations" not in pi[tab] or not isinstance(pi[tab]["observations"], list):
                pi[tab]["observations"] = []
            if "recommendations" not in pi[tab] or not isinstance(pi[tab]["recommendations"], list):
                pi[tab]["recommendations"] = []

    return insights


def generate_comparison_ai_insights(comparison_facts: dict) -> dict:
    """
    Synthesizes factual multi-release comparison observations from calculated deterministic facts.
    Strictly forbids speculative root-cause statements.
    """
    _load_env()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = build_comparison_prompt(comparison_facts)

    if preferred_provider == "openrouter" and openrouter_key:
        try:
            import urllib.request
            model = preferred_model or "nvidia/nemotron-3-ultra-550b-a55b:free"
            if model == "nvidia/llama-3.1-nemotron-70b-instruct":
                model = "nvidia/nemotron-3-ultra-550b-a55b:free"
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "PerfPilot",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(text)
                parsed["source"] = "openrouter"
                return parsed
        except Exception as e:
            print(f"[AI Comparison] OpenRouter error: {e}", flush=True)

    if gemini_key:
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                parsed["source"] = "gemini"
                return parsed
        except Exception as e:
            print(f"[AI Comparison] Gemini API error: {e}", flush=True)

    if openrouter_key:
        try:
            import urllib.request
            model = preferred_model or "nvidia/nemotron-3-ultra-550b-a55b:free"
            if model == "nvidia/llama-3.1-nemotron-70b-instruct":
                model = "nvidia/nemotron-3-ultra-550b-a55b:free"
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "PerfPilot",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(text)
                parsed["source"] = "openrouter"
                return parsed
        except Exception as e:
            print(f"[AI Comparison] OpenRouter fallback error: {e}", flush=True)

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

    return {
        "source": "none",
        "executive_bullets": [],
        "trend_observation": "",
        "sla_observation": "",
        "degradation_observation": "",
        "improvement_observation": "",
        "risk_observation": ""
    }


def execute_chat_completion(system_prompt: str, messages: list,
                            provider: str = None, model: str = None,
                            temperature: float = 0.3) -> tuple[str, str, int]:
    """
    Execute a conversational multi-turn chat completion with section-scoped context.
    Supports OpenRouter, Gemini REST API, and GitHub Models.
    
    Returns:
        tuple[reply_text: str, provider_used: str, elapsed_ms: int]
    """
    import urllib.request
    import urllib.error

    _load_env()
    pref_provider = (provider or os.environ.get("DEFAULT_AI_PROVIDER", "")).strip().lower()
    pref_model = (model or os.environ.get("DEFAULT_AI_MODEL", "")).strip()

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    start_time = time.time()

    # 1. OpenRouter
    if (pref_provider == "openrouter" or not pref_provider) and openrouter_key:
        try:
            m = pref_model or "nvidia/nemotron-3-ultra-550b-a55b:free"
            if m == "nvidia/llama-3.1-nemotron-70b-instruct":
                m = "nvidia/nemotron-3-ultra-550b-a55b:free"
            
            payload_msgs = [{"role": "system", "content": system_prompt}] + messages
            req_body = {
                "model": m,
                "messages": payload_msgs,
                "temperature": float(temperature)
            }
            if "nemotron" in m.lower():
                req_body["reasoning"] = {"enabled": True}

            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(req_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "HTTP-Referer": "http://localhost:8080",
                    "X-Title": "PerfPilot Chat",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                reply = res_data["choices"][0]["message"]["content"]
                elapsed_ms = int((time.time() - start_time) * 1000)
                return reply.strip(), "openrouter", elapsed_ms
        except Exception as e:
            print(f"[AI Chat] OpenRouter error: {e}. Falling back to Gemini...", flush=True)

    # 2. Gemini
    if (pref_provider == "gemini" or gemini_key):
        try:
            m = pref_model if ("gemini" in pref_model.lower()) else "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
            
            # Format contents with system instruction
            contents = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
            
            gemini_payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": contents,
                "generationConfig": {
                    "temperature": float(temperature)
                }
            }
            req = urllib.request.Request(url,
                data=json.dumps(gemini_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = parts[0].get("text", "") if parts else ""
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return reply.strip(), "gemini", elapsed_ms
        except Exception as e:
            print(f"[AI Chat] Gemini API error: {e}. Falling back to GitHub...", flush=True)

    # 3. GitHub Models
    if github_token:
        try:
            m = pref_model if not ("/" in pref_model or "gemini" in pref_model) else "gpt-4o-mini"
            payload_msgs = [{"role": "system", "content": system_prompt}] + messages
            req = urllib.request.Request("https://models.inference.ai.azure.com/chat/completions",
                data=json.dumps({
                    "messages": payload_msgs,
                    "model": m,
                    "temperature": float(temperature)
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                reply = res_data["choices"][0]["message"]["content"]
                elapsed_ms = int((time.time() - start_time) * 1000)
                return reply.strip(), "github", elapsed_ms
        except Exception as e:
            print(f"[AI Chat] GitHub API error: {e}", flush=True)

    raise ValueError("No configured AI provider succeeded in handling the chat request. Please check API keys in Settings.")

