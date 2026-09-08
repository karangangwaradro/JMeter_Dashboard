# PerfPilot System Architecture — Detailed Data Flow Diagram (DFD)

This document provides a comprehensive, multi-tiered **Data Flow Diagram (DFD)** specification for the **PerfPilot / JMeter AI** performance engineering and autonomous reporting platform.

---

## 1. DFD Level 0: Context Diagram

The Level 0 Context Diagram models the boundary of the entire PerfPilot system, identifying all external entities, inbound inputs, and outbound deliverables.

```mermaid
graph TD
    classDef entity fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef system fill:#0f172a,stroke:#8b5cf6,stroke-width:3px,color:#f8fafc;
    classDef datastore fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc;

    User["👤 Performance Engineer / Stakeholder"]:::entity
    JMeter["⚡ Apache JMeter Engine"]:::entity
    Azure["☁️ Azure Monitor / Cloud Infra"]:::entity
    LLM["🧠 AI Providers<br/>(OpenRouter / Gemini / GitHub Models)"]:::entity

    PerfPilot[["⚙️ [0.0] PerfPilot Platform<br/>(JMeter AI & Autonomous Report System)"]]:::system

    JMeter -->|"JTL Sample Logs (CSV/XML)"| PerfPilot
    Azure -->|"Host & App Gateway Telemetry (CPU, Mem, Disk, Net)"| PerfPilot
    User -->|"Test Config, SLA Targets (Excel), AI Chat Prompts"| PerfPilot
    User -->|"Baseline Run Selection (Comparison), Edit & Publish Actions"| PerfPilot

    PerfPilot -->|"Formatted Analytics Prompts + Metrics Summary"| LLM
    LLM -->|"Structured JSON AI Insights & Verdicts"| PerfPilot

    PerfPilot -->|"Interactive Single-File Draft Report (HTML)"| User
    PerfPilot -->|"Permanent Non-Editable Published Report (HTML)"| User
    PerfPilot -->|"Live Web Management Dashboard (SPA)"| User
```

---

## 2. DFD Level 1: High-Level System Process Flow

Level 1 breaks down the platform into its 5 primary subsystems, tracing data movement between external entities, core processes, and internal datastores.

```mermaid
flowchart TD
    classDef proc fill:#1e1e2e,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef store fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#34d399;
    classDef ext fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#93c5fd;

    %% External Entities
    E_Eng["👤 Performance Engineer"]:::ext
    E_JMeter["⚡ JMeter Exec"]:::ext
    E_Azure["☁️ Azure API"]:::ext
    E_LLM["🧠 LLM Providers"]:::ext

    %% Datastores
    D_Runs[("💾 data/runs.json")]:::store
    D_SLA[("📄 config/sla_targets.xlsx")]:::store
    D_JTL[("📊 Results/jtl/*.jtl")]:::store
    D_JSON[("🗄️ Results/json/*_result.json")]:::store
    D_Azure[("☁️ Results/json/azure_*.json")]:::store
    D_HTML[("🌐 Results/html/*_report.html")]:::store
    D_Pub[("📑 Results/Published/*_published.html")]:::store

    %% Subprocesses
    P1["[1.0] Test Execution & Ingestion Engine"]:::proc
    P2["[2.0] SLA Target & Metric Analyzer"]:::proc
    P3["[3.0] AI Intelligence & Prompt Synthesis Engine"]:::proc
    P4["[4.0] Modular Report Generator Pipeline"]:::proc
    P5["[5.0] Differential Run Comparison Service"]:::proc
    P6["[6.0] Web Server & Lifecycle Manager"]:::proc

    %% Flows for P1
    E_JMeter -->|"Generates JTL"| D_JTL
    E_Azure -->|"Queries Metrics"| D_Azure
    D_JTL --> P1
    D_Azure --> P1
    P1 -->|"Parses & Registers Runs"| D_Runs

    %% Flows for P2
    P1 -->|"Raw Timestamps & Samplers"| P2
    D_SLA -->|"Configured Targets"| P2
    P2 -->|"Structured Metrics, Apdex, SLA Compliance"| D_JSON

    %% Flows for P3
    D_JSON -->|"Metrics & Findings Context"| P3
    D_Azure -->|"Infrastructure Context"| P3
    P3 <-->|"Prompt / Resilient JSON Loads (json_repair)"| E_LLM
    P3 -->|"Enriched AI Insights & Recommendations"| D_JSON

    %% Flows for P4
    D_JSON -->|"Report Context (ctx)"| P4
    D_Azure -->|"Aligned Infra Metrics"| P4
    P4 -->|"Compiles Self-Contained Standalone HTML"| D_HTML

    %% Flows for P5
    D_Runs -->|"List of Prior Executions"| P5
    D_JSON -->|"Baseline vs Current Metric Diffs"| P5
    P5 <-->|"Comparative LLM Synthesis"| E_LLM
    P5 -->|"Differential Scorecard & Transitions"| P6

    %% Flows for P6
    E_Eng <-->|"Browser Navigation & Web UI"| P6
    D_HTML -->|"Served as Draft Report"| P6
    P6 -->|"Bakes / Strips Selectors on Publish"| D_Pub
    D_Pub -->|"Served as Permanent Report"| E_Eng
```

