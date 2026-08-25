#!/usr/bin/env python3
"""
main.py — Entry point for JmeterAI.

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
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║   ⚡ JmeterAI — Local Performance Testing Utility    ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    url = "http://localhost:8080/"

    def open_browser():
        import urllib.request
        for _ in range(30):
            time.sleep(0.3)
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                pass
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    web_server.start_server(port=8080)


if __name__ == "__main__":
    main()
