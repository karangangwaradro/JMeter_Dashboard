"""
timeseries_parser.py — Converts BlazeMeter timeline metrics into a typed TimeSeriesResult.
Responsible ONLY for normalizing BlazeMeter timeline data into the common domain contract.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import TimeSeriesParser
from app.domain.models.timeseries import TimeSeriesResult, LabelTimeSeries


class BlazeMeterTimeSeriesParser(TimeSeriesParser):
    """Translates BlazeMeter timeline responses into a typed TimeSeriesResult."""

    def parse_timeseries(self, raw_data: Union[Path, str, Dict[str, Any]], test_id: str) -> TimeSeriesResult:
        try:
            if isinstance(raw_data, (str, Path)):
                import json
                payload = json.loads(Path(raw_data).read_text(encoding="utf-8"))
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid raw_data type for BlazeMeter: {type(raw_data)}")

            ts_raw = payload.get("timeseries", payload)
            if isinstance(ts_raw, dict) and "result" in ts_raw:
                ts_raw = ts_raw["result"]

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

            # BlazeMeter chart points array format
            points = ts_raw if isinstance(ts_raw, list) else ts_raw.get("timeline", ts_raw.get("points", []))

            if points and isinstance(points, list):
                for idx, pt in enumerate(points):
                    sec_val = (idx + 1) * 10
                    bucket_labels.append(f"{sec_val}s" if sec_val < 60 else f"{sec_val//60}m{sec_val%60}s" if sec_val % 60 else f"{sec_val//60}m")

                    art = float(pt.get("avg_rt", pt.get("avgResponseTime", pt.get("avg", 0.0))))
                    p95 = float(pt.get("p95", pt.get("95th", art * 1.5)))
                    p99 = float(pt.get("p99", pt.get("99th", art * 2.0)))
                    tps = float(pt.get("tps", pt.get("throughput", pt.get("hits", 0.0))))
                    err = int(pt.get("errors", pt.get("errorCount", 0)))
                    th = int(pt.get("users", pt.get("threads", pt.get("activeUsers", 1))))

                    avg_rt.append(round(art, 2))
                    p95_rt.append(round(p95, 2))
                    p99_rt.append(round(p99, 2))
                    throughput.append(round(tps, 2))
                    errors.append(err)
                    active_threads.append(th)

                    ts_val = int(pt.get("timestamp", pt.get("ts", 0)))
                    if ts_val > 0:
                        if start_epoch == 0 or ts_val < start_epoch:
                            start_epoch = ts_val
                        if ts_val > end_epoch:
                            end_epoch = ts_val

            # Process per-label timeline series if present
            labels_raw = ts_raw.get("labels", {}) if isinstance(ts_raw, dict) else {}
            if isinstance(labels_raw, dict):
                for lbl_name, l_pts in labels_raw.items():
                    l_avg, l_p95, l_p99, l_tps, l_err = [], [], [], [], []
                    if isinstance(l_pts, list):
                        for pt in l_pts:
                            art = float(pt.get("avg_rt", pt.get("avgResponseTime", 0.0)))
                            l_avg.append(round(art, 2))
                            l_p95.append(float(pt.get("p95", art * 1.5)))
                            l_p99.append(float(pt.get("p99", art * 2.0)))
                            l_tps.append(float(pt.get("tps", pt.get("throughput", 0.0))))
                            l_err.append(int(pt.get("errors", 0)))
                    label_series[lbl_name] = LabelTimeSeries(
                        label=lbl_name,
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
                tool="blazemeter",
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
            raise ParserError(f"Failed to parse BlazeMeter time-series: {e}", context={"test_id": test_id})


# Global singleton
blazemeter_timeseries_parser = BlazeMeterTimeSeriesParser()
