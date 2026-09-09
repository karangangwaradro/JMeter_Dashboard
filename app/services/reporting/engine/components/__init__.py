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

from app.services.reporting.engine.components.header import render_header
from app.services.reporting.engine.components.navigation import render_navigation
from app.services.reporting.engine.components.tab_executive import render_tab_executive
from app.services.reporting.engine.components.tab_load import render_tab_load
from app.services.reporting.engine.components.tab_iterations import render_tab_iterations
from app.services.reporting.engine.components.tab_response_time import render_tab_response_time
from app.services.reporting.engine.components.tab_errors import render_tab_errors
from app.services.reporting.engine.components.tab_infrastructure import render_tab_infrastructure
from app.services.reporting.engine.components.tab_comparison import render_tab_comparison
from app.services.reporting.engine.components.modals import render_modals


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
