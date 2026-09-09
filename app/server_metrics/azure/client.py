"""
client.py — Azure Monitor metrics collector for PerfPilot.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.constants import ROOT_DIR, CONFIG_DIR
from app.core.config import load_env_file
from app.server_metrics.azure.parser import _parse_mock_metrics


def _empty_result() -> dict:
    """Return an empty Azure metrics structure for graceful fallback."""
    mock_paths = [
        ROOT_DIR / "app" / "server_metrics" / "azure" / "mock_azure_metrics.json",
        ROOT_DIR / "data" / "mock_azure_metrics.json",
    ]
    for mock_path in mock_paths:
        if mock_path.exists():
            try:
                with open(mock_path, "r", encoding="utf-8") as f:
                    mock_data = json.load(f)
                return _parse_mock_metrics(mock_data)
            except Exception:
                pass

    return {
        "configured": False,
        "infra_summary": {},
        "time_series": {},
        "app_service": {},
        "resources_queried": [],
    }


def collect_azure_metrics(start_epoch: int, end_epoch: int, run_id: str = "") -> dict:
    """
    Collect Azure Monitor metrics for the given time window.
    """
    load_env_file()

    resource_ids_str = os.environ.get("AZURE_RESOURCE_IDS", "").strip()
    if not resource_ids_str:
        return _empty_result()

    resource_ids = [r.strip() for r in resource_ids_str.split(",") if r.strip()]
    if not resource_ids:
        return _empty_result()

    try:
        from azure.identity import DefaultAzureCredential
        from azure.monitor.query import MetricsQueryClient, MetricAggregationType
    except ImportError:
        print("[Azure] azure-identity or azure-monitor-query not installed.", flush=True)
        return _empty_result()

    try:
        credential = DefaultAzureCredential()
        client = MetricsQueryClient(credential)
    except Exception as auth_err:
        print(f"[Azure] Authentication failed: {auth_err}", flush=True)
        return _empty_result()

    start_dt = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(end_epoch, tz=timezone.utc)
    start_dt -= timedelta(minutes=2)
    end_dt += timedelta(minutes=2)
    timespan = (start_dt, end_dt)

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
    http_2xx = 0
    http_4xx = 0
    http_5xx = 0
    app_avg_rt = 0
    resources_queried = []

    for resource_id in resource_ids:
        resource_lower = resource_id.lower()
        try:
            if "microsoft.compute/virtualmachines" in resource_lower:
                metrics_to_query = [
                    "Percentage CPU",
                    "Available Memory Bytes",
                    "Network In Total",
                    "Network Out Total",
                    "Disk Read Operations/Sec",
                    "Disk Write Operations/Sec",
                ]
                resource_type = "vm"
            elif "microsoft.web/sites" in resource_lower:
                metrics_to_query = [
                    "CpuPercentage",
                    "MemoryPercentage",
                    "HttpResponseTime",
                    "Http2xx",
                    "Http4xx",
                    "Http5xx",
                    "BytesReceived",
                    "BytesSent",
                ]
                resource_type = "appservice"
            elif "microsoft.containerservice/managedclusters" in resource_lower:
                metrics_to_query = [
                    "node_cpu_usage_percentage",
                    "node_memory_rss_percentage",
                    "kube_pod_status_ready",
                ]
                resource_type = "aks"
            else:
                metrics_to_query = ["Percentage CPU", "Available Memory Bytes"]
                resource_type = "generic"

            response = client.query_resource(
                resource_uri=resource_id,
                metric_names=metrics_to_query,
                timespan=timespan,
                granularity=timedelta(minutes=1),
                aggregations=[
                    MetricAggregationType.AVERAGE,
                    MetricAggregationType.MAXIMUM,
                    MetricAggregationType.TOTAL,
                ],
            )

            for metric in response.metrics:
                m_name = metric.name.lower()
                for ts in metric.timeseries:
                    for dp in ts.data:
                        val = dp.average if dp.average is not None else dp.total or 0
                        ts_str = dp.time_stamp.isoformat() if dp.time_stamp else ""

                        if "cpu" in m_name:
                            all_cpu.append(val)
                            ts_cpu.append(round(val, 2))
                            if ts_str and ts_str not in ts_timestamps:
                                ts_timestamps.append(ts_str)
                        elif "memory" in m_name:
                            all_memory.append(val)
                            ts_memory.append(round(val, 2))
                        elif "network in" in m_name or "bytesreceived" in m_name:
                            mbps = val / 1024 / 1024
                            all_network_in.append(mbps)
                            ts_network_in.append(round(mbps, 2))
                        elif "network out" in m_name or "bytessent" in m_name:
                            mbps = val / 1024 / 1024
                            all_network_out.append(mbps)
                            ts_network_out.append(round(mbps, 2))
                        elif "disk read" in m_name:
                            all_disk_read.append(val)
                        elif "disk write" in m_name:
                            all_disk_write.append(val)
                        elif "http2xx" in m_name:
                            http_2xx += int(val)
                        elif "http4xx" in m_name:
                            http_4xx += int(val)
                        elif "http5xx" in m_name:
                            http_5xx += int(val)
                        elif "responsetime" in m_name:
                            app_avg_rt = val

            resources_queried.append({
                "resource_id": resource_id,
                "type": resource_type,
                "metrics_queried": len(metrics_to_query),
            })
        except Exception as q_err:
            print(f"[Azure] Query failed for {resource_id}: {q_err}", flush=True)

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    def safe_max(lst):
        return round(max(lst), 2) if lst else 0

    return {
        "configured": bool(all_cpu or all_memory),
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
            "http_2xx": http_2xx,
            "http_4xx": http_4xx,
            "http_5xx": http_5xx,
            "avg_response_time_ms": round(app_avg_rt, 2),
        },
        "resources_queried": resources_queried,
    }
