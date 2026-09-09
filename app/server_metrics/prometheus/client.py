"""
client.py — Prometheus HTTP API Client for query_range.
"""

from typing import Any, Dict, Optional
import requests
from app.core.config import settings
from app.core.exceptions import IntegrationError
from app.core.logging import logger


class PrometheusClient:
    """Queries Prometheus range vectors for node/container metrics."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.prometheus_url or "http://localhost:9090").rstrip("/")

    def query_range(self, query: str, start: int, end: int, step: int = 15) -> Dict[str, Any]:
        """Executes a Prometheus range vector query."""
        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": query, "start": start, "end": end, "step": f"{step}s"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code >= 400:
                raise IntegrationError(f"Prometheus query failed: {resp.text[:200]}")
            return resp.json()
        except requests.RequestException as e:
            raise IntegrationError(f"Network error contacting Prometheus: {e}")


# Global singleton
prometheus_client = PrometheusClient()
