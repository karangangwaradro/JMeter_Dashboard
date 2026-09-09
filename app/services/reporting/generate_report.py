"""
generate_report.py — Tool-agnostic performance report generator.
Consumes ONLY strongly-typed domain contracts (AggregateResult, TimeSeriesResult, ServerMetrics).
Contains ZERO vendor-specific parsing logic.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import RESULTS_HTML_DIR
from app.core.exceptions import ReportGenerationError
from app.core.logging import logger
from app.domain.interfaces.report_generator import ReportGeneratorInterface
from app.domain.models.aggregate import AggregateResult
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.server_metrics import ServerMetrics


class DomainReportGenerator(ReportGeneratorInterface):
    """
    Synthesizes standalone interactive HTML reports from normalized domain contracts.
    Completely decoupled from JMeter, BlazeMeter, or NeoLoad internals.
    """

    def generate(
        self,
        aggregate: AggregateResult,
        timeseries: TimeSeriesResult,
        server_metrics: Optional[ServerMetrics] = None,
        ai_insights: Optional[Dict[str, Any]] = None,
        output_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Builds the standalone HTML performance dashboard consuming strictly normalized models.
        """
        options = options or {}
        run_id = aggregate.test_id
        test_name = options.get("test_name", options.get("jmx_name", f"{aggregate.tool.upper()}_{run_id}"))
        users = options.get("users", aggregate.total_iterations or 1)

        if not output_path:
            RESULTS_HTML_DIR.mkdir(parents=True, exist_ok=True)
            output_path = RESULTS_HTML_DIR / f"{run_id}_report.html"

        logger.info(f"Generating standalone report for {run_id} (tool={aggregate.tool}) -> {output_path.name}")

        try:
            # Construct standard view context dictionary expected by UI components
            # Derived strictly from domain models
            parsed_context = {
                "run_id": run_id,
                "tool": aggregate.tool,
                "jmx_name": test_name,
                "users": users,
                "duration": str(aggregate.duration_seconds),
                "summary": {
                    "total": aggregate.total_requests,
                    "total_iterations": aggregate.total_iterations,
                    "errors": aggregate.failed_requests,
                    "tc_errors": aggregate.failed_requests,
                    "error_rate": aggregate.error_rate,
                    "raw_error_rate": aggregate.raw_error_rate,
                    "avg_rt": aggregate.avg_response_time,
                    "p50": aggregate.p50,
                    "p90": aggregate.p90,
                    "p95": aggregate.p95,
                    "p99": aggregate.p99,
                    "min_rt": aggregate.min_response_time,
                    "max_rt": aggregate.max_response_time,
                    "throughput": aggregate.throughput,
                    "duration_sec": aggregate.duration_seconds,
                    "start_epoch": aggregate.start_epoch,
                    "end_epoch": aggregate.end_epoch,
                },
                "labels": {
                    k: {
                        "count": v.count,
                        "errors": v.errors,
                        "error_rate": v.error_rate,
                        "avg_rt": v.avg_rt,
                        "p50": v.p50,
                        "p90": v.p90,
                        "p95": v.p95,
                        "p99": v.p99,
                        "min_rt": v.min_rt,
                        "max_rt": v.max_rt,
                        "samples": v.samples,
                        "success_flags": v.success_flags,
                    }
                    for k, v in (aggregate.all_labels if aggregate.all_labels else aggregate.transactions).items()
                },
                "labels_by_tg": {
                    tg: {k: v.model_dump() for k, v in lbls.items()}
                    for tg, lbls in aggregate.transactions_by_thread_group.items()
                },
                "time_series": {
                    "ts_labels": timeseries.bucket_labels,
                    "ts_avg_rt": timeseries.avg_response_time,
                    "ts_p95_rt": timeseries.p95_response_time,
                    "ts_p99_rt": timeseries.p99_response_time,
                    "ts_throughput": timeseries.throughput,
                    "ts_errors": timeseries.errors,
                    "ts_active_threads": timeseries.active_threads,
                    "label_ts_map": {
                        k: {
                            "ts_avg_rt": v.avg_rt,
                            "ts_p95_rt": v.p95_rt,
                            "ts_p99_rt": v.p99_rt,
                            "ts_throughput": v.throughput,
                            "ts_errors": v.errors,
                        }
                        for k, v in timeseries.label_series.items()
                    },
                },
                "error_details": {
                    k: {
                        "code": v.code,
                        "message": v.message,
                        "failure_message": v.failure_message,
                        "count": v.count,
                        "occurrences": [occ.model_dump() for occ in v.occurrences],
                    }
                    for k, v in aggregate.errors_breakdown.items()
                },
            }

            azure_payload = {}
            if server_metrics and server_metrics.configured:
                azure_payload = {
                    "configured": True,
                    "infra_summary": server_metrics.infra_summary.model_dump(),
                    "time_series": server_metrics.time_series,
                    "timestamps": server_metrics.timestamps,
                    "resources_queried": server_metrics.resources_queried,
                }

            from app.services.reporting.engine.generator import generate_report as legacy_gen
            report_out = legacy_gen(
                parsed=parsed_context,
                azure_data=azure_payload,
                ai_insights=ai_insights or {},
                report_path=output_path,
                jmx_name=test_name,
                users=users,
            )
            return Path(report_out)
        except Exception as e:
            raise ReportGenerationError(f"Report synthesis failed: {e}", context={"test_id": run_id})


# Global singleton
domain_report_generator = DomainReportGenerator()
