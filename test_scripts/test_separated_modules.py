#!/usr/bin/env python3
"""
test_separated_modules.py — Verification script for the architectural separation
of Compare Runs (2-Run Deep Dive) and Historical Trend Analysis (Multi-Release Direction).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_files.comparison_engine import (
    get_available_runs,
    build_run_comparison,
    generate_run_comparison_html
)
from python_files.trend_engine import (
    get_hierarchy_tree,
    build_trend_analysis,
    generate_trend_dashboard_html
)


def test_separation():
    print("=" * 65)
    print("TESTING ARCHITECTURAL SEPARATION: COMPARE RUNS vs TREND ANALYSIS")
    print("=" * 65)

    # ─────────────────────────────────────────────────────────────
    # PART 1: COMPARE RUNS ENGINE (Run A vs Run B Deep Dive)
    # ─────────────────────────────────────────────────────────────
    print("\n[*] 1. Testing Compare Runs Engine (Run A vs Run B)...")
    runs = get_available_runs()
    assert len(runs) >= 2, f"Expected at least 2 runs, found {len(runs)}"
    run_a_id = runs[1]["id"]
    run_b_id = runs[0]["id"]
    print(f"    Comparing Run A: {run_a_id} vs Run B: {run_b_id}")

    comp_res = build_run_comparison(run_a_id, run_b_id, item_type_filter="TRANSACTIONS_ONLY")
    assert comp_res.get("success") is True, f"Run comparison failed: {comp_res.get('message')}"

    scorecard = comp_res.get("scorecard", {})
    findings = comp_res.get("ai_findings", [])
    rows = comp_res.get("transaction_comparisons", [])
    rankings = comp_res.get("rankings", {})

    print(f"    - Transactions Analyzed: {len(rows)}")
    print(f"    - Avg RT Change: {scorecard.get('run_a_rt'):.2f}ms -> {scorecard.get('run_b_rt'):.2f}ms ({scorecard.get('rt_change_pct'):+.2f}%)")
    print(f"    - Throughput Change: {scorecard.get('run_a_tps'):.2f} TPS -> {scorecard.get('run_b_tps'):.2f} TPS ({scorecard.get('tps_change_pct'):+.2f}%)")
    print(f"    - Error Rate Change: {scorecard.get('run_a_err'):.2f}% -> {scorecard.get('run_b_err'):.2f}% ({scorecard.get('err_change_pp'):+.2f} pp)")
    print(f"    - SLA Pass Rate: {scorecard.get('run_a_sla_pass'):.1f}% -> {scorecard.get('run_b_sla_pass'):.1f}% ({scorecard.get('sla_pass_change_pp'):+.1f} pp)")
    print(f"    - State Changes: Improved={scorecard.get('transactions_improved')}, Degraded={scorecard.get('transactions_degraded')}, Unchanged={scorecard.get('transactions_unchanged')}, New Breaches={scorecard.get('new_sla_breaches')}, Resolved={scorecard.get('resolved_sla_breaches')}")
    print(f"    - Grounded AI Findings: {len(findings)} bullets generated.")

    # Check 5 rankings exist
    assert "biggest_degradation" in rankings, "Ranking 1 missing"
    assert "biggest_improvement" in rankings, "Ranking 2 missing"
    assert "largest_sla_breach" in rankings, "Ranking 3 missing"
    assert "largest_throughput_change" in rankings, "Ranking 4 missing"
    assert "highest_error_increase" in rankings, "Ranking 5 missing"
    print("    - Verified all 5 Comparison Rankings.")

    # Test HTML generation for Run Comparison
    comp_html = generate_run_comparison_html(comp_res)
    assert "<!DOCTYPE html>" in comp_html and "Run Comparison Engineering Report" in comp_html
    print(f"    - Generated Run Comparison HTML Report ({len(comp_html)} bytes).")

    # ─────────────────────────────────────────────────────────────
    # PART 2: TREND ANALYSIS ENGINE (Multi-Release Direction)
    # ─────────────────────────────────────────────────────────────
    print("\n[*] 2. Testing Historical Trend Analysis Engine (Multi-Release)...")
    tree = get_hierarchy_tree()
    assert "hierarchy" in tree, "Hierarchy tree missing"
    print(f"    Hierarchy Projects: {list(tree['hierarchy'].keys())}")

    trend_res = build_trend_analysis(item_type_filter="TRANSACTIONS_ONLY", limit=10)
    assert trend_res.get("success") is True, f"Trend analysis failed: {trend_res.get('message')}"

    kpis = trend_res.get("kpis", {})
    obs = trend_res.get("ai_observations", [])
    nodes = trend_res.get("release_nodes", [])
    heatmap = trend_res.get("heatmap", {})
    sev_dist = trend_res.get("severity_distribution", [])

    print(f"    - Releases Tracked: {len(nodes)} ({nodes[0]['code']} -> {nodes[-1]['code']})")
    print(f"    - Current RT: {kpis.get('current_rt'):.2f}ms (Overall Trend: {kpis.get('overall_trend_pct'):+.2f}%)")
    print(f"    - Current SLA Pass Rate: {kpis.get('current_sla_pass_rate'):.1f}% ({kpis.get('current_sla_status')})")
    print(f"    - Best Release: {kpis.get('best_release')} | Worst Release: {kpis.get('worst_release')}")
    print(f"    - Executive Observations: {len(obs)} high-level bullets.")
    print(f"    - Heatmap Matrix Rows: {len(heatmap.get('matrix', []))}")
    print(f"    - Severity Evolution Stack Points: {len(sev_dist)}")

    # Test HTML generation for Trend Dashboard
    trend_html = generate_trend_dashboard_html(trend_res)
    assert "<!DOCTYPE html>" in trend_html and "Historical Trend Analysis Dashboard" in trend_html
    print(f"    - Generated Trend Dashboard HTML Report ({len(trend_html)} bytes).")

    print("\n[SUCCESS] All architectural separation verification tests passed perfectly!")


if __name__ == "__main__":
    test_separation()
