"""
app.services.analytics — Performance analytics, Apdex, SLA evaluation, run comparison, and trend analysis.
"""

from app.services.analytics.apdex import calculate_apdex, calculate_apdex_from_summary, get_apdex_rating
from app.services.analytics.sla_manager import (
    load_sla_targets,
    load_sla_scenarios_and_targets,
    save_sla_targets,
    parse_jmx_hierarchy,
    parse_jmx_thread_groups,
    parse_jmx_full_tree,
    match_nearest_scenario,
    get_matched_scenario_info,
)
from app.services.analytics.correlation import correlate_metrics
from app.services.analytics.comparison import (
    get_available_runs,
    load_run_data,
    compare_two_runs,
    save_comparison_draft,
    load_comparison_draft,
    clear_comparison_draft,
)
from app.services.analytics.trends import (
    get_hierarchy_tree,
    build_trend_analysis,
    generate_trend_dashboard_html,
    load_all_runs_data,
)

__all__ = [
    "calculate_apdex",
    "calculate_apdex_from_summary",
    "get_apdex_rating",
    "load_sla_targets",
    "load_sla_scenarios_and_targets",
    "save_sla_targets",
    "parse_jmx_hierarchy",
    "parse_jmx_thread_groups",
    "parse_jmx_full_tree",
    "match_nearest_scenario",
    "get_matched_scenario_info",
    "correlate_metrics",
    "get_available_runs",
    "load_run_data",
    "compare_two_runs",
    "save_comparison_draft",
    "load_comparison_draft",
    "clear_comparison_draft",
    "get_hierarchy_tree",
    "build_trend_analysis",
    "generate_trend_dashboard_html",
    "load_all_runs_data",
]
