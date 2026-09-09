"""
orchestrator.py — High-level workflow orchestrator for PerfPilot.
Composes independent execution, collection, parsing, normalization, and reporting services.
Enables customizable lifecycle workflows:
  - run_full_pipeline(...)
  - ingest_uploaded_file(...)
  - parse_and_report_raw(...)
  - generate_report_from_normalized(...)
"""

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import json

from app.core.constants import RESULTS_JSON_DIR, DATA_DIR, RESULTS_HTML_DIR
from app.core.logging import logger
from app.domain.models.test_run import (
    ToolType,
    IngestionMethod,
    TestExecutionRequest,
    TestExecutionStatus,
)
from app.domain.models.test_metadata import TestRunMetadata
from app.services.execution.run_test import execution_service
from app.services.collection.collect_results import collection_service
from app.services.parsing.parse_results import parsing_service
from app.services.normalization.validate_results import validation_service
from app.services.reporting.generate_report import domain_report_generator
from app.serialization.serializer import load_aggregate, load_timeseries, load_server_metrics


class TestWorkflowOrchestrator:
    """Orchestrates composable performance testing lifecycle workflows."""

    def ingest_and_process(
        self,
        tool: ToolType,
        ingestion: IngestionMethod,
        identifier: str,
        test_name: Optional[str] = None,
        users: int = 1,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingestion pipeline: Collect/Upload -> Parse -> Normalize -> Report.
        Works universally for JMeter JTL, BlazeMeter JSON, and NeoLoad files.
        """
        options = options or {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = options.get("run_id") or (identifier if identifier.startswith("run_") and not identifier.endswith(".jtl") else f"run_{timestamp}")
        actual_test_name = test_name or Path(identifier).stem

        # Step 1: Collect / Ingest raw artifact
        raw_path = collection_service.collect(tool, ingestion, identifier, options)

        # Step 2: Parse into typed domain contracts
        parse_options = {"test_name": actual_test_name, "jmx_name": actual_test_name, **options}
        agg_result, ts_result = parsing_service.parse_all(tool, raw_path, run_id, options=parse_options)

        # Resolve total concurrent users from JMX if default was passed
        if users <= 1 and actual_test_name:
            try:
                from app.services.analytics.sla_manager import parse_jmx_thread_groups
                tgs = parse_jmx_thread_groups(actual_test_name)
                if tgs:
                    total_jmx_users = sum(tg.get("users", 1) for tg in tgs if tg.get("enabled", True))
                    if total_jmx_users > users:
                        users = total_jmx_users
            except Exception:
                pass

        # Step 3: Optional Server Metrics
        server_metrics = None
        srv_file = options.get("server_metrics_file")
        if srv_file and Path(srv_file).exists():
            from app.server_metrics.csv.parser import csv_metrics_parser
            server_metrics = csv_metrics_parser.parse_server_metrics(Path(srv_file))

        # Step 3.5: AI Insights Generation (Multi-Provider Cascade)
        ai_insights = options.get("ai_insights")
        if not ai_insights:
            try:
                from app.services.ai.insights import generate_insights
                from app.services.analytics.sla_manager import load_sla_targets
                logger.info(f"Generating AI performance insights for {run_id}...")
                sla_targets, default_rt, default_err = load_sla_targets(actual_test_name, actual_users=users)
                all_lbls_dict = agg_result.all_labels if agg_result.all_labels else agg_result.transactions
                ai_insights = generate_insights(
                    test_name=actual_test_name,
                    summary=agg_result.model_dump(),
                    labels={k: v.model_dump() for k, v in all_lbls_dict.items()},
                    time_series=ts_result.model_dump(),
                    infra=server_metrics.model_dump() if server_metrics else {},
                    correlation={},
                    sla_targets=sla_targets,
                    default_rt=default_rt,
                    default_err=default_err,
                    users=users,
                    rampup=int(options.get("rampup", 0)),
                )
                if ai_insights:
                    logger.info(f"AI insights generated successfully for {run_id} (source={ai_insights.get('source')})")
            except Exception as ai_err:
                logger.warning(f"AI insights generation skipped: {ai_err}")

        # Step 4: Validate and serialize modular artifacts
        has_ai = bool(ai_insights and ai_insights.get("source") != "none")
        metadata = TestRunMetadata(
            id=run_id,
            tool=tool.value,
            ingestion=ingestion.value,
            jmx_name=actual_test_name,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            epoch=int(datetime.now(timezone.utc).timestamp()),
            users=users,
            duration=str(agg_result.duration_seconds),
            rampup="0",
            total_samples=agg_result.total_requests,
            avg_rt=agg_result.avg_response_time,
            p95_rt=agg_result.p95,
            error_rate=agg_result.error_rate,
            throughput=agg_result.throughput,
            duration_sec=agg_result.duration_seconds,
            has_azure=bool(server_metrics and server_metrics.configured),
            has_ai_insights=has_ai,
            report_file=f"{run_id}_report.html",
            result_file=f"{run_id}_result.json",
            status="passed" if agg_result.error_rate <= 1.0 else "warning" if agg_result.error_rate <= 5.0 else "failed",
        )

        persisted_files = validation_service.validate_and_save(
            run_id=run_id,
            aggregate=agg_result,
            timeseries=ts_result,
            server_metrics=server_metrics,
            metadata=metadata,
        )

        # Also write legacy run_{timestamp}_result.json for existing compare & trend features
        legacy_result_path = RESULTS_JSON_DIR / f"{run_id}_result.json"
        all_lbls_dict = agg_result.all_labels if agg_result.all_labels else agg_result.transactions
        legacy_data = {
            "summary": agg_result.model_dump(),
            "labels": {k: v.model_dump() for k, v in all_lbls_dict.items()},
            "labels_by_tg": {
                tg: {k: v.model_dump() for k, v in lbls.items()}
                for tg, lbls in agg_result.transactions_by_thread_group.items()
            },
            "hierarchy_tree": agg_result.hierarchy_tree,
            "time_series": {
                "ts_labels": ts_result.bucket_labels,
                "ts_avg_rt": ts_result.avg_response_time,
                "ts_p95_rt": ts_result.p95_response_time,
                "ts_p99_rt": ts_result.p99_response_time,
                "ts_throughput": ts_result.throughput,
                "ts_errors": ts_result.errors,
                "ts_active_threads": ts_result.active_threads,
            },
            "jmx_name": actual_test_name,
            "users": users,
            "run_id": run_id,
            "execution_time": metadata.timestamp,
            "ai_insights": ai_insights or {},
        }
        legacy_result_path.write_text(json.dumps(legacy_data, indent=2), encoding="utf-8")

        # Step 5: Report generation
        report_path = RESULTS_HTML_DIR / f"{run_id}_report.html"
        domain_report_generator.generate(
            aggregate=agg_result,
            timeseries=ts_result,
            server_metrics=server_metrics,
            ai_insights=ai_insights or {},
            output_path=report_path,
            options={"test_name": actual_test_name, "jmx_name": actual_test_name, "users": users},
        )

        # Step 6: Update historical catalog data/runs.json
        self._register_run(metadata)

        return {
            "success": True,
            "run_id": run_id,
            "tool": tool.value,
            "ingestion": ingestion.value,
            "report_url": f"/Results/html/{report_path.name}",
            "report_file": str(report_path),
            "artifacts": persisted_files,
            "summary": {
                "total": agg_result.total_requests,
                "avg_rt": agg_result.avg_response_time,
                "error_rate": agg_result.error_rate,
                "throughput": agg_result.throughput,
            },
        }

    def _register_run(self, metadata: TestRunMetadata) -> None:
        """Appends run entry to data/runs.json."""
        runs_path = DATA_DIR / "runs.json"
        catalog = {"runs": []}
        if runs_path.exists():
            try:
                catalog = json.loads(runs_path.read_text(encoding="utf-8"))
            except Exception:
                catalog = {"runs": []}
        catalog["runs"].insert(0, metadata.model_dump())
        runs_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")


# Global singleton
orchestrator = TestWorkflowOrchestrator()
