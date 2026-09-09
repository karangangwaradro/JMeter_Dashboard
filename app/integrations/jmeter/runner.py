"""
runner.py — Apache JMeter execution engine implementing TestExecutor.
Responsible ONLY for starting, monitoring, and stopping JMeter execution processes.
Does NOT parse, normalize, collect server telemetry, or generate reports.
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.core.constants import ROOT_DIR, TESTS_DIR, LOGS_DIR, RESULTS_JTL_DIR
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import TestExecutionError
from app.domain.interfaces.test_executor import TestExecutor
from app.domain.models.test_run import (
    ToolType,
    TestExecutionRequest,
    TestExecutionStatus,
    ThreadGroupConfig,
)


class JMeterRunner(TestExecutor):
    """Encapsulates CLI execution and process lifecycle for Apache JMeter."""

    def __init__(self):
        self._active_process: Optional[subprocess.Popen] = None
        self._active_run_id: Optional[str] = None
        self._active_jtl_path: Optional[Path] = None
        self._stop_watcher_event = threading.Event()
        self._watcher_thread: Optional[threading.Thread] = None
        self._state = {
            "active": False,
            "done": False,
            "run_id": "",
            "jmx_name": "",
            "start_time": 0.0,
            "exit_code": None,
            "error": None,
            "live_stats": {},
            "failed_requests": {},
            "stdout_lines": [],
        }
        self._lock = threading.Lock()

    def find_jmeter_bin(self) -> str:
        """Find path to the jmeter executable."""
        jmeter_home = settings.jmeter_home or os.environ.get("JMETER_HOME", "")
        if jmeter_home:
            for candidate in [
                Path(jmeter_home) / "jmeter.bat",
                Path(jmeter_home) / "jmeter",
                Path(jmeter_home) / "bin" / "jmeter.bat",
                Path(jmeter_home) / "bin" / "jmeter",
            ]:
                if candidate.exists():
                    return str(candidate)
        return "jmeter"

    def check_jmeter(self) -> Dict[str, Any]:
        """Validates that JMeter is installed and functional (cached for 60s)."""
        now = time.time()
        cached = getattr(self, "_cached_jmeter_info", None)
        cached_time = getattr(self, "_cached_jmeter_time", 0.0)
        if cached and (now - cached_time < 60.0):
            return cached

        jmeter_bin = self.find_jmeter_bin()
        if not os.path.exists(jmeter_bin) and jmeter_bin != "jmeter":
            res = {"available": False, "error": f"JMeter binary not found at '{jmeter_bin}'"}
            self._cached_jmeter_info = res
            self._cached_jmeter_time = now
            return res

        try:
            env = os.environ.copy()
            java_home = settings.java_home or os.environ.get("JAVA_HOME", "")
            if java_home and os.path.exists(java_home):
                env["PATH"] = os.path.join(java_home, "bin") + os.path.pathsep + env.get("PATH", "")

            cmd = [jmeter_bin, "-v"]
            if os.name == "nt" and jmeter_bin.endswith(".bat"):
                cmd = ["cmd.exe", "/c", jmeter_bin, "-v"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=8, env=env
            )
            version_text = (result.stdout + result.stderr).strip()
            if result.returncode == 0 or "Apache JMeter" in version_text:
                version = "Apache JMeter"
                for line in version_text.splitlines():
                    if "Apache JMeter" in line:
                        version = line.strip()
                        break
                res = {"available": True, "version": version, "bin": jmeter_bin}
            else:
                res = {"available": False, "error": f"Exit code {result.returncode}: {version_text[:300]}"}
        except Exception as e:
            res = {"available": False, "error": str(e)}

        self._cached_jmeter_info = res
        self._cached_jmeter_time = now
        return res

    def start_test(self, request: TestExecutionRequest) -> TestExecutionStatus:
        """Launches a local JMeter execution process."""
        with self._lock:
            if self._state["active"]:
                raise TestExecutionError(f"A test is already running ({self._state['jmx_name']})")

            jmx_name = request.test_identifier
            jmx_path = TESTS_DIR / jmx_name
            if not jmx_path.exists():
                raise TestExecutionError(f"JMX test plan '{jmx_name}' not found in {TESTS_DIR}")

            info = self.check_jmeter()
            if not info["available"]:
                raise TestExecutionError(f"JMeter unavailable: {info.get('error')}")

            # Apply thread groups if requested
            if request.thread_groups:
                try:
                    from app.integrations.jmeter.jmx_editor import update_jmx_thread_groups
                    tg_dicts = [tg.model_dump() for tg in request.thread_groups]
                    update_jmx_thread_groups(jmx_path, tg_dicts)
                except Exception as tg_err:
                    logger.warning(f"Could not apply thread group settings: {tg_err}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"run_{timestamp}"
            jtl_path = RESULTS_JTL_DIR / f"{run_id}.jtl"
            log_path = LOGS_DIR / f"{run_id}.log"

            cmd = [
                info["bin"],
                "-n",
                "-Jjmeter.save.saveservice.autoflush=true",
                "-Jsummariser.interval=3",
                "-t", str(jmx_path),
                "-l", str(jtl_path),
                "-j", str(log_path),
            ]
            if os.name == "nt" and info["bin"].endswith(".bat"):
                cmd = ["cmd.exe", "/c"] + cmd

            self._active_run_id = run_id
            self._active_jtl_path = jtl_path
            self._state = {
                "active": True,
                "done": False,
                "run_id": run_id,
                "jmx_name": jmx_name,
                "start_time": time.time(),
                "exit_code": None,
                "error": None,
                "live_stats": {},
                "failed_requests": {},
                "stdout_lines": [],
            }

            self._stop_watcher_event.clear()
            self._watcher_thread = threading.Thread(
                target=self._watch_jtl_live, args=(jtl_path, self._stop_watcher_event), daemon=True
            )
            self._watcher_thread.start()

            exec_thread = threading.Thread(
                target=self._run_subprocess, args=(cmd, run_id), daemon=True
            )
            exec_thread.start()

            logger.info(f"Started JMeter test '{jmx_name}' as {run_id}", extra={"run_id": run_id})
            return self.get_status(run_id)

    def _run_subprocess(self, cmd: List[str], run_id: str):
        """Worker thread to execute subprocess and collect lines."""
        env = os.environ.copy()
        if settings.java_home and os.path.exists(settings.java_home):
            env["JAVA_HOME"] = settings.java_home
            env["PATH"] = os.path.join(settings.java_home, "bin") + os.path.pathsep + env.get("PATH", "")

        exit_code = -1
        try:
            self._active_process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(ROOT_DIR),
                env=env,
            )
            for line in iter(self._active_process.stdout.readline, ""):
                if line:
                    with self._lock:
                        self._state["stdout_lines"].append(line.strip())
            self._active_process.stdout.close()
            exit_code = self._active_process.wait()
        except Exception as e:
            with self._lock:
                self._state["error"] = str(e)
                self._state["stdout_lines"].append(f"Process error: {e}")
            logger.error(f"Execution error for {run_id}: {e}")

        self._stop_watcher_event.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2.0)

        with self._lock:
            self._state["active"] = False
            self._state["done"] = True
            self._state["exit_code"] = exit_code
            self._active_process = None

        logger.info(f"JMeter test {run_id} finished with exit code {exit_code}")

    def _watch_jtl_live(self, jtl_path: Path, stop_event: threading.Event):
        """Background thread streaming sample counts and metrics from the live JTL file."""
        import csv
        last_pos = 0
        header = None

        while not stop_event.is_set():
            if jtl_path.exists():
                try:
                    with open(jtl_path, "r", encoding="utf-8", errors="replace") as f:
                        if last_pos > 0:
                            f.seek(last_pos)
                        else:
                            first_line = f.readline()
                            if first_line:
                                reader = csv.reader([first_line.strip()])
                                header_list = next(reader, [])
                                header = [h.strip() for h in header_list]
                                last_pos = f.tell()

                        if header:
                            lines = f.readlines()
                            if lines:
                                last_pos = f.tell()
                                reader = csv.reader(lines)
                                with self._lock:
                                    for row_parts in reader:
                                        if not row_parts or len(row_parts) < len(header):
                                            continue
                                        r = dict(zip(header, [p.strip() for p in row_parts]))
                                        lbl = r.get("label", "Unknown")
                                        success = r.get("success", "true").lower() == "true"
                                        try:
                                            elapsed = int(r.get("elapsed", 0))
                                        except Exception:
                                            elapsed = 0

                                        if lbl not in self._state["live_stats"]:
                                            self._state["live_stats"][lbl] = {
                                                "total": 0, "errors": 0, "total_rt": 0,
                                                "min_rt": elapsed, "max_rt": elapsed,
                                            }
                                        st = self._state["live_stats"][lbl]
                                        st["total"] += 1
                                        st["total_rt"] += elapsed
                                        st["min_rt"] = min(st["min_rt"], elapsed)
                                        st["max_rt"] = max(st["max_rt"], elapsed)

                                        if not success:
                                            st["errors"] += 1
                                            code = r.get("responseCode", "500")
                                            msg = r.get("responseMessage", "HTTP Error")
                                            if lbl not in self._state["failed_requests"]:
                                                self._state["failed_requests"][lbl] = {
                                                    "count": 0, "status_code": code, "sample_error": msg
                                                }
                                            self._state["failed_requests"][lbl]["count"] += 1
                except Exception as e:
                    logger.debug(f"Live watcher read warning: {e}")
            time.sleep(0.5)

    def get_status(self, run_id: Optional[str] = None) -> TestExecutionStatus:
        """Returns the current execution status."""
        with self._lock:
            elapsed = time.time() - self._state["start_time"] if self._state["start_time"] else 0.0
            elapsed_m, elapsed_s = divmod(int(elapsed), 60)
            elapsed_str = f"{elapsed_m:02d}:{elapsed_s:02d}"

            status_str = "running" if self._state["active"] else ("completed" if self._state["done"] else "idle")
            if self._state["error"] or (self._state["exit_code"] is not None and self._state["exit_code"] != 0):
                status_str = "failed"

            return TestExecutionStatus(
                run_id=self._state["run_id"] or run_id or "unknown",
                tool=ToolType.JMETER,
                status=status_str,
                active=self._state["active"],
                done=self._state["done"],
                elapsed_seconds=round(elapsed, 1),
                elapsed_str=elapsed_str,
                error=self._state["error"],
                live_stats=dict(self._state["live_stats"]),
                failed_requests=dict(self._state["failed_requests"]),
                stdout_lines=list(self._state["stdout_lines"][-100:]),
            )

    def stop_test(self, run_id: Optional[str] = None) -> bool:
        """Terminates running JMeter processes."""
        with self._lock:
            self._stop_watcher_event.set()
            if self._active_process:
                try:
                    self._active_process.terminate()
                except Exception:
                    pass

            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "java.exe", "/T"], capture_output=True, text=True)
                except Exception:
                    pass

            self._state["active"] = False
            self._state["done"] = True
            logger.info("Stopped JMeter execution process")
            return True


# Global runner singleton
jmeter_runner = JMeterRunner()