---

## 3. DFD Level 2: Detailed Sub-Process Decompositions

### 3.1 Sub-Process 2.0: Metrics Processing & Intelligence Engine

```mermaid
flowchart TD
    classDef subproc fill:#181825,stroke:#c084fc,stroke-width:2px,color:#f8fafc;
    classDef store fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#34d399;

    D_JTL[("📊 *.jtl")]:::store
    D_SLA[("📄 sla_targets.xlsx")]:::store

    P2_1["[2.1] JTL Stream Parser<br/>(jtl_parser.py)"]:::subproc
    P2_2["[2.2] SLA Target Evaluator<br/>(sla_manager.py)"]:::subproc
    P2_3["[2.3] Apdex Score Calculator<br/>(apdex_calculator.py)"]:::subproc
    P2_4["[2.4] Time-Series & Cross-Correlation<br/>(Pearson Correlation Engine)"]:::subproc
    P2_5["[2.5] User Journey & Story Grouper<br/>(Transaction Hierarchy Builder)"]:::subproc

    D_Out[("🗄️ Parsed Result Data")]:::store

    D_JTL --> P2_1
    P2_1 -->|"Sample counts, RT, Errors, Time buckets"| P2_2
    P2_1 -->|"Sample arrays & Timestamps"| P2_4
    P2_1 -->|"Thread Groups & Transaction Labels"| P2_5
    D_SLA -->|"Per-transaction SLA Targets"| P2_2

    P2_2 -->|"SLA Status, Breaches, Deviation %"| P2_3
    P2_2 -->|"SLA Compliance Summary"| D_Out
    P2_3 -->|"Apdex Scores per transaction"| D_Out
    P2_4 -->|"Client vs Server Correlation Matrix"| D_Out
    P2_5 -->|"Hierarchical Tree JSON Structure"| D_Out
```

---

### 3.2 Sub-Process 3.0: AI Intelligence & Resilient Parsing Pipeline

```mermaid
flowchart TD
    classDef proc fill:#181825,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef llm fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#93c5fd;

    InContext["Parsed Metrics + Azure Telemetry + SLA Target Facts"] --> P3_1["[3.1] Prompt Construction & Context Assembly<br/>(ai_prompts.py)"]:::proc

    P3_1 -->|"Engineered Prompt with JSON Schema Guidance"| P3_2["[3.2] Provider Dispatcher & Credit Balancer<br/>(OpenRouter 4096 tok / Gemini 8192 tok / GitHub)"]:::proc

    P3_2 -->|"HTTPS POST (payload + auth)"| LLM_Active["Active LLM Provider"]:::llm
    LLM_Active -->|"Raw Text String (May have commas/fences/truncation)"| P3_3["[3.3] Multi-Pass JSON Recovery Engine<br/>(_safe_json_loads in ai_insights.py)"]:::proc

    subgraph Resilient_Parser ["Multi-Pass JSON Recovery Engine"]
        R1["Pass 1: json.loads(strict=False)"]
        R2["Pass 2: json_repair.loads(raw_text)"]
        R3["Pass 3: Substring Extraction { ... }"]
        R4["Pass 4: Heuristic Regex (Backslashes, Missing/Trailing Commas)"]
        R5["Pass 5: json_repair.loads(fixed_substring)"]
        R1 -->|If error| R2
        R2 -->|If error| R3
        R3 -->|If error| R4
        R4 -->|If error| R5
    end

    P3_3 --> Resilient_Parser
    Resilient_Parser -->|"Sanitized Dictionary"| P3_4["[3.4] Performance Intelligence Integrator<br/>(Scores, Root Cause, Recommendations)"]:::proc
    P3_4 --> OutJSON["Persisted to *_result.json"]
```

---

### 3.3 Sub-Process 4.0: Modular Report Generator Pipeline

