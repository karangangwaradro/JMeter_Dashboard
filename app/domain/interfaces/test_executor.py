"""
test_executor.py — Abstract interface for performance test execution engines.
"""

from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models.test_run import TestExecutionRequest, TestExecutionStatus


class TestExecutor(ABC):
    """Abstract interface defining the execution contract for load testing tools."""

    @abstractmethod
    def start_test(self, request: TestExecutionRequest) -> TestExecutionStatus:
        """Launch a performance test execution asynchronously."""
        pass

    @abstractmethod
    def get_status(self, run_id: Optional[str] = None) -> TestExecutionStatus:
        """Query current execution status, progress, and live statistics."""
        pass

    @abstractmethod
    def stop_test(self, run_id: Optional[str] = None) -> bool:
        """Terminate an active test execution."""
        pass
