"""
parse_results.py — Tool-agnostic result parsing service.
Responsible ONLY for translating raw formats into typed domain contracts:
TimeSeriesResult and AggregateResult.
Does NOT execute tests, collect server telemetry, or generate reports.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from app.core.exceptions import ParserError
from app.core.logging import logger
from app.domain.models.test_run import ToolType
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.aggregate import AggregateResult

from app.integrations.jmeter.timeseries_parser import jmeter_timeseries_parser
from app.integrations.jmeter.aggregate_parser import jmeter_aggregate_parser
from app.integrations.blazemeter.timeseries_parser import blazemeter_timeseries_parser
from app.integrations.blazemeter.aggregate_parser import blazemeter_aggregate_parser
from app.integrations.neoload.timeseries_parser import neoload_timeseries_parser
from app.integrations.neoload.aggregate_parser import neoload_aggregate_parser


class ResultParsingService:
    """Dispatches raw inputs to the corresponding tool parser to produce typed domain models."""

    def parse_timeseries(
        self,
        tool: ToolType,
        raw_data: Any,
        test_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> TimeSeriesResult:
        """Translates raw results into the common TimeSeriesResult model."""
        logger.info(f"Parsing time-series data for {test_id} using tool adapter '{tool}'")
        if tool == ToolType.JMETER:
            return jmeter_timeseries_parser.parse_timeseries(raw_data, test_id)
        elif tool == ToolType.BLAZEMETER:
            return blazemeter_timeseries_parser.parse_timeseries(raw_data, test_id, options=options)
        elif tool == ToolType.NEOLOAD:
            return neoload_timeseries_parser.parse_timeseries(raw_data, test_id)
        raise ParserError(f"Unsupported parser tool: {tool}")

    def parse_aggregate(
        self,
        tool: ToolType,
        raw_data: Any,
        test_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AggregateResult:
        """Translates raw results into the common AggregateResult model."""
        logger.info(f"Parsing aggregate data for {test_id} using tool adapter '{tool}'")
        if tool == ToolType.JMETER:
            return jmeter_aggregate_parser.parse_aggregate(raw_data, test_id, options=options)
        elif tool == ToolType.BLAZEMETER:
            return blazemeter_aggregate_parser.parse_aggregate(raw_data, test_id, options=options)
        elif tool == ToolType.NEOLOAD:
            return neoload_aggregate_parser.parse_aggregate(raw_data, test_id)
        raise ParserError(f"Unsupported parser tool: {tool}")

    def parse_all(
        self,
        tool: ToolType,
        raw_data: Any,
        test_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AggregateResult, TimeSeriesResult]:
        """Convenience method returning both normalized domain contracts."""
        agg = self.parse_aggregate(tool, raw_data, test_id, options=options)
        ts = self.parse_timeseries(tool, raw_data, test_id, options=options)
        return agg, ts


# Global singleton
parsing_service = ResultParsingService()
