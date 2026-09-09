"""
test_metadata.py — Domain model for historical test run metadata and catalog entry.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TestRunMetadata(BaseModel):
    """Catalog metadata entry for an executed or ingested performance test run."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique run identifier (e.g. run_20260909_120000)")
    tool: str = Field(default="jmeter", description="jmeter, blazemeter, neoload")
    ingestion: str = Field(default="local", description="local, direct_api, mcp, file_upload")
    jmx_name: str = Field(default="Scenario", description="Test plan or script name")
    timestamp: str = Field(..., description="Human-readable execution timestamp")
    epoch: int = Field(default=0, description="Unix timestamp of test execution")
    users: int = Field(default=1, description="Total configured virtual users")
    duration: str = Field(default="0", description="Configured duration")
    rampup: str = Field(default="0", description="Configured ramp-up")
    total_samples: int = Field(default=0, description="Total HTTP/transaction samples")
    avg_rt: float = Field(default=0.0, description="Average response time in ms")
    p95_rt: float = Field(default=0.0, description="95th percentile response time in ms")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    throughput: float = Field(default=0.0, description="Throughput in TPS")
    duration_sec: float = Field(default=0.0, description="Actual execution duration in seconds")
    has_azure: bool = Field(default=False, description="Whether server metrics were recorded")
    has_ai_insights: bool = Field(default=False, description="Whether AI insights were generated")
    report_file: Optional[str] = Field(default=None, description="HTML report filename")
    result_file: Optional[str] = Field(default=None, description="Result JSON filename")
    status: str = Field(default="passed", description="'passed', 'warning', 'failed'")
    notes: Optional[str] = None


class RunCatalog(BaseModel):
    """List of all registered historical test runs."""
    model_config = ConfigDict(extra="ignore")

    runs: List[TestRunMetadata] = Field(default_factory=list)
