"""
test_run.py — Domain models for test execution requests, options, and status.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class ToolType(str, Enum):
    """Supported performance testing platforms."""
    JMETER = "jmeter"
    BLAZEMETER = "blazemeter"
    NEOLOAD = "neoload"


class IngestionMethod(str, Enum):
    """Methods of acquiring performance data."""
    LOCAL = "local"
    DIRECT_API = "direct_api"
    MCP = "mcp"
    FILE_UPLOAD = "file_upload"


class ThreadGroupConfig(BaseModel):
    """Configuration for an individual thread group or scenario user journey."""
    model_config = ConfigDict(extra="ignore")

    name: str = "__all__"
    enabled: bool = True
    users: int = 1
    duration: str = "0"
    rampup: str = "0"
    iterations: int = 1


class TestExecutionRequest(BaseModel):
    """Request to initiate a test run or ingest performance results."""
    model_config = ConfigDict(extra="ignore")

    tool: ToolType = ToolType.JMETER
    ingestion: IngestionMethod = IngestionMethod.LOCAL
    test_identifier: str = Field(..., description="JMX script name, BlazeMeter test ID, NeoLoad test ID, or raw filename")
    users: int = 1
    duration: str = "0"
    rampup: str = "0"
    thread_groups: List[ThreadGroupConfig] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific options, headers, or API tokens")


class TestExecutionStatus(BaseModel):
    """Live progress and execution state of an ongoing test run."""
    model_config = ConfigDict(extra="ignore")

    run_id: str
    tool: ToolType
    status: str = Field(default="idle", description="'idle', 'running', 'completed', 'failed', 'stopped'")
    active: bool = False
    running: bool = False
    done: bool = False
    progress_pct: float = 0.0
    elapsed_seconds: float = 0.0
    elapsed_str: str = "00:00"
    error: Optional[str] = None
    live_stats: Dict[str, Any] = Field(default_factory=dict)
    failed_requests: Dict[str, Any] = Field(default_factory=dict)
    stdout_lines: List[str] = Field(default_factory=list)
