"""
collect_results.py — Tool-agnostic result collection service.
Responsible ONLY for retrieving test results, downloading result files, and obtaining API/MCP results.
Does NOT parse data, normalize data, or generate reports.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from app.core.exceptions import ResultCollectionError
from app.core.logging import logger
from app.domain.models.test_run import ToolType, IngestionMethod
from app.integrations.jmeter.result_reader import jmeter_result_reader
from app.integrations.blazemeter.result_reader import blazemeter_result_reader
from app.integrations.neoload.result_reader import neoload_result_reader
from app.integrations.upload.file_source import file_result_source
from app.integrations.mcp.result_source import mcp_result_source


class ResultCollectionService:
    """Retrieves raw result files and artifacts across tools and ingestion methods."""

    def collect(
        self,
        tool: ToolType,
        ingestion: IngestionMethod,
        run_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Retrieves or downloads the raw performance result file and returns its Path in storage/raw/.
        """
        options = options or {}
        logger.info(f"Collecting results for run '{run_id}' [tool={tool}, method={ingestion}]")

        if ingestion == IngestionMethod.FILE_UPLOAD:
            file_id = options.get("file_path", options.get("file_name", run_id))
            return file_result_source.fetch_data(file_id, options)

        if ingestion == IngestionMethod.MCP:
            res = mcp_result_source.fetch_data(run_id, options)
            # Write MCP fetched dictionary to raw storage
            from app.core.constants import STORAGE_RAW_DIR
            import json
            raw_path = STORAGE_RAW_DIR / f"{run_id}_mcp_raw.json"
            raw_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
            return raw_path

        # Direct tool collectors
        if tool == ToolType.JMETER:
            return jmeter_result_reader.collect_raw_results(run_id, options)

        elif tool == ToolType.BLAZEMETER:
            return blazemeter_result_reader.collect_raw_results(run_id, options)

        elif tool == ToolType.NEOLOAD:
            return neoload_result_reader.collect_raw_results(run_id, options)

        raise ResultCollectionError(f"Unsupported tool '{tool}' or ingestion '{ingestion}'")


# Global singleton
collection_service = ResultCollectionService()
