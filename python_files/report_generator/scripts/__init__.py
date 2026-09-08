#!/usr/bin/env python3
"""
scripts — Modular JavaScript for the performance report.

Combines all client-side modules:
  - core: Themes (dark/light), tab switching (switchReportTab), storage
  - comparison: Benchmark & run comparison (initComparisonTab, onBaselineSelectionChange)
  - interactions: Edit mode toggling, human validation persistence, publishReport()
  - charts: Chart.js hierarchical latency graphs, error donuts, VU profile
  - drawers: Contextual AI assistant chat, patch parser, findings drawer, graph guide modals
"""

from python_files.report_generator.scripts.core import get_core_js
from python_files.report_generator.scripts.comparison import get_comparison_js
from python_files.report_generator.scripts.interactions import get_interactions_js
from python_files.report_generator.scripts.charts import get_charts_js
from python_files.report_generator.scripts.drawers import get_drawers_js


def build_all_js(ctx: dict) -> str:
    """Combine all JavaScript modules into the complete client-side script."""
    return "\n".join([
        get_core_js(ctx),
        get_comparison_js(ctx),
        get_interactions_js(ctx),
        get_charts_js(ctx),
        get_drawers_js(ctx)
    ])
