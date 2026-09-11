#!/usr/bin/env python3
"""
insights.py — AI-Powered Performance Analysis.

Uses OpenRouter, Gemini API, or GitHub Models to generate deep performance optimization insights,
evidence-backed observations, and actionable recommendations.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from app.core.constants import ROOT_DIR, LOGS_DIR, CONFIG_DIR

_ROOT_DIR = ROOT_DIR
_LOGS_DIR = LOGS_DIR


def _load_env():
    env_path = CONFIG_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key and val:
                    os.environ[key] = val


from app.services.ai.prompts import build_insights_prompt, build_comparison_prompt, build_2run_comparison_prompt

_PROMPT_LOG_FILE = _LOGS_DIR / "ai_last_prompt.txt"
_RESPONSE_LOG_FILE = _LOGS_DIR / "ai_last_response.txt"
_DEBUG_LOG_FILE = _LOGS_DIR / "ai_debug.log"


def _ensure_logs_dir():
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def safe_print(*args, **kwargs) -> None:
    """Print to stdout safely on Windows, suppressing Errno 22 / invalid handle errors."""
    try:
        kwargs.setdefault("flush", True)
        print(*args, **kwargs)
    except OSError as e:
        if getattr(e, "errno", None) in (22, 9):  # EINVAL, EBADF
            pass
        else:
            raise
    except Exception:
        pass


def _log_ai_prompt(provider: str, model: str, prompt: str, action: str = "insights") -> None:
    """Save full prompt to logs/ai_last_prompt.txt, append to ai_debug.log, and print console banner."""
    try:
        _ensure_logs_dir()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        tokens_est = len(prompt) // 4
        
        header = (
            f"{'='*80}\n"
            f"TIMESTAMP:     {ts}\n"
            f"PROVIDER:      {provider}\n"
            f"MODEL:         {model}\n"
            f"ACTION:        {action}\n"
            f"PROMPT LENGTH: {len(prompt):,} characters (~{tokens_est:,} estimated tokens)\n"
            f"{'='*80}\n\n"
        )
        try:
            _PROMPT_LOG_FILE.write_text(header + prompt, encoding="utf-8", errors="replace")
        except Exception:
            pass
        
        try:
            with open(_DEBUG_LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"[{ts}] [PROMPT] provider={provider} model={model} action={action} chars={len(prompt)} tokens~{tokens_est}\n")
        except Exception:
            pass
            
        prompt_snippet = prompt.strip()[:400].replace("\n", " ")
        safe_prompt = prompt_snippet.encode(getattr(sys.stdout, "encoding", None) or "utf-8", errors="replace").decode(getattr(sys.stdout, "encoding", None) or "utf-8")
        safe_print(f"\n{'='*80}")
        safe_print(f"[AI ENGINE] >>> DISPATCHING PROMPT TO: {provider.upper()} ({model})")
        safe_print(f"[AI ENGINE] Action: {action} | Length: {len(prompt):,} chars (~{tokens_est:,} tokens)")
        safe_print(f"[AI ENGINE] Prompt Preview: {safe_prompt}...")
        safe_print(f"[AI ENGINE] Full Prompt Saved to: logs/ai_last_prompt.txt")
        safe_print(f"{'='*80}\n")
    except Exception as e:
        safe_print(f"[AI ENGINE] Warning: Failed to write prompt log: {e}")


def _log_ai_response(provider: str, model: str, raw_text: str, elapsed_ms: int,
                     status: str = "OK", error: str = None, token_usage: dict = None) -> None:
    """Save full raw response to logs/ai_last_response.txt, append to ai_debug.log, and print console banner with token consumption."""
    try:
        _ensure_logs_dir()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        raw_len = len(raw_text or "")
        
        prompt_tokens = token_usage.get("prompt_tokens") if token_usage else None
        completion_tokens = token_usage.get("completion_tokens") if token_usage else None
        total_tokens = token_usage.get("total_tokens") if token_usage else None

        if total_tokens is not None:
            usage_str = f"Prompt: {prompt_tokens:,} | Completion: {completion_tokens:,} | Total: {total_tokens:,} tokens"
            usage_debug = f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} total_tokens={total_tokens}"
        elif raw_text:
            est_comp = raw_len // 4
            usage_str = f"Prompt: N/A | Completion: ~{est_comp:,} (est) | Total: ~{est_comp:,} (est)"
            usage_debug = f"tokens_est~{est_comp}"
        else:
            usage_str = "N/A"
            usage_debug = "tokens=N/A"

        header = (
            f"{'='*80}\n"
            f"TIMESTAMP:       {ts}\n"
            f"PROVIDER:        {provider}\n"
            f"MODEL:           {model}\n"
            f"STATUS:          {status}\n"
            f"ELAPSED:         {elapsed_ms:,} ms\n"
            f"RESPONSE LENGTH: {raw_len:,} characters\n"
            f"TOKEN USAGE:     {usage_str}\n"
        )
        if error:
            header += f"ERROR:           {error}\n"
        header += f"{'='*80}\n\n"
        try:
            _RESPONSE_LOG_FILE.write_text(header + (raw_text or ""), encoding="utf-8", errors="replace")
        except Exception:
            pass
        
        try:
            with open(_DEBUG_LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
                err_str = f" error=\"{error}\"" if error else ""
                f.write(f"[{ts}] [RESPONSE] provider={provider} model={model} status={status} elapsed={elapsed_ms}ms chars={raw_len} {usage_debug}{err_str}\n")
        except Exception:
            pass
            
        safe_print(f"\n{'='*80}")
        safe_print(f"[AI ENGINE] <<< RAW RESPONSE RECEIVED FROM {provider.upper()} ({elapsed_ms:,} ms)")
        safe_print(f"[AI ENGINE] Status: {status} | Length: {raw_len:,} chars")
        safe_print(f"[AI ENGINE] Token Consumption: {usage_str}")
        safe_print(f"[AI ENGINE] Full Raw Response Saved to: logs/ai_last_response.txt")
        if raw_text:
            snippet = raw_text.strip()[:400].replace("\n", " ")
            safe_snippet = snippet.encode(getattr(sys.stdout, "encoding", None) or "utf-8", errors="replace").decode(getattr(sys.stdout, "encoding", None) or "utf-8")
            safe_print(f"[AI ENGINE] Response Preview: {safe_snippet}...")
        if error:
            safe_err = str(error).encode(getattr(sys.stdout, "encoding", None) or "utf-8", errors="replace").decode(getattr(sys.stdout, "encoding", None) or "utf-8")
            safe_print(f"[AI ENGINE] Error Detail: {safe_err}")
        safe_print(f"{'='*80}\n")
    except Exception as e:
        safe_print(f"[AI ENGINE] Warning: Failed to write response log: {e}")


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
        if m in ("minimax/minimax-m3:free", "nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3.5-lightning:free", "nvidia/llama-3.1-nemotron-70b-instruct"):
            return "openrouter/free"
        if ":free" in m:
            return m
        if not m or m in ("default", "gemini", "gemini-flash", "auto", "google/gemini-2.0-flash-001"):
            return "openrouter/free"
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


def _pure_python_repair_json(s: str) -> dict:
    """Robust, pure-Python repair for truncated or malformed JSON from LLMs without third-party dependencies."""
    import re
    if not s or not isinstance(s, str):
        raise ValueError("Empty string")

    start = s.find("{")
    if start < 0:
        raise ValueError("No JSON object opening brace '{' found")
    s = s[start:].strip()

    try:
        res = json.loads(s, strict=False)
        if isinstance(res, dict):
            return res
    except Exception:
        pass

    in_string = False
    escape = False
    clean_chars = []
    for ch in s:
        if escape:
            clean_chars.append(ch)
            escape = False
            continue
        if ch == '\\':
            clean_chars.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            clean_chars.append(ch)
            continue
        clean_chars.append(ch)

    res = ''.join(clean_chars)
    if in_string:
        res += '"'

    for _ in range(5):
        res = res.strip()
        res = re.sub(r',\s*$', '', res)
        res = re.sub(r':\s*$', ': null', res)
        res = re.sub(r',\s*"[^"]*"\s*:\s*null\s*$', '', res)
        res = re.sub(r',\s*"[^"]*"\s*:\s*$', '', res)
        res = re.sub(r',\s*"[^"]*"\s*$', '', res)

    in_str = False
    esc = False
    stack = []
    for ch in res:
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch in ('}', ']') and stack and stack[-1] == ch:
            stack.pop()

    while stack:
        closer = stack.pop()
        res = re.sub(r',\s*$', '', res)
        res += closer

    parsed = json.loads(res, strict=False)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("Repaired content is not a JSON object")


def _safe_json_loads(text: str, provider_name: str = "AI") -> dict:
    """Robustly parse JSON response from LLMs, handling markdown fences, unescaped characters, and truncated JSON."""
    import re
    t = (text or "").strip()
    if not t:
        raise ValueError(f"Empty response received from {provider_name}.")

    safe_print(f"[AI ENGINE] Parsing JSON response ({len(t):,} chars)...")

    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
    if t.endswith("```"):
        t = t[:-3]
    if t.startswith("json"):
        t = t[4:]
    t = t.strip()

    try:
        parsed = json.loads(t, strict=False)
        if isinstance(parsed, dict):
            safe_print(f"[AI ENGINE] [JSON OK] Standard parser succeeded. Keys: {list(parsed.keys())[:6]}")
            return parsed
    except Exception as e1:
        safe_print(f"[AI ENGINE] [JSON NOTICE] Standard parser failed ({e1}). Attempting automated repair...")

    try:
        repaired = _pure_python_repair_json(t)
        if isinstance(repaired, dict) and repaired:
            safe_print(f"[AI ENGINE] [JSON REPAIRED] Pure-Python repair succeeded. Keys: {list(repaired.keys())[:6]}")
            return repaired
    except Exception:
        pass

    try:
        import json_repair
        repaired = json_repair.loads(t)
        if isinstance(repaired, str):
            try:
                repaired = json.loads(repaired, strict=False)
            except Exception:
                pass
        if isinstance(repaired, dict) and repaired:
            safe_print(f"[AI ENGINE] [JSON REPAIRED] json_repair package succeeded. Keys: {list(repaired.keys())[:6]}")
            return repaired
    except Exception:
        pass

    start = t.find("{")
    end = t.rfind("}") + 1
    if start >= 0:
        sub = t[start:end] if end > start else t[start:]
        try:
            parsed = json.loads(sub, strict=False)
            if isinstance(parsed, dict):
                safe_print(f"[AI ENGINE] [JSON REPAIRED] Outer braces extraction parsed successfully.")
                return parsed
        except Exception:
            pass

        try:
            repaired = _pure_python_repair_json(sub)
            if isinstance(repaired, dict) and repaired:
                safe_print(f"[AI ENGINE] [JSON REPAIRED] Pure-Python substring repair succeeded. Keys: {list(repaired.keys())[:6]}")
                return repaired
        except Exception:
            pass

    err_preview = t[:300].replace("\n", " ")
    safe_print(f"[AI ENGINE] [JSON FAILED] All JSON parse and repair attempts failed for {provider_name} response!")
    safe_print(f"[AI ENGINE] [JSON FAILED] Response preview: {err_preview}...")
    safe_print(f"[AI ENGINE] [JSON FAILED] Complete raw response saved to: logs/ai_last_response.txt")
    raise ValueError(f"Failed to parse JSON response from {provider_name}. Full response logged to logs/ai_last_response.txt. Preview: {err_preview}")


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
    _log_ai_prompt("gemini", norm_model, prompt, action="insights")

    start_time = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_model}:generateContent?key={key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": float(temperature),
            "maxOutputTokens": 8192
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    usage = {}
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise Exception(f"Gemini returned empty candidates: {res_data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            res_text = parts[0].get("text", "") if parts else ""
            meta = res_data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": meta.get("promptTokenCount", 0),
                "completion_tokens": meta.get("candidatesTokenCount", 0),
                "total_tokens": meta.get("totalTokenCount", 0)
            }
    except urllib.error.HTTPError as err:
        elapsed_ms = int((time.time() - start_time) * 1000)
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        _log_ai_response("gemini", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"HTTP {err.code}: {err_msg}")
        raise Exception(f"Gemini API Error ({err.code}): {err_msg}")
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        _log_ai_response("gemini", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=str(e))
        raise

    elapsed_ms = int((time.time() - start_time) * 1000)
    _log_ai_response("gemini", norm_model, res_text, elapsed_ms=elapsed_ms, status="OK", token_usage=usage)

    result = _safe_json_loads(res_text, "Gemini")

    result["source"] = "gemini"
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms
    result["token_usage"] = usage

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
    _log_ai_prompt("github", norm_model, prompt, action="insights")

    start_time = time.time()
    url = "https://models.inference.ai.azure.com/chat/completions"

    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": norm_model,
        "temperature": float(temperature),
        "max_tokens": 20000,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    usage = {}
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"GitHub Models returned empty choices: {res_data}")
            content = choices[0].get("message", {}).get("content", "")
            raw_usage = res_data.get("usage", {})
            usage = {
                "prompt_tokens": raw_usage.get("prompt_tokens", 0),
                "completion_tokens": raw_usage.get("completion_tokens", 0),
                "total_tokens": raw_usage.get("total_tokens", 0)
            }
    except urllib.error.HTTPError as err:
        elapsed_ms = int((time.time() - start_time) * 1000)
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        _log_ai_response("github", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"HTTP {err.code}: {err_msg}")
        raise Exception(f"GitHub Models Error ({err.code}): {err_msg}")
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        _log_ai_response("github", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=str(e))
        raise

    elapsed_ms = int((time.time() - start_time) * 1000)
    _log_ai_response("github", norm_model, content, elapsed_ms=elapsed_ms, status="OK", token_usage=usage)

    result = _safe_json_loads(content, "GitHub AI")

    result["source"] = "github_ai"
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms
    result["token_usage"] = usage

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def execute_openrouter_prompt(prompt: str, api_key: str = None, model: str = "google/gemini-2.5-flash",
                              temperature: float = 0.2, summary: dict = None, infra: dict = None) -> tuple[dict, str, int]:
    """Execute prompt directly against OpenRouter API with performance timing, token usage capture, and auto credit tuning."""
    import re
    _load_env()
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    norm_model = _normalize_model_for_provider("openrouter", model)
    _log_ai_prompt("openrouter", norm_model, prompt, action="insights")

    start_time = time.time()
    url = "https://openrouter.ai/api/v1/chat/completions"

    def _do_call(tokens_limit: int) -> tuple[str, dict]:
        system_content = (
            "You are an automated Performance Intelligence Engine JSON API. "
            "You must respond with ONLY a valid, complete JSON object. "
            "Do NOT output any conversational text, thinking process, chain-of-thought, preamble, or markdown code fences. "
            "Start immediately with '{' and end with '}'."
        )
        req_body = {
            "model": norm_model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": float(temperature),
            "max_tokens": tokens_limit,
            "response_format": {"type": "json_object"},
            "reasoning": {
                "effort": "none"
            }
        }
        payload = json.dumps(req_body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "PerfPilot Insights",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"OpenRouter returned empty choices: {res_data}")
            msg = choices[0].get("message", {})
            text_content = msg.get("content") or ""
            # If content is empty or model dumped reasoning into content, strip reasoning
            if not text_content and msg.get("reasoning"):
                text_content = msg.get("reasoning")
            if "<think>" in text_content and "</think>" in text_content:
                text_content = re.sub(r"<think>.*?</think>", "", text_content, flags=re.DOTALL).strip()
            first_brace = text_content.find("{")
            last_brace = text_content.rfind("}")
            if first_brace >= 0 and last_brace > first_brace:
                text_content = text_content[first_brace:last_brace + 1]

            raw_usage = res_data.get("usage", {})
            u_info = {
                "prompt_tokens": raw_usage.get("prompt_tokens", 0),
                "completion_tokens": raw_usage.get("completion_tokens", 0),
                "total_tokens": raw_usage.get("total_tokens", 0)
            }
            return text_content, u_info

    current_max_tokens = 4096
    content = ""
    usage = {}

    try:
        content, usage = _do_call(current_max_tokens)
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            err_msg = err_body

        if err.code == 402:
            m = re.search(r"can only afford (\d+)", err_msg)
            if m:
                affordable = int(m.group(1)) - 50
                if affordable >= 800:
                    safe_print(f"[AI ENGINE] [CREDIT LIMIT DETECTED] OpenRouter 402: Auto-retrying with max_tokens={affordable}...")
                    try:
                        content, usage = _do_call(affordable)
                    except Exception as retry_err:
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"Retry failed: {retry_err}")
                        raise Exception(f"OpenRouter Error (402 retry failed): {retry_err}")
                else:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"HTTP 402: {err_msg}")
                    raise Exception(f"OpenRouter Error (402 Insufficient Credits): {err_msg}")
            else:
                if norm_model != "openrouter/free":
                    safe_print(f"[AI ENGINE] [CREDIT LIMIT DETECTED] OpenRouter 402 ({norm_model}): Auto-falling back to openrouter/free...")
                    try:
                        norm_model = "openrouter/free"
                        content, usage = _do_call(4000)
                    except Exception as free_err:
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"Fallback to free failed: {free_err}")
                        raise Exception(f"OpenRouter Error (402 Insufficient Credits): {err_msg}")
                else:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"HTTP 402: {err_msg}")
                    raise Exception(f"OpenRouter Error (402 Insufficient Credits): {err_msg}")
        else:
            elapsed_ms = int((time.time() - start_time) * 1000)
            _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=f"HTTP {err.code}: {err_msg}")
            raise Exception(f"OpenRouter Error ({err.code}): {err_msg}")
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        _log_ai_response("openrouter", norm_model, "", elapsed_ms=elapsed_ms, status="ERROR", error=str(e))
        raise

    elapsed_ms = int((time.time() - start_time) * 1000)
    _log_ai_response("openrouter", norm_model, content, elapsed_ms=elapsed_ms, status="OK", token_usage=usage)

    result = _safe_json_loads(content, "OpenRouter")

    result["source"] = "openrouter"
    result["model"] = norm_model
    result["elapsed_ms"] = elapsed_ms
    result["token_usage"] = usage

    if summary is not None:
        score, grade = calculate_performance_score(summary, infra)
        result["performance_score"] = score
        result["performance_grade"] = grade

    result = _ensure_performance_intelligence(result)
    return result, content, elapsed_ms


def generate_ai_insights(test_name: str, summary: dict, labels: dict,
                         time_series: dict, infra: dict, correlation: dict,
                         sla_targets: dict = None, default_rt: float = 500.0,
                         default_err: float = 1.0, error_details: dict = None,
                         users: int = 1, rampup: int = 0,
                         labels_by_tg: dict = None) -> dict:
    """Generate full AI performance intelligence insights with transparent logging and multi-provider cascade."""
    _load_env()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    if not preferred_provider:
        preferred_provider = "openrouter" if openrouter_key else "gemini" if gemini_key else "github" if github_token else ""
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()

    if not error_details and summary and isinstance(summary, dict):
        error_details = summary.get("errors_breakdown") or {}
    if not labels_by_tg and summary and isinstance(summary, dict):
        labels_by_tg = summary.get("transactions_by_thread_group") or {}

    try:
        prompt = build_insights_prompt(
            test_name, summary, labels, time_series, infra, correlation,
            sla_targets=sla_targets, default_rt=default_rt, default_err=default_err,
            error_details=error_details, users=users, rampup=rampup,
            labels_by_tg=labels_by_tg
        )
    except Exception as prompt_err:
        safe_print(f"[AI ENGINE] Error constructing insights prompt: {prompt_err}")
        return {}

    # 1. Attempt preferred provider first
    if preferred_provider == "openrouter" and openrouter_key:
        try:
            model = _normalize_model_for_provider("openrouter", preferred_model)
            safe_print(f"[AI ENGINE] [PRIMARY] Attempting preferred provider: OpenRouter ({model})")
            return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            safe_print(f"[AI ENGINE] [NOTICE] OpenRouter error: {e}. Initiating fallback cascade...")

    elif preferred_provider == "gemini" and gemini_key:
        try:
            model = _normalize_model_for_provider("gemini", preferred_model)
            safe_print(f"[AI ENGINE] [PRIMARY] Attempting preferred provider: Gemini ({model})")
            return execute_gemini_prompt(prompt, api_key=gemini_key, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            safe_print(f"[AI ENGINE] [NOTICE] Gemini error: {e}. Initiating fallback cascade...")

    elif preferred_provider == "github" and github_token:
        try:
            model = _normalize_model_for_provider("github", preferred_model)
            safe_print(f"[AI ENGINE] [PRIMARY] Attempting preferred provider: GitHub AI ({model})")
            return execute_github_prompt(prompt, github_token=github_token, model=model, summary=summary, infra=infra)[0]
        except Exception as e:
            safe_print(f"[AI ENGINE] [NOTICE] GitHub AI error: {e}. Initiating fallback cascade...")

    # 2. Fallback Cascade: Gemini Direct
    if gemini_key and preferred_provider != "gemini":
        try:
            safe_print("[AI ENGINE] [FALLBACK] Attempting fallback: Gemini (gemini-2.5-flash)...")
            return execute_gemini_prompt(prompt, api_key=gemini_key, model="gemini-2.5-flash", summary=summary, infra=infra)[0]
        except Exception as e:
            safe_print(f"[AI ENGINE] [FALLBACK FAILED] Gemini error: {e}")

    # 3. Fallback Cascade: GitHub Models
    if github_token and preferred_provider != "github":
        try:
            safe_print("[AI ENGINE] [FALLBACK] Attempting fallback: GitHub Models (gpt-4o-mini)...")
            return execute_github_prompt(prompt, github_token=github_token, model="gpt-4o-mini", summary=summary, infra=infra)[0]
        except Exception as e:
            safe_print(f"[AI ENGINE] [FALLBACK FAILED] GitHub Models error: {e}")

    # 4. Fallback Cascade: OpenRouter Free Models
    if openrouter_key:
        free_models = [
            "openrouter/free",
            "google/gemma-4-31b-it:free",
            "liquid/lfm-2.5-2.6b:free",
            "dots-studio/dots-3-note-preview:free"
        ]
        for fm in free_models:
            try:
                safe_print(f"[AI ENGINE] [FALLBACK] Attempting OpenRouter free tier model: {fm}...")
                return execute_openrouter_prompt(prompt, api_key=openrouter_key, model=fm, summary=summary, infra=infra)[0]
            except Exception as e:
                safe_print(f"[AI ENGINE] [FALLBACK FAILED] OpenRouter ({fm}) error: {e}")

    safe_print("[AI ENGINE] [WARNING] All AI providers in fallback cascade failed or are unconfigured.")
    safe_print("[AI ENGINE] [WARNING] Full prompt and raw response error details saved in logs/ directory.")
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


def generate_2run_comparison_ai_insights(scorecard: dict, transactions: list, new_breaches: list,
                                         resolved_breaches: list, current_info: dict, baseline_info: dict) -> dict:
    """Generates actual deep LLM insights comparing two test executions."""
    _load_env()
    preferred_provider = os.environ.get("DEFAULT_AI_PROVIDER", "").strip().lower()
    preferred_model = os.environ.get("DEFAULT_AI_MODEL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    prompt = build_2run_comparison_prompt(scorecard, transactions, new_breaches, resolved_breaches, current_info, baseline_info)

    # 1. Try preferred provider first
    if preferred_provider == "openrouter" and openrouter_key:
        try:
            model = _normalize_model_for_provider("openrouter", preferred_model)
            safe_print(f"[Comparison AI] Attempting OpenRouter ({model})...")
            res = execute_openrouter_prompt(prompt, api_key=openrouter_key, model=model)[0]
            if res and res.get("executive_summary"):
                return res
        except Exception as e:
            safe_print(f"[Comparison AI] OpenRouter error: {e}")

    elif preferred_provider == "gemini" and gemini_key:
        try:
            model = _normalize_model_for_provider("gemini", preferred_model)
            safe_print(f"[Comparison AI] Attempting Gemini ({model})...")
            res = execute_gemini_prompt(prompt, api_key=gemini_key, model=model)[0]
            if res and res.get("executive_summary"):
                return res
        except Exception as e:
            safe_print(f"[Comparison AI] Gemini error: {e}")

    elif preferred_provider == "github" and github_token:
        try:
            model = _normalize_model_for_provider("github", preferred_model)
            safe_print(f"[Comparison AI] Attempting GitHub ({model})...")
            res = execute_github_prompt(prompt, github_token=github_token, model=model)[0]
            if res and res.get("executive_summary"):
                return res
        except Exception as e:
            safe_print(f"[Comparison AI] GitHub error: {e}")

    # 2. Try fallbacks
    if gemini_key:
        try:
            safe_print("[Comparison AI] Fallback to Gemini (gemini-2.5-flash)...")
            res = execute_gemini_prompt(prompt, api_key=gemini_key, model="gemini-2.5-flash")[0]
            if res and res.get("executive_summary"):
                return res
        except Exception:
            pass

    if github_token:
        try:
            safe_print("[Comparison AI] Fallback to GitHub (gpt-4o-mini)...")
            res = execute_github_prompt(prompt, github_token=github_token, model="gpt-4o-mini")[0]
            if res and res.get("executive_summary"):
                return res
        except Exception:
            pass

    if openrouter_key:
        for fm in ["openrouter/free", "google/gemma-4-31b-it:free", "liquid/lfm-2.5-2.6b:free", "dots-studio/dots-3-note-preview:free"]:
            try:
                safe_print(f"[Comparison AI] Fallback to OpenRouter free model ({fm})...")
                res = execute_openrouter_prompt(prompt, api_key=openrouter_key, model=fm)[0]
                if res and res.get("executive_summary"):
                    return res
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
        
        fallbacks = [
            "openrouter/free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "google/gemma-4-31b-it:free",
            "liquid/lfm-2.5-2.6b:free",
            "dots-studio/dots-3-note-preview:free"
        ]
        for alt in fallbacks:
            if alt not in models_to_try:
                models_to_try.append(alt)

        chat_prompt_str = f"SYSTEM:\n{system_prompt}\n\nMESSAGES:\n" + "\n".join(f"[{msg.get('role')}]: {msg.get('content')}" for msg in sanitized_messages)
        for m in models_to_try:
            try:
                _log_ai_prompt("openrouter", m, chat_prompt_str, action="chat")
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
                with urllib.request.urlopen(req, timeout=60) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices:
                        reply = choices[0]["message"]["content"]
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        raw_usage = res_data.get("usage", {})
                        _log_ai_response("openrouter", m, reply, elapsed_ms=elapsed_ms, status="OK", token_usage=raw_usage)
                        return reply.strip(), f"openrouter ({m})", elapsed_ms
            except urllib.error.HTTPError as err:
                err_body = err.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_body)
                    err_detail = err_json.get("error", {}).get("message", err_body)
                except Exception:
                    err_detail = err_body
                msg_err = f"OpenRouter ({m}) [{err.code}]: {err_detail[:120]}"
                safe_print(f"[AI Chat] {msg_err}")
                _log_ai_response("openrouter", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
                errors_log.append(msg_err)
            except Exception as e:
                msg_err = f"OpenRouter ({m}): {str(e)}"
                safe_print(f"[AI Chat] {msg_err}")
                _log_ai_response("openrouter", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
                errors_log.append(msg_err)

    # 2. Gemini Direct Fallback
    if gemini_key:
        m = _normalize_model_for_provider("gemini", pref_model)
        chat_prompt_str = f"SYSTEM:\n{system_prompt}\n\nMESSAGES:\n" + "\n".join(f"[{msg.get('role')}]: {msg.get('content')}" for msg in sanitized_messages)
        try:
            _log_ai_prompt("gemini", m, chat_prompt_str, action="chat")
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = parts[0].get("text", "") if parts else ""
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    meta = res_data.get("usageMetadata", {})
                    usage = {
                        "prompt_tokens": meta.get("promptTokenCount", 0),
                        "completion_tokens": meta.get("candidatesTokenCount", 0),
                        "total_tokens": meta.get("totalTokenCount", 0)
                    }
                    _log_ai_response("gemini", m, reply, elapsed_ms=elapsed_ms, status="OK", token_usage=usage)
                    return reply.strip(), f"gemini ({m})", elapsed_ms
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                err_detail = err_json.get("error", {}).get("message", err_body)
            except Exception:
                err_detail = err_body
            msg_err = f"Gemini [{err.code}]: {err_detail[:120]}"
            safe_print(f"[AI Chat] {msg_err}")
            _log_ai_response("gemini", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
            errors_log.append(msg_err)
        except Exception as e:
            msg_err = f"Gemini: {str(e)}"
            safe_print(f"[AI Chat] {msg_err}")
            _log_ai_response("gemini", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
            errors_log.append(msg_err)

    # 3. GitHub Models Fallback
    if github_token:
        m = _normalize_model_for_provider("github", pref_model)
        chat_prompt_str = f"SYSTEM:\n{system_prompt}\n\nMESSAGES:\n" + "\n".join(f"[{msg.get('role')}]: {msg.get('content')}" for msg in sanitized_messages)
        try:
            _log_ai_prompt("github", m, chat_prompt_str, action="chat")
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices:
                    reply = choices[0]["message"]["content"]
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    raw_usage = res_data.get("usage", {})
                    usage = {
                        "prompt_tokens": raw_usage.get("prompt_tokens", 0),
                        "completion_tokens": raw_usage.get("completion_tokens", 0),
                        "total_tokens": raw_usage.get("total_tokens", 0)
                    }
                    _log_ai_response("github", m, reply, elapsed_ms=elapsed_ms, status="OK", token_usage=usage)
                    return reply.strip(), f"github ({m})", elapsed_ms
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                err_detail = err_json.get("error", {}).get("message", err_body)
            except Exception:
                err_detail = err_body
            msg_err = f"GitHub AI [{err.code}]: {err_detail[:120]}"
            safe_print(f"[AI Chat] {msg_err}")
            _log_ai_response("github", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
            errors_log.append(msg_err)
        except Exception as e:
            msg_err = f"GitHub AI: {str(e)}"
            safe_print(f"[AI Chat] {msg_err}")
            _log_ai_response("github", m, "", elapsed_ms=int((time.time() - start_time) * 1000), status="ERROR", error=msg_err)
            errors_log.append(msg_err)

    if errors_log:
        details = " | ".join(errors_log[:3])
        raise ValueError(f"AI Chat failed. Provider error details: {details}")

    raise ValueError("No configured AI provider succeeded in handling the chat request. Please check API keys in Settings.")
