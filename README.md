# PerfPilot — Multi-Tool Performance Engineering Platform

An enterprise performance testing, telemetry correlation, AI diagnostics, and interactive reporting platform supporting **Apache JMeter**, **BlazeMeter Cloud**, and **NeoLoad Web**.

---

## Key Features

- **Multi-Tool Support:** Native support for Apache JMeter, BlazeMeter Cloud, and NeoLoad Web.
- **Multiple Ingestion Methods:** Local CLI execution, direct REST API polling, Model Context Protocol (MCP), and raw result file uploads.
- **Strongly Typed Domain Contracts:** Internal communication strictly through Pydantic V2 models (`TimeSeriesResult`, `AggregateResult`, `ServerMetrics`) with two-way legacy schema key normalization.
- **Decoupled Architecture:** Complete independence between Execution, Collection, Parsing, Normalization, Analytics, and Reporting.
- **SLA & Apdex Management:** Strict transaction vs. request hierarchy (`MAIN_TRANSACTION` depth=0 vs `HTTP_REQUEST` depth=1), evaluating SLAs and compliance strictly at transaction level while keeping leaf request metrics neutrally styled.
- **Infrastructure Telemetry Correlation:** Correlate test performance against Azure Monitor, Prometheus, or generic CSV metrics.
- **AI Diagnostics & Studio:** Multi-provider LLM cascade (OpenRouter with automatic free-tier fallback on 402, Gemini, GitHub) with token budgeting, live prompt preview, and real-time report telemetry injection.
- **Executive Summary Multi-Chart Snapshots:** Dynamic time-series chart duplication allowing users to freeze comparison snapshots across user journeys and metrics without cluttered controls.
- **Historical Trends & 2-Run Comparison:** Multi-release trend engine with heatmap matrix and 2-run differential scorecard.
- **Modular Report Generator:** Standalone HTML reports synthesized via decoupled components, stylesheets, and scripts with full-width responsive time-series charts (`maintainAspectRatio: false`).

---

## Recent Platform Enhancements

1. **AI Insights Studio Auto-Fallback & Token Optimization**:
   - Integrated automatic fallback to OpenRouter free-tier models (`google/gemini-2.0-flash-lite-preview-02-05:free`, `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`) when account credit exhaustion (HTTP 402) occurs.
   - Built a live prompt preview endpoint with token budgeting, injecting real run telemetry and deterministic findings.
   - Enhanced the frontend studio with an ES6-to-global bridge for frictionless prompt analysis and direct report generation.

2. **Transaction vs. Request Hierarchy & Accurate SLA Compliance**:
   - Clarified the distinction between business transactions (`depth=0`) and child HTTP requests (`depth=1`).
   - SLA targets and overall compliance rates are now evaluated strictly over parent transactions, preventing dilution from leaf requests.
   - Request-level rows in the report transaction breakdown table now render in neutral styling (`var(--text)`) without misleading pass/fail coloring, reflecting that SLAs apply exclusively at transaction level.

3. **Two-Way Schema Normalization**:
   - Implemented bidirectional key normalization across `AggregateResult` and reporting dictionaries (`avg_response_time` $\leftrightarrow$ `avg_rt`, `duration_seconds` $\leftrightarrow$ `duration_sec`, `total_requests` $\leftrightarrow$ `total`, `failed_requests` $\leftrightarrow$ `errors`).
   - Fixed zero-value KPI reporting across Executive Summary metric cards and synthetic summaries.

4. **Multi-Chart Snapshot Comparison**:
   - Added `duplicateTxRtView()` functionality to the Executive Summary response time chart.
   - When a user duplicates a filtered view, the new snapshot is rendered without interactive filter dropdowns, pinned with a snapshot timestamp badge and close button for side-by-side comparison.

5. **Full-Width Responsive Time-Series Visualizations**:
   - Configured `maintainAspectRatio: false` with responsive container heights (280px) on time-series charts, allowing them to expand across full viewport widths cleanly.

---

## Repository Structure

```
JmeterAI/
├── app/                             # Core Application Package
│   ├── api/                         # FastAPI Web Layer & Route Controllers
│   │   ├── app.py                   # FastAPI application factory & OpenAPI docs
│   │   ├── server.py                # Server runner with port-hunting fallback
│   │   ├── middleware/              # Exception handling & logging
│   │   └── routes/                  # Modular endpoints (status, execution, ingestion, runs, compare, trends, ai_studio, reports)
│   ├── cli/                         # CLI Utilities (build_web, recompile, organize, setup)
│   ├── core/                        # Settings, constants, logging, exception types
│   ├── domain/                      # Typed Pydantic contracts & abstract interfaces
│   ├── integrations/                # Tool runners & parsers (jmeter, blazemeter, neoload, mcp, upload)
│   ├── serialization/               # JSON domain serializer & JSON Schema validator
│   ├── server_metrics/              # Telemetry collectors & parsers (azure, prometheus, csv)
│   └── services/                    # Domain services (analytics, ai, reporting, execution, orchestrator)
├── config/                          # SLA targets and runtime configuration
├── data/                            # Historical runs manifest and data files
├── docs/                            # Documentation
├── logs/                            # Application and AI execution logs
├── Results/                         # Test outputs (html/, json/, jtl/, normalized/, raw/)
├── schemas/                         # JSON Schema contract definitions
├── Tests/                           # Test scripts (.jmx test plans, unit & integration tests)
├── test_scripts/                    # Verification test scripts
├── web/                             # Modular Frontend Application
│   ├── views/                       # Semantic HTML component templates
│   ├── css/                         # Modular stylesheets (base, navbar, sidebar, components, etc.)
│   ├── js/                          # Modular ES6 JavaScript (core/ and modules/)
│   ├── index.html                   # Pre-assembled App Shell (Zero-latency delivery)
│   ├── app.css                      # Backward-compatible proxy to css/main.css
│   └── app.js                       # Backward-compatible proxy to js/app.js
├── main.py                          # Application entry point
├── START_SERVER.bat                 # Windows quick launcher script (auto-builds web & launches)
└── requirements.txt                 # Project dependencies
```

---

## Getting Started

1. **Launch Server**:
   ```bash
   python main.py
   # or double-click START_SERVER.bat
   ```

2. **Rebuild Web Assets (Optional)**:
   ```bash
   python app/cli/build_web.py
   ```

3. **Access Interactive Web Interfaces**:
   - Web Dashboard: [http://localhost:8080/](http://localhost:8080/)
   - Swagger Interactive API Docs: [http://localhost:8080/docs](http://localhost:8080/docs)
   - ReDoc API Specification: [http://localhost:8080/redoc](http://localhost:8080/redoc)

4. **Run Automated Tests**:
   ```bash
   python -m unittest discover -s Tests/unit
   python -m unittest discover -s Tests/integration
   ```
