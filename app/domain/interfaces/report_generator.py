"""
report_generator.py — Abstract interface for tool-agnostic performance report generators.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from app.domain.models.aggregate import AggregateResult
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.server_metrics import ServerMetrics


class ReportGeneratorInterface(ABC):
    """Abstract interface for compiling reports strictly from typed domain contracts."""

    @abstractmethod
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
        Synthesizes a standalone, interactive report consuming only normalized domain models.
        """
        pass
