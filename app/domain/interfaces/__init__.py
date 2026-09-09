"""
Interfaces package for PerfPilot domain boundaries.
"""

from app.domain.interfaces.test_executor import TestExecutor
from app.domain.interfaces.result_collector import ResultCollector, ResultSource
from app.domain.interfaces.parser import TimeSeriesParser, AggregateParser, ServerMetricsParser
from app.domain.interfaces.serializer import DomainSerializer
from app.domain.interfaces.report_generator import ReportGeneratorInterface

__all__ = [
    "TestExecutor",
    "ResultCollector",
    "ResultSource",
    "TimeSeriesParser",
    "AggregateParser",
    "ServerMetricsParser",
    "DomainSerializer",
    "ReportGeneratorInterface",
]
