#!/usr/bin/env python3
"""
azure_monitor.py — Azure Monitor Metrics Collector for PerfPilot.

Collects server-side infrastructure metrics from Azure Monitor
during a test execution window. Supports VMs, App Services, and AKS.

Uses azure-identity DefaultAzureCredential (supports az login, Service Principal,
Managed Identity) and azure-monitor-query MetricsQueryClient.

If Azure is not configured, returns an empty structure gracefully.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

_ROOT_DIR = Path(__file__).parent.parent.resolve()
_RESULTS_DIR = _ROOT_DIR / "Results"


def _load_env():
    """Load environment variables from config/.env if not already set."""
    env_path = _ROOT_DIR / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key and val and key not in os.environ:
                    os.environ[key] = val


def _parse_mock_metrics(mock_data):
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
        if not timeseries: continue
        
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
            "avg_response_time_ms": round(app_avg_rt, 2)
        },
        "resources_queried": [{"resource_id": "mock_resource", "type": "mock", "metrics_queried": len(values)}]
    }

def _empty_result():
    """Return an empty Azure metrics structure for graceful fallback.
       If mock_azure_metrics.json exists, return parsed mock metrics instead.
    """
    mock_path = _ROOT_DIR / "python_files" / "mock_azure_metrics.json"
    if mock_path.exists():
        try:
            with open(mock_path, "r") as f:
                mock_data = json.load(f)
            return _parse_mock_metrics(mock_data)
        except Exception as e:
            print(f"[Azure] Error loading mock metrics: {e}")
            
    return {
        "configured": False,
        "infra_summary": {},
        "time_series": {},
        "app_service": {},
        "resources_queried": []
    }


def collect_azure_metrics(start_epoch: int, end_epoch: int, run_id: str = "") -> dict:
    """
    Collect Azure Monitor metrics for the given time window.

    Args:
        start_epoch: Unix timestamp for start of test
        end_epoch: Unix timestamp for end of test
        run_id: Optional identifier for this run

    Returns:
        dict with infra_summary, time_series, app_service data.
        Returns empty structure if Azure is not configured.
    """
    _load_env()

    resource_ids_str = os.environ.get("AZURE_RESOURCE_IDS", "").strip()
    if not resource_ids_str:
        return _empty_result()

    resource_ids = [r.strip() for r in resource_ids_str.split(",") if r.strip()]
    if not resource_ids:
        return _empty_result()

    try:
        # pyrefly: ignore [missing-import]
        from azure.identity import DefaultAzureCredential
        # pyrefly: ignore [missing-import]
        from azure.monitor.query import MetricsQueryClient, MetricAggregationType
    except ImportError:
        print("[Azure] azure-identity or azure-monitor-query not installed. Run: pip install azure-identity azure-monitor-query", flush=True)
        return _empty_result()

    try:
        credential = DefaultAzureCredential()
        client = MetricsQueryClient(credential)
    except Exception as auth_err:
        print(f"[Azure] Authentication failed: {auth_err}", flush=True)
        return _empty_result()

    start_dt = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(end_epoch, tz=timezone.utc)
    # Add buffer of 2 minutes on each side
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
            # Determine resource type and appropriate metrics
            if "microsoft.compute/virtualmachines" in resource_lower:
                metrics_to_query = [
                    "Percentage CPU",
                    "Available Memory Bytes",
                    "Network In Total",
                    "Network Out Total",
                    "Disk Read Operations/Sec",
                    "Disk Write Operations/Sec"
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
                    "BytesSent"
                ]
                resource_type = "appservice"
            elif "microsoft.containerservice/managedclusters" in resource_lower:
                metrics_to_query = [
                    "node_cpu_usage_percentage",
                    "node_memory_rss_percentage",
                    "kube_pod_status_ready"
                ]
                resource_type = "aks"
            else:
                # Generic — try common VM metrics
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
                    MetricAggregationType.TOTAL
                ]
            )

            resources_queried.append({
                "resource_id": resource_id,
                "type": resource_type,
                "metrics_queried": len(metrics_to_query)
            })

            for metric in response.metrics:
                metric_name = metric.name.lower()
                for ts_elem in metric.timeseries:
                    for data_point in ts_elem.data:
                        val = data_point.average or data_point.total or 0

                        if "cpu" in metric_name:
                            all_cpu.append(val)
                            ts_cpu.append(val)
                            if data_point.timestamp:
                                ts_timestamps.append(data_point.timestamp.isoformat())
                        elif "memory" in metric_name or "mem" in metric_name:
                            # Convert bytes to percentage for VMs (assume 16GB baseline)
                            if "bytes" in metric_name and val > 100:
                                val = max(0, 100 - (val / (16 * 1024**3) * 100))
                            all_memory.append(val)
                            ts_memory.append(val)
                        elif "network in" in metric_name or "bytesreceived" in metric_name:
                            all_network_in.append(val / 1024 / 1024)  # Convert to MB
                            ts_network_in.append(val / 1024 / 1024)
                        elif "network out" in metric_name or "bytessent" in metric_name:
                            all_network_out.append(val / 1024 / 1024)
                            ts_network_out.append(val / 1024 / 1024)
                        elif "disk read" in metric_name:
                            all_disk_read.append(val)
                        elif "disk write" in metric_name:
                            all_disk_write.append(val)
                        elif "http2xx" in metric_name:
                            http_2xx += int(data_point.total or 0)
                        elif "http4xx" in metric_name:
                            http_4xx += int(data_point.total or 0)
                        elif "http5xx" in metric_name:
                            http_5xx += int(data_point.total or 0)
                        elif "responsetime" in metric_name:
                            if val > 0:
                                app_avg_rt = val * 1000  # Convert to ms

        except Exception as resource_err:
            print(f"[Azure] Error querying resource {resource_id}: {resource_err}", flush=True)
            resources_queried.append({
                "resource_id": resource_id,
                "type": "error",
                "error": str(resource_err)
            })

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    def safe_max(lst):
        return round(max(lst), 2) if lst else 0

    result = {
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
            "timestamps": ts_timestamps[:60],  # Cap at 60 data points
            "cpu": ts_cpu[:60],
            "memory": ts_memory[:60],
            "network_in": ts_network_in[:60],
            "network_out": ts_network_out[:60],
        },
        "app_service": {
            "http_2xx": http_2xx,
            "http_4xx": http_4xx,
            "http_5xx": http_5xx,
            "avg_response_time_ms": round(app_avg_rt, 2)
        },
        "resources_queried": resources_queried
    }

    # Save raw data locally
    if run_id:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        azure_path = _RESULTS_DIR / f"azure_{run_id}.json"
        azure_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result
