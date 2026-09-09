"""
aggregate_parser.py — Converts BlazeMeter aggregate reports into a typed AggregateResult.
Responsible ONLY for normalizing BlazeMeter summary and KPI statistics into the common contract.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import AggregateParser
from app.domain.models.aggregate import (
    AggregateResult,
    TransactionMetric,
    ErrorDetail,
)


class BlazeMeterAggregateParser(AggregateParser):
    """Translates BlazeMeter aggregate report responses into a typed AggregateResult."""

    def parse_aggregate(self, raw_data: Union[Path, str, Dict[str, Any]], test_id: str) -> AggregateResult:
        try:
            if isinstance(raw_data, (str, Path)):
                import json
                payload = json.loads(Path(raw_data).read_text(encoding="utf-8"))
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid raw_data type for BlazeMeter aggregate: {type(raw_data)}")

            summary_raw = payload.get("summary", payload)
            if isinstance(summary_raw, dict) and "result" in summary_raw:
                summary_raw = summary_raw["result"]

            elements = summary_raw if isinstance(summary_raw, list) else summary_raw.get("elements", summary_raw.get("reports", []))

            transactions: Dict[str, TransactionMetric] = {}
            total_requests = 0
            failed_requests = 0
            total_elapsed_weighted = 0.0
            overall_min = 9999999.0
            overall_max = 0.0
            p50_list, p90_list, p95_list, p99_list = [], [], [], []

            for item in elements:
                label = item.get("label", item.get("lbl", "Transaction"))
                samples = int(item.get("samples", item.get("count", 0)))
                errors = int(item.get("errors", item.get("errorCount", 0)))
                err_rate = float(item.get("errorPercentage", item.get("errorPct", 0.0)))
                avg_rt = float(item.get("avgResponseTime", item.get("avg", 0.0)))
                min_rt = float(item.get("minResponseTime", item.get("min", 0.0)))
                max_rt = float(item.get("maxResponseTime", item.get("max", 0.0)))
                p50 = float(item.get("medianResponseTime", item.get("p50", avg_rt)))
                p90 = float(item.get("90line", item.get("p90", avg_rt * 1.3)))
                p95 = float(item.get("95line", item.get("p95", avg_rt * 1.5)))
                p99 = float(item.get("99line", item.get("p99", avg_rt * 2.0)))

                if samples > 0:
                    total_requests += samples
                    failed_requests += errors
                    total_elapsed_weighted += (avg_rt * samples)
                    overall_min = min(overall_min, min_rt)
                    overall_max = max(overall_max, max_rt)
                    p50_list.append(p50)
                    p90_list.append(p90)
                    p95_list.append(p95)
                    p99_list.append(p99)

                transactions[label] = TransactionMetric(
                    label=label,
                    count=samples,
                    errors=errors,
                    error_rate=err_rate,
                    avg_rt=avg_rt,
                    min_rt=min_rt,
                    max_rt=max_rt,
                    p50=p50,
                    p90=p90,
                    p95=p95,
                    p99=p99,
                )

            duration_sec = float(payload.get("duration", summary_raw.get("duration", 60.0) if isinstance(summary_raw, dict) else 60.0))
            if duration_sec <= 0:
                duration_sec = 60.0

            overall_avg = round(total_elapsed_weighted / total_requests, 2) if total_requests > 0 else 0.0
            overall_err_rate = round(failed_requests / total_requests * 100, 2) if total_requests > 0 else 0.0
            throughput = round(total_requests / duration_sec, 2) if duration_sec > 0 else 0.0

            def _safe_mean(lst: List[float], fallback: float) -> float:
                return round(sum(lst) / len(lst), 2) if lst else fallback

            return AggregateResult(
                schema_version="1.0",
                test_id=test_id,
                tool="blazemeter",
                total_requests=total_requests,
                total_iterations=1,
                successful_requests=total_requests - failed_requests,
                failed_requests=failed_requests,
                error_rate=overall_err_rate,
                raw_error_rate=overall_err_rate,
                throughput=throughput,
                avg_response_time=overall_avg,
                min_response_time=overall_min if overall_min != 9999999.0 else 0.0,
                max_response_time=overall_max,
                p50=_safe_mean(p50_list, overall_avg),
                p90=_safe_mean(p90_list, overall_avg * 1.3),
                p95=_safe_mean(p95_list, overall_avg * 1.5),
                p99=_safe_mean(p99_list, overall_avg * 2.0),
                duration_seconds=duration_sec,
                start_epoch=0,
                end_epoch=int(duration_sec),
                transactions=transactions,
                transactions_by_thread_group={},
                errors_breakdown={},
            )
        except Exception as e:
            raise ParserError(f"Failed to parse BlazeMeter aggregate report: {e}", context={"test_id": test_id})


# Global singleton
blazemeter_aggregate_parser = BlazeMeterAggregateParser()
