#!/usr/bin/env python3
"""
styles — Modular CSS stylesheets for the performance report.

Combines all CSS modules:
  - base: Design tokens, CSS variables, typography, reset
  - layout: Header, navigation tabs, KPI grids, glass panels
  - tables: Metrics tables, hierarchical tree rows, search & filters
  - charts: Chart.js containers, multi-series filters, snapshots
  - comparison: Benchmark delta badges, split cards, transition grid
  - drawers: AI assistant chat drawer, graph guides, validation badges
  - print_media: Print styling & PDF export rules
"""

from python_files.report_generator.styles.base import get_base_styles
from python_files.report_generator.styles.layout import get_layout_styles
from python_files.report_generator.styles.tables import get_table_styles
from python_files.report_generator.styles.charts import get_chart_styles
from python_files.report_generator.styles.comparison import get_comparison_styles
from python_files.report_generator.styles.drawers import get_drawer_styles
from python_files.report_generator.styles.print_media import get_print_styles


def build_all_css(ctx: dict) -> str:
    """Combine all CSS modules into the complete stylesheet."""
    return "\n".join([
        get_base_styles(ctx),
        get_layout_styles(ctx),
        get_table_styles(ctx),
        get_chart_styles(ctx),
        get_comparison_styles(ctx),
        get_drawer_styles(ctx),
        get_print_styles(ctx)
    ])
