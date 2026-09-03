#!/usr/bin/env python3
"""
main.py — Entry point for PerfPilot.

Boots the web server on port 8080 and auto-opens the dashboard UI in the browser.

Usage:
    python main.py
"""

import sys
import os
import time
import webbrowser
import threading
from pathlib import Path

_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services import web_server


def main():
    _load_env = getattr(web_server, "_load_env", None)
    if _load_env:
        _load_env()

    port_str = os.environ.get("PORT", "8080").strip()
    port = int(port_str) if port_str.isdigit() else 8080
    url = f"http://127.0.0.1:{port}/"

    def open_browser():
        import urllib.request
        for _ in range(40):
            time.sleep(0.25)
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                pass
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    web_server.start_server(port=port)


if __name__ == "__main__":
    main()
