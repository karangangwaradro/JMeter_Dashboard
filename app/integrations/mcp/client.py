"""
client.py — Generic MCP Client for tool invocation and result sourcing.
"""

from typing import Any, Dict, Optional
from app.core.exceptions import IntegrationError
from app.core.logging import logger


class MCPClient:
    """Client for communicating with local or network Model Context Protocol (MCP) servers."""

    def __init__(self, server_name: str = "blazemeter"):
        self.server_name = server_name

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Invokes an MCP tool by name."""
        logger.info(f"[MCP] Calling tool {self.server_name}:{tool_name}")
        # When running within Antigravity or headless, delegate or execute
        if self.server_name == "blazemeter":
            from app.integrations.blazemeter.mcp_source import blazemeter_mcp_source
            return blazemeter_mcp_source.fetch_data(
                identifier=arguments.get("test_id", arguments.get("master_id", "")),
                options=arguments
            )
        raise IntegrationError(f"MCP server '{self.server_name}' not implemented")


# Global singleton
mcp_client = MCPClient()
