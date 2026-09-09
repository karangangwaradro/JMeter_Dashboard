"""
aggregate_parser.py — Converts JMeter JTL log data into a typed AggregateResult.
Responsible ONLY for calculating summary KPIs, percentiles, and transaction breakdowns.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

from app.core.exceptions import ParserError
from app.domain.interfaces.parser import AggregateParser
from app.domain.models.aggregate import (
    AggregateResult,
    TransactionMetric,
    ErrorDetail,
    ErrorOccurrence,
)
from app.integrations.jmeter.result_reader import jmeter_result_reader


def _pct(lst: List[int], p: float) -> int:
    if not lst:
        return 0
    idx = max(0, int(len(lst) * p / 100) - 1)
    return lst[idx]


def _get_col(row_dict: dict, key_name: str, default: Any = "") -> Any:
    if key_name in row_dict:
        return row_dict[key_name]
    for k, v in row_dict.items():
        if k and k.lower() == key_name.lower():
            return v
    return default


def _is_transaction(lbl: str) -> bool:
    u = (lbl or "").upper()
    if "_R_" in u or "_R0" in u or "_R1" in u or u.startswith("HTTP_") or u.startswith("GET_") or u.startswith("POST_"):
        return False
    return bool(u.startswith("TC") or u.startswith("T_") or u.startswith("T-") or "LAUNCH" in u or "SELECT" in u or "SEARCH" in u or "SIGN" in u or "CHECKOUT" in u)


class JMeterAggregateParser(AggregateParser):
    """Translates raw JTL sample records into a typed AggregateResult."""

    def parse_aggregate(self, raw_data: Union[Path, str, List[Dict[str, Any]]], test_id: str) -> AggregateResult:
        """Parses JTL rows into a validated AggregateResult model."""
        try:
            if isinstance(raw_data, (str, Path)):
                rows = jmeter_result_reader.read_rows(Path(raw_data))
            elif isinstance(raw_data, list):
                rows = raw_data
            else:
                raise ParserError(f"Unsupported raw_data type for JTL aggregate parsing: {type(raw_data)}")

            if not rows:
                return AggregateResult(
                    test_id=test_id,
                    tool="jmeter",
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    error_rate=0.0,
                    throughput=0.0,
                    avg_response_time=0.0,
                    min_response_time=0.0,
                    max_response_time=0.0,
                    p50=0.0,
                    p90=0.0,
                    p95=0.0,
                    p99=0.0,
                    duration_seconds=0.0,
                    start_epoch=0,
                    end_epoch=0,
                )

            total = len(rows)
            raw_errors = 0
            elapsed_values: List[int] = []
            timestamps: List[int] = []
            label_data: Dict[str, Dict[str, Any]] = {}
            tg_label_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
            error_details_map: Dict[str, Dict[str, Any]] = {}

            for r in rows:
                try:
                    elapsed = int(_get_col(r, "elapsed", 0))
                    elapsed_values.append(elapsed)
                except (ValueError, TypeError):
                    elapsed = 0

                try:
                    ts = int(_get_col(r, "timeStamp", 0))
                    if ts > 0:
                        timestamps.append(ts)
                except (ValueError, TypeError):
                    ts = 0

                label = _get_col(r, "label", "Total")
                if label not in label_data:
                    label_data[label] = {"count": 0, "errors": 0, "elapsed": [], "success_flags": []}
                label_data[label]["count"] += 1
                label_data[label]["elapsed"].append(elapsed)

                # Thread group disaggregation
                t_name = _get_col(r, "threadName", "").strip()
                tg_key = t_name.rsplit(" ", 1)[0].strip() if (" " in t_name and any(c.isdigit() for c in t_name.rsplit(" ", 1)[1])) else t_name
                if tg_key:
                    if tg_key not in tg_label_data:
                        tg_label_data[tg_key] = {}
                    if label not in tg_label_data[tg_key]:
                        tg_label_data[tg_key][label] = {"count": 0, "errors": 0, "elapsed": [], "success_flags": []}
                    tg_label_data[tg_key][label]["count"] += 1
                    tg_label_data[tg_key][label]["elapsed"].append(elapsed)

                is_succ = str(_get_col(r, "success", "true")).lower() == "true"
                label_data[label]["success_flags"].append(is_succ)
                if tg_key and tg_key in tg_label_data and label in tg_label_data[tg_key]:
                    tg_label_data[tg_key][label]["success_flags"].append(is_succ)

                if not is_succ:
                    raw_errors += 1
                    label_data[label]["errors"] += 1
                    if tg_key and tg_key in tg_label_data and label in tg_label_data[tg_key]:
                        tg_label_data[tg_key][label]["errors"] += 1

                    resp_code = str(_get_col(r, "responseCode", "")).strip()
                    resp_msg = str(_get_col(r, "responseMessage", "")).strip()
                    failure_msg = str(_get_col(r, "failureMessage", "")).strip()

                    f_lower = failure_msg.lower()
                    r_lower = resp_msg.lower()
                    lbl_lower = label.lower()
                    u_lbl = label.upper()
                    url_val = str(_get_col(r, "URL", "")).strip()

                    is_http_request = (
                        "_R_" in u_lbl or "_R0" in u_lbl or "_R1" in u_lbl or
                        u_lbl.startswith("HTTP_") or u_lbl.startswith("GET_") or u_lbl.startswith("POST_") or
                        bool(url_val and url_val not in ("", "null", "None"))
                    )

                    is_tc_rollup = (
                        "samples in transaction" in f_lower or "samples in transaction" in r_lower or
                        "failed samples" in f_lower or "failed samples" in r_lower or
                        "failing samples" in f_lower or "failing samples" in r_lower or
                        "transaction failed" in f_lower or "transaction failed" in r_lower or
                        "transaction controller" in lbl_lower or "overall_iteration" in lbl_lower
                    )
                    if not is_http_request:
                        is_tc_rollup = is_tc_rollup or (u_lbl.startswith("T-") or "CONTROLLER" in u_lbl)

                    if not is_tc_rollup or is_http_request:
                        if failure_msg:
                            err_key = failure_msg[:80]
                        elif resp_code and resp_code not in ("", "200"):
                            err_key = f"{resp_code} {resp_msg}" if resp_msg else resp_code
                        else:
                            err_key = resp_msg if resp_msg else "Unknown Error"
                        err_key = err_key.strip()

                        if err_key not in error_details_map:
                            error_details_map[err_key] = {
                                "code": resp_code,
                                "message": resp_msg,
                                "failure_message": failure_msg,
                                "count": 0,
                                "occurrences": [],
                            }
                        error_details_map[err_key]["count"] += 1
                        if len(error_details_map[err_key]["occurrences"]) < 50:
                            error_details_map[err_key]["occurrences"].append(
                                ErrorOccurrence(label=label, timestamp=ts, elapsed=elapsed)
                            )

            elapsed_values.sort()
            n = len(elapsed_values)
            start_ts = min(timestamps) if timestamps else 0
            end_ts = max(timestamps) if timestamps else 0
            duration_sec = (end_ts - start_ts) / 1000 if end_ts > start_ts else 1.0

            # Build transactions map
            transactions: Dict[str, TransactionMetric] = {}
            for lname, ldata in label_data.items():
                s_elapsed = sorted(ldata["elapsed"])
                ln = len(s_elapsed)
                err_count = ldata["errors"]
                err_rate = round(err_count / ln * 100, 2) if ln > 0 else 0.0

                transactions[lname] = TransactionMetric(
                    label=lname,
                    count=ldata["count"],
                    errors=err_count,
                    error_rate=err_rate,
                    avg_rt=round(sum(s_elapsed) / ln, 2) if ln > 0 else 0.0,
                    min_rt=float(min(s_elapsed)) if s_elapsed else 0.0,
                    max_rt=float(max(s_elapsed)) if s_elapsed else 0.0,
                    p50=float(_pct(s_elapsed, 50)),
                    p90=float(_pct(s_elapsed, 90)),
                    p95=float(_pct(s_elapsed, 95)),
                    p99=float(_pct(s_elapsed, 99)),
                    samples=ldata["elapsed"][:500],  # cap raw sample arrays
                    success_flags=ldata["success_flags"][:500],
                )

            # Build thread group transactions map
            transactions_by_tg: Dict[str, Dict[str, TransactionMetric]] = {}
            for tg_k, tg_lbls in tg_label_data.items():
                transactions_by_tg[tg_k] = {}
                for lname, ldata in tg_lbls.items():
                    s_elapsed = sorted(ldata["elapsed"])
                    ln = len(s_elapsed)
                    err_count = ldata["errors"]
                    err_rate = round(err_count / ln * 100, 2) if ln > 0 else 0.0
                    transactions_by_tg[tg_k][lname] = TransactionMetric(
                        label=lname,
                        count=ldata["count"],
                        errors=err_count,
                        error_rate=err_rate,
                        avg_rt=round(sum(s_elapsed) / ln, 2) if ln > 0 else 0.0,
                        min_rt=float(min(s_elapsed)) if s_elapsed else 0.0,
                        max_rt=float(max(s_elapsed)) if s_elapsed else 0.0,
                        p50=float(_pct(s_elapsed, 50)),
                        p90=float(_pct(s_elapsed, 90)),
                        p95=float(_pct(s_elapsed, 95)),
                        p99=float(_pct(s_elapsed, 99)),
                    )

            # Error details model mapping
            errors_breakdown: Dict[str, ErrorDetail] = {}
            for ekey, edata in error_details_map.items():
                errors_breakdown[ekey] = ErrorDetail(
                    error_key=ekey,
                    code=edata["code"],
                    message=edata["message"],
                    failure_message=edata["failure_message"],
                    count=edata["count"],
                    occurrences=edata["occurrences"],
                )

            # Transaction controllers vs leaf requests
            tc_main = {k: v for k, v in transactions.items() if _is_transaction(k)}
            if not tc_main:
                tc_main = transactions

            total_iterations = max((v.count for v in tc_main.values()), default=total) if tc_main else total
            total_tx_execs = sum(v.count for v in tc_main.values()) if tc_main else total
            tc_errors = sum(v.errors for v in tc_main.values()) if tc_main else raw_errors
            tc_err_rate = round((tc_errors / total_tx_execs * 100), 2) if total_tx_execs > 0 else 0.0

            leaf_http_errors = sum(ed.count for ed in errors_breakdown.values())
            final_errors = leaf_http_errors if (errors_breakdown or leaf_http_errors > 0) else raw_errors
            raw_err_pct = round((final_errors / total * 100), 2) if total > 0 else 0.0
            throughput = total / duration_sec if duration_sec > 0 else 0.0

            return AggregateResult(
                schema_version="1.0",
                test_id=test_id,
                tool="jmeter",
                total_requests=total,
                total_iterations=total_iterations,
                successful_requests=total - final_errors,
                failed_requests=final_errors,
                error_rate=tc_err_rate,
                raw_error_rate=raw_err_pct,
                throughput=round(throughput, 2),
                avg_response_time=round(sum(elapsed_values) / n, 2) if n > 0 else 0.0,
                min_response_time=float(min(elapsed_values)) if elapsed_values else 0.0,
                max_response_time=float(max(elapsed_values)) if elapsed_values else 0.0,
                p50=float(_pct(elapsed_values, 50)),
                p90=float(_pct(elapsed_values, 90)),
                p95=float(_pct(elapsed_values, 95)),
                p99=float(_pct(elapsed_values, 99)),
                duration_seconds=round(duration_sec, 1),
                start_epoch=start_ts // 1000 if start_ts else 0,
                end_epoch=end_ts // 1000 if end_ts else 0,
                transactions=transactions,
                transactions_by_thread_group=transactions_by_tg,
                errors_breakdown=errors_breakdown,
            )
        except Exception as e:
            raise ParserError(f"Failed to parse JMeter aggregate metrics: {e}", context={"test_id": test_id})


# Global singleton instance
jmeter_aggregate_parser = JMeterAggregateParser()
