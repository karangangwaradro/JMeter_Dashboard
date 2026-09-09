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
        run_id = f"run_{timestamp}"
        actual_test_name = test_name or Path(identifier).stem

        # Step 1: Collect / Ingest raw artifact
        raw_path = collection_service.collect(tool, ingestion, identifier, options)

        # Step 2: Parse into typed domain contracts
        agg_result, ts_result = parsing_service.parse_all(tool, raw_path, run_id)

        # Step 3: Optional Server Metrics
        server_metrics = None
        srv_file = options.get("server_metrics_file")
        if srv_file and Path(srv_file).exists():
            from app.server_metrics.csv.parser import csv_metrics_parser
            server_metrics = csv_metrics_parser.parse_server_metrics(Path(srv_file))

        # Step 4: Validate and serialize modular artifacts
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
            has_ai_insights=False,
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
        legacy_data = {
            "summary": agg_result.model_dump(),
            "labels": {k: v.model_dump() for k, v in agg_result.transactions.items()},
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
        }
        legacy_result_path.write_text(json.dumps(legacy_data, indent=2), encoding="utf-8")

        # Step 5: Report generation
        report_path = RESULTS_HTML_DIR / f"{run_id}_report.html"
        domain_report_generator.generate(
            aggregate=agg_result,
            timeseries=ts_result,
            server_metrics=server_metrics,
            output_path=report_path,
            options={"test_name": actual_test_name, "users": users},
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
