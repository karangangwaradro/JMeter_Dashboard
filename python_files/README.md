# Python Modules & Architecture Guide

This document provides a comprehensive guide to the backend Python modules in `python_files/`, explaining the overall architecture, data pipeline, how the **2-Run Comparison** and **Historical Trend Analysis** modules operate conceptually, and the detailed functional catalog of every module.

---

## 🏗️ Architecture & Pipeline Flow

The backend follows a **modular functional pipeline**. Test execution runs independently to generate raw JTL logs, which are processed by the dedicated `jtl_parser.py` engine before flowing into analytics, rule engines, AI insights, interactive single-run HTML reports, and dedicated comparative/trend modules.

```mermaid
flowchart TD
    subgraph Configuration ["1. Configuration & Setup"]
        JMXEditor["jmx_editor.py<br/><b>JMX Configuration Editor</b>"]
        SLAManager["sla_manager.py<br/><b>SLA & Hierarchy Manager</b>"]
    end

    subgraph Execution ["2. Test Execution & Raw Logs"]
        JMeterExec["run_local_jmeter.py<br/><b>JMeter Test Runner</b>"]
        RawJTL[("results.jtl<br/>(Raw CSV Log)")]
        AzureMon["azure_monitor.py<br/><b>Infrastructure Telemetry</b>"]
    end

    subgraph Parsing ["3. Log Parsing & Data Extraction"]
        JTLParser["jtl_parser.py<br/><b>JTL / CSV Parser Engine</b>"]
        RunJSON[("Results/json/<run_id>.json<br/>(Normalized Run Data)")]
    end

    subgraph Analytics ["4. Analysis & Intelligence"]
        Apdex["apdex_calculator.py<br/><b>Apdex Satisfaction Engine</b>"]
        Correlation["correlation_engine.py<br/><b>Client-Server Correlator</b>"]
        Findings["findings_engine.py<br/><b>Rule-Based Findings Engine</b>"]
        AI["ai_insights.py<br/><b>LLM Diagnostics & Scoring</b>"]
    end

    subgraph Products ["5. Analytical Products & Reports"]
        ReportGen["report_generator.py<br/><b>Single-Run HTML Report</b>"]
        CompareEngine["comparison_engine.py<br/><b>2-Run Comparison Engine</b>"]
        TrendEngine["trend_engine.py<br/><b>Multi-Release Trend Engine</b>"]
        Organize["organize_results.py<br/><b>Artifact Organizer</b>"]
        RecompileLatest["recompile_latest.py<br/><b>Single-Run Recompiler</b>"]
        RecompileAll["recompile_all.py<br/><b>Batch Recompiler</b>"]
    end

    %% Flow connections
    JMXEditor -->|Updated .jmx| JMeterExec
    SLAManager -->|Thread Groups & SLAs| JMeterExec
    SLAManager -->|SLA Targets| ReportGen
    SLAManager -->|SLA Targets| CompareEngine
    SLAManager -->|SLA Targets| TrendEngine

    JMeterExec -->|Executes JMeter CLI| RawJTL
    JMeterExec -->|Execution Timestamps| AzureMon
    
    RawJTL -->|Reads CSV Rows| JTLParser
    JTLParser -->|Outputs Structured JSON| RunJSON

    RunJSON --> Apdex
    RunJSON --> Correlation
    AzureMon --> Correlation
    RunJSON --> Findings
    AzureMon --> Findings
    
    Correlation --> AI
    Findings --> AI
    RunJSON --> AI

    Apdex --> ReportGen
    Findings --> ReportGen
    AI --> ReportGen
    AzureMon --> ReportGen
    RunJSON --> ReportGen

    RunJSON -->|Exactly 2 Runs (Run A vs Run B)| CompareEngine
    RunJSON -->|3 to 20+ Historical Runs| TrendEngine

    ReportGen --> Organize
    RecompileLatest -.->|Rebuilds| ReportGen
    RecompileAll -.->|Rebuilds| ReportGen
```

---

## 💡 Two Dedicated Analytical Products

Performance engineering requires answering two fundamentally different questions. The system treats them as two distinct analytical products:

