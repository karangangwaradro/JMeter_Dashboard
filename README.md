# PerfPilot — Multi-Tool Performance Engineering Platform

An enterprise performance testing, telemetry correlation, AI diagnostics, and interactive reporting platform supporting **Apache JMeter**, **BlazeMeter Cloud**, and **NeoLoad Web**.

---

## Key Features

- **Multi-Tool Support:** Native support for Apache JMeter, BlazeMeter Cloud, and NeoLoad Web.
- **Multiple Ingestion Methods:** Local CLI execution, direct REST API polling, Model Context Protocol (MCP), and raw result file uploads.
- **Strongly Typed Domain Contracts:** Internal communication strictly through Pydantic V2 models (`TimeSeriesResult`, `AggregateResult`, `ServerMetrics`).
- **Decoupled Architecture:** Complete independence between Execution, Collection, Parsing, Normalization, Analytics, and Reporting.
- **SLA & Apdex Management:** Nearest-neighbor load scenario matching, hierarchical transaction parsing, and custom SLA targets.
- **Infrastructure Telemetry Correlation:** Correlate test performance against Azure Monitor, Prometheus, or generic CSV metrics.
- **AI Diagnostics & Scoring:** Multi-provider LLM cascade (OpenRouter, Gemini, GitHub) for automated root-cause analysis and executive summaries.
- **Historical Trends & 2-Run Comparison:** Multi-release trend engine with heatmap matrix and 2-run differential scorecard.
- **Modular Report Generator:** Standalone HTML reports synthesized via decoupled components, stylesheets, and scripts.

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
│   ├── cli/                         # CLI Utilities (recompile, organize, setup)
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
├── web/                             # Frontend UI assets (HTML, CSS, JS)
├── main.py                          # Application entry point
├── START_SERVER.bat                 # Windows quick launcher script
└── requirements.txt                 # Project dependencies
```

---

## Getting Started

1. **Launch Server**:
   ```bash
   python main.py
   # or double-click START_SERVER.bat
   ```
2. **Access Interactive Web Interfaces**:
   - Web Dashboard: [http://localhost:8080/](http://localhost:8080/)
   - Swagger Interactive API Docs: [http://localhost:8080/docs](http://localhost:8080/docs)
   - ReDoc API Specification: [http://localhost:8080/redoc](http://localhost:8080/redoc)

3. **Run Automated Tests**:
   ```bash
   python -m unittest discover -s Tests/unit
   python -m unittest discover -s Tests/integration
   ```
