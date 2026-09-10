"""
file_source.py — File upload result source for raw performance logs and multi-file archives.
Handles single files (.jtl, .csv, .json) and zip bundles (.zip) containing kpi.jtl and error.jtl.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import STORAGE_RAW_DIR
from app.core.exceptions import ResultCollectionError
from app.core.logging import logger
from app.domain.interfaces.result_collector import ResultSource


class FileResultSource(ResultSource):
    """Handles raw result file uploads (JTL, BlazeMeter JSON/ZIP, NeoLoad CSV/XML)."""

    def fetch_data(self, identifier: str, options: Optional[Dict[str, Any]] = None) -> Path:
        """
        Locates, unpacks (if zip), or copies the uploaded file into storage/raw/ and returns the Path.
        Registers auxiliary files (e.g. error.jtl) in options.
        """
        options = options if options is not None else {}
        source_path = Path(identifier)

        if not source_path.exists():
            # Check in storage/raw
            in_raw = STORAGE_RAW_DIR / source_path.name
            if in_raw.exists():
                source_path = in_raw
            else:
                raise ResultCollectionError(f"Uploaded file '{identifier}' not found")

        # If source is a directory
        if source_path.is_dir():
            kpi_cand = source_path / "kpi.jtl"
            err_cand = source_path / "error.jtl"
            if err_cand.exists():
                options["error_jtl_path"] = str(err_cand)
            if kpi_cand.exists():
                return kpi_cand
            return source_path

        # If source is a .zip archive
        if source_path.suffix.lower() == ".zip":
            extract_dir = STORAGE_RAW_DIR / source_path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Extracting zip archive '{source_path.name}' to '{extract_dir}'...")

            try:
                with zipfile.ZipFile(source_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                raise ResultCollectionError(f"Failed to extract zip archive '{source_path.name}': {e}")

            # Locate kpi.jtl and error.jtl
            kpi_file = extract_dir / "kpi.jtl"
            if not kpi_file.exists():
                # Search recursively
                for cand in extract_dir.rglob("kpi.jtl"):
                    kpi_file = cand
                    break
                if not kpi_file.exists():
                    for cand in extract_dir.rglob("*.jtl"):
                        if cand.name != "error.jtl":
                            kpi_file = cand
                            break

            error_file = extract_dir / "error.jtl"
            if not error_file.exists():
                for cand in extract_dir.rglob("error.jtl"):
                    error_file = cand
                    break

            if error_file and error_file.exists():
                options["error_jtl_path"] = str(error_file)
                logger.info(f"Discovered BlazeMeter error trace log: {error_file}")

            # Discover optional JMX test plan in archive
            jmx_file = None
            for cand in extract_dir.rglob("*.jmx"):
                jmx_file = cand
                break
            if jmx_file and jmx_file.exists():
                options["jmx_file_path"] = str(jmx_file)
                options["jmx_name"] = jmx_file.stem
                if not options.get("test_name"):
                    options["test_name"] = jmx_file.stem
                from app.core.constants import TESTS_DIR
                target_jmx = TESTS_DIR / jmx_file.name
                if not target_jmx.exists():
                    shutil.copy2(jmx_file, target_jmx)
                logger.info(f"Discovered JMX test scenario in archive: {jmx_file.name}")

            # Discover optional SLA CSV in archive
            sla_file = None
            for cand in extract_dir.rglob("*sla*.csv"):
                sla_file = cand
                break
            if sla_file and sla_file.exists():
                options["sla_file_path"] = str(sla_file)
                logger.info(f"Discovered SLA targets CSV in archive: {sla_file.name}")

            if kpi_file and kpi_file.exists():
                return kpi_file

            return extract_dir

        # Standard single file copy to storage/raw
        target_path = STORAGE_RAW_DIR / source_path.name
        if source_path.resolve() != target_path.resolve():
            shutil.copy2(source_path, target_path)

        # Check for sibling error.jtl
        sibling_error = source_path.parent / "error.jtl"
        if sibling_error.exists() and "error_jtl_path" not in options:
            options["error_jtl_path"] = str(sibling_error)

        return target_path


# Global singleton
file_result_source = FileResultSource()
