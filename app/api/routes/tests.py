"""
tests.py — Test assets, JMX configuration, file uploads, and SLA targets.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.constants import TESTS_DIR
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["Tests & SLA Management"])


class SaveConfigRequest(BaseModel):
    jmx: str
    thread_groups: Optional[List[Dict[str, Any]]] = None
    users: Optional[int] = None
    duration: Optional[str] = None
    rampup: Optional[str] = None
    iterations: Optional[int] = None


class SaveSLARequest(BaseModel):
    jmx_name: Optional[str] = None
    default_rt: float = 500.0
    default_err: float = 1.0
    targets: Optional[Dict[str, Any]] = None
    slas: Optional[List[Dict[str, Any]]] = None
    scenarios: Optional[Dict[str, Any]] = None


@router.get("/tests")
def list_tests() -> Dict[str, Any]:
    """Lists all JMX test plans in the Tests/ folder and cloud tests if available."""
    jmx_names = []
    jmx_details = []
    if TESTS_DIR.exists():
        for f in sorted(TESTS_DIR.glob("*.jmx")):
            jmx_names.append(f.name)
            jmx_details.append({"name": f.name, "path": str(f), "size": f.stat().st_size})

    return {
        "tests": jmx_names,
        "test_details": jmx_details,
        "tools": ["jmeter", "blazemeter", "neoload"],
    }


@router.get("/jmx-config")
def get_jmx_config(jmx: str) -> Dict[str, Any]:
    """Reads configuration parameters and thread groups from a JMX test script."""
    jmx_path = TESTS_DIR / jmx
    if not jmx_path.exists():
        raise HTTPException(status_code=404, detail=f"JMX '{jmx}' not found")

    try:
        from app.integrations.jmeter.jmx_editor import read_jmx_config
        config = read_jmx_config(jmx_path)
        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"Error reading JMX config: {e}")
        return {"success": False, "message": str(e)}


@router.post("/save-config")
def save_jmx_config(req: SaveConfigRequest) -> Dict[str, Any]:
    """Updates load parameters directly in the JMX file."""
    jmx_path = TESTS_DIR / req.jmx
    if not jmx_path.exists():
        raise HTTPException(status_code=404, detail=f"JMX '{req.jmx}' not found")

    try:
        if req.thread_groups:
            from app.integrations.jmeter.jmx_editor import update_jmx_thread_groups
            update_jmx_thread_groups(jmx_path, req.thread_groups)
        else:
            from app.integrations.jmeter.jmx_editor import update_jmx_config
            update_jmx_config(
                jmx_path,
                users=req.users or 1,
                duration=req.duration or "0",
                rampup=req.rampup or "0",
                iterations=req.iterations or 1,
            )
        return {"success": True, "message": f"Updated {req.jmx} successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update JMX: {e}")


@router.post("/upload-jmx")
async def upload_jmx_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploads JMX, CSV, or ZIP files to Tests/."""
    try:
        filename = Path(file.filename).name
        target_path = TESTS_DIR / filename
        content = await file.read()
        target_path.write_bytes(content)
        logger.info(f"Uploaded test asset: {filename} ({len(content)} bytes)")
        return {"success": True, "message": f"Uploaded {filename}", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.post("/delete-jmx")
def delete_jmx_file(payload: Dict[str, str]) -> Dict[str, Any]:
    """Deletes a test script or asset from Tests/."""
    jmx_name = payload.get("jmx", payload.get("filename", ""))
    target = TESTS_DIR / jmx_name
    if target.exists() and target.is_file():
        target.unlink()
        return {"success": True, "message": f"Deleted {jmx_name}"}
    raise HTTPException(status_code=404, detail=f"File {jmx_name} not found")


@router.get("/sla")
def get_sla_config(jmx: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves SLA configurations, targets, and transaction classifications."""
    try:
        from app.services.analytics.sla_manager import load_sla_targets, parse_jmx_hierarchy
        targets, default_rt, default_err = load_sla_targets(jmx or "")
        identifications = []
        if jmx:
            jmx_path = TESTS_DIR / jmx
            tc_list, _ = parse_jmx_hierarchy(jmx_path)
            for tc in tc_list:
                if tc in targets:
                    identifications.append({
                        "label": tc, "rt": targets[tc]["rt"], "err": targets[tc]["err"],
                        "is_critical": targets[tc].get("is_critical", 0), "defined": True,
                    })
                else:
                    identifications.append({
                        "label": tc, "rt": default_rt, "err": default_err,
                        "is_critical": 0, "defined": False,
                    })
        return {
            "success": True,
            "default_rt": default_rt,
            "default_err": default_err,
            "targets": targets,
            "identifications": identifications,
        }
    except Exception as e:
        logger.error(f"SLA read error: {e}")
        return {"success": False, "message": str(e)}


@router.post("/sla")
def save_sla_config(req: SaveSLARequest) -> Dict[str, Any]:
    """Persists SLA thresholds to CSV/Excel targets."""
    try:
        from app.services.analytics.sla_manager import save_sla_targets
        slas = req.slas or []
        if not slas and req.targets:
            slas = [
                {"label": k, "rt": v.get("rt", req.default_rt), "err": v.get("err", req.default_err), "is_critical": v.get("is_critical", 0)}
                for k, v in req.targets.items()
            ]
        save_sla_targets(slas, req.jmx_name or "default", scenarios=req.scenarios)
        return {"success": True, "message": "SLA targets saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save SLA targets: {e}")
