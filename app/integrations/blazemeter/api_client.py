"""
api_client.py — BlazeMeter REST API Client for PerfPilot.
Provides programmatic access to BlazeMeter V4 APIs for test execution, status, and reporting.
"""

from typing import Any, Dict, List, Optional
import requests
from requests.auth import HTTPBasicAuth

from app.core.config import settings
from app.core.exceptions import IntegrationError
from app.core.logging import logger


class BlazeMeterApiClient:
    """Client for BlazeMeter V4 REST API."""

    def __init__(
        self,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key_id = api_key_id or settings.blazemeter_api_key_id
        self.api_key_secret = api_key_secret or settings.blazemeter_api_key_secret
        self.base_url = (base_url or settings.blazemeter_base_url).rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key_id and self.api_key_secret)

    def _get_auth(self) -> Optional[HTTPBasicAuth]:
        if not self.is_configured:
            return None
        return HTTPBasicAuth(self.api_key_id, self.api_key_secret)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        auth = self._get_auth()
        if not auth:
            raise IntegrationError("BlazeMeter credentials not configured. Set BLAZEMETER_API_KEY_ID and BLAZEMETER_API_KEY_SECRET.")

        try:
            resp = requests.request(method, url, auth=auth, timeout=15, **kwargs)
            if resp.status_code >= 400:
                raise IntegrationError(
                    f"BlazeMeter API {method} {endpoint} failed ({resp.status_code}): {resp.text[:300]}",
                    context={"status_code": resp.status_code, "url": url}
                )
            return resp.json()
        except requests.RequestException as e:
            raise IntegrationError(f"Network failure contacting BlazeMeter API: {e}", context={"url": url})

    def list_tests(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists available performance tests."""
        ws = workspace_id or settings.blazemeter_default_workspace_id
        endpoint = f"/tests?workspaceId={ws}" if ws else "/tests"
        data = self._request("GET", endpoint)
        return data.get("result", [])

    def start_test(self, test_id: str) -> Dict[str, Any]:
        """Initiates test execution in BlazeMeter cloud."""
        endpoint = f"/tests/{test_id}/start"
        data = self._request("POST", endpoint)
        result = data.get("result", {})
        logger.info(f"Launched BlazeMeter test {test_id} -> master {result.get('id')}")
        return result

    def get_master_status(self, master_id: str) -> Dict[str, Any]:
        """Queries status of an active test execution master."""
        endpoint = f"/masters/{master_id}/status"
        data = self._request("GET", endpoint)
        return data.get("result", {})

    def stop_master(self, master_id: str) -> bool:
        """Terminates an active BlazeMeter master run."""
        endpoint = f"/masters/{master_id}/terminate"
        self._request("POST", endpoint)
        logger.info(f"Terminated BlazeMeter master {master_id}")
        return True

    def get_master_summary(self, master_id: str) -> Dict[str, Any]:
        """Retrieves aggregated summary statistics for a completed run."""
        endpoint = f"/masters/{master_id}/reports/aggregate"
        data = self._request("GET", endpoint)
        return data.get("result", {})

    def get_master_timeseries(self, master_id: str) -> Dict[str, Any]:
        """Retrieves time-series KPI timeline data."""
        endpoint = f"/masters/{master_id}/reports/default/chart"
        data = self._request("GET", endpoint)
        return data.get("result", {})


# Global singleton
blazemeter_client = BlazeMeterApiClient()
