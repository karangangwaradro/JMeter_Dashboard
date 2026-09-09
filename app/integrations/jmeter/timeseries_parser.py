"""
timeseries_parser.py — Converts JMeter JTL log data into a typed TimeSeriesResult.
Responsible ONLY for time-series extraction and bucketing.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import TimeSeriesParser
from app.domain.models.timeseries import TimeSeriesResult, LabelTimeSeries
from app.integrations.jmeter.result_reader import jmeter_result_reader


def _pct(lst: List[int], p: float) -> int:
    if not lst:
        return 0
    idx = max(0, int(len(lst) * p / 100) - 1)
    return lst[idx]


def _get_col(row_dict: dict, key_name: str, default: Any = "") -> Any:
    if key_name in row_dict:
        return row_dict[key_name]
    for k, v in row_dict.items():
        if k and k.lower() == key_name.lower():
            return v
    return default


def _is_transaction(lbl: str) -> bool:
    u = (lbl or "").upper()
    if "_R_" in u or "_R0" in u or "_R1" in u or u.startswith("HTTP_") or u.startswith("GET_") or u.startswith("POST_"):
        return False
    return bool(u.startswith("TC") or u.startswith("T_") or u.startswith("T-") or "LAUNCH" in u or "SELECT" in u or "SEARCH" in u or "SIGN" in u or "CHECKOUT" in u)


class JMeterTimeSeriesParser(TimeSeriesParser):
    """Translates raw JTL sample records into a typed TimeSeriesResult."""

    def parse_timeseries(self, raw_data: Union[Path, str, List[Dict[str, Any]]], test_id: str) -> TimeSeriesResult:
        """Parses JTL rows into a validated TimeSeriesResult model."""
        try:
            if isinstance(raw_data, (str, Path)):
                rows = jmeter_result_reader.read_rows(Path(raw_data))
            elif isinstance(raw_data, list):
                rows = raw_data
            else:
                raise ParserError(f"Unsupported raw_data type for JTL time-series parsing: {type(raw_data)}")

            if not rows:
                now = datetime.now(timezone.utc)
                return TimeSeriesResult(
                    test_id=test_id,
                    tool="jmeter",
                    start_time=now,
                    end_time=now,
                    interval_seconds=10,
                )

            timestamps = []
            for r in rows:
                try:
                    ts = int(_get_col(r, "timeStamp", 0))
                    if ts > 0:
                        timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

            start_ts = min(timestamps) if timestamps else int(datetime.now(timezone.utc).timestamp() * 1000)
            end_ts = max(timestamps) if timestamps else start_ts + 1000

            duration_sec = (end_ts - start_ts) / 1000 if end_ts > start_ts else 1
            bucket_sec = 10 if duration_sec <= 300 else 60
            bucket_ms = bucket_sec * 1000

            buckets: Dict[int, Dict[str, Any]] = {}
            label_buckets: Dict[str, Dict[int, Dict[str, Any]]] = {}

            # First pass: bucket by transaction
            for r in rows:
                try:
                    t_val = int(_get_col(r, "timeStamp", 0))
                    e_val = int(_get_col(r, "elapsed", 0))
                    lbl_val = _get_col(r, "label", "Total")
                    s_val = str(_get_col(r, "success", "true")).lower() == "true"

                    if t_val > 0:
                        b_idx = max(0, int((t_val - start_ts) // bucket_ms))

                        # Per-label tracking
                        if lbl_val not in label_buckets:
                            label_buckets[lbl_val] = {}
                        if b_idx not in label_buckets[lbl_val]:
                            label_buckets[lbl_val][b_idx] = {"elapsed": [], "errors": 0, "count": 0}
                        label_buckets[lbl_val][b_idx]["elapsed"].append(e_val)
                        label_buckets[lbl_val][b_idx]["count"] += 1
                        if not s_val:
                            label_buckets[lbl_val][b_idx]["errors"] += 1
                except Exception:
                    pass

            # Overall buckets: prioritize transaction controllers if present
            has_tc_rows = any(_is_transaction(k) for k in label_buckets.keys())
            for r in rows:
                try:
                    t_val = int(_get_col(r, "timeStamp", 0))
                    e_val = int(_get_col(r, "elapsed", 0))
                    lbl_val = _get_col(r, "label", "Total")
                    s_val = str(_get_col(r, "success", "true")).lower() == "true"

                    if t_val > 0:
                        is_tc = _is_transaction(lbl_val)
                        if not has_tc_rows or is_tc:
                            b_idx = max(0, int((t_val - start_ts) // bucket_ms))
                            if b_idx not in buckets:
                                buckets[b_idx] = {"elapsed": [], "errors": 0, "count": 0, "threads": []}
                            buckets[b_idx]["elapsed"].append(e_val)
                            buckets[b_idx]["count"] += 1
                            try:
                                th_val = int(_get_col(r, "allThreads", 0))
                                if th_val > 0:
                                    buckets[b_idx]["threads"].append(th_val)
                            except (ValueError, TypeError):
                                pass
                            if not s_val:
                                buckets[b_idx]["errors"] += 1
                except Exception:
                    pass

            total_buckets = (max(buckets.keys()) + 1) if buckets else max(1, int(duration_sec // bucket_sec) + 1)

            bucket_labels = []
            ts_avg_rt = []
            ts_p95_rt = []
            ts_p99_rt = []
            ts_throughput = []
            ts_errors = []
            ts_active_threads = []

            for idx in range(total_buckets):
                if bucket_sec == 10:
                    sec_val = (idx + 1) * 10
                    bucket_labels.append(f"{sec_val}s" if sec_val < 60 else f"{sec_val//60}m{sec_val%60}s" if sec_val % 60 else f"{sec_val//60}m")
                else:
                    bucket_labels.append(f"{idx + 1}m")

                bdata = buckets.get(idx)
                if bdata and bdata["elapsed"]:
                    bdata["elapsed"].sort()
                    blen = len(bdata["elapsed"])
                    ts_avg_rt.append(round(sum(bdata["elapsed"]) / blen, 2))
                    ts_p95_rt.append(float(_pct(bdata["elapsed"], 95)))
                    ts_p99_rt.append(float(_pct(bdata["elapsed"], 99)))
                    ts_throughput.append(round(bdata["count"] / float(bucket_sec), 2))
                    ts_errors.append(bdata["errors"])
                    th_list = bdata.get("threads", [])
                    ts_active_threads.append(max(th_list) if th_list else (ts_active_threads[-1] if ts_active_threads else 0))
                else:
                    ts_avg_rt.append(ts_avg_rt[-1] if ts_avg_rt else 0.0)
                    ts_p95_rt.append(ts_p95_rt[-1] if ts_p95_rt else 0.0)
                    ts_p99_rt.append(ts_p99_rt[-1] if ts_p99_rt else 0.0)
                    ts_throughput.append(0.0)
                    ts_errors.append(0)
                    ts_active_threads.append(ts_active_threads[-1] if ts_active_threads else 0)

            # Build label_series map
            label_series: Dict[str, LabelTimeSeries] = {}
            for lname, lb_dict in label_buckets.items():
                l_avg, l_p95, l_p99, l_tps, l_err = [], [], [], [], []
                for idx in range(total_buckets):
                    lbdata = lb_dict.get(idx)
                    if lbdata and lbdata["elapsed"]:
                        lbdata["elapsed"].sort()
                        lblen = len(lbdata["elapsed"])
                        l_avg.append(round(sum(lbdata["elapsed"]) / lblen, 2))
                        l_p95.append(float(_pct(lbdata["elapsed"], 95)))
                        l_p99.append(float(_pct(lbdata["elapsed"], 99)))
                        l_tps.append(round(lbdata["count"] / float(bucket_sec), 2))
                        l_err.append(lbdata["errors"])
                    else:
                        l_avg.append(0.0)
                        l_p95.append(0.0)
                        l_p99.append(0.0)
                        l_tps.append(0.0)
                        l_err.append(0)

                label_series[lname] = LabelTimeSeries(
                    label=lname,
                    avg_rt=l_avg,
                    p95_rt=l_p95,
                    p99_rt=l_p99,
                    throughput=l_tps,
                    errors=l_err,
                )

            start_dt = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
            end_dt = datetime.fromtimestamp(end_ts / 1000, tz=timezone.utc)

            return TimeSeriesResult(
                schema_version="1.0",
                test_id=test_id,
                tool="jmeter",
                start_time=start_dt,
                end_time=end_dt,
                interval_seconds=bucket_sec,
                bucket_labels=bucket_labels,
                avg_response_time=ts_avg_rt,
                p95_response_time=ts_p95_rt,
                p99_response_time=ts_p99_rt,
                throughput=ts_throughput,
                errors=ts_errors,
                active_threads=ts_active_threads,
                label_series=label_series,
            )
        except Exception as e:
            raise ParserError(f"Failed to parse JMeter time-series: {e}", context={"test_id": test_id})


# Global singleton instance
jmeter_timeseries_parser = JMeterTimeSeriesParser()
