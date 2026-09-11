"""
tracker.py — Real-time Pipeline Execution & Stage Tracking Service.
Provides live stage transitions, execution timings, diagnostic logs, and status queries
for test execution, raw uploads, AI insights, and report generation workflows.
"""

import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PipelineStage:
    id: str
    name: str
    description: str
    status: str = "pending"  # "pending" | "running" | "completed" | "failed" | "skipped"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    elapsed_ms: int = 0
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        cur_elapsed = self.elapsed_ms
        if self.status == "running" and self.started_at:
            cur_elapsed = int((time.time() - self.started_at) * 1000)
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "elapsed_ms": cur_elapsed,
            "detail": self.detail,
        }


DEFAULT_STAGES = [
    ("ingestion", "Archive Ingestion & File Discovery", "Extracting uploaded archive and discovering test logs"),
    ("parsing", "Parsing & Domain Normalization", "Translating raw tool metrics into typed domain contracts"),
    ("sla", "Workload & SLA Scenario Resolution", "Calculating concurrency and resolving SLA threshold profiles"),
    ("ai_insights", "AI Insights Synthesis", "Multi-provider LLM analysis for findings and recommendations"),
    ("storage", "Artifact Serialization", "Persisting normalized models and backward-compatible JSON"),
    ("reporting", "HTML Report Compilation", "Building standalone interactive performance report"),
]


class PipelineTracker:
    """Thread-safe store tracking live progress and stage transitions of test pipelines."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._latest_run_id: Optional[str] = None

    def start_pipeline(
        self,
        run_id: str,
        tool: str,
        test_name: str,
        initial_stage: str = "ingestion",
        initial_detail: str = "",
    ) -> None:
        """Initializes a new pipeline run with standard stages."""
        with self._lock:
            # If already running with this run_id, keep existing stages
            if run_id in self._runs:
                existing = self._runs[run_id]
                if existing.get("overall_status") == "running":
                    return

            stages = [
                PipelineStage(id=sid, name=name, description=desc)
                for sid, name, desc in DEFAULT_STAGES
            ]
            now = time.time()

            # Set the initial stage to running
            for st in stages:
                if st.id == initial_stage:
                    st.status = "running"
                    st.started_at = now
                    st.detail = initial_detail or st.description
                    break

            self._runs[run_id] = {
                "run_id": run_id,
                "tool": tool,
                "test_name": test_name,
                "overall_status": "running",
                "current_stage_id": initial_stage,
                "started_at": now,
                "ended_at": None,
                "total_elapsed_ms": 0,
                "error_message": None,
                "report_url": None,
                "stages": stages,
                "logs": [
                    {
                        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                        "stage": "init",
                        "message": f"Pipeline started for {test_name} ({tool})",
                        "level": "INFO",
                    }
                ],
                "summary": {},
            }
            if initial_detail:
                self._runs[run_id]["logs"].append({
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                    "stage": initial_stage,
                    "message": initial_detail,
                    "level": "INFO",
                })
            self._latest_run_id = run_id

    def start_stage(self, run_id: str, stage_id: str, detail: str = "") -> None:
        """Marks a stage as active."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            run["current_stage_id"] = stage_id
            now = time.time()
            for st in run["stages"]:
                if st.id == stage_id:
                    st.status = "running"
                    st.started_at = now
                    st.detail = detail
                    break
            run["logs"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                "stage": stage_id,
                "message": detail or f"Starting stage: {stage_id}",
                "level": "INFO",
            })

    def update_stage(self, run_id: str, stage_id: str, detail: str) -> None:
        """Updates detail text for an active stage."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            for st in run["stages"]:
                if st.id == stage_id:
                    st.detail = detail
                    break
            run["logs"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                "stage": stage_id,
                "message": detail,
                "level": "INFO",
            })

    def complete_stage(self, run_id: str, stage_id: str, detail: str = "") -> None:
        """Marks a stage as completed with its elapsed time."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            now = time.time()
            for st in run["stages"]:
                if st.id == stage_id:
                    st.status = "completed"
                    st.ended_at = now
                    if st.started_at:
                        st.elapsed_ms = int((now - st.started_at) * 1000)
                    if detail:
                        st.detail = detail
                    break
            run["logs"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                "stage": stage_id,
                "message": detail or f"Completed stage: {stage_id}",
                "level": "INFO",
            })

    def skip_stage(self, run_id: str, stage_id: str, detail: str = "") -> None:
        """Marks a stage as skipped."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            for st in run["stages"]:
                if st.id == stage_id:
                    st.status = "skipped"
                    st.detail = detail
                    break

    def complete_pipeline(self, run_id: str, report_url: str = "", summary: Optional[Dict[str, Any]] = None) -> None:
        """Marks the entire pipeline as successfully completed."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            now = time.time()
            run["overall_status"] = "completed"
            run["ended_at"] = now
            run["total_elapsed_ms"] = int((now - run["started_at"]) * 1000)
            run["report_url"] = report_url
            run["summary"] = summary or {}
            # Mark any remaining running stages as completed
            for st in run["stages"]:
                if st.status == "running":
                    st.status = "completed"
                    st.ended_at = now
                    if st.started_at:
                        st.elapsed_ms = int((now - st.started_at) * 1000)

            run["logs"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                "stage": "finish",
                "message": f"Pipeline successfully completed in {run['total_elapsed_ms']/1000:.1f}s",
                "level": "SUCCESS",
            })

    def fail_pipeline(self, run_id: str, stage_id: str, error_message: str) -> None:
        """Marks the pipeline and current stage as failed."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            now = time.time()
            run["overall_status"] = "failed"
            run["ended_at"] = now
            run["total_elapsed_ms"] = int((now - run["started_at"]) * 1000)
            run["error_message"] = error_message
            for st in run["stages"]:
                if st.id == stage_id:
                    st.status = "failed"
                    st.ended_at = now
                    if st.started_at:
                        st.elapsed_ms = int((now - st.started_at) * 1000)
                    st.detail = f"Failed: {error_message}"
                    break
            run["logs"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                "stage": stage_id,
                "message": f"Pipeline failed: {error_message}",
                "level": "ERROR",
            })

    def get_status(self, run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns snapshot of the requested run or the latest active run."""
        with self._lock:
            target_id = run_id or self._latest_run_id
            if not target_id or target_id not in self._runs:
                return None
            run = self._runs[target_id]
            now = time.time()
            total_elapsed = run["total_elapsed_ms"]
            if run["overall_status"] == "running":
                total_elapsed = int((now - run["started_at"]) * 1000)

            return {
                "run_id": run["run_id"],
                "tool": run["tool"],
                "test_name": run["test_name"],
                "overall_status": run["overall_status"],
                "current_stage_id": run["current_stage_id"],
                "total_elapsed_ms": total_elapsed,
                "error_message": run["error_message"],
                "report_url": run["report_url"],
                "stages": [st.to_dict() for st in run["stages"]],
                "logs": list(run["logs"][-50:]),  # Return last 50 log lines
                "summary": run["summary"],
            }


# Global singleton
pipeline_tracker = PipelineTracker()
