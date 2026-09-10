"""
ingestion.py — Data ingestion routes for raw result uploads, Direct APIs, and MCP sources.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.constants import STORAGE_RAW_DIR
from app.core.logging import logger
from app.domain.models.test_run import ToolType, IngestionMethod
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/api/ingest", tags=["Data Ingestion"])


class ApiIngestRequest(BaseModel):
    tool: str  # "blazemeter" | "neoload"
    identifier: str  # Master ID or Test Result ID
    test_name: Optional[str] = None
    users: int = 1


class MCPIngestRequest(BaseModel):
    tool: str = "blazemeter"
    identifier: str
    options: Optional[Dict[str, Any]] = None
    test_name: Optional[str] = None
    users: int = 1


@router.get("/sla-options")
def get_sla_options() -> Dict[str, Any]:
    """Returns available SLA target profile files from config/ and Tests/."""
    from app.services.analytics.sla_manager import list_available_sla_files
    return {"sla_files": list_available_sla_files()}


@router.post("/upload")
async def upload_result_file(
    file: UploadFile = File(...),
    tool: str = Form("jmeter"),
    test_name: Optional[str] = Form(None),
    users: int = Form(1),
    sla_file: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """
    Ingests an uploaded raw performance result file (JTL, BlazeMeter JSON, NeoLoad CSV/XML),
    translates into strongly typed domain models, and compiles a standalone HTML report.
    """
    try:
        filename = Path(file.filename).name
        target_path = STORAGE_RAW_DIR / filename
        content = await file.read()
        target_path.write_bytes(content)

        tool_enum = ToolType(tool.lower())
        opts = {}
        if sla_file:
            opts["sla_file"] = sla_file

        res = orchestrator.ingest_and_process(
            tool=tool_enum,
            ingestion=IngestionMethod.FILE_UPLOAD,
            identifier=str(target_path),
            test_name=test_name or filename,
            users=users,
            options=opts,
        )
        return res
    except Exception as e:
        logger.error(f"Upload ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {e}")


@router.post("/api")
def ingest_via_api(req: ApiIngestRequest) -> Dict[str, Any]:
    """Retrieves results directly from BlazeMeter or NeoLoad REST APIs and normalizes them."""
    try:
        tool_enum = ToolType(req.tool.lower())
        res = orchestrator.ingest_and_process(
            tool=tool_enum,
            ingestion=IngestionMethod.DIRECT_API,
            identifier=req.identifier,
            test_name=req.test_name or f"{req.tool.upper()}_{req.identifier}",
            users=req.users,
            options={"master_id": req.identifier, "result_id": req.identifier},
        )
        return res
    except Exception as e:
        logger.error(f"API ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp")
def ingest_via_mcp(req: MCPIngestRequest) -> Dict[str, Any]:
    """Retrieves results via Model Context Protocol (MCP) tool integration and normalizes them."""
    try:
        tool_enum = ToolType(req.tool.lower())
        res = orchestrator.ingest_and_process(
            tool=tool_enum,
            ingestion=IngestionMethod.MCP,
            identifier=req.identifier,
            test_name=req.test_name or f"MCP_{req.identifier}",
            users=req.users,
            options=req.options or {},
        )
        return res
    except Exception as e:
        logger.error(f"MCP ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
