"""
config.py — Centralized configuration management for PerfPilot.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from app.core.constants import ROOT_DIR, CONFIG_DIR


def load_env_file() -> None:
    """Load environment variables from config/.env if present."""
    env_path = CONFIG_DIR / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k and v and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass


load_env_file()


class Settings(BaseModel):
    """Application settings and integration configuration."""

    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)
    environment: str = Field(default="production")
    debug: bool = Field(default=False)

    # Tool paths
    jmeter_home: Optional[str] = Field(default=None)
    java_home: Optional[str] = Field(default=None)

    # BlazeMeter settings
    blazemeter_api_key_id: Optional[str] = Field(default=None)
    blazemeter_api_key_secret: Optional[str] = Field(default=None)
    blazemeter_base_url: str = Field(default="https://a.blazemeter.com/api/v4")
    blazemeter_default_workspace_id: Optional[str] = Field(default=None)
    blazemeter_default_project_id: Optional[str] = Field(default=None)

    # NeoLoad settings
    neoload_api_url: str = Field(default="https://neoload.saas.neotys.com/v3")
    neoload_api_token: Optional[str] = Field(default=None)
    neoload_default_workspace_id: Optional[str] = Field(default=None)

    # Server Metrics settings
    prometheus_url: Optional[str] = Field(default=None)
    grafana_url: Optional[str] = Field(default=None)
    grafana_api_token: Optional[str] = Field(default=None)
    azure_resource_ids: Optional[str] = Field(default=None)

    # AI settings
    openrouter_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    ai_model_name: str = Field(default="gemini-2.5-flash")

    @classmethod
    def load(cls) -> "Settings":
        """Instantiate settings from environment variables."""
        load_env_file()
        return cls(
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8080")) if os.environ.get("PORT", "").isdigit() else 8080,
            environment=os.environ.get("ENV", "production"),
            debug=os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes"),
            jmeter_home=os.environ.get("JMETER_HOME"),
            java_home=os.environ.get("JAVA_HOME"),
            blazemeter_api_key_id=os.environ.get("BLAZEMETER_API_KEY_ID"),
            blazemeter_api_key_secret=os.environ.get("BLAZEMETER_API_KEY_SECRET"),
            blazemeter_base_url=os.environ.get("BLAZEMETER_BASE_URL", "https://a.blazemeter.com/api/v4"),
            blazemeter_default_workspace_id=os.environ.get("BLAZEMETER_WORKSPACE_ID"),
            blazemeter_default_project_id=os.environ.get("BLAZEMETER_PROJECT_ID"),
            neoload_api_url=os.environ.get("NEOLOAD_API_URL", "https://neoload.saas.neotys.com/v3"),
            neoload_api_token=os.environ.get("NEOLOAD_API_TOKEN"),
            neoload_default_workspace_id=os.environ.get("NEOLOAD_WORKSPACE_ID"),
            prometheus_url=os.environ.get("PROMETHEUS_URL"),
            grafana_url=os.environ.get("GRAFANA_URL"),
            grafana_api_token=os.environ.get("GRAFANA_API_TOKEN"),
            azure_resource_ids=os.environ.get("AZURE_RESOURCE_IDS"),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            ai_model_name=os.environ.get("AI_MODEL_NAME", "gemini-2.5-flash"),
        )


settings = Settings.load()
