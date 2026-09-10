"""
kpi_parser.py — BlazeMeter kpi.jtl (CSV) Performance Log Parser.
Parses BlazeMeter raw execution samples into strongly-typed AggregateResult and TimeSeriesResult domain models.
Maintains strict separation: does NOT depend on JMeter or NeoLoad parsers.
"""

import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.constants import TESTS_DIR
from app.core.exceptions import ParserError
from app.core.logging import logger
from app.domain.models.aggregate import (
    AggregateResult,
    TransactionMetric,
    ErrorDetail,
)
from app.domain.models.timeseries import TimeSeriesResult, LabelTimeSeries
from app.integrations.blazemeter.error_parser import blazemeter_error_parser


def _is_http_request(lbl: str) -> bool:
    """Identify if a sample label represents a leaf HTTP request sampler."""
    u = (lbl or "").upper()
    return bool(
        "_R_" in u or "_R0" in u or "_R1" in u or
        u.startswith("HTTP_") or u.startswith("GET_") or u.startswith("POST_") or
        u.startswith("PUT_") or u.startswith("DELETE_")
    )


def _clean_thread_group_name(thread_name: str) -> str:
    """Clean thread name into canonical thread group / user story name."""
    # BlazeMeter format: "TC_01_Browse_Catalog-ThreadStarter 1-1" or "TC_01_Browse_Catalog 1-1"
    clean = thread_name.split("-ThreadStarter")[0].strip()
    if " " in clean:
        clean = clean.rsplit(" ", 1)[0].strip()
    return clean


def _calc_pct(lst_sorted: List[int], p: float) -> float:
    """Calculate percentile from a sorted list of integers."""
    if not lst_sorted:
        return 0.0
    idx = max(0, int(len(lst_sorted) * p / 100.0) - 1)
    return float(lst_sorted[idx])


