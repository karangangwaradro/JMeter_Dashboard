"""
run_test.py — Tool-agnostic test execution service.
Responsible ONLY for starting, polling, and stopping test executions across tools.
Does NOT parse results, collect server metrics, or generate reports.
"""

from typing import Optional, Dict, Any
from app.core.exceptions import TestExecutionError
from app.core.logging import logger
from app.domain.models.test_run import (
    ToolType,
    TestExecutionRequest,
    TestExecutionStatus,
)
from app.integrations.jmeter.runner import jmeter_runner
from app.integrations.blazemeter.api_client import blazemeter_client
from app.integrations.neoload.api_client import neoload_client


class TestExecutionService:
    """Dispatches execution commands to the appropriate performance tool adapter."""

    def execute_test(self, request: TestExecutionRequest) -> TestExecutionStatus:
        """Starts a test run for the specified tool."""
        logger.info(f"Executing test with tool '{request.tool}' for '{request.test_identifier}'")

        if request.tool == ToolType.JMETER:
            return jmeter_runner.start_test(request)

        elif request.tool == ToolType.BLAZEMETER:
            try:
                res = blazemeter_client.start_test(request.test_identifier)
                master_id = str(res.get("id", res.get("masterId", request.test_identifier)))
                return TestExecutionStatus(
                    run_id=f"bm_{master_id}",
                    tool=ToolType.BLAZEMETER,
                    status="running",
                    active=True,
                    running=True,
                    done=False,
                    stdout_lines=[f"Launched BlazeMeter master ID: {master_id}"],
                )
            except Exception as e:
                raise TestExecutionError(f"BlazeMeter execution failed: {e}")

        elif request.tool == ToolType.NEOLOAD:
            try:
                res = neoload_client.start_test(request.test_identifier)
                result_id = str(res.get("resultId", res.get("id", request.test_identifier)))
                return TestExecutionStatus(
                    run_id=f"nl_{result_id}",
                    tool=ToolType.NEOLOAD,
                    status="running",
                    active=True,
                    running=True,
                    done=False,
                    stdout_lines=[f"Launched NeoLoad test result ID: {result_id}"],
                )
            except Exception as e:
                raise TestExecutionError(f"NeoLoad execution failed: {e}")

        raise TestExecutionError(f"Unsupported performance tool: '{request.tool}'")

    def get_status(self, tool: ToolType, run_id: Optional[str] = None) -> TestExecutionStatus:
        """Queries status of an ongoing or completed test execution."""
        if tool == ToolType.JMETER:
            return jmeter_runner.get_status(run_id)

        elif tool == ToolType.BLAZEMETER:
            if not run_id:
                return TestExecutionStatus(run_id="unknown", tool=ToolType.BLAZEMETER, status="idle")
            clean_id = run_id.replace("bm_", "")
            try:
                st = blazemeter_client.get_master_status(clean_id)
                status_name = str(st.get("status", "running")).lower()
                is_done = status_name in ("ended", "terminated", "cancelled", "completed")
                return TestExecutionStatus(
                    run_id=run_id,
                    tool=ToolType.BLAZEMETER,
                    status="completed" if is_done else "running",
                    active=not is_done,
                    done=is_done,
                    progress_pct=float(st.get("progress", 100.0 if is_done else 50.0)),
                )
            except Exception as e:
                return TestExecutionStatus(run_id=run_id, tool=ToolType.BLAZEMETER, status="failed", error=str(e))

        elif tool == ToolType.NEOLOAD:
            if not run_id:
                return TestExecutionStatus(run_id="unknown", tool=ToolType.NEOLOAD, status="idle")
            clean_id = run_id.replace("nl_", "")
            try:
                st = neoload_client.get_result_status(clean_id)
                status_name = str(st.get("status", "running")).lower()
                is_done = status_name in ("terminated", "stopped", "completed")
                return TestExecutionStatus(
                    run_id=run_id,
                    tool=ToolType.NEOLOAD,
                    status="completed" if is_done else "running",
                    active=not is_done,
                    done=is_done,
                )
            except Exception as e:
                return TestExecutionStatus(run_id=run_id, tool=ToolType.NEOLOAD, status="failed", error=str(e))

        raise TestExecutionError(f"Unsupported tool: {tool}")

    def stop_test(self, tool: ToolType, run_id: Optional[str] = None) -> bool:
        """Terminates an active execution."""
        if tool == ToolType.JMETER:
            return jmeter_runner.stop_test(run_id)
        elif tool == ToolType.BLAZEMETER:
            if run_id:
                return blazemeter_client.stop_master(run_id.replace("bm_", ""))
            return True
        elif tool == ToolType.NEOLOAD:
            if run_id:
                return neoload_client.stop_test(run_id.replace("nl_", ""))
            return True
        return False


# Global singleton
execution_service = TestExecutionService()
