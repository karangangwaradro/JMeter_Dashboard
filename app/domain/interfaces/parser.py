"""
parser.py — Abstract interfaces for parsing native test and infrastructure results.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.aggregate import AggregateResult
from app.domain.models.server_metrics import ServerMetrics


class TimeSeriesParser(ABC):
    """Parses raw tool results into a normalized TimeSeriesResult domain model."""

    @abstractmethod
    def parse_timeseries(self, raw_data: Any, test_id: str, options: Optional[Dict[str, Any]] = None) -> TimeSeriesResult:
        """Translates tool-specific time series data into a typed TimeSeriesResult."""
        pass


class AggregateParser(ABC):
    """Parses raw tool results into a normalized AggregateResult domain model."""

    @abstractmethod
    def parse_aggregate(self, raw_data: Any, test_id: str, options: Optional[Dict[str, Any]] = None) -> AggregateResult:
        """Translates tool-specific summary/aggregate data into a typed AggregateResult."""
        pass


class ServerMetricsParser(ABC):
    """Parses raw telemetry into a normalized ServerMetrics domain model."""

    @abstractmethod
    def parse_server_metrics(self, raw_data: Any) -> ServerMetrics:
        """Translates provider-specific infrastructure data into typed ServerMetrics."""
        pass