class BlazeMeterKPIParser:
    """Parses BlazeMeter kpi.jtl (CSV) logs into typed domain contracts."""

    def parse_kpi(
        self,
        kpi_file: Union[Path, str],
        test_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AggregateResult:
        """
        Parses BlazeMeter kpi.jtl and returns a fully populated AggregateResult.
        """
        path = Path(kpi_file)
        if not path.exists():
            raise ParserError(f"BlazeMeter KPI file not found: {path}", context={"test_id": test_id})

        options = options or {}
        jmx_name = options.get("jmx_name") or options.get("test_name", "")

        # Statistics accumulation per label
        label_stats: Dict[str, Dict[str, Any]] = {}
        all_timestamps: List[int] = []
        raw_total_samples = 0
        raw_error_samples = 0

        try:
            with open(path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                # Case-insensitive column resolution
                col_map = {c.strip().lower(): c for c in fieldnames}

                ts_col = col_map.get("timestamp", "timeStamp")
                el_col = col_map.get("elapsed", "elapsed")
                lb_col = col_map.get("label", "label")
                rc_col = col_map.get("responsecode", "responseCode")
                rm_col = col_map.get("responsemessage", "responseMessage")
                tn_col = col_map.get("threadname", "threadName")
                sc_col = col_map.get("success", "success")

                for row in reader:
                    lbl = (row.get(lb_col) or "").strip()
                    if not lbl:
                        continue

                    raw_total_samples += 1

                    try:
                        elapsed = int(float(row.get(el_col, 0)))
                    except (ValueError, TypeError):
                        elapsed = 0

                    try:
                        ts = int(row.get(ts_col, 0))
                        if ts > 0:
                            all_timestamps.append(ts)
                    except (ValueError, TypeError):
                        pass

                    success_str = str(row.get(sc_col, "true")).strip().lower()
                    is_success = success_str in ("true", "1")
                    if not is_success:
                        raw_error_samples += 1

                    thread_name = row.get(tn_col, "")
                    tg_clean = _clean_thread_group_name(thread_name)

                    if lbl not in label_stats:
                        label_stats[lbl] = {
                            "samples": [],
                            "successes": 0,
                            "errors": 0,
                            "user_story": tg_clean,
                        }

                    label_stats[lbl]["samples"].append(elapsed)
                    if is_success:
                        label_stats[lbl]["successes"] += 1
                    else:
                        label_stats[lbl]["errors"] += 1

            if not label_stats:
                raise ParserError(f"No sample records found in {path.name}", context={"test_id": test_id})

            # Calculate duration and time bounds
            min_ts = min(all_timestamps) if all_timestamps else 0
            max_ts = max(all_timestamps) if all_timestamps else 0
            start_epoch = int(min_ts / 1000) if min_ts > 0 else 0
            end_epoch = int(max_ts / 1000) if max_ts > 0 else 0
            duration_sec = max(1.0, round((max_ts - min_ts) / 1000.0, 2)) if max_ts > min_ts else 60.0

            # Build TransactionMetric models
            transactions: Dict[str, TransactionMetric] = {}
            http_requests: Dict[str, TransactionMetric] = {}
            all_labels: Dict[str, TransactionMetric] = {}
            transactions_by_tg: Dict[str, Dict[str, TransactionMetric]] = {}

            for lbl, data in label_stats.items():
                samples_sorted = sorted(data["samples"])
                count = len(samples_sorted)
                errors = data["errors"]
                error_rate = round((errors / count * 100.0), 2) if count > 0 else 0.0
                avg_rt = round(sum(samples_sorted) / count, 2) if count > 0 else 0.0
                min_rt = float(samples_sorted[0]) if samples_sorted else 0.0
                max_rt = float(samples_sorted[-1]) if samples_sorted else 0.0
                p50 = _calc_pct(samples_sorted, 50.0)
                p90 = _calc_pct(samples_sorted, 90.0)
                p95 = _calc_pct(samples_sorted, 95.0)
                p99 = _calc_pct(samples_sorted, 99.0)

                is_req = _is_http_request(lbl)
                item_type = "HTTP_REQUEST" if is_req else "MAIN_TRANSACTION"
                item_type_lbl = "HTTP Request" if is_req else "Main Transaction"
                depth = 1 if is_req else 0
                tg_name = data["user_story"]

                metric = TransactionMetric(
                    label=lbl,
                    count=count,
                    errors=errors,
                    error_rate=error_rate,
                    avg_rt=avg_rt,
                    min_rt=min_rt,
                    max_rt=max_rt,
                    p50=p50,
                    p90=p90,
                    p95=p95,
                    p99=p99,
                    samples=samples_sorted,
                    item_type=item_type,
                    item_type_label=item_type_lbl,
                    depth=depth,
                    user_story=tg_name,
                )

                all_labels[lbl] = metric
                if is_req:
                    http_requests[lbl] = metric
                else:
                    transactions[lbl] = metric
                    if tg_name:
                        if tg_name not in transactions_by_tg:
                            transactions_by_tg[tg_name] = {}
                        transactions_by_tg[tg_name][lbl] = metric

            # If no transaction controllers exist in test, fallback transactions to all_labels
            effective_transactions = transactions if transactions else all_labels

            # Determine parent-child links and compile hierarchy tree
            hierarchy_tree = self._compile_hierarchy(
                jmx_name=jmx_name,
                transactions=transactions,
                http_requests=http_requests,
                transactions_by_tg=transactions_by_tg,
            )

            # Process optional error.jtl
            errors_breakdown: Dict[str, ErrorDetail] = {}
            error_jtl_path = options.get("error_jtl_path")
            if not error_jtl_path:
                # Look in same directory
                sibling_error = path.parent / "error.jtl"
                if sibling_error.exists():
                    error_jtl_path = sibling_error

            if error_jtl_path and Path(error_jtl_path).exists():
                try:
                    errors_breakdown = blazemeter_error_parser.parse_errors(error_jtl_path)
                except Exception as err:
                    logger.warning(f"Could not parse BlazeMeter error.jtl: {err}")

            # Overall summary metrics calculated strictly over main transactions
            total_tx_execs = sum(m.count for m in effective_transactions.values())
            total_tx_errors = sum(m.errors for m in effective_transactions.values())
            tx_error_rate = round((total_tx_errors / total_tx_execs * 100.0), 2) if total_tx_execs > 0 else 0.0

            total_req_execs = sum(m.count for m in http_requests.values()) if http_requests else total_tx_execs
            total_req_errors = sum(m.errors for m in http_requests.values()) if http_requests else total_tx_errors
            raw_err_rate = round((total_req_errors / total_req_execs * 100.0), 2) if total_req_execs > 0 else 0.0

            # Weighted overall response times over transactions
            all_tx_samples: List[int] = []
            for m in effective_transactions.values():
                all_tx_samples.extend(m.samples)
            all_tx_samples.sort()

            overall_avg = round(sum(all_tx_samples) / len(all_tx_samples), 2) if all_tx_samples else 0.0
            overall_min = float(all_tx_samples[0]) if all_tx_samples else 0.0
            overall_max = float(all_tx_samples[-1]) if all_tx_samples else 0.0
            p50_overall = _calc_pct(all_tx_samples, 50.0)
            p90_overall = _calc_pct(all_tx_samples, 90.0)
            p95_overall = _calc_pct(all_tx_samples, 95.0)
            p99_overall = _calc_pct(all_tx_samples, 99.0)
            throughput = round(total_tx_execs / duration_sec, 2) if duration_sec > 0 else 0.0

            return AggregateResult(
                schema_version="1.0",
                test_id=test_id,
                tool="blazemeter",
                total_requests=total_tx_execs,
                total_iterations=max((m.count for m in effective_transactions.values()), default=1),
                successful_requests=total_tx_execs - total_tx_errors,
                failed_requests=total_tx_errors,
                error_rate=tx_error_rate,
                raw_error_rate=raw_err_rate,
                throughput=throughput,
                avg_response_time=overall_avg,
                min_response_time=overall_min,
                max_response_time=overall_max,
                p50=p50_overall,
                p90=p90_overall,
                p95=p95_overall,
                p99=p99_overall,
                duration_seconds=duration_sec,
                start_epoch=start_epoch,
                end_epoch=end_epoch,
                transactions=transactions,
                http_requests=http_requests,
                all_labels=all_labels,
                transactions_by_thread_group=transactions_by_tg,
                hierarchy_tree=hierarchy_tree,
                errors_breakdown=errors_breakdown,
            )

        except Exception as e:
            if isinstance(e, ParserError):
                raise
            raise ParserError(f"Failed to parse BlazeMeter KPI file: {e}", context={"test_id": test_id})

    def _compile_hierarchy(
        self,
        jmx_name: str,
        transactions: Dict[str, TransactionMetric],
        http_requests: Dict[str, TransactionMetric],
        transactions_by_tg: Dict[str, Dict[str, TransactionMetric]],
    ) -> List[Dict[str, Any]]:
        """
        Builds the full compiled hierarchy tree (User Story -> Transaction -> Requests).
        Attempts JMX full tree resolution first; falls back to heuristic prefix matching.
        """
        compiled_tree: List[Dict[str, Any]] = []

        # Attempt to resolve from JMX test plan
        if jmx_name:
            try:
                from app.services.analytics.sla_manager import parse_jmx_full_tree
                candidate_jmx = None
                # Check directly
                p = Path(jmx_name)
                if p.is_absolute() and p.exists():
                    candidate_jmx = p
                elif (TESTS_DIR / jmx_name).exists():
                    candidate_jmx = TESTS_DIR / jmx_name
                elif (TESTS_DIR / f"{Path(jmx_name).stem}.jmx").exists():
                    candidate_jmx = TESTS_DIR / f"{Path(jmx_name).stem}.jmx"

                if candidate_jmx:
                    jmx_tree, _ = parse_jmx_full_tree(candidate_jmx)
                    if jmx_tree:
                        for tg_node in jmx_tree:
                            tg_name = tg_node.get("name", "").strip()
                            tg_entry = {"thread_group": tg_name, "transactions": []}

                            def _collect_tx_nodes(children):
                                return [c for c in children if c.get("type") == "transaction"]

                            top_txs = _collect_tx_nodes(tg_node.get("children", []))
                            for tx_node in top_txs:
                                t_name = tx_node.get("name", "").strip()
                                inner_txs = _collect_tx_nodes(tx_node.get("children", []))
                                target_txs = inner_txs if inner_txs else [tx_node]

                                for t_item in target_txs:
                                    sub_tx_name = t_item.get("name", "").strip()
                                    if sub_tx_name not in transactions:
                                        continue

                                    def _collect_leaf_requests(node):
                                        reqs = []
                                        for c in node.get("children", []):
                                            if c.get("type") == "request":
                                                reqs.append(c.get("name", "").strip())
                                            else:
                                                reqs.extend(_collect_leaf_requests(c))
                                        return reqs

                                    leaf_names = _collect_leaf_requests(t_item)
                                    req_entries = []
                                    for r_name in leaf_names:
                                        if r_name in http_requests:
                                            http_requests[r_name].parent_tc = sub_tx_name
                                            req_entries.append({
                                                "name": r_name,
                                                "type": "request",
                                                "metric": http_requests[r_name].model_dump(),
                                            })

                                    transactions[sub_tx_name].child_requests = [r["name"] for r in req_entries]
                                    tg_entry["transactions"].append({
                                        "name": sub_tx_name,
                                        "type": "transaction",
                                        "metric": transactions[sub_tx_name].model_dump(),
                                        "requests": req_entries,
                                    })

                            if tg_entry["transactions"]:
                                compiled_tree.append(tg_entry)

                        if compiled_tree:
                            return compiled_tree
            except Exception as e:
                logger.debug(f"JMX hierarchy tree resolution skipped: {e}")

        # Fallback: compile tree from transactions_by_tg and prefix matching
        for tg_name, tx_map in transactions_by_tg.items():
            tg_entry = {"thread_group": tg_name, "transactions": []}
            for tx_name, tx_metric in tx_map.items():
                # Match child requests by prefix (e.g. TC01_T_01)
                prefix = tx_name
                parts = tx_name.split("_")
                if len(parts) >= 3 and parts[1] == "T":
                    prefix = f"{parts[0]}_{parts[1]}_{parts[2]}"

                req_entries = []
                for req_name, req_metric in http_requests.items():
                    if req_name.startswith(prefix):
                        req_metric.parent_tc = tx_name
                        req_entries.append({
                            "name": req_name,
                            "type": "request",
                            "metric": req_metric.model_dump(),
                        })

                tx_metric.child_requests = [r["name"] for r in req_entries]
                tg_entry["transactions"].append({
                    "name": tx_name,
                    "type": "transaction",
                    "metric": tx_metric.model_dump(),
                    "requests": req_entries,
                })

            if tg_entry["transactions"]:
                compiled_tree.append(tg_entry)

        return compiled_tree

    def parse_timeseries(
        self,
        kpi_file: Union[Path, str],
        test_id: str,
        options: Optional[Dict[str, Any]] = None,
        bucket_seconds: int = 10,
    ) -> TimeSeriesResult:
        """
        Calculates time-series buckets (10-second default) from BlazeMeter kpi.jtl.
        """
        path = Path(kpi_file)
        if not path.exists():
            raise ParserError(f"BlazeMeter KPI file not found: {path}", context={"test_id": test_id})

        options = options or {}
        samples_by_bucket: Dict[int, List[int]] = {}
        errors_by_bucket: Dict[int, int] = {}
        all_threads_by_bucket: Dict[int, List[int]] = {}
        label_samples_by_bucket: Dict[str, Dict[int, List[int]]] = {}
        label_errors_by_bucket: Dict[str, Dict[int, int]] = {}

        min_ts = 0
        max_ts = 0

        with open(path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            col_map = {c.strip().lower(): c for c in fieldnames}

            ts_col = col_map.get("timestamp", "timeStamp")
            el_col = col_map.get("elapsed", "elapsed")
            lb_col = col_map.get("label", "label")
            sc_col = col_map.get("success", "success")
            th_col = col_map.get("allthreads", "allThreads")

            for row in reader:
                lbl = (row.get(lb_col) or "").strip()
                if not lbl:
                    continue

                try:
                    ts = int(row.get(ts_col, 0))
                except (ValueError, TypeError):
                    continue

                if ts <= 0:
                    continue

                if min_ts == 0 or ts < min_ts:
                    min_ts = ts
                if ts > max_ts:
                    max_ts = ts

                try:
                    elapsed = int(float(row.get(el_col, 0)))
                except (ValueError, TypeError):
                    elapsed = 0

                try:
                    threads = int(row.get(th_col, 1))
                except (ValueError, TypeError):
                    threads = 1

                is_success = str(row.get(sc_col, "true")).strip().lower() in ("true", "1")

                # Bucket key in seconds from start
                bucket_idx = int((ts - min_ts) / 1000.0 / bucket_seconds)

                # Overall metrics bucket
                if bucket_idx not in samples_by_bucket:
                    samples_by_bucket[bucket_idx] = []
                    errors_by_bucket[bucket_idx] = 0
                    all_threads_by_bucket[bucket_idx] = []

                samples_by_bucket[bucket_idx].append(elapsed)
                all_threads_by_bucket[bucket_idx].append(threads)
                if not is_success:
                    errors_by_bucket[bucket_idx] += 1

                # Label-specific bucket
                if lbl not in label_samples_by_bucket:
                    label_samples_by_bucket[lbl] = {}
                    label_errors_by_bucket[lbl] = {}

                if bucket_idx not in label_samples_by_bucket[lbl]:
                    label_samples_by_bucket[lbl][bucket_idx] = []
                    label_errors_by_bucket[lbl][bucket_idx] = 0

                label_samples_by_bucket[lbl][bucket_idx].append(elapsed)
                if not is_success:
                    label_errors_by_bucket[lbl][bucket_idx] += 1

        total_duration_sec = max(1.0, (max_ts - min_ts) / 1000.0) if max_ts > min_ts else 60.0
        num_buckets = max(1, math.ceil(total_duration_sec / bucket_seconds))

        bucket_labels: List[str] = []
        avg_rt: List[float] = []
        p95_rt: List[float] = []
        p99_rt: List[float] = []
        throughput: List[float] = []
        errors: List[int] = []
        active_threads: List[int] = []

        for b in range(num_buckets):
            sec_val = (b + 1) * bucket_seconds
            lbl_str = f"{sec_val}s" if sec_val < 60 else f"{sec_val//60}m{sec_val%60}s" if sec_val % 60 else f"{sec_val//60}m"
            bucket_labels.append(lbl_str)

            b_samples = sorted(samples_by_bucket.get(b, []))
            b_errors = errors_by_bucket.get(b, 0)
            b_threads = all_threads_by_bucket.get(b, [])

            if b_samples:
                avg_val = round(sum(b_samples) / len(b_samples), 2)
                p95_val = _calc_pct(b_samples, 95.0)
                p99_val = _calc_pct(b_samples, 99.0)
                tps_val = round(len(b_samples) / bucket_seconds, 2)
            else:
                avg_val = 0.0
                p95_val = 0.0
                p99_val = 0.0
                tps_val = 0.0

            th_val = max(b_threads) if b_threads else (active_threads[-1] if active_threads else 1)

            avg_rt.append(avg_val)
            p95_rt.append(p95_val)
            p99_rt.append(p99_val)
            throughput.append(tps_val)
            errors.append(b_errors)
            active_threads.append(th_val)

        # Build label series
        label_series: Dict[str, LabelTimeSeries] = {}
        for lbl_name, l_buckets in label_samples_by_bucket.items():
            l_avg, l_p95, l_p99, l_tps, l_err = [], [], [], [], []
            for b in range(num_buckets):
                lb_samples = sorted(l_buckets.get(b, []))
                lb_errors = label_errors_by_bucket[lbl_name].get(b, 0)
                if lb_samples:
                    l_avg.append(round(sum(lb_samples) / len(lb_samples), 2))
                    l_p95.append(_calc_pct(lb_samples, 95.0))
                    l_p99.append(_calc_pct(lb_samples, 99.0))
                    l_tps.append(round(len(lb_samples) / bucket_seconds, 2))
                else:
                    l_avg.append(0.0)
                    l_p95.append(0.0)
                    l_p99.append(0.0)
                    l_tps.append(0.0)
                l_err.append(lb_errors)

            label_series[lbl_name] = LabelTimeSeries(
                label=lbl_name,
                avg_rt=l_avg,
                p95_rt=l_p95,
                p99_rt=l_p99,
                throughput=l_tps,
                errors=l_err,
            )

        start_dt = datetime.fromtimestamp(min_ts / 1000.0, tz=timezone.utc) if min_ts > 0 else datetime.now(timezone.utc)
        end_dt = datetime.fromtimestamp(max_ts / 1000.0, tz=timezone.utc) if max_ts > 0 else datetime.now(timezone.utc)

        return TimeSeriesResult(
            schema_version="1.0",
            test_id=test_id,
            tool="blazemeter",
            start_time=start_dt,
            end_time=end_dt,
            interval_seconds=bucket_seconds,
            bucket_labels=bucket_labels,
            avg_response_time=avg_rt,
            p95_response_time=p95_rt,
            p99_response_time=p99_rt,
            throughput=throughput,
            errors=errors,
            active_threads=active_threads,
            label_series=label_series,
        )


# Global singleton
blazemeter_kpi_parser = BlazeMeterKPIParser()