| Product | **Compare Runs Engine** (`comparison_engine.py`) | **Historical Trend Engine** (`trend_engine.py`) |
| :--- | :--- | :--- |
| **Primary Purpose** | Deep-dive comparative engineering analysis | Identify high-level directional patterns over time |
| **Runs Analyzed** | **Exactly 2** (Run A vs Run B) with quick swap `⇄` | **3 to 20+** releases ($R_1 \rightarrow R_2 \dots R_n$) |
| **Core Question** | *"What changed between these two executions?"* | *"Where is performance heading over time?"* |
| **Target Audience** | Performance Engineers & Developers debugging regressions | Leadership, Product Owners & Release Managers |
| **Analytical Depth** | Deep, transaction-by-transaction, percentiles, margins | Lightweight management dashboard, hero visuals |
| **Key Output** | Standalone Engineering Comparison HTML Report | Standalone Management Trend Dashboard HTML |

---

## 🔍 How `comparison_engine.py` Works (2-Run Deep Dive)

The **Comparison Engine** performs a deep, deterministic differential analysis between **Run A (Baseline)** and **Run B (Target)**.

### The Workflow:
1. **Load & Align Runs**:
   - Loads the raw data for Run A and Run B from `Results/json/`.
   - Aligns every transaction by its hierarchical context (User Story $\rightarrow$ Main Transaction Controller $\rightarrow$ Sub-Transaction $\rightarrow$ HTTP Request).
2. **Compute Metric Differentials**:
   - Calculates side-by-side deltas for **Average Response Time**, **Percentiles ($P50, P90, P95, P99$)**, **Throughput (TPS)**, and **Error Rates**.
3. **Classify State Transitions**:
   - Evaluates whether each transaction passed or failed its configured SLA target in both runs:
     - **Pass $\rightarrow$ Pass**: Persistent Pass (healthy).
     - **Pass $\rightarrow$ Fail**: **New SLA Breach** (regression introduced in Run B).
     - **Fail $\rightarrow$ Pass**: **Resolved Breach** (performance fix verified in Run B).
     - **Fail $\rightarrow$ Fail**: Persistent Breach (ongoing issue).
4. **Generate the Core Visualizations**:
   - **Overall Performance Split Cards**: Side-by-side cards for Avg RT, P95, P99, TPS, and Error Rate with individual % deltas.
   - **Response Time Change % (Hero Diverging Chart)**: Centered zero-axis chart showing improvements expanding green to the left and regressions expanding red to the right. Sortable by Degradation, % Change, or Hierarchy.
   - **SLA Compliance Comparison**: 100% stacked bar showing the proportion of passing vs breaching transactions.
   - **SLA Status Transition Matrix**: 4-quadrant breakdown of new vs resolved breaches.
   - **Throughput & Error Rate Comparison**: Side-by-side transaction throughput and functional error rates.
   - **Percentile Progression Table**: Compares $P50 \rightarrow P90 \rightarrow P95 \rightarrow P99$ to detect tail latency issues.
   - **Transaction Performance Heatmap Matrix**: High-density matrix displaying the health status across all 5 metrics.
   - **5 Comparison Rankings**: Top 5 lists for Largest Degradation, Top Improvements, Largest SLA Breaches, Throughput Changes, and Error Spikes.
5. **Attach Compact Factual Observations**:
   - Calculates exact numerical summaries directly under every single chart (e.g. *"7 transactions improved to the left while 7 degraded to the right. Max degradation: TC01 (+1.38%)."*).
6. **Export Report**:
   - Renders a standalone, self-contained HTML comparison report saved in `Results/Published/`.

---

## 📈 How `trend_engine.py` Works (Historical Trend Analysis)

The **Trend Engine** provides a lightweight management overview across a sequence of 3 to 20+ test executions ($R_1 \rightarrow R_2 \rightarrow R_3 \dots$).

### The Workflow:
1. **Extract Release Timeline**:
   - Scans past test runs, labels them chronologically ($R_1 \dots R_n$), and normalizes data across test executions.
2. **Scope by Hierarchy**:
   - Allows instant scoping by **Project**, **User Story**, or **Hierarchy Scope** (e.g. Transactions only vs all requests).
3. **Compute Management KPIs**:
   - **Overall Trend %**: Baseline-to-current response time drift.
   - **Current SLA Pass Rate & Status**: Deterministic grade (`Pass`, `Warning`, `Critical`).
   - **Best & Worst Releases**: Identifies the highest and lowest latency executions in the timeline.
