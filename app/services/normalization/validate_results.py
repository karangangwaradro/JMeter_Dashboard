"""
validate_results.py — Result validation and persistence service.
Ensures domain models satisfy contract constraints before serializing into modular JSON artifacts.
"""

from pathlib import Path
from typing import Optional

from app.core.constants import STORAGE_NORMALIZED_DIR, RESULTS_JSON_DIR
from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.aggregate import AggregateResult
from app.domain.models.server_metrics import ServerMetrics
from app.domain.models.test_metadata import TestRunMetadata
from app.serialization.serializer import (
    save_timeseries,
    save_aggregate,
    save_server_metrics,
    serializer,
)


class ResultValidationService:
    """Validates domain models and persists versioned JSON artifacts."""

    def validate_and_save(
        self,
        run_id: str,
        aggregate: AggregateResult,
        timeseries: TimeSeriesResult,
        server_metrics: Optional[ServerMetrics] = None,
        metadata: Optional[TestRunMetadata] = None,
    ) -> dict:
        """
        Validates the models and writes modular JSON artifacts into storage/normalized/.
        Also maintains backward-compatible unified JSON in Results/json/ for legacy consumers.
        """
        STORAGE_NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_JSON_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Validating and persisting normalized artifacts for run '{run_id}'")

        # 1. Validation checks
        if not aggregate.test_id or aggregate.test_id != timeseries.test_id:
            logger.warning(f"Test ID mismatch between aggregate ({aggregate.test_id}) and timeseries ({timeseries.test_id})")

        if aggregate.total_requests < 0 or aggregate.failed_requests < 0:
            raise ValidationError(f"Invalid request counts in aggregate model for {run_id}")

        # 2. Serialize modular normalized artifacts
        ts_path = STORAGE_NORMALIZED_DIR / f"{run_id}_timeseries.json"
        agg_path = STORAGE_NORMALIZED_DIR / f"{run_id}_aggregate.json"

        save_timeseries(timeseries, ts_path)
        save_aggregate(aggregate, agg_path)

        srv_path = None
        if server_metrics:
            srv_path = STORAGE_NORMALIZED_DIR / f"{run_id}_server_metrics.json"
            save_server_metrics(server_metrics, srv_path)

        meta_path = None
        if metadata:
            meta_path = STORAGE_NORMALIZED_DIR / f"{run_id}_metadata.json"
            serializer.serialize(metadata, meta_path)

        return {
            "timeseries_file": str(ts_path),
            "aggregate_file": str(agg_path),
            "server_metrics_file": str(srv_path) if srv_path else None,
            "metadata_file": str(meta_path) if meta_path else None,
        }


# Global singleton
validation_service = ResultValidationService()
