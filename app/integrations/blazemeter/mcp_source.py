"""
mcp_source.py — BlazeMeter MCP Server Result Source.
Provides integration with the BlazeMeter MCP server toolset.
"""

from typing import Any, Dict, Optional
from app.core.exceptions import IntegrationError
from app.core.logging import logger
from app.domain.interfaces.result_collector import ResultSource


class BlazeMeterMCPSource(ResultSource):
    """Retrieves test runs and executions via the BlazeMeter MCP toolset."""

    def __init__(self):
        self.available = True

    def fetch_data(self, identifier: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetches test results via MCP tools or proxies to API client.
        identifier can be testId or masterId.
        """
        options = options or {}
        action = options.get("action", "get_results")
        master_id = options.get("master_id", identifier)

        logger.info(f"[BlazeMeter MCP] Fetching data for master {master_id}")
        from app.integrations.blazemeter.api_client import blazemeter_client
        try:
            summary = blazemeter_client.get_master_summary(master_id)
            timeseries = blazemeter_client.get_master_timeseries(master_id)
            return {
                "master_id": master_id,
                "summary": summary,
                "timeseries": timeseries,
            }
        except Exception as e:
            raise IntegrationError(f"BlazeMeter MCP source error: {e}", context={"master_id": master_id})


# Global singleton
blazemeter_mcp_source = BlazeMeterMCPSource()
