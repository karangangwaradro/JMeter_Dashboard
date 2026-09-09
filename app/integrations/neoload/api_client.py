"""
api_client.py — NeoLoad Web REST API Client for PerfPilot.
Supports NeoLoad Web SaaS and on-premise REST API V3.
"""

from typing import Any, Dict, List, Optional
import requests

from app.core.config import settings
from app.core.exceptions import IntegrationError
from app.core.logging import logger


class NeoLoadApiClient:
    """Client for NeoLoad Web V3 REST API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ):
        self.api_url = (api_url or settings.neoload_api_url).rstrip("/")
        self.api_token = api_token or settings.neoload_api_token
        self.workspace_id = workspace_id or settings.neoload_default_workspace_id or "default"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token)

    def _headers(self) -> Dict[str, str]:
        if not self.is_configured:
            return {}
        return {
            "accountToken": self.api_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = self._headers()
        if not headers:
            raise IntegrationError("NeoLoad API token not configured. Set NEOLOAD_API_TOKEN in environment or config/.env.")

        try:
            resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)
            if resp.status_code >= 400:
                raise IntegrationError(
                    f"NeoLoad API {method} {endpoint} failed ({resp.status_code}): {resp.text[:300]}",
                    context={"status_code": resp.status_code, "url": url}
                )
            return resp.json()
        except requests.RequestException as e:
            raise IntegrationError(f"Network error contacting NeoLoad API: {e}", context={"url": url})

    def list_tests(self) -> List[Dict[str, Any]]:
        """Lists tests available in the workspace."""
        endpoint = f"/workspaces/{self.workspace_id}/tests"
        data = self._request("GET", endpoint)
        return data if isinstance(data, list) else data.get("tests", [])

    def start_test(self, test_id: str) -> Dict[str, Any]:
        """Launches a test run on NeoLoad Web."""
        endpoint = f"/workspaces/{self.workspace_id}/tests/{test_id}/start"
        result = self._request("POST", endpoint)
        logger.info(f"Launched NeoLoad test {test_id} -> result ID {result.get('resultId', result.get('id'))}")
        return result

    def get_result_status(self, result_id: str) -> Dict[str, Any]:
        """Queries status of a NeoLoad test run."""
        endpoint = f"/workspaces/{self.workspace_id}/test-results/{result_id}"
        return self._request("GET", endpoint)

    def stop_test(self, result_id: str) -> bool:
        """Stops a running NeoLoad test."""
        endpoint = f"/workspaces/{self.workspace_id}/test-results/{result_id}/stop"
        self._request("POST", endpoint)
        logger.info(f"Stopped NeoLoad test result {result_id}")
        return True

    def get_result_statistics(self, result_id: str) -> Dict[str, Any]:
        """Fetches high-level KPIs and aggregate statistics."""
        endpoint = f"/workspaces/{self.workspace_id}/test-results/{result_id}/statistics"
        return self._request("GET", endpoint)

    def get_transaction_elements(self, result_id: str) -> List[Dict[str, Any]]:
        """Fetches per-transaction metrics."""
        endpoint = f"/workspaces/{self.workspace_id}/test-results/{result_id}/elements?category=TRANSACTION"
        data = self._request("GET", endpoint)
        return data if isinstance(data, list) else data.get("elements", [])

    def get_result_points(self, result_id: str) -> List[Dict[str, Any]]:
        """Fetches time-series points across the test execution duration."""
        endpoint = f"/workspaces/{self.workspace_id}/test-results/{result_id}/points"
        data = self._request("GET", endpoint)
        return data if isinstance(data, list) else data.get("points", [])


# Global singleton
neoload_client = NeoLoadApiClient()
