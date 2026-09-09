"""
constants.py — Global constants and directory paths for PerfPilot.
"""

from pathlib import Path

# Base Paths
ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
RESULTS_DIR = ROOT_DIR / "Results"
RESULTS_HTML_DIR = RESULTS_DIR / "html"
RESULTS_JSON_DIR = RESULTS_DIR / "json"
RESULTS_JTL_DIR = RESULTS_DIR / "jtl"
RESULTS_PUBLISHED_DIR = RESULTS_DIR / "Published"
STORAGE_NORMALIZED_DIR = RESULTS_DIR / "normalized"
STORAGE_RAW_DIR = RESULTS_DIR / "raw"
TESTS_DIR = ROOT_DIR / "Tests"
WEB_DIR = ROOT_DIR / "web"
SCHEMAS_DIR = ROOT_DIR / "schemas"

# Ensure essential runtime directories exist
for d in (
    CONFIG_DIR,
    DATA_DIR,
    LOGS_DIR,
    RESULTS_DIR,
    RESULTS_HTML_DIR,
    RESULTS_JSON_DIR,
    RESULTS_JTL_DIR,
    RESULTS_PUBLISHED_DIR,
    STORAGE_NORMALIZED_DIR,
    STORAGE_RAW_DIR,
    TESTS_DIR,
    WEB_DIR,
    SCHEMAS_DIR,
):
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_SCHEMA_VERSION = "1.0"
