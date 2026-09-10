# Architecture Rules & Standards for PerfPilot Integration Pipeline

This document defines the **mandatory architectural rules, coding standards, and step-by-step procedures** for integrating new performance testing tools (e.g., JMeter, BlazeMeter, NeoLoad, k6, Gatling, Locust) and ingestion methods (CLI execution, file upload, zip archives, REST APIs, MCP) into PerfPilot.

Any agent or developer working on this codebase **must strictly follow these rules by default**.

---

## 1. The Rule of Strict Tool Isolation (Adapter Pattern)

1. **Tool-Specific Packages**:
   - Every performance tool must reside entirely in its own directory under `app/integrations/<tool_name>/`:
     - `app/integrations/jmeter/`
     - `app/integrations/blazemeter/`
     - `app/integrations/neoload/`
     - `app/integrations/<new_tool>/`
2. **Zero Cross-Tool Coupling**:
   - Parsers, readers, and executors for one tool **MUST NEVER** import, call, or depend on classes, functions, or files from another tool.
   - *Example*: BlazeMeter parsers must never import JMeter's `JTLParser` or `jmeter_aggregate_parser`.
3. **Encapsulate Tool Dialects**:
   - Tool-specific peculiarities (e.g., BlazeMeter thread names ending in `-ThreadStarter`, XML `<httpSample>` vs `<sample>` rollups, CSV header case variations, custom timestamp formats) must be completely handled within `app/integrations/<tool_name>/`.

---

## 2. The Rule of Canonical Domain Contracts

Every tool adapter must translate tool-specific data into the **two standard, strongly typed domain contracts**:

1. **`AggregateResult`** ([`app/domain/models/aggregate.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/domain/models/aggregate.py)):
   - `tool`: Canonical lowercase tool string (e.g. `"jmeter"`, `"blazemeter"`, `"neoload"`, `"k6"`).
   - `total_requests`: Total sample executions (calculated over main transactions when present).
   - `error_rate`: Overall transaction-level error rate percentage ($0.0 - 100.0$).
   - `raw_error_rate`: Raw HTTP leaf request error rate percentage ($0.0 - 100.0$).
   - `avg_response_time`, `min_response_time`, `max_response_time`.
   - `p50`, `p90`, `p95`, `p99`: True calculated percentiles.
   - `throughput`: Transactions per second ($TPS = \text{total\_requests} / \text{duration\_seconds}$).
   - `transactions`: Dict of `TransactionMetric` (main transactions only, `depth=0`).
   - `http_requests`: Dict of `TransactionMetric` (leaf HTTP requests only, `depth=1`).
   - `all_labels`: Complete dictionary combining transactions and requests.
   - `transactions_by_thread_group`: Mapped by User Story / Thread Group.
   - `hierarchy_tree`: Full nested list representing `Thread Group` $\rightarrow$ `Transaction` $\rightarrow$ `HTTP Requests`.
   - `errors_breakdown`: Keyed by error key, populated with `ErrorDetail` and representative `ErrorOccurrence` items.

2. **`TimeSeriesResult`** ([`app/domain/models/timeseries.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/domain/models/timeseries.py)):
   - `interval_seconds`: Bucket interval (typically 10 seconds).
   - `bucket_labels`: Ordered time markers (`["10s", "20s", ..., "1m", "1m10s", ...]`).
   - `avg_response_time`: List of mean RT per bucket.
   - `p95_response_time`, `p99_response_time`: Percentile response times per bucket.
   - `throughput`: Samples per second per bucket.
   - `errors`: Error count per bucket.
   - `active_threads`: Concurrency / virtual user count per bucket.
   - `label_series`: Map of `label` $\rightarrow$ `LabelTimeSeries`.

---

## 3. The Rule of Two-Level Transaction vs. Request Hierarchy

1. **Main Transactions (`depth=0`, `item_type="MAIN_TRANSACTION"`)**:
   - Represents user business journeys and Transaction Controllers.
   - **SLA compliance, executive summary metrics, and overall test error rate apply STRICTLY to Main Transactions**.
