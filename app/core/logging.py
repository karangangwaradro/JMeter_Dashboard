"""
logging.py — Centralized structured logging for PerfPilot.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Formats log records as readable text with structured contextual metadata."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        msg = record.getMessage()

        context_dict = getattr(record, "context", None)
        ctx_str = ""
        if context_dict and isinstance(context_dict, dict):
            try:
                ctx_str = f" | ctx={json.dumps(context_dict, default=str)}"
            except Exception:
                ctx_str = f" | ctx={context_dict}"

        level = record.levelname
        name = record.name
        return f"[{timestamp}] [{level:<7}] [{name}] {msg}{ctx_str}"


def get_logger(name: str = "perfpilot") -> logging.Logger:
    """Returns a configured logger instance with structured output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = get_logger()
