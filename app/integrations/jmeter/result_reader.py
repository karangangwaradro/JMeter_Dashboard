"""
result_reader.py — JTL result file reader implementing ResultCollector.
Responsible ONLY for locating and reading raw CSV/XML JTL files from disk.
Does NOT parse, normalize, or compute statistics.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import csv

from app.core.constants import RESULTS_JTL_DIR
from app.core.exceptions import ResultCollectionError
from app.domain.interfaces.result_collector import ResultCollector


class JMeterResultReader(ResultCollector):
    """Collects and retrieves raw JMeter JTL log files."""

    def collect_raw_results(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Path:
        """Locates the raw JTL file for a given test run."""
        candidates = [
            RESULTS_JTL_DIR / f"{run_id}.jtl",
            RESULTS_JTL_DIR / f"run_{run_id}.jtl",
            RESULTS_JTL_DIR.parent / f"{run_id}.jtl",
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return p

        # Check if run_id is already an absolute or relative path
        direct_path = Path(run_id)
        if direct_path.exists() and direct_path.is_file():
            return direct_path

        raise ResultCollectionError(
            f"JMeter JTL file not found for run '{run_id}'",
            context={"searched_paths": [str(c) for c in candidates]}
        )

    def read_rows(self, jtl_path: Path) -> List[Dict[str, Any]]:
        """Reads raw CSV records from the JTL file into a list of row dictionaries."""
        if not jtl_path.exists():
            raise ResultCollectionError(f"JTL file does not exist: {jtl_path}")

        rows = []
        try:
            with open(jtl_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            return rows
        except Exception as e:
            raise ResultCollectionError(
                f"Failed to read raw JTL records from {jtl_path.name}: {e}",
                context={"jtl_path": str(jtl_path)}
            )


# Global singleton
jmeter_result_reader = JMeterResultReader()
