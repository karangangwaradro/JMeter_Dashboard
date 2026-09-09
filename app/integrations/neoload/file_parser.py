"""
file_parser.py — Parses exported NeoLoad CSV/XML result files into raw dictionary structures.
"""

from pathlib import Path
from typing import Any, Dict
import csv
from app.core.exceptions import ParserError


def parse_neoload_csv_export(file_path: Path) -> Dict[str, Any]:
    """Parses a NeoLoad CSV export into a dictionary representation."""
    if not file_path.exists():
        raise ParserError(f"NeoLoad CSV file not found: {file_path}")

    elements = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Element", row.get("Name", row.get("Transaction", "Unknown")))
                count = int(row.get("Count", row.get("Requests", 0)))
                errors = int(row.get("Errors", row.get("Error Count", 0)))
                avg_dur = float(row.get("Average", row.get("Avg Duration", row.get("Duration", 0.0))))
                elements.append({
                    "name": name,
                    "count": count,
                    "errorCount": errors,
                    "durationAverage": avg_dur,
                    "durationMin": float(row.get("Min", avg_dur)),
                    "durationMax": float(row.get("Max", avg_dur)),
                    "durationP90": float(row.get("90%", avg_dur * 1.3)),
                    "durationP95": float(row.get("95%", avg_dur * 1.5)),
                    "durationP99": float(row.get("99%", avg_dur * 2.0)),
                })

        total_reqs = sum(e["count"] for e in elements)
        total_errs = sum(e["errorCount"] for e in elements)
        total_avg = (sum(e["durationAverage"] * e["count"] for e in elements) / total_reqs) if total_reqs > 0 else 0.0

        return {
            "statistics": {
                "totalRequestCount": total_reqs,
                "totalErrorCount": total_errs,
                "totalRequestDurationAverage": total_avg,
                "totalDuration": 60.0,
            },
            "elements": elements,
            "points": [],
        }
    except Exception as e:
        raise ParserError(f"Failed to parse NeoLoad CSV export {file_path.name}: {e}")
