"""
server.py — Production-grade web server bootstrapper for PerfPilot.
Runs the modular FastAPI application with Uvicorn and port-hunting fallback.
"""
import os
import sys
import socket
from pathlib import Path
from typing import Optional

from app.core.config import load_env_file, settings
from app.core.logging import logger
from app.api.app import app


def _load_env():
    """Helper to load environment configuration."""
    load_env_file()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def start_server(host: Optional[str] = None, port: Optional[int] = None) -> int:
    """
    Starts the production FastAPI application via Uvicorn.
    Performs automatic port hunting from base port up to base+10.
    """
    import uvicorn

    load_env_file()
    selected_host = host or settings.host
    selected_port = port or settings.port

    actual_port = selected_port
    for p in range(selected_port, selected_port + 10):
        if not is_port_in_use(p, "127.0.0.1"):
            actual_port = p
            break
        else:
            print(f"  [!] Port {p} is in use. Trying port {p + 1}...", flush=True)

    print(f"\n  +------------------------------------------------------+")
    print(f"  |   PerfPilot Platform (Production FastAPI) Ready!     |")
    print(f"  |   -> Dashboard: http://localhost:{actual_port}/                |")
    print(f"  |   -> API Docs:  http://localhost:{actual_port}/docs            |")
    print(f"  |   -> OpenAPI:   http://localhost:{actual_port}/redoc           |")
    print(f"  |   Press Ctrl+C in terminal to stop.                  |")
    print(f"  +------------------------------------------------------+\n", flush=True)

    config = uvicorn.Config(
        app=app,
        host=selected_host,
        port=actual_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n  [SERVER] Stopped.", flush=True)
    except Exception as e:
        logger.error(f"Server runtime error: {e}")

    return actual_port


if __name__ == "__main__":
    start_server()
