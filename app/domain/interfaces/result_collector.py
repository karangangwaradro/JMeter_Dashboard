"""
result_collector.py — Abstract interface for collecting raw test results.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class ResultCollector(ABC):
    """Abstract interface for collecting raw result data from a tool or service."""

    @abstractmethod
    def collect_raw_results(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Path:
        """
        Collects, downloads, or accesses raw result files/payloads and returns
        the path to the stored raw artifact in storage/raw/.
        """
        pass


class ResultSource(ABC):
    """Abstract interface for ingestion sources (File upload, REST API, MCP)."""

    @abstractmethod
    def fetch_data(self, identifier: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Fetches raw data from the underlying source."""
        pass
