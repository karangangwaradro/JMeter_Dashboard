#!/usr/bin/env python3
"""
ai_insights.py — AI-Powered Performance Analysis for PerfPilot.

Uses OpenRouter, Gemini API, or GitHub Models to generate deep performance optimization insights,
evidence-backed observations, and actionable recommendations.
"""

import os
import json
import time
import urllib.request
import urllib.error
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


def _normalize_model_for_provider(provider: str, model_str: str) -> str:
    """Normalize model string to provider-specific expected format."""
    m = (model_str or "").strip()
    p = (provider or "").strip().lower()
    
    if p == "gemini":
        clean = m.replace("google/", "").replace(":free", "").strip()
        if not clean or clean in ("default", "gemini", "gemini-flash", "auto", "gemini-2.0-flash-exp", "gemini-2.0-flash"):
            return "gemini-2.5-flash"
        if "nemotron" in clean or "llama" in clean or "gpt" in clean or "deepseek" in clean:
            return "gemini-2.5-flash"
        return clean

    elif p == "openrouter":
        if not m or m in ("default", "gemini", "gemini-flash", "auto", "google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-001", "google/gemini-flash-1.5:free"):
            return "google/gemini-2.5-flash"
        if "/" not in m:
            if m.startswith("gemini"):
                return f"google/{m}"
            if "llama" in m:
                return f"meta-llama/{m}"
            if "deepseek" in m:
                return f"deepseek/{m}"
            if "gpt" in m:
                return f"openai/{m}"
        return m

    elif p == "github":
        if not m or "/" in m or "gemini" in m or "nemotron" in m:
            return "gpt-4o-mini"
        return m

    return m


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
                fixed = re.sub(r'\\(?![/u"bfnrt])', r'\\\\', sub)
                return json.loads(fixed, strict=False)
            except Exception as final_err:
                raise ValueError(f"Failed to parse JSON response from {provider_name}: {final_err}")
    raise ValueError(f"Failed to parse JSON response from {provider_name}: {t[:200]}")


def calculate_performance_score(summary: dict, infra: dict = None) -> tuple[int, str]:
    """Computes an overall 0-100 score and letter grade (A-F) based on error rate, SLA compliance, and infra."""
    error_rate = summary.get("error_rate", 0.0)
    avg_rt = summary.get("avg_rt", 0.0)
    
    score = 100
    if error_rate > 10.0:
        score -= 40
    elif error_rate > 1.0:
        score -= 20
    elif error_rate > 0.1:
        score -= 10

    if avg_rt > 2000:
        score -= 30
    elif avg_rt > 1000:
        score -= 20
    elif avg_rt > 500:
        score -= 10

    if infra:
        max_cpu = infra.get("max_cpu", 0)
        max_mem = infra.get("max_memory", 0)
        if max_cpu > 90 or max_mem > 90:
            score -= 15
        elif max_cpu > 80 or max_mem > 80:
            score -= 5

    score = max(0, min(100, score))
    
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return score, grade


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


