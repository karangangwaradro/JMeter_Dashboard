#!/usr/bin/env python3
"""
components — Modular HTML body components for the performance report.

Assembles all page sections:
  - Header & Summary KPI Strip
  - Tab Navigation Bar
  - Tab 1: Executive Dashboard
  - Tab 2: Load & Capacity Profile
  - Tab 3: Iteration Stats & Pacing
  - Tab 4: Response Time Analytics & Transactions
  - Tab 5: SLA & Failure Analysis
  - Tab 6: Infrastructure & Correlations
  - Tab 7: Benchmark & Run Comparison
  - Modals & AI Drawers
"""

from python_files.report_generator.components.header import render_header
from python_files.report_generator.components.navigation import render_navigation
from python_files.report_generator.components.tab_executive import render_tab_executive
from python_files.report_generator.components.tab_load import render_tab_load
from python_files.report_generator.components.tab_iterations import render_tab_iterations
from python_files.report_generator.components.tab_response_time import render_tab_response_time
from python_files.report_generator.components.tab_errors import render_tab_errors
from python_files.report_generator.components.tab_infrastructure import render_tab_infrastructure
from python_files.report_generator.components.tab_comparison import render_tab_comparison
from python_files.report_generator.components.modals import render_modals


def render_body(ctx: dict) -> str:
    """Render the complete HTML body by assembling all modular components."""
    parts = [
        render_header(ctx),
        render_navigation(ctx),
        render_tab_executive(ctx),
        render_tab_load(ctx),
        render_tab_iterations(ctx),
        render_tab_response_time(ctx),
        render_tab_errors(ctx),
        render_tab_infrastructure(ctx),
        render_tab_comparison(ctx),
        render_modals(ctx)
    ]
    return "".join(parts)
