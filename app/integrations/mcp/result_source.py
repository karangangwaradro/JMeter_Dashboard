"""
result_source.py — MCP Result Source implementation of ResultSource interface.
"""

from typing import Any, Dict, Optional
from app.domain.interfaces.result_collector import ResultSource
from app.integrations.mcp.client import mcp_client


class MCPResultSource(ResultSource):
    """Retrieves raw performance data via MCP servers."""

    def fetch_data(self, identifier: str, options: Optional[Dict[str, Any]] = None) -> Any:
        options = options or {}
        tool_name = options.get("tool_name", "get_execution_results")
        return mcp_client.call_tool(tool_name, {"identifier": identifier, **options})


# Global singleton
mcp_result_source = MCPResultSource()
