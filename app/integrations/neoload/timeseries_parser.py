"""
timeseries_parser.py — Converts NeoLoad points timeline data into a typed TimeSeriesResult.
Responsible ONLY for normalizing NeoLoad time-series data into the common contract.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import TimeSeriesParser
from app.domain.models.timeseries import TimeSeriesResult, LabelTimeSeries


class NeoLoadTimeSeriesParser(TimeSeriesParser):
    """Translates NeoLoad points timeline records into a typed TimeSeriesResult."""

    def parse_timeseries(self, raw_data: Union[Path, str, Dict[str, Any]], test_id: str) -> TimeSeriesResult:
        try:
            if isinstance(raw_data, (str, Path)):
                import json
                payload = json.loads(Path(raw_data).read_text(encoding="utf-8"))
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid raw_data type for NeoLoad timeseries: {type(raw_data)}")

            points = payload.get("points", payload if isinstance(payload, list) else [])
            if isinstance(points, dict) and "points" in points:
                points = points["points"]

            bucket_labels: List[str] = []
            avg_rt: List[float] = []
            p95_rt: List[float] = []
            p99_rt: List[float] = []
            throughput: List[float] = []
            errors: List[int] = []
            active_threads: List[int] = []
            label_series: Dict[str, LabelTimeSeries] = {}

            start_epoch = 0
            end_epoch = 0

            if isinstance(points, list):
                for idx, pt in enumerate(points):
                    sec_val = (idx + 1) * 10
                    bucket_labels.append(f"{sec_val}s" if sec_val < 60 else f"{sec_val//60}m{sec_val%60}s" if sec_val % 60 else f"{sec_val//60}m")

                    # NeoLoad duration fields
                    dur = float(pt.get("durationAverage", pt.get("avgDuration", pt.get("avg_rt", 0.0))))
                    p95 = float(pt.get("durationP95", pt.get("p95", dur * 1.4)))
                    p99 = float(pt.get("durationP99", pt.get("p99", dur * 1.8)))
                    tps = float(pt.get("throughput", pt.get("rate", pt.get("count", 0.0))))
                    err = int(pt.get("errorCount", pt.get("errors", 0)))
                    th = int(pt.get("userCount", pt.get("users", 1)))

                    avg_rt.append(round(dur, 2))
                    p95_rt.append(round(p95, 2))
                    p99_rt.append(round(p99, 2))
                    throughput.append(round(tps, 2))
                    errors.append(err)
                    active_threads.append(th)

                    ts_val = int(pt.get("from", pt.get("timestamp", 0)))
                    if ts_val > 0:
                        ts_sec = ts_val // 1000 if ts_val > 1e11 else ts_val
                        if start_epoch == 0 or ts_sec < start_epoch:
                            start_epoch = ts_sec
                        if ts_sec > end_epoch:
                            end_epoch = ts_sec

            # Process transaction elements for per-label data if available
            elements = payload.get("elements", [])
            if isinstance(elements, list):
                for el in elements:
                    lbl = el.get("name", el.get("path", "Transaction"))
                    l_avg = [float(el.get("durationAverage", 0.0))] * len(bucket_labels) if bucket_labels else []
                    l_p95 = [float(el.get("durationP95", el.get("durationAverage", 0.0) * 1.4))] * len(bucket_labels) if bucket_labels else []
                    l_p99 = [float(el.get("durationP99", el.get("durationAverage", 0.0) * 1.8))] * len(bucket_labels) if bucket_labels else []
                    l_tps = [round(float(el.get("count", 0)) / max(1, len(bucket_labels)), 2)] * len(bucket_labels) if bucket_labels else []
                    l_err = [int(el.get("errorCount", 0))] * len(bucket_labels) if bucket_labels else []

                    label_series[lbl] = LabelTimeSeries(
                        label=lbl,
                        avg_rt=l_avg,
                        p95_rt=l_p95,
                        p99_rt=l_p99,
                        throughput=l_tps,
                        errors=l_err,
                    )

            now = datetime.now(timezone.utc)
            start_dt = datetime.fromtimestamp(start_epoch, tz=timezone.utc) if start_epoch else now
            end_dt = datetime.fromtimestamp(end_epoch, tz=timezone.utc) if end_epoch else now

            return TimeSeriesResult(
                schema_version="1.0",
                test_id=test_id,
                tool="neoload",
                start_time=start_dt,
                end_time=end_dt,
                interval_seconds=10,
                bucket_labels=bucket_labels,
                avg_response_time=avg_rt,
                p95_response_time=p95_rt,
                p99_response_time=p99_rt,
                throughput=throughput,
                errors=errors,
                active_threads=active_threads,
                label_series=label_series,
            )
        except Exception as e:
            raise ParserError(f"Failed to parse NeoLoad time-series: {e}", context={"test_id": test_id})


# Global singleton
neoload_timeseries_parser = NeoLoadTimeSeriesParser()
