"""
parser.py — Normalizes Prometheus query responses into typed ServerMetrics.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Union
from pathlib import Path
import json

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import ServerMetricsParser
from app.domain.models.server_metrics import (
    ServerMetrics,
    InfraSummary,
    ServerMetricPoint,
)


class PrometheusServerMetricsParser(ServerMetricsParser):
    """Parses Prometheus API responses into the typed ServerMetrics contract."""

    def parse_server_metrics(self, raw_data: Union[Path, str, Dict[str, Any]]) -> ServerMetrics:
        try:
            if isinstance(raw_data, (str, Path)):
                payload = json.loads(Path(raw_data).read_text(encoding="utf-8"))
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid Prometheus raw data: {type(raw_data)}")

            cpu_vals: List[float] = []
            mem_vals: List[float] = []
            timestamps: List[str] = []
            points: List[ServerMetricPoint] = []

            # Process Prometheus matrix result
            results = payload.get("data", {}).get("result", [])
            for res in results:
                metric_name = res.get("metric", {}).get("__name__", "cpu").lower()
                instance = res.get("metric", {}).get("instance", "default")
                values = res.get("values", [])

                for item in values:
                    if len(item) >= 2:
                        ts_epoch = float(item[0])
                        val = float(item[1])
                        dt = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
                        ts_str = dt.isoformat()

                        if "cpu" in metric_name or "rate" in metric_name:
                            cpu_vals.append(round(val * 100 if val <= 1.0 else val, 2))
                            if ts_str not in timestamps:
                                timestamps.append(ts_str)
                            points.append(ServerMetricPoint(timestamp=dt, host=instance, metric="cpu", value=val, unit="%"))
                        elif "mem" in metric_name:
                            mem_vals.append(round(val, 2))
                            points.append(ServerMetricPoint(timestamp=dt, host=instance, metric="memory", value=val, unit="%"))

            def _safe_avg(lst: List[float]) -> float:
                return round(sum(lst) / len(lst), 2) if lst else 0.0

            def _safe_max(lst: List[float]) -> float:
                return round(max(lst), 2) if lst else 0.0

            summary = InfraSummary(
                avg_cpu=_safe_avg(cpu_vals),
                max_cpu=_safe_max(cpu_vals),
                avg_memory=_safe_avg(mem_vals),
                max_memory=_safe_max(mem_vals),
            )

            time_series = {
                "cpu": cpu_vals,
                "memory": mem_vals,
                "network_in": [],
                "network_out": [],
            }

            return ServerMetrics(
                schema_version="1.0",
                provider="prometheus",
                configured=True,
                infra_summary=summary,
                points=points,
                time_series=time_series,
                timestamps=timestamps,
                resources_queried=[{"provider": "prometheus", "targets": len(results)}],
            )
        except Exception as e:
            raise ParserError(f"Failed to parse Prometheus metrics: {e}")


# Global singleton
prometheus_metrics_parser = PrometheusServerMetricsParser()
