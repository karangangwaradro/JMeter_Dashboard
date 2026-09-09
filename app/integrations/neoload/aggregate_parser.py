"""
aggregate_parser.py — Converts NeoLoad statistics and elements into a typed AggregateResult.
Responsible ONLY for normalizing NeoLoad summary metrics into the common domain contract.
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


class NeoLoadAggregateParser(AggregateParser):
    """Translates NeoLoad statistics into a typed AggregateResult."""

    def parse_aggregate(self, raw_data: Union[Path, str, Dict[str, Any]], test_id: str) -> AggregateResult:
        try:
            if isinstance(raw_data, (str, Path)):
                import json
                payload = json.loads(Path(raw_data).read_text(encoding="utf-8"))
            elif isinstance(raw_data, dict):
                payload = raw_data
            else:
                raise ParserError(f"Invalid raw_data type for NeoLoad aggregate: {type(raw_data)}")

            stats = payload.get("statistics", payload)
            elements = payload.get("elements", [])
            if not isinstance(elements, list) and isinstance(elements, dict):
                elements = elements.get("elements", [])

            transactions: Dict[str, TransactionMetric] = {}
            total_requests = int(stats.get("totalRequestCount", stats.get("count", 0)))
            failed_requests = int(stats.get("totalErrorCount", stats.get("errors", 0)))
            avg_rt = float(stats.get("totalRequestDurationAverage", stats.get("avg_rt", 0.0)))
            duration_sec = float(stats.get("totalDuration", stats.get("duration", 60.0)))
            if duration_sec <= 0:
                duration_sec = 60.0

            overall_err_rate = round(failed_requests / total_requests * 100, 2) if total_requests > 0 else 0.0
            throughput = round(total_requests / duration_sec, 2) if duration_sec > 0 else 0.0

            p50_list, p90_list, p95_list, p99_list = [], [], [], []
            min_list, max_list = [], []

            for el in elements:
                name = el.get("name", el.get("path", "Transaction"))
                count = int(el.get("count", 0))
                errors = int(el.get("errorCount", 0))
                err_rate = float(el.get("errorRate", (errors / count * 100) if count > 0 else 0.0))
                d_avg = float(el.get("durationAverage", 0.0))
                d_min = float(el.get("durationMin", 0.0))
                d_max = float(el.get("durationMax", 0.0))
                d_p50 = float(el.get("durationP50", d_avg))
                d_p90 = float(el.get("durationP90", d_avg * 1.3))
                d_p95 = float(el.get("durationP95", d_avg * 1.5))
                d_p99 = float(el.get("durationP99", d_avg * 2.0))

                if count > 0:
                    p50_list.append(d_p50)
                    p90_list.append(d_p90)
                    p95_list.append(d_p95)
                    p99_list.append(d_p99)
                    min_list.append(d_min)
                    max_list.append(d_max)

                transactions[name] = TransactionMetric(
                    label=name,
                    count=count,
                    errors=errors,
                    error_rate=err_rate,
                    avg_rt=d_avg,
                    min_rt=d_min,
                    max_rt=d_max,
                    p50=d_p50,
                    p90=d_p90,
                    p95=d_p95,
                    p99=d_p99,
                )

            # If total_requests wasn't populated from stats, sum element counts
            if total_requests == 0 and transactions:
                total_requests = sum(t.count for t in transactions.values())
                failed_requests = sum(t.errors for t in transactions.values())
                overall_err_rate = round(failed_requests / total_requests * 100, 2) if total_requests > 0 else 0.0
                throughput = round(total_requests / duration_sec, 2) if duration_sec > 0 else 0.0

            def _safe_mean(lst: List[float], fallback: float) -> float:
                return round(sum(lst) / len(lst), 2) if lst else fallback

            return AggregateResult(
                schema_version="1.0",
                test_id=test_id,
                tool="neoload",
                total_requests=total_requests,
                total_iterations=1,
                successful_requests=total_requests - failed_requests,
                failed_requests=failed_requests,
                error_rate=overall_err_rate,
                raw_error_rate=overall_err_rate,
                throughput=throughput,
                avg_response_time=avg_rt or _safe_mean([t.avg_rt for t in transactions.values()], 0.0),
                min_response_time=min(min_list) if min_list else 0.0,
                max_response_time=max(max_list) if max_list else 0.0,
                p50=_safe_mean(p50_list, avg_rt),
                p90=_safe_mean(p90_list, avg_rt * 1.3),
                p95=_safe_mean(p95_list, avg_rt * 1.5),
                p99=_safe_mean(p99_list, avg_rt * 2.0),
                duration_seconds=duration_sec,
                start_epoch=0,
                end_epoch=int(duration_sec),
                transactions=transactions,
                transactions_by_thread_group={},
                errors_breakdown={},
            )
        except Exception as e:
            raise ParserError(f"Failed to parse NeoLoad aggregate metrics: {e}", context={"test_id": test_id})


# Global singleton
neoload_aggregate_parser = NeoLoadAggregateParser()
