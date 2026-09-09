"""
timeseries.py — Strongly typed domain model for performance time-series data.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TimeSeriesPoint(BaseModel):
    """A single discrete time-series metric measurement."""
    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    metric: str
    value: float
    unit: str = "ms"


class LabelTimeSeries(BaseModel):
    """Time-series arrays for an individual transaction label."""
    model_config = ConfigDict(extra="ignore")

    label: str
    avg_rt: List[float] = Field(default_factory=list, description="Average response time in ms per bucket")
    p95_rt: List[float] = Field(default_factory=list, description="95th percentile response time in ms per bucket")
    p99_rt: List[float] = Field(default_factory=list, description="99th percentile response time in ms per bucket")
    throughput: List[float] = Field(default_factory=list, description="Transactions per second per bucket")
    errors: List[int] = Field(default_factory=list, description="Error count per bucket")


class TimeSeriesResult(BaseModel):
    """
    Common normalized time-series result contract across all performance tools
    (JMeter, BlazeMeter, NeoLoad, Gatling, etc.).
    """
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0", description="Contract schema version")
    test_id: str = Field(..., description="Unique test run identifier")
    tool: str = Field(..., description="Performance testing tool name (e.g. jmeter, blazemeter, neoload)")
    start_time: datetime = Field(..., description="Test execution start time (UTC)")
    end_time: datetime = Field(..., description="Test execution end time (UTC)")
    interval_seconds: int = Field(default=10, description="Bucket interval granularity in seconds")
    
    bucket_labels: List[str] = Field(default_factory=list, description="Human-readable bucket time labels (e.g. 10s, 20s, 1m)")
    avg_response_time: List[float] = Field(default_factory=list, description="Overall average response time per bucket")
    p95_response_time: List[float] = Field(default_factory=list, description="Overall 95th percentile response time per bucket")
    p99_response_time: List[float] = Field(default_factory=list, description="Overall 99th percentile response time per bucket")
    throughput: List[float] = Field(default_factory=list, description="Overall transactions per second per bucket")
    errors: List[int] = Field(default_factory=list, description="Overall error count per bucket")
    active_threads: List[int] = Field(default_factory=list, description="Virtual user concurrency per bucket")
    
    # Per-transaction breakdowns
    label_series: Dict[str, LabelTimeSeries] = Field(
        default_factory=dict,
        description="Time-series arrays keyed by transaction label"
    )
