"""
aggregate.py — Strongly typed domain model for aggregate performance metrics.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class TransactionMetric(BaseModel):
    """Aggregated metrics for a single transaction / request label."""
    model_config = ConfigDict(extra="ignore")

    label: str
    count: int = Field(default=0, description="Total executions of this transaction")
    errors: int = Field(default=0, description="Number of failed executions")
    error_rate: float = Field(default=0.0, description="Percentage of executions that failed (0-100)")
    avg_rt: float = Field(default=0.0, description="Mean response time in ms")
    min_rt: float = Field(default=0.0, description="Minimum response time in ms")
    max_rt: float = Field(default=0.0, description="Maximum response time in ms")
    p50: float = Field(default=0.0, description="50th percentile (median) response time in ms")
    p90: float = Field(default=0.0, description="90th percentile response time in ms")
    p95: float = Field(default=0.0, description="95th percentile response time in ms")
    p99: float = Field(default=0.0, description="99th percentile response time in ms")
    samples: List[int] = Field(default_factory=list, description="Raw response time samples (optional)")
    success_flags: List[bool] = Field(default_factory=list, description="Success boolean for samples (optional)")
    item_type: str = Field(default="MAIN_TRANSACTION", description="MAIN_TRANSACTION | HTTP_REQUEST")
    item_type_label: str = Field(default="Main Transaction", description="Display label for item type")
    parent_tc: Optional[str] = Field(default=None, description="Name of parent Transaction Controller")
    depth: int = Field(default=0, description="Hierarchy depth: 0=Main, 1=Request")
    user_story: Optional[str] = Field(default=None, description="Associated Thread Group / User Story")
    child_requests: List[str] = Field(default_factory=list, description="Child HTTP request names under this transaction")


class ErrorOccurrence(BaseModel):
    """Metadata for an error sample occurrence."""
    model_config = ConfigDict(extra="ignore")

    label: str
    timestamp: int = 0
    elapsed: int = 0


class ErrorDetail(BaseModel):
    """Categorized error summary with representative occurrences."""
    model_config = ConfigDict(extra="ignore")

    error_key: str
    code: str = ""
    message: str = ""
    failure_message: str = ""
    count: int = 0
    occurrences: List[ErrorOccurrence] = Field(default_factory=list)


class AggregateResult(BaseModel):
    """
    Common normalized aggregate performance result contract across all performance tools
    (JMeter, BlazeMeter, NeoLoad, etc.).
    """
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0", description="Contract schema version")
    test_id: str = Field(..., description="Unique test run identifier")
    tool: str = Field(..., description="Performance testing tool name (e.g. jmeter, blazemeter, neoload)")
    total_requests: int = Field(default=0, description="Total sample requests executed")
    total_iterations: int = Field(default=1, description="Total complete journey iterations completed")
    successful_requests: int = Field(default=0, description="Number of successful requests")
    failed_requests: int = Field(default=0, description="Number of failed requests")
    error_rate: float = Field(default=0.0, description="Overall transaction error percentage (0-100)")
    raw_error_rate: float = Field(default=0.0, description="Raw HTTP request error percentage (0-100)")
    throughput: float = Field(default=0.0, description="Overall transactions per second (TPS)")
    avg_response_time: float = Field(default=0.0, description="Overall average response time in ms")
    min_response_time: float = Field(default=0.0, description="Overall minimum response time in ms")
    max_response_time: float = Field(default=0.0, description="Overall maximum response time in ms")
    p50: float = Field(default=0.0, description="50th percentile response time in ms")
    p90: float = Field(default=0.0, description="90th percentile response time in ms")
    p95: float = Field(default=0.0, description="95th percentile response time in ms")
    p99: float = Field(default=0.0, description="99th percentile response time in ms")
    duration_seconds: float = Field(default=0.0, description="Total test duration in seconds")
    start_epoch: int = Field(default=0, description="Unix timestamp of test start")
    end_epoch: int = Field(default=0, description="Unix timestamp of test end")

    # Transaction-level breakdown (actual transaction controllers)
    transactions: Dict[str, TransactionMetric] = Field(
        default_factory=dict,
        description="Keyed by transaction label (only transaction controllers)"
    )
    # HTTP requests breakdown
    http_requests: Dict[str, TransactionMetric] = Field(
        default_factory=dict,
        description="Keyed by HTTP request sampler label"
    )
    # Complete map of all sample labels
    all_labels: Dict[str, TransactionMetric] = Field(
        default_factory=dict,
        description="Complete map of all sample labels (transactions + requests)"
    )
    transactions_by_thread_group: Dict[str, Dict[str, TransactionMetric]] = Field(
        default_factory=dict,
        description="Thread group -> transaction label -> metrics"
    )
    hierarchy_tree: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full compiled tree: User Story -> Transaction -> Requests"
    )
    errors_breakdown: Dict[str, ErrorDetail] = Field(
        default_factory=dict,
        description="Keyed by error diagnostic key"
    )