2. **Leaf HTTP Requests (`depth=1`, `item_type="HTTP_REQUEST"`)**:
   - Represents low-level network calls / child HTTP requests.
   - Used for technical root-cause investigation, breakdown tables, and raw error counts.
   - **Do NOT penalize or dilute SLA compliance with leaf HTTP requests**.
   - Leaf HTTP request metrics in graphs and tables must use neutral styling (e.g. black/grey) because they do not have separate SLA thresholds.

---

## 4. The Rule of Multi-File Bundles & Archive Ingestion

1. **File & Archive Support**:
   - Ingestion routes must support single files (`.jtl`, `.csv`, `.json`), multi-file directories, and compressed bundles (`.zip`).
2. **Archive Extraction**:
   - All `.zip` uploads must unpack into `Results/raw/<bundle_stem>/` via [`app/integrations/upload/file_source.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/integrations/upload/file_source.py).
   - The primary performance log (e.g. `kpi.jtl`) must be returned as the primary file path.
   - Auxiliary diagnostic logs (e.g. `error.jtl`, server telemetry CSVs) must be registered in the execution `options` dictionary (e.g., `options["error_jtl_path"]`).
3. **Error Parsing & Double-Count Prevention**:
   - Error trace parsers must extract root-cause messages (HTTP status, Tomcat 404 details, application/framework exceptions).
   - Top-level container rollups that merely state `"Number of samples in transaction..."` must be filtered out so errors are not counted twice.

---

## 5. The Rule of the Zero-Tool-Branching Common Pipeline

Once tool data is normalized into `AggregateResult` and `TimeSeriesResult`:
1. **Tool-Agnostic Processing**:
   - Downstream services (`app/services/analytics/sla_manager.py`, `app/services/ai/insights.py`, `app/services/reporting/`, `app/services/storage/`) **MUST NOT** check `if tool == "..."` for core data flow.
2. **Dynamic Concurrency Resolution**:
   - If the user provides default or unassigned users (`users <= 1`), infer concurrency from `max(ts_result.active_threads)` or parse from the test scenario JMX plan.
3. **Unified Output Artifacts**:
   - Every test run must produce:
     1. `storage/normalized/{run_id}_aggregate.json`
     2. `storage/normalized/{run_id}_timeseries.json`
     3. `Results/json/{run_id}_result.json` (Legacy schema for 100% backward compatibility with Comparison, Trend, and History tabs)
     4. `Results/html/{run_id}_report.html` (Complete standalone interactive report)
     5. Entry registered in `data/runs.json` catalog.

---

## 6. Step-by-Step Procedure for Adding a New Tool

When adding any new tool `<new_tool>` (e.g., `k6`, `gatling`, `locust`):

1. **Register Enum**:
   - Add `<new_tool>` to `ToolType` in [`app/domain/models/test_run.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/domain/models/test_run.py).
2. **Create Tool Adapter Directory**:
   - Create `app/integrations/<new_tool>/`.
3. **Implement Aggregate Parser**:
   - Create `app/integrations/<new_tool>/aggregate_parser.py` subclassing `AggregateParser`.
   - Produces `AggregateResult` with `tool="<new_tool>"`.
4. **Implement Time-Series Parser**:
   - Create `app/integrations/<new_tool>/timeseries_parser.py` subclassing `TimeSeriesParser`.
   - Produces `TimeSeriesResult` with `tool="<new_tool>"`.
5. **Implement Result Reader / Executor**:
   - Create `result_reader.py` subclassing `ResultCollector`.
   - If local CLI execution is supported, create `executor.py` subclassing `ExecutionService`.
6. **Register in Dispatches**:
   - Register the parsers in [`app/services/parsing/parse_results.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/services/parsing/parse_results.py).
   - Register the collector in [`app/services/collection/collect_results.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/services/collection/collect_results.py).
   - If local execution is supported, register executor in [`app/services/execution/execute_test.py`](file:///d:/BlazemeterMCPZIP/JmeterAI/app/services/execution/execute_test.py).
7. **Write Unit Tests**:
   - Create `Tests/unit/test_<new_tool>_parser.py` validating:
     - Output is an instance of `AggregateResult` and `TimeSeriesResult`.
     - Transaction vs request separation.
     - Percentile and error rate correctness.
8. **Verify Pipeline**:
   - Run `python -m unittest discover -s Tests/unit` and `Tests/integration`.
   - Verify that `Results/json/{run_id}_result.json` and `Results/html/{run_id}_report.html` are generated cleanly.
