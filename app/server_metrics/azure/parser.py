"""
parser.py — Normalizes Azure Monitor telemetry into typed ServerMetrics.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union
import json

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import ServerMetricsParser
from app.domain.models.server_metrics import (
    ServerMetrics,
    InfraSummary,
    ServerMetricPoint,
)


class AzureServerMetricsParser(ServerMetricsParser):
    """Parses native Azure Monitor query responses into the typed ServerMetrics contract."""

    def parse_server_metrics(self, raw_data: Union[Path, str, Dict[str, Any]]) -> ServerMetrics:
        try:
            if isinstance(raw_data, (str, Path)):
                content = Path(raw_data).read_text(encoding="utf-8")
                payload = json.loads(content)
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid Azure raw_data: {type(raw_data)}")

            if not payload or not payload.get("configured", True):
                return ServerMetrics(
                    schema_version="1.0",
                    provider="azure_monitor",
                    configured=False,
                )

            summary_raw = payload.get("infra_summary", {})
            ts_raw = payload.get("time_series", {})
            app_raw = payload.get("app_service", {})
            resources = payload.get("resources_queried", [])

            infra_summary = InfraSummary(
                avg_cpu=float(summary_raw.get("avg_cpu", 0.0)),
                max_cpu=float(summary_raw.get("max_cpu", 0.0)),
                avg_memory=float(summary_raw.get("avg_memory", 0.0)),
                max_memory=float(summary_raw.get("max_memory", 0.0)),
                avg_network_in_mbps=float(summary_raw.get("avg_network_in_mbps", 0.0)),
                avg_network_out_mbps=float(summary_raw.get("avg_network_out_mbps", 0.0)),
                avg_disk_read_iops=float(summary_raw.get("avg_disk_read_iops", 0.0)),
                avg_disk_write_iops=float(summary_raw.get("avg_disk_write_iops", 0.0)),
                http_5xx_errors=int(app_raw.get("http_5xx", 0)),
                app_avg_rt_ms=float(app_raw.get("avg_response_time_ms", 0.0)),
            )

            # Standardized time-series dict
            time_series = {
                "cpu": [float(x) for x in ts_raw.get("cpu", [])],
                "memory": [float(x) for x in ts_raw.get("memory", [])],
                "network_in": [float(x) for x in ts_raw.get("network_in", [])],
                "network_out": [float(x) for x in ts_raw.get("network_out", [])],
            }
            timestamps = ts_raw.get("timestamps", [])

            # Discrete points
            points: List[ServerMetricPoint] = []
            for idx, ts_str in enumerate(timestamps):
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.now(timezone.utc)

                if idx < len(time_series["cpu"]):
                    points.append(ServerMetricPoint(timestamp=dt, metric="cpu", value=time_series["cpu"][idx], unit="%"))
                if idx < len(time_series["memory"]):
                    points.append(ServerMetricPoint(timestamp=dt, metric="memory", value=time_series["memory"][idx], unit="%"))
                if idx < len(time_series["network_in"]):
                    points.append(ServerMetricPoint(timestamp=dt, metric="network_in", value=time_series["network_in"][idx], unit="Mbps"))
                if idx < len(time_series["network_out"]):
                    points.append(ServerMetricPoint(timestamp=dt, metric="network_out", value=time_series["network_out"][idx], unit="Mbps"))

            return ServerMetrics(
                schema_version="1.0",
                provider="azure_monitor",
                configured=True,
                infra_summary=infra_summary,
                points=points,
                time_series=time_series,
                timestamps=timestamps,
                resources_queried=resources,
            )
        except Exception as e:
            raise ParserError(f"Failed to parse Azure Monitor metrics: {e}")


# Global singleton
azure_metrics_parser = AzureServerMetricsParser()


def _parse_mock_metrics(mock_data: dict) -> dict:
    """Parse mock metrics JSON for Azure reporting fallback."""
    all_cpu = []
    all_memory = []
    all_network_in = []
    all_network_out = []
    all_disk_read = []
    all_disk_write = []
    ts_timestamps = []
    ts_cpu = []
    ts_memory = []
    ts_network_in = []
    ts_network_out = []
    http_5xx = 0
    app_avg_rt = 0

    values = mock_data.get("value", [])
    for metric in values:
        metric_name = metric.get("name", {}).get("value", "").lower()
        timeseries = metric.get("timeseries", [])
        if not timeseries:
            continue

        data_points = timeseries[0].get("data", [])
        for dp in data_points:
            val = dp.get("average") or dp.get("total") or 0
            ts_str = dp.get("timeStamp", "")

            if "percentage cpu" in metric_name:
                all_cpu.append(val)
                ts_cpu.append(val)
                if ts_str not in ts_timestamps:
                    ts_timestamps.append(ts_str)
            elif "memory usage" in metric_name:
                all_memory.append(val)
                ts_memory.append(val)
            elif "network in total" in metric_name:
                all_network_in.append(val / 1024 / 1024)
                ts_network_in.append(val / 1024 / 1024)
            elif "network out total" in metric_name:
                all_network_out.append(val / 1024 / 1024)
                ts_network_out.append(val / 1024 / 1024)
            elif "disk read bytes" in metric_name:
                all_disk_read.append(val)
            elif "disk write bytes" in metric_name:
                all_disk_write.append(val)
            elif "5xx" in metric_name:
                http_5xx += int(val)
            elif "response time" in metric_name:
                app_avg_rt = val

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    def safe_max(lst):
        return round(max(lst), 2) if lst else 0

    return {
        "configured": True,
        "infra_summary": {
            "avg_cpu": safe_avg(all_cpu),
            "max_cpu": safe_max(all_cpu),
            "avg_memory": safe_avg(all_memory),
            "max_memory": safe_max(all_memory),
            "avg_network_in_mbps": safe_avg(all_network_in),
            "avg_network_out_mbps": safe_avg(all_network_out),
            "avg_disk_read_iops": safe_avg(all_disk_read),
            "avg_disk_write_iops": safe_avg(all_disk_write),
        },
        "time_series": {
            "timestamps": ts_timestamps,
            "cpu": ts_cpu,
            "memory": ts_memory,
            "network_in": ts_network_in,
            "network_out": ts_network_out,
        },
        "app_service": {
            "http_2xx": 0,
            "http_4xx": 0,
            "http_5xx": http_5xx,
            "avg_response_time_ms": round(app_avg_rt, 2),
        },
        "resources_queried": [{"resource_id": "mock_resource", "type": "mock", "metrics_queried": len(values)}],
    }
