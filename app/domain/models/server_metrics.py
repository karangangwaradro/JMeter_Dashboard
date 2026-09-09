"""
server_metrics.py — Strongly typed domain model for server-side infrastructure metrics.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class ServerMetricPoint(BaseModel):
    """Discrete server infrastructure measurement."""
    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    host: Optional[str] = None
    metric: str
    value: float
    unit: str = ""


class InfraSummary(BaseModel):
    """High-level summary averages and peaks for key system resources."""
    model_config = ConfigDict(extra="ignore")

    avg_cpu: float = Field(default=0.0, description="Average CPU utilization percentage")
    max_cpu: float = Field(default=0.0, description="Peak CPU utilization percentage")
    avg_memory: float = Field(default=0.0, description="Average memory utilization percentage")
    max_memory: float = Field(default=0.0, description="Peak memory utilization percentage")
    avg_network_in_mbps: float = Field(default=0.0, description="Average inbound network bandwidth in Mbps")
    avg_network_out_mbps: float = Field(default=0.0, description="Average outbound network bandwidth in Mbps")
    avg_disk_read_iops: float = Field(default=0.0, description="Average disk read operations/sec")
    avg_disk_write_iops: float = Field(default=0.0, description="Average disk write operations/sec")
    http_5xx_errors: int = Field(default=0, description="Server-side 5xx error count")
    app_avg_rt_ms: float = Field(default=0.0, description="Application server average response time in ms")


class ServerMetrics(BaseModel):
    """
    Common normalized contract for server-side infrastructure metrics
    (Azure Monitor, Prometheus, Grafana, CloudWatch, CSV, etc.).
    """
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0", description="Contract schema version")
    provider: str = Field(default="unknown", description="Telemetry provider (e.g. azure_monitor, prometheus, csv)")
    configured: bool = Field(default=True, description="Whether telemetry was successfully configured and collected")
    infra_summary: InfraSummary = Field(default_factory=InfraSummary)
    points: List[ServerMetricPoint] = Field(default_factory=list, description="Raw discrete data points")
    time_series: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Metric name -> bucketed metric array aligned with test window (e.g. cpu, memory, network_in)"
    )
    timestamps: List[str] = Field(default_factory=list, description="ISO timestamp labels corresponding to time_series arrays")
    resources_queried: List[Dict[str, Any]] = Field(default_factory=list, description="List of monitored hosts/resources")
