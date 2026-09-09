#!/usr/bin/env python3
"""
organize_results.py — Organizes output files into html/, json/, jtl/ subdirectories.
"""
import sys
import shutil
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.constants import RESULTS_DIR, RESULTS_HTML_DIR, RESULTS_JSON_DIR, RESULTS_JTL_DIR


def organize():
    for d in (RESULTS_HTML_DIR, RESULTS_JSON_DIR, RESULTS_JTL_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # Move HTML files
    for f_path in RESULTS_DIR.glob("*.html"):
        if f_path.is_file():
            shutil.move(str(f_path), str(RESULTS_HTML_DIR / f_path.name))

    # Move JSON files
    for f_path in RESULTS_DIR.glob("*.json"):
        if f_path.is_file():
            shutil.move(str(f_path), str(RESULTS_JSON_DIR / f_path.name))

    # Move JTL files
    for f_path in RESULTS_DIR.glob("*.jtl"):
        if f_path.is_file():
            shutil.move(str(f_path), str(RESULTS_JTL_DIR / f_path.name))


if __name__ == "__main__":
    organize()
