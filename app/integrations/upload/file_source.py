"""
file_source.py — File upload result source for raw performance logs.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import shutil

from app.core.constants import STORAGE_RAW_DIR
from app.core.exceptions import ResultCollectionError
from app.domain.interfaces.result_collector import ResultSource


class FileResultSource(ResultSource):
    """Handles raw result file uploads (JTL, BlazeMeter JSON/ZIP, NeoLoad CSV/XML)."""

    def fetch_data(self, identifier: str, options: Optional[Dict[str, Any]] = None) -> Path:
        """
        Locates or copies the uploaded file into storage/raw/ and returns the Path.
        """
        source_path = Path(identifier)
        if not source_path.exists():
            # Check in storage/raw
            in_raw = STORAGE_RAW_DIR / source_path.name
            if in_raw.exists():
                return in_raw
            raise ResultCollectionError(f"Uploaded file '{identifier}' not found")

        # Copy to storage/raw if not already there
        target_path = STORAGE_RAW_DIR / source_path.name
        if source_path.resolve() != target_path.resolve():
            shutil.copy2(source_path, target_path)

        return target_path


# Global singleton
file_result_source = FileResultSource()
