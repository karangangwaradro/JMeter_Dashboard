"""
parser.py — Normalizes CSV server metrics files into typed ServerMetrics.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union
import csv

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import ServerMetricsParser
from app.domain.models.server_metrics import (
    ServerMetrics,
    InfraSummary,
    ServerMetricPoint,
)


class CSVServerMetricsParser(ServerMetricsParser):
    """Parses standard CSV infrastructure telemetry into the typed ServerMetrics contract."""

    def parse_server_metrics(self, raw_data: Union[Path, str]) -> ServerMetrics:
        file_path = Path(raw_data)
        if not file_path.exists():
            raise ParserError(f"Server metrics CSV not found: {file_path}")

        try:
            timestamps: List[str] = []
            cpu_vals: List[float] = []
            mem_vals: List[float] = []
            net_in_vals: List[float] = []
            net_out_vals: List[float] = []
            points: List[ServerMetricPoint] = []

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts_val = row.get("timestamp", row.get("Time", row.get("timeStamp", "")))
                    if not ts_val:
                        ts_val = datetime.now(timezone.utc).isoformat()
                    timestamps.append(ts_val)

                    try:
                        dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                    except Exception:
                        dt = datetime.now(timezone.utc)

                    cpu = float(row.get("cpu", row.get("CPU", row.get("cpu_percent", 0.0))))
                    mem = float(row.get("memory", row.get("Memory", row.get("mem_percent", 0.0))))
                    net_in = float(row.get("network_in", row.get("NetIn", 0.0)))
                    net_out = float(row.get("network_out", row.get("NetOut", 0.0)))

                    cpu_vals.append(cpu)
                    mem_vals.append(mem)
                    net_in_vals.append(net_in)
                    net_out_vals.append(net_out)

                    host = row.get("host", row.get("Host", "server1"))
                    points.append(ServerMetricPoint(timestamp=dt, host=host, metric="cpu", value=cpu, unit="%"))
                    points.append(ServerMetricPoint(timestamp=dt, host=host, metric="memory", value=mem, unit="%"))

            def _safe_avg(lst: List[float]) -> float:
                return round(sum(lst) / len(lst), 2) if lst else 0.0

            def _safe_max(lst: List[float]) -> float:
                return round(max(lst), 2) if lst else 0.0

            summary = InfraSummary(
                avg_cpu=_safe_avg(cpu_vals),
                max_cpu=_safe_max(cpu_vals),
                avg_memory=_safe_avg(mem_vals),
                max_memory=_safe_max(mem_vals),
                avg_network_in_mbps=_safe_avg(net_in_vals),
                avg_network_out_mbps=_safe_avg(net_out_vals),
            )

            return ServerMetrics(
                schema_version="1.0",
                provider="csv",
                configured=True,
                infra_summary=summary,
                points=points,
                time_series={
                    "cpu": cpu_vals,
                    "memory": mem_vals,
                    "network_in": net_in_vals,
                    "network_out": net_out_vals,
                },
                timestamps=timestamps,
                resources_queried=[{"provider": "csv", "source": file_path.name}],
            )
        except Exception as e:
            raise ParserError(f"Failed to parse CSV server metrics: {e}", context={"file": file_path.name})


# Global singleton
csv_metrics_parser = CSVServerMetricsParser()
