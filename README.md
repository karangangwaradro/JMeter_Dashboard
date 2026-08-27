# PerfPilot Dashboard & Performance Analytics

An automated performance testing, telemetry correlation, AI diagnostics, and interactive reporting platform for Apache JMeter tests.

---

## 🌟 Key Features

- **Local JMeter Execution & Live Monitoring:** Run `.jmx` test scripts with real-time response time and throughput tracking.
- **Dedicated JTL Parser Engine:** Robust parsing of raw JMeter CSV logs for statistical percentiles, error breakdowns, and dynamic time series.
- **Hierarchical Transaction & Thread Group Support:** Configure per-thread-group user loads, ramp-ups, and durations.
- **SLA & Apdex Management:** Define custom SLA thresholds per transaction and calculate user satisfaction indices.
- **Infrastructure Telemetry Correlation:** Correlate client performance against Azure App Service/VM server metrics (CPU, Memory, Disk, Network).
- **AI Diagnostics & Scoring:** Automated root-cause analysis, bottleneck detection, and remediation recommendations via LLMs and deterministic rule engines.
- **Historical Trends & Run Comparison:** Multi-run trend tracking and side-by-side performance comparison dashboards.
- **Interactive Reports:** Standalone HTML reports with rich interactive Chart.js visualizations.

---

## 📁 Repository Structure

```
PerfPilot/
├── python_files/           # Backend modules & analytics engines (see python_files/README.md)
│   ├── run_local_jmeter.py # Test runner & process orchestrator
│   ├── jtl_parser.py       # Dedicated JTL / CSV parser engine
│   ├── comparison_engine.py# 2-Run deep dive comparison engine (Run A vs Run B)
│   ├── trend_engine.py     # Multi-release historical trend analysis engine
│   ├── report_generator.py # HTML report generation
│   ├── ai_insights.py      # LLM & rule-based diagnostics
│   ├── findings_engine.py  # Performance findings & rules
│   ├── correlation_engine.py# Client vs. Server correlator
│   ├── sla_manager.py      # SLA targets & JMX hierarchy parser
│   ├── jmx_editor.py       # JMX XML editor
│   ├── apdex_calculator.py # Apdex score calculation
│   ├── azure_monitor.py    # Infrastructure telemetry collector
│   ├── organize_results.py # Artifact organization utility
│   ├── recompile_latest.py # Single run recompiler
│   └── recompile_all.py    # Batch run recompiler
├── services/               # Web backend services & API routes
│   └── web_server.py       # FastAPI / HTTP web server
├── web/                    # Frontend UI assets (HTML, CSS, JS)
├── config/                 # SLA targets and runtime configuration
├── Tests/                  # JMeter test plans (.jmx scripts)
├── Results/                # Test outputs (runs, raw JTLs, HTML reports)
└── START_SERVER.bat        # Quick launcher script
```

---

## 📖 Module Documentation

For a detailed functional overview, data flow pipeline, and input/output specifications of every Python engine, see the **[Python Modules & Architecture Guide](file:///d:/BlazemeterMCPZIP/PerfPilot/python_files/README.md)**.
