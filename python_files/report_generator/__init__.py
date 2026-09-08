#!/usr/bin/env python3
"""
Report Generator Package — Public API.

This package modularizes the monolithic report_generator.py into:
  - data_processor.py: All metric computation, SLA evaluation, chart data prep
  - styles/: CSS modules (tokens, layout, components, charts, etc.)
  - components/: HTML template builders (one per tab/section)
  - scripts/: JavaScript modules (charts, edit/publish, AI chat, etc.)
  - generator.py: Core orchestrator that assembles the final HTML

Usage:
    from python_files.report_generator import generate_report
    generate_report(parsed, azure_data, ai_insights, report_path, jmx_name, users)
"""

from python_files.report_generator.generator import generate_report

__all__ = ["generate_report"]
