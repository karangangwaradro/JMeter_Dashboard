"""
status.py — System health, environment, and cloud provider status endpoints.
"""

import os
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import settings, load_env_file
from app.core.constants import ROOT_DIR
from app.integrations.jmeter.runner import jmeter_runner

router = APIRouter(prefix="/api", tags=["Status & Configuration"])


class AIConfigRequest(BaseModel):
    openrouter_key: str = ""
    gemini_key: str = ""
    github_token: str = ""
    azure_inference_endpoint: str = ""
    azure_inference_credential: str = ""
    active_provider: str = "openrouter"
    active_model: str = ""
    credit_protection: bool = True
    ai_role_persona: str = ""


class AzureConfigRequest(BaseModel):
    resource_ids: str = ""
    client_id: str = ""
    client_secret: str = ""
    tenant_id: str = ""


@router.get("/status")
def get_system_status() -> Dict[str, Any]:
    """Returns availability of JMeter, BlazeMeter, NeoLoad, Azure Monitor, and AI providers."""
    load_env_file()
    jmeter_info = jmeter_runner.check_jmeter()
    azure_configured = bool(os.environ.get("AZURE_RESOURCE_IDS", "").strip())
    openrouter_configured = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
    gemini_configured = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    github_configured = bool(os.environ.get("GITHUB_TOKEN", "").strip())
    blazemeter_configured = bool(
        os.environ.get("BLAZEMETER_API_KEY_ID", "").strip() and
        os.environ.get("BLAZEMETER_API_KEY_SECRET", "").strip()
    )
    neoload_configured = bool(os.environ.get("NEOLOAD_API_TOKEN", "").strip())

    active_provider = os.environ.get("ACTIVE_AI_PROVIDER", "openrouter")
    active_model = os.environ.get("AI_MODEL_NAME", "gemini-2.5-flash")

    return {
        "jmeter": jmeter_info,
        "azure_configured": azure_configured,
        "openrouter_configured": openrouter_configured,
        "gemini_configured": gemini_configured,
        "github_configured": github_configured,
        "blazemeter_configured": blazemeter_configured,
        "neoload_configured": neoload_configured,
        "active_provider": active_provider,
        "active_model": active_model,
        "credit_protection": os.environ.get("AI_CREDIT_PROTECTION", "true").lower() == "true",
        "supported_tools": ["jmeter", "blazemeter", "neoload"],
        "supported_ingestion_methods": ["local", "direct_api", "mcp", "file_upload"],
    }


@router.get("/ai-config")
def get_ai_config() -> Dict[str, Any]:
    """Retrieves current AI provider configuration."""
    load_env_file()
    return {
        "openrouter_configured": bool(os.environ.get("OPENROUTER_API_KEY", "").strip()),
        "openrouter_key_masked": _mask(os.environ.get("OPENROUTER_API_KEY", "")),
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
        "gemini_key_masked": _mask(os.environ.get("GEMINI_API_KEY", "")),
        "github_configured": bool(os.environ.get("GITHUB_TOKEN", "").strip()),
        "github_token_masked": _mask(os.environ.get("GITHUB_TOKEN", "")),
        "azure_inference_configured": bool(os.environ.get("AZURE_INFERENCE_ENDPOINT", "").strip()),
        "active_provider": os.environ.get("ACTIVE_AI_PROVIDER", "openrouter"),
        "active_model": os.environ.get("AI_MODEL_NAME", "gemini-2.5-flash"),
        "credit_protection": os.environ.get("AI_CREDIT_PROTECTION", "true").lower() == "true",
        "ai_role_persona": os.environ.get("AI_ROLE_PERSONA", ""),
    }


@router.post("/ai-config")
def save_ai_config(cfg: AIConfigRequest) -> Dict[str, Any]:
    """Updates AI configuration and persists to config/.env."""
    env_path = ROOT_DIR / "config" / ".env"
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

    updates = {
        "ACTIVE_AI_PROVIDER": cfg.active_provider,
        "AI_MODEL_NAME": cfg.active_model or "gemini-2.5-flash",
        "AI_CREDIT_PROTECTION": str(cfg.credit_protection).lower(),
    }
    if cfg.openrouter_key and not cfg.openrouter_key.startswith("***"):
        updates["OPENROUTER_API_KEY"] = cfg.openrouter_key
    if cfg.gemini_key and not cfg.gemini_key.startswith("***"):
        updates["GEMINI_API_KEY"] = cfg.gemini_key
    if cfg.github_token and not cfg.github_token.startswith("***"):
        updates["GITHUB_TOKEN"] = cfg.github_token
    if cfg.ai_role_persona:
        updates["AI_ROLE_PERSONA"] = cfg.ai_role_persona

    _write_env_updates(env_path, existing_lines, updates)
    for k, v in updates.items():
        os.environ[k] = v

    return {"success": True, "message": "AI configuration updated successfully"}


@router.post("/azure-config")
def save_azure_config(cfg: AzureConfigRequest) -> Dict[str, Any]:
    """Updates Azure Monitor configuration and persists to config/.env."""
    env_path = ROOT_DIR / "config" / ".env"
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

    updates = {}
    if cfg.resource_ids:
        updates["AZURE_RESOURCE_IDS"] = cfg.resource_ids
    if cfg.client_id and not cfg.client_id.startswith("***"):
        updates["AZURE_CLIENT_ID"] = cfg.client_id
    if cfg.client_secret and not cfg.client_secret.startswith("***"):
        updates["AZURE_CLIENT_SECRET"] = cfg.client_secret
    if cfg.tenant_id:
        updates["AZURE_TENANT_ID"] = cfg.tenant_id

    _write_env_updates(env_path, existing_lines, updates)
    for k, v in updates.items():
        os.environ[k] = v

    return {"success": True, "message": "Azure Monitor configuration saved"}


def _mask(val: str) -> str:
    val = (val or "").strip()
    return f"{val[:4]}...{val[-4:]}" if len(val) >= 8 else ("****" if val else "")


def _write_env_updates(env_path: Path, lines: list, updates: dict):
    new_lines = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