4. **Build 5 Hero Trend Visuals**:
   - **Graph 1: Response Time Trend Line**: Overall latency progression curve ($R_1 \rightarrow R_n$).
   - **Graph 2: SLA Compliance Trend**: Progression of transaction SLA pass percentage per release.
   - **Graph 3: Transaction Heatmap Matrix**: Color-coded matrix showing transaction latency across all releases.
   - **Graph 4: SLA Severity Distribution Stack**: Tracks the count of Pass, Low, Moderate, High, and Critical transactions over time.
   - **Graph 5: Baseline vs Current Summary**: First release vs latest release comparative overview.
5. **High-Level Observations & Export**:
   - Formulates high-level directional bullet points for executive briefings and renders a standalone Management Trend Dashboard HTML.

---

## 📋 Complete Module Catalog & Technical Specifications

| Module | Category | Primary Function |
| :--- | :--- | :--- |
| [`run_local_jmeter.py`](#1-run_local_jmeterpy) | Execution | Executes JMeter CLI tests and outputs raw `.jtl` results |
| [`jtl_parser.py`](#2-jtl_parserpy) | Parser | Parses `.jtl` CSV logs into metrics, label summaries, error diagnostics, and time-series |
| [`comparison_engine.py`](#3-comparison_enginepy) | Analytics | Dedicated 2-run comparative analysis engine (Run A vs Run B) |
| [`trend_engine.py`](#4-trend_enginepy) | Analytics | Analyzes multi-run historical trends, health scores, and release trajectories |
| [`report_generator.py`](#5-report_generatorpy) | Reporting | Generates self-contained interactive HTML dashboards with Chart.js charts and analytics |
| [`ai_insights.py`](#6-ai_insightspy) | Intelligence | Generates diagnostic insights, root-cause deductions, and performance scores via LLMs / rules |
| [`findings_engine.py`](#7-findings_enginepy) | Analytics | Evaluates statistical performance thresholds, chart observations, and automated recommendations |
| [`correlation_engine.py`](#8-correlation_enginepy) | Analytics | Cross-correlates client-side latency/TPS with server-side CPU/Memory/IOPS |
| [`sla_manager.py`](#9-sla_managerpy) | Configuration | Parses JMX hierarchies (Thread Groups, Samplers) and manages SLA threshold targets |
| [`jmx_editor.py`](#10-jmx_editorpy) | Configuration | Safely reads and updates user concurrency, ramp-up, and duration inside `.jmx` XML scripts |
| [`apdex_calculator.py`](#11-apdex_calculatorpy) | Analytics | Computes Apdex user satisfaction scores and ratings based on target thresholds ($T$ and $4T$) |
| [`azure_monitor.py`](#12-azure_monitorpy) | Telemetry | Collects server-side telemetry from Azure Monitor API or realistic local mock metrics |
| [`organize_results.py`](#13-organize_resultspy) | Utility | Migrates and organizes loose test outputs into structured timestamped run folders |
| [`recompile_latest.py`](#14-recompile_latestpy) | Utility | Recompiles the HTML report for the most recent run without re-running JMeter |
| [`recompile_all.py`](#15-recompile_allpy) | Utility | Batch re-parses JTLs and regenerates HTML reports for all past test runs |

---

### 1. `run_local_jmeter.py`
**Test Orchestrator & Execution Engine**
- **Functional Purpose:** Drives the end-to-end local JMeter test execution. Handles process spawning, parameter injection (users, duration, ramp-up), real-time stdout streaming, and exit code handling.
- **Inputs:**
  - `jmx_path`: Path to the `.jmx` test script in `Tests/`.
  - `users`, `duration`, `rampup`: Concurrency parameters.
  - `environment`, `build_version`: Optional test metadata.
- **Outputs:**
  - Raw `results.jtl` execution log in `Results/`.
  - `run_<timestamp>` run identifier and timestamps (`start_epoch`, `end_epoch`).
  - Calls downstream post-processing pipelines (`jtl_parser`, `azure_monitor`, `report_generator`).

---

### 2. `jtl_parser.py`
**Log Parsing & Metrics Extraction Engine**
- **Functional Purpose:** Dedicated parser for raw `.jtl` (CSV format) logs. Extracts raw sampler entries, filters out parent transaction controllers from raw totals to avoid double-counting, computes exact statistics ($Avg$, $Median$, $P90$, $P95$, $P99$, $Min$, $Max$, Error %, Throughput), groups by sampler labels, extracts error breakdowns by response code, and produces 5-second interval time-series datasets.
- **Inputs:**
  - `jtl_path`: Absolute or relative path to a `.jtl` CSV file.
- **Outputs:**
  - Comprehensive parsed dictionary saved as `<run_id>_result.json` containing:
    - `summary`: Overall test totals, average response time, overall error rate, throughput, duration.
    - `labels`: Dictionary mapping each label/transaction to its individual statistical metrics.
    - `timeseries`: 5-second interval metrics for charts (Response Time, Active Threads, Throughput TPS, Error Count).
    - `errors`: Categorized list of failed requests with response codes and failure messages.

---

### 3. `comparison_engine.py`
**Dedicated 2-Run Comparison Engine**
- **Functional Purpose:** Computes exact 2-run comparative metrics between Run A and Run B, tracks SLA state transitions ($Pass \rightarrow Pass$, $Pass \rightarrow Fail$, $Fail \rightarrow Pass$, $Fail \rightarrow Fail$), computes diverging percentage deltas, percentile progressions ($P50 \rightarrow P90 \rightarrow P95 \rightarrow P99$), 5-tab rankings, and exports standalone HTML comparison reports.
- **Inputs:**
  - `run_a_id`, `run_b_id`: Identifiers for the two runs being compared.
  - `project`, `user_story`, `item_type_filter`: Optional scoping filters.
- **Outputs:**
  - Detailed 2-Run Comparison JSON dataset.
  - Generates standalone Engineering Comparison HTML Report (`Results/Published/comparison_<project>_<timestamp>.html`).

---

### 4. `trend_engine.py`
**Historical Trends & Multi-Release Analytics Engine**
- **Functional Purpose:** Scans historical test run artifacts, groups runs by project and user story, computes health score trajectories, generates 5 hero trend visuals, builds transaction heatmap matrices, and renders executive trend dashboards.
- **Inputs:**
  - Historical run folders (`Results/runs/` and `Results/json/`).
  - Query filters: `project`, `user_story`, `item_type_filter`, `limit`.
- **Outputs:**
  - Multi-release trend datasets (response time drifts, error trends, throughput variations, severity evolution stacks).
  - Standalone Management Trend Dashboard HTML (`Results/Published/trend_<project>_<timestamp>.html`).

---

### 5. `report_generator.py`
**Interactive HTML Report Compiler**
- **Functional Purpose:** Compiles all parsed metrics, Azure infrastructure telemetry, Apdex scores, rule-based findings, AI insights, and interactive Chart.js charts into a single self-contained HTML report.
- **Inputs:**
  - `run_data`: Parsed results dictionary from `jtl_parser.py`.
  - `azure_data`: Telemetry dictionary from `azure_monitor.py`.
  - `ai_data`: AI insights dictionary from `ai_insights.py`.
  - `sla_targets`: SLA threshold lookup map from `sla_manager.py`.
- **Outputs:**
  - `<run_id>_report.html` saved in `Results/html/` and `Results/runs/<run_id>/`.

---

### 6. `ai_insights.py`
**AI Diagnostics & Performance Scoring Engine**
- **Functional Purpose:** Evaluates test metrics against SLA targets and server telemetry to formulate executive summaries, overall performance grades ($A$ through $F$), and root-cause deductions. Supports deterministic rule-based analysis as well as LLM-powered insights (via OpenAI / Anthropic / Gemini APIs or Ollama local models).
- **Inputs:**
  - Test summary statistics and per-transaction metrics.
  - List of SLA breaches and Apdex score.
  - Infrastructure saturation metrics (peak CPU %, peak Memory %).
- **Outputs:**
  - Executive summary paragraph.
  - Letter grade and numeric score ($0-100$).
  - Bulleted diagnostic findings and recommendations.

---

### 7. `findings_engine.py`
**Rule-Based Performance Findings Engine**
- **Functional Purpose:** Analyzes raw metrics against industry best-practice heuristics to flag issues such as high tail latency ($P99 > 3 \times \text{Avg}$), high error rates ($> 1\%$), CPU saturation ($> 80\%$), memory leaks, and throughput degradation.
- **Inputs:**
  - Parsed JTL metrics, timeseries intervals, and server telemetry.
- **Outputs:**
  - Structured list of findings with severity ratings (`CRITICAL`, `WARNING`, `INFO`), affected components, and actionable remediation recommendations.

---

### 8. `correlation_engine.py`
**Client-Server Infrastructure Correlator**
- **Functional Purpose:** Synchronizes client-side response time/TPS time-series with server-side CPU/Memory time-series across matching timestamp windows. Computes Pearson correlation coefficients and pinpoints whether latency spikes were caused by server resource exhaustion.
- **Inputs:**
  - Client-side timeseries from `jtl_parser.py`.
  - Server-side timeseries from `azure_monitor.py`.
- **Outputs:**
  - Correlation coefficient ($-1.0$ to $+1.0$).
  - Primary bottleneck classification (`CPU Bound`, `Memory Bound`, `Network/External Bound`, or `Healthy`).

---

### 9. `sla_manager.py`
**JMX Hierarchy Parser & SLA Target Manager**
- **Functional Purpose:** Recursively inspects JMeter `.jmx` XML script trees to extract Thread Groups (User Stories), Transaction Controllers (Main & Sub-Transactions), and HTTP Samplers. Loads and saves SLA targets (response time and error rate thresholds) from `config/sla_targets.json`.
- **Inputs:**
  - `.jmx` test script file.
  - `config/sla_targets.json`.
- **Outputs:**
  - JMX hierarchical tree structure.
  - SLA lookup map mapping every transaction label to its target RT (ms), error rate (%), and criticality flag.

---

### 10. `jmx_editor.py`
**JMX XML Parameter Editor**
- **Functional Purpose:** Safely updates thread concurrency (`ThreadGroup.num_threads`), ramp-up time (`ThreadGroup.ramp_time`), duration (`ThreadGroup.duration`), and loop counts directly in `.jmx` XML files without breaking test logic or samplers.
- **Inputs:**
  - `.jmx` file path.
  - Concurrency parameters (`users`, `rampup`, `duration`, `loop_count`).
- **Outputs:**
  - Modified `.jmx` file ready for execution.

---

### 11. `apdex_calculator.py`
**Apdex (Application Performance Index) Engine**
- **Functional Purpose:** Calculates Apdex user satisfaction scores based on customizable target response time thresholds ($T$). Categorizes requests into Satisfied ($RT \le T$), Tolerating ($T < RT \le 4T$), and Frustrated ($RT > 4T$ or Error).
- **Inputs:**
  - Response time data (raw data points or aggregated percentile metrics).
  - Threshold target $T$ (default: 1.5 seconds / 1500 ms).
- **Outputs:**
  - Apdex score ($0.00$ to $1.00$) and satisfaction grade (`Excellent`, `Good`, `Fair`, `Poor`, `Unacceptable`).
  - Apdex time-series breakdown for chart visualization.

---

### 12. `azure_monitor.py`
**Infrastructure Telemetry Collector**
- **Functional Purpose:** Collects server-side telemetry (App Service / VM metrics) for the exact duration of a test run. Supports querying the Azure Monitor REST API or generating realistic local mock metrics for offline environments.
- **Inputs:**
  - `start_epoch`, `end_epoch`: Test execution start and end timestamps.
  - `run_id`: Unique run identifier.
- **Outputs:**
  - Infrastructure telemetry dictionary (CPU %, Memory %, Disk I/O, Network In/Out, HTTP Requests time-series).

---

### 13. `organize_results.py`
**Results Organization Utility**
- **Functional Purpose:** Scans the `Results/` directory for unorganized test output files (JTLs, JSONs, HTMLs) and sorts them into organized timestamped subdirectories under `Results/runs/run_<timestamp>/`.
- **Inputs:** Root `Results/` directory.
- **Outputs:** Structured file layout with cleaned top-level folders.

---

### 14. `recompile_latest.py`
**Latest Run Report Recompiler**
- **Functional Purpose:** Quickly regenerates the HTML report for the most recent test run using existing saved artifacts without having to re-execute the JMeter test.
- **Inputs:** Most recent run directory in `Results/runs/`.
- **Outputs:** Updated HTML report in `Results/html/`.

---

### 15. `recompile_all.py`
**Batch Historical Report Recompiler**
- **Functional Purpose:** Iterates over all historical test runs in `Results/runs/`, re-parses JTL logs via `jtl_parser.py`, and rebuilds updated HTML reports with latest report templates and styling.
- **Inputs:** All run directories in `Results/runs/`.
- **Outputs:** Recompiled HTML reports for all past test executions.
