"""
execution.py — Multi-tool performance test execution and live progress polling endpoints.
Supports JMeter, BlazeMeter, and NeoLoad.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logging import logger
from app.domain.models.test_run import (
    ToolType,
    IngestionMethod,
    TestExecutionRequest,
    ThreadGroupConfig,
)
from app.services.execution.run_test import execution_service

router = APIRouter(prefix="/api", tags=["Execution & Live Monitoring"])


class RunTestPayload(BaseModel):
    tool: Optional[str] = "jmeter"
    jmx: Optional[str] = None
    test_identifier: Optional[str] = None
    thread_groups: Optional[List[Dict[str, Any]]] = None
    tests: Optional[List[Dict[str, Any]]] = None
    users: Optional[int] = None
    duration: Optional[str] = "0"
    rampup: Optional[str] = "0"
    parameters: Optional[Dict[str, Any]] = None


@router.post("/run-test")
def run_test_endpoint(payload: RunTestPayload) -> Dict[str, Any]:
    """
    Launches a performance test run across JMeter, BlazeMeter, or NeoLoad.
    Maintains complete backward compatibility with existing legacy frontend payloads.
    """
    tool_str = (payload.tool or "jmeter").lower()
    tool_enum = ToolType.JMETER
    if tool_str in ("blazemeter", "bm"):
        tool_enum = ToolType.BLAZEMETER
    elif tool_str in ("neoload", "nl"):
        tool_enum = ToolType.NEOLOAD

    # Determine test identifier
    identifier = payload.test_identifier or payload.jmx or ""
    if not identifier and payload.tests and len(payload.tests) > 0:
        identifier = payload.tests[0].get("jmx", "")

    if not identifier:
        raise HTTPException(status_code=400, detail="Test identifier or JMX name is required")

    # Map thread groups
    tg_list = []
    if payload.thread_groups:
        for tg in payload.thread_groups:
            tg_list.append(ThreadGroupConfig(
                name=tg.get("name", "__all__"),
                enabled=bool(tg.get("enabled", True)),
                users=int(tg.get("users", 1)),
                duration=str(tg.get("duration", "0")),
                rampup=str(tg.get("rampup", "0")),
                iterations=int(tg.get("iterations", 1)),
            ))
    elif payload.tests:
        for t in payload.tests:
            tg_list.append(ThreadGroupConfig(
                name="__all__",
                enabled=True,
                users=int(t.get("users", 1)),
                duration=str(t.get("duration", "0")),
                rampup=str(t.get("rampup", "0")),
                iterations=int(t.get("iterations", 1)),
            ))

    total_calculated_users = (
        sum(tg.users for tg in tg_list if tg.enabled)
        if tg_list
        else (payload.users or 1)
    )

    req = TestExecutionRequest(
        tool=tool_enum,
        ingestion=IngestionMethod.LOCAL if tool_enum == ToolType.JMETER else IngestionMethod.DIRECT_API,
        test_identifier=identifier,
        users=total_calculated_users,
        duration=payload.duration or "0",
        rampup=payload.rampup or "0",
        thread_groups=tg_list,
        parameters=payload.parameters or {},
    )

    try:
        status = execution_service.execute_test(req)
        return {
            "success": True,
            "tool": tool_enum.value,
            "run_id": status.run_id,
            "message": f"Started test '{identifier}' via {tool_enum.value}",
            "jmx_name": identifier,
        }
    except Exception as e:
        logger.error(f"Execution trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jmeter-progress")
def get_progress_endpoint(tool: Optional[str] = "jmeter", run_id: Optional[str] = None) -> Dict[str, Any]:
    """Polls progress, active status, elapsed timer, and live sample metrics."""
    tool_enum = ToolType.JMETER
    if tool and tool.lower() in ("blazemeter", "bm"):
        tool_enum = ToolType.BLAZEMETER
    elif tool and tool.lower() in ("neoload", "nl"):
        tool_enum = ToolType.NEOLOAD

    st = execution_service.get_status(tool_enum, run_id)
    return st.model_dump()


@router.post("/stop-test")
def stop_test_endpoint(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Terminates an active performance test."""
    tool_str = (payload or {}).get("tool", "jmeter")
    tool_enum = ToolType.JMETER
    if tool_str.lower() in ("blazemeter", "bm"):
        tool_enum = ToolType.BLAZEMETER
    elif tool_str.lower() in ("neoload", "nl"):
        tool_enum = ToolType.NEOLOAD

    success = execution_service.stop_test(tool_enum)
    return {"success": success, "message": f"Stop signal dispatched for {tool_enum.value}"}