def execute_gemini_prompt(prompt: str, api_key: str = None, model: str = "gemini-2.0-flash",
                          temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against Gemini REST API with performance timing."""
    _load_env()
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    norm_model = _normalize_model_for_provider("gemini", model)
    start_time = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_model}:generateContent?key={key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": float(temperature)
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise Exception(f"Gemini returned empty candidates: {res_data}")
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
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, res_text, elapsed_ms


def execute_github_prompt(prompt: str, github_token: str = None, model: str = "gpt-4o-mini",
                          temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against GitHub Models API with performance timing."""
    _load_env()
    token = github_token or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError("GITHUB_TOKEN is not configured.")

    norm_model = _normalize_model_for_provider("github", model)
    start_time = time.time()
    url = "https://models.inference.ai.azure.com/chat/completions"

    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": norm_model,
        "temperature": float(temperature),
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"GitHub Models returned empty choices: {res_data}")
            content = choices[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"GitHub Models Error ({err.code}): {err_msg}")

    elapsed_ms = int((time.time() - start_time) * 1000)
    result = _safe_json_loads(content, "GitHub AI")

    result["source"] = "github_ai"
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def execute_openrouter_prompt(prompt: str, api_key: str = None, model: str = "google/gemini-2.5-flash",
                              temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against OpenRouter API with performance timing."""
    _load_env()
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    norm_model = _normalize_model_for_provider("openrouter", model)
    start_time = time.time()
    url = "https://openrouter.ai/api/v1/chat/completions"

    req_body = {
        "model": norm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(temperature),
        "response_format": {"type": "json_object"}
    }

    payload = json.dumps(req_body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "PerfPilot Insights",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"OpenRouter returned empty choices: {res_data}")
            content = choices[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"OpenRouter Error ({err.code}): {err_msg}")

    elapsed_ms = int((time.time() - start_time) * 1000)
    result = _safe_json_loads(content, "OpenRouter")

    result["source"] = "openrouter"
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def generate_ai_insights(test_name: str, summary: dict, labels: dict,
                         time_series: dict, infra: dict, correlation: dict,
                         sla_targets: dict = None, default_rt: float = 500.0,
                         default_err: float = 1.0) -> dict:
    """Generate full AI performance intelligence insights."""
    _load_env()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = build_insights_prompt(
        test_name, summary, labels, time_series, infra, correlation,
        sla_targets=sla_targets, default_rt=default_rt, default_err=default_err
    )

    if preferred_provider == "openrouter" and openrouter_key:
        try:
            model = _normalize_model_for_provider("openrouter", preferred_model)
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] OpenRouter error: {e}. Trying fallback AI providers...", flush=True)

    elif preferred_provider == "gemini" and gemini_key:
        try:
            model = _normalize_model_for_provider("gemini", preferred_model)
            return execute_gemini_prompt(prompt, api_key=gemini_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] Gemini error: {e}. Trying fallback AI providers...", flush=True)

    elif preferred_provider == "github" and github_token:
        try:
            model = _normalize_model_for_provider("github", preferred_model)
            return execute_github_prompt(prompt, github_token=github_token, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            print(f"[AI] GitHub AI error: {e}. Trying fallback AI providers...", flush=True)

    # Fallback cascade
    if openrouter_key:
        try:
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model="google/gemini-2.5-flash", summary=summary, infra=infra)[0]
        except Exception:
            pass

    if gemini_key:
        try:
            return execute_gemini_prompt(prompt, api_key=gemini_key, model="gemini-2.5-flash", summary=summary, infra=infra)[0]
        except Exception:
            pass

    if github_token:
        try:
            return execute_github_prompt(prompt, github_token=github_token, model="gpt-4o-mini", summary=summary, infra=infra)[0]
        except Exception:
            pass

    return {}


# Alias for backwards compatibility
generate_insights = generate_ai_insights


def generate_comparison_ai_insights(comparison_facts: dict) -> dict:
    """Synthesizes factual multi-release comparison observations."""
    _load_env()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = build_comparison_prompt(comparison_facts)

    if preferred_provider == "openrouter" and openrouter_key:
        try:
            model = _normalize_model_for_provider("openrouter", preferred_model)
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model)[0]
        except Exception:
            pass

    if gemini_key:
        try:
            return execute_gemini_prompt(prompt, api_key=gemini_key, model="gemini-2.5-flash")[0]
        except Exception:
            pass

    if openrouter_key:
        try:
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model="google/gemini-2.5-flash")[0]
        except Exception:
            pass

    return {}


def execute_chat_completion(system_prompt: str, messages: list, temperature: float = 0.2) -> tuple[str, str, int]:
    """
    Executes a contextual section-level AI chat completion.
    Attempts OpenRouter -> Google Gemini -> GitHub Models in preferred order.
    Returns: (reply_text, provider_name, elapsed_ms)
    """
    _load_env()
    pref_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    pref_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    start_time = time.time()
    errors_log = []

    # Format sanitized chat messages
    sanitized_messages = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("content"):
            r = "user" if msg.get("role") in ("user", "human") else "assistant"
            sanitized_messages.append({"role": r, "content": str(msg.get("content"))})

    if not sanitized_messages:
        sanitized_messages = [{"role": "user", "content": "Hello"}]

    # 1. OpenRouter
    if (pref_provider == "openrouter" or not pref_provider) and openrouter_key:
        primary_model = _normalize_model_for_provider("openrouter", pref_model)
        models_to_try = [primary_model]
        
        # Add active Gemini & fast fallback models on OpenRouter
        fallbacks = [
            "google/gemini-2.5-flash",
            "google/gemini-flash-1.5",
            "openrouter/free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ]
        for alt in fallbacks:
            if alt not in models_to_try:
                models_to_try.append(alt)

        for m in models_to_try:
            try:
                payload_msgs = [{"role": "system", "content": system_prompt}] + sanitized_messages
                req_body = {
                    "model": m,
                    "messages": payload_msgs,
                    "temperature": float(temperature)
                }

                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps(req_body).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {openrouter_key}",
                        "HTTP-Referer": "http://localhost:8080",
                        "X-Title": "PerfPilot Chat",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices:
                        reply = choices[0]["message"]["content"]
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        return reply.strip(), f"openrouter ({m})", elapsed_ms
            except urllib.error.HTTPError as err:
                err_body = err.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_body)
                    err_detail = err_json.get("error", {}).get("message", err_body)
                except Exception:
                    err_detail = err_body
                msg_err = f"OpenRouter ({m}) [{err.code}]: {err_detail[:120]}"
                print(f"[AI Chat] {msg_err}", flush=True)
                errors_log.append(msg_err)
            except Exception as e:
                msg_err = f"OpenRouter ({m}): {str(e)}"
                print(f"[AI Chat] {msg_err}", flush=True)
                errors_log.append(msg_err)

    # 2. Gemini Direct Fallback
    if gemini_key:
        try:
            m = _normalize_model_for_provider("gemini", pref_model)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
            
            contents = []
            for msg in sanitized_messages:
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
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = parts[0].get("text", "") if parts else ""
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return reply.strip(), "gemini", elapsed_ms
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            msg_err = f"Gemini [{err.code}]: {err_body[:120]}"
            print(f"[AI Chat] {msg_err}", flush=True)
            errors_log.append(msg_err)
        except Exception as e:
            msg_err = f"Gemini: {str(e)}"
            print(f"[AI Chat] {msg_err}", flush=True)
            errors_log.append(msg_err)

    # 3. GitHub Models Fallback
    if github_token:
        try:
            m = _normalize_model_for_provider("github", pref_model)
            payload_msgs = [{"role": "system", "content": system_prompt}] + sanitized_messages
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
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices:
                    reply = choices[0]["message"]["content"]
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return reply.strip(), "github", elapsed_ms
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            msg_err = f"GitHub AI [{err.code}]: {err_body[:120]}"
            print(f"[AI Chat] {msg_err}", flush=True)
            errors_log.append(msg_err)
        except Exception as e:
            msg_err = f"GitHub AI: {str(e)}"
            print(f"[AI Chat] {msg_err}", flush=True)
            errors_log.append(msg_err)

    if errors_log:
        details = " | ".join(errors_log[:3])
        raise ValueError(f"AI Chat failed. Provider error details: {details}")

    raise ValueError("No configured AI provider succeeded in handling the chat request. Please check API keys in Settings.")
