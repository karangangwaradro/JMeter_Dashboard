"""
result_reader.py — Result Collector for BlazeMeter.
Retrieves and persists raw BlazeMeter execution responses to raw storage.
Does NOT parse, normalize, or generate reports.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import STORAGE_RAW_DIR
from app.core.exceptions import ResultCollectionError
from app.core.logging import logger
from app.domain.interfaces.result_collector import ResultCollector
from app.integrations.blazemeter.api_client import blazemeter_client


class BlazeMeterResultReader(ResultCollector):
    """Retrieves raw JSON artifacts from BlazeMeter and stores them in raw results."""

    def collect_raw_results(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Path:
        """
        Retrieves raw summary and timeseries JSON for a BlazeMeter master run
        and writes it into storage/raw/{run_id}_blazemeter_raw.json.
        """
        context = context or {}
        master_id = context.get("master_id", run_id)
        raw_path = STORAGE_RAW_DIR / f"{run_id}_blazemeter_raw.json"

        # If file already exists locally (e.g. uploaded or previously fetched)
        if raw_path.exists():
            return raw_path

        # If a raw file path was directly passed in context
        file_override = context.get("file_path")
        if file_override and Path(file_override).exists():
            return Path(file_override)

        try:
            logger.info(f"Downloading BlazeMeter master {master_id} reports...")
            summary_data = blazemeter_client.get_master_summary(master_id)
            timeseries_data = blazemeter_client.get_master_timeseries(master_id)

            payload = {
                "master_id": master_id,
                "summary": summary_data,
                "timeseries": timeseries_data,
            }
            raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return raw_path
        except Exception as e:
            raise ResultCollectionError(
                f"Failed to retrieve BlazeMeter raw results: {e}",
                context={"master_id": master_id, "run_id": run_id}
            )

    def read_json(self, raw_path: Path) -> Dict[str, Any]:
        """Reads raw JSON content from disk."""
        try:
            return json.loads(raw_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ResultCollectionError(f"Failed to read BlazeMeter raw JSON {raw_path.name}: {e}")


# Global singleton
blazemeter_result_reader = BlazeMeterResultReader()
