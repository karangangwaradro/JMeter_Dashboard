"""
error_parser.py — BlazeMeter XML Error Parser.
Parses BlazeMeter error.jtl files (XML format) into structured ErrorDetail models.
Extracts HTTP status codes, root cause messages from responseData, and error samples.
"""

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.exceptions import ParserError
from app.core.logging import logger
from app.domain.models.aggregate import ErrorDetail, ErrorOccurrence


class BlazeMeterErrorParser:
    """Parses BlazeMeter XML error.jtl logs into strongly-typed ErrorDetail domain models."""

    def parse_errors(self, error_file: Union[Path, str]) -> Dict[str, ErrorDetail]:
        """
        Parses error.jtl (XML format) and returns a mapping of error_key -> ErrorDetail.
        """
        path = Path(error_file)
        if not path.exists():
            logger.warning(f"BlazeMeter error file does not exist: {path}")
            return {}

        errors_map: Dict[str, Dict[str, Any]] = {}

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            for elem in root:
                # In BlazeMeter error.jtl, leaf HTTP requests are <httpSample>.
                # Container/transaction rollups are <sample> with message "Number of samples in transaction...".
                # We focus on the leaf HTTP samples to avoid double-counting and to obtain actual root causes.
                tag = elem.tag.lower()
                if tag != "httpsample":
                    # If it's a sample without httpSample tag, verify if it's a leaf request or transaction rollup
                    rm = elem.get("rm", "")
                    if "number of samples in transaction" in rm.lower():
                        continue
                    if elem.get("s", "true").lower() == "true":
                        continue

                s_val = elem.get("s", "true").lower()
                if s_val == "true":
                    continue

                rc = elem.get("rc", "Unknown").strip()
                rm = elem.get("rm", "").strip()
                lb = elem.get("lb", "").strip()
                ts = int(elem.get("ts", 0))
                t = int(elem.get("t", 0))

                # Extract URL and responseData if present
                url_elem = elem.find("java.net.URL")
                url = url_elem.text.strip() if url_elem is not None and url_elem.text else ""

                rd_elem = elem.find("responseData")
                resp_text = rd_elem.text if rd_elem is not None and rd_elem.text else ""
                resp_text = html.unescape(resp_text)

                # Extract failure message from assertion if available
                assertion_elem = elem.find(".//failureMessage")
                assertion_msg = assertion_elem.text.strip() if assertion_elem is not None and assertion_elem.text else ""

                clean_msg, failure_snippet = self._extract_root_cause(rc, rm, resp_text, assertion_msg, url)

                error_key = f"HTTP {rc} - {clean_msg}" if rc and rc != "Unknown" else clean_msg

                if error_key not in errors_map:
                    errors_map[error_key] = {
                        "error_key": error_key,
                        "code": rc,
                        "message": clean_msg,
                        "failure_message": failure_snippet,
                        "count": 0,
                        "occurrences": [],
                    }

                errors_map[error_key]["count"] += 1
                if len(errors_map[error_key]["occurrences"]) < 50:
                    errors_map[error_key]["occurrences"].append(
                        ErrorOccurrence(
                            label=lb,
                            timestamp=ts,
                            elapsed=t,
                        )
                    )

            result: Dict[str, ErrorDetail] = {}
            for k, v in errors_map.items():
                result[k] = ErrorDetail(
                    error_key=v["error_key"],
                    code=v["code"],
                    message=v["message"],
                    failure_message=v["failure_message"],
                    count=v["count"],
                    occurrences=v["occurrences"],
                )

            logger.info(f"Parsed {sum(e.count for e in result.values())} errors ({len(result)} categories) from BlazeMeter error.jtl")
            return result

        except Exception as e:
            logger.error(f"Failed to parse BlazeMeter error file {path}: {e}")
            raise ParserError(f"Failed to parse BlazeMeter error.jtl: {e}")

    def _extract_root_cause(
        self, rc: str, rm: str, resp_text: str, assertion_msg: str, url: str
    ) -> Tuple[str, str]:
        """
        Derives a human-readable, concise error message and representative failure snippet.
        """
        if assertion_msg:
            return assertion_msg, assertion_msg

        snippet = resp_text[:1000].strip()

        # Check for HTML Tomcat / Jetty / Application error reports
        if "Stripes validation error report" in resp_text:
            msg = "Stripes validation error: missing source page resolution"
            return msg, snippet or msg

        # Check for standard server error message tags: <p><b>Message</b> ...</p>
        msg_match = re.search(r"<p><b>Message</b>\s*([^<]+)</p>", resp_text, re.IGNORECASE)
        if msg_match:
            clean_msg = msg_match.group(1).strip()
            # Clean common formatting
            clean_msg = clean_msg.replace("&#47;", "/")
            return clean_msg, snippet or clean_msg

        # Check for <title>HTTP Status ...</title>
        title_match = re.search(r"<title>HTTP Status \d+ [–-]\s*([^<]+)</title>", resp_text, re.IGNORECASE)
        if title_match:
            clean_msg = title_match.group(1).strip()
            return clean_msg, snippet or clean_msg

        # Fallback to response message or status code
        if rm:
            return rm, snippet or rm

        if rc == "404":
            return f"Resource Not Found ({url})" if url else "Not Found (404)", snippet
        elif rc == "500":
            return "Internal Server Error (500)", snippet
        elif rc == "502":
            return "Bad Gateway (502)", snippet
        elif rc == "503":
            return "Service Unavailable (503)", snippet
        elif rc == "504":
            return "Gateway Timeout (504)", snippet

        return f"HTTP {rc} Error", snippet


# Global singleton
blazemeter_error_parser = BlazeMeterErrorParser()
