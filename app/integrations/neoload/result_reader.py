"""
result_reader.py — Result Collector for NeoLoad.
Retrieves and persists raw NeoLoad responses to raw storage or reads uploaded NeoLoad files.
Does NOT parse, normalize, or generate reports.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import STORAGE_RAW_DIR
from app.core.exceptions import ResultCollectionError
from app.core.logging import logger
from app.domain.interfaces.result_collector import ResultCollector
from app.integrations.neoload.api_client import neoload_client


class NeoLoadResultReader(ResultCollector):
    """Collects raw NeoLoad JSON / XML artifacts into storage/raw/."""

    def collect_raw_results(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Path:
        """
        Retrieves raw statistics, elements, and points for a NeoLoad test result
        and writes it into storage/raw/{run_id}_neoload_raw.json.
        """
        context = context or {}
        result_id = context.get("result_id", run_id)
        raw_path = STORAGE_RAW_DIR / f"{run_id}_neoload_raw.json"

        # Check local file or uploaded file
        if raw_path.exists():
            return raw_path

        file_override = context.get("file_path")
        if file_override and Path(file_override).exists():
            return Path(file_override)

        try:
            logger.info(f"Downloading NeoLoad result {result_id} metrics...")
            stats = neoload_client.get_result_statistics(result_id)
            elements = neoload_client.get_transaction_elements(result_id)
            points = neoload_client.get_result_points(result_id)

            payload = {
                "result_id": result_id,
                "statistics": stats,
                "elements": elements,
                "points": points,
            }
            raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return raw_path
        except Exception as e:
            raise ResultCollectionError(
                f"Failed to retrieve NeoLoad raw results: {e}",
                context={"result_id": result_id, "run_id": run_id}
            )

    def read_json(self, raw_path: Path) -> Dict[str, Any]:
        """Reads raw JSON payload from disk."""
        try:
            return json.loads(raw_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ResultCollectionError(f"Failed to read NeoLoad raw JSON: {e}")


# Global singleton
neoload_result_reader = NeoLoadResultReader()