```mermaid
flowchart LR
    classDef comp fill:#1e1e2e,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef orch fill:#311b92,stroke:#a855f7,stroke-width:3px,color:#f8fafc;
    classDef out fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;

    Input["Parsed Result JSON + Azure JSON + JMX Info"] --> DP["[4.1] Data Processor<br/>(data_processor.py)<br/>Computes 440+ context keys"]:::comp

    DP -->|"Context Dict (ctx)"| Orchestrator["[4.2] Generator Orchestrator<br/>(generator.py)"]:::orch

    subgraph Design_Components ["Parallel Modular Components"]
        direction TB
        STYLES["[4.3] Modular Styles<br/>(styles/)<br/>• base.py<br/>• layout.py<br/>• tables.py<br/>• charts.py<br/>• comparison.py<br/>• drawers.py<br/>• print_media.py"]:::comp
        COMPS["[4.4] HTML Components<br/>(components/)<br/>• header.py<br/>• navigation.py<br/>• tab_executive.py<br/>• tab_load.py<br/>• tab_iterations.py<br/>• tab_response_time.py<br/>• tab_errors.py<br/>• tab_infrastructure.py<br/>• tab_comparison.py<br/>• modals.py"]:::comp
        SCRIPTS["[4.5] Client Scripts<br/>(scripts/)<br/>• core.py<br/>• comparison.py<br/>• interactions.py<br/>• charts.py<br/>• drawers.py"]:::comp
    end

    Orchestrator --> STYLES
    Orchestrator --> COMPS
    Orchestrator --> SCRIPTS

    STYLES -->|"Complete CSS Bundle"| Assembler["[4.6] Document Assembler<br/>(_assemble_document)"]:::orch
    COMPS -->|"Combined Body DOM"| Assembler
    SCRIPTS -->|"Unified JavaScript Logic"| Assembler

    Assembler --> SingleHTML["📄 Single Standalone HTML Report<br/>(1.17 MB Self-Contained Document)"]:::out
```

---

### 3.4 Sub-Process 5.0: Differential Comparison & Publishing System

```mermaid
sequenceDiagram
    autonumber
    actor User as Performance Engineer
    participant Report as Report Client (HTML)
    participant Server as Web Server (web_server.py)
    participant Compare as Compare Service (compare_service.py)
    participant AI as AI Engine (ai_insights.py)
    participant Storage as File Storage (Results/Published)

    Note over User,Report: 1. Draft Report Interactivity (Editable Mode)
    User->>Report: Opens Draft HTML Report
    Report->>Server: GET /api/compare-runs/list
    Server->>Compare: get_available_runs()
    Compare-->>Server: Return list of prior runs
    Server-->>Report: JSON { runs: [...] }
    Report->>Report: Populate dropdown: #compareBaselineSelect

    User->>Report: Selects Baseline Run (Run A)
    Report->>Server: GET /api/compare-runs?baseline_id=A&current_id=B
    Server->>Compare: compare_two_runs(baseline_id, current_id)
    Compare->>Compare: Compute Diff (TPS, RT, P90, P95, Errors)
    Compare->>Compare: Compute 4-Quadrant SLA Matrix (Pass->Pass, Pass->Fail, etc.)
    Compare->>AI: generate_2run_comparison_ai_insights(...)
    AI-->>Compare: Live Grounded LLM Comparative Insights
    Compare-->>Server: JSON { scorecard, ai_insights, transitions, ... }
    Server-->>Report: Render differential split cards & Chart.js delta graphs

    Note over User,Storage: 2. Publishing Workflow
    User->>Report: Clicks "🚀 Publish Report"
    alt Comparison is Active
        Report->>Report: Strip #compare-selector-bar & #compare-empty-state
        Report->>Report: Permanently freeze comparison cards in DOM
    else No Comparison Active
        Report->>Report: Remove #nav-btn-comparison and #rpt-compare completely
    end
    Report->>Report: Remove contenteditable, cleanup canvas sizing
    Report->>Server: POST /api/save-published-report { report_name, html_content }
    Server->>Storage: Writes to Results/Published/*_published.html
    Server-->>Report: Return Success + redirect URL
    Report-->>User: Open permanent, frozen published report
```

---

## 4. Key Data Stores Dictionary

| Data Store | Physical Path / Format | Description | Consuming Subsystems |
|---|---|---|---|
| **D_JTL** | `Results/jtl/*.jtl` (CSV / XML) | Raw sample execution logs from JMeter runs | `[1.0]` Ingestion, `[2.1]` JTL Parser |
| **D_Azure** | `Results/json/azure_*.json` (JSON) | Azure Monitor infrastructure metrics (CPU, Memory, Disk Queue, Network I/O) | `[1.0]` Collector, `[2.4]` Correlation, `[4.1]` Data Processor |
| **D_SLA** | `config/sla_targets.xlsx` (Excel) | User-defined transaction latency and error rate SLAs | `[2.2]` SLA Evaluator, `[3.1]` Prompt Builder |
| **D_JSON** | `Results/json/*_result.json` (JSON) | Aggregated run metrics, percentiles, error breakdowns, and persisted AI insights | `[3.0]` AI Engine, `[4.1]` Data Processor, `[5.0]` Compare Service |
| **D_Runs** | `data/runs.json` (JSON) | Global catalog of all historical runs, statuses, timestamps, and test script names | `[5.0]` Compare Service, `[6.0]` Web Server |
| **D_HTML** | `Results/html/*_report.html` (HTML) | Single standalone draft interactive report with client-side comparison selector and AI chat drawer | `[6.0]` Web Server / Browser |
| **D_Pub** | `Results/Published/*_published.html` (HTML) | Permanent, read-only published report with comparisons baked in (or stripped out) and edit controls removed | Stakeholders / CI/CD Delivery |
