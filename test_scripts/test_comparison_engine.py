#!/usr/bin/env python3
"""
test_comparison_engine.py — Automated verification script for the Performance Release Comparison & Trend Analysis module.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_files.trend_engine import (
    load_all_runs_data,
    get_hierarchy_tree,
    build_comparison_analysis,
    generate_professional_comparison_html
)
from python_files.ai_insights import generate_comparison_ai_insights


def test_comparison():
    print("=" * 60)
    print("Testing Performance Release Comparison & Trend Analysis Module")
    print("=" * 60)

    # 1. Test data loading
    runs = load_all_runs_data()
    print(f"[*] Loaded {len(runs)} enriched test runs.")
    assert len(runs) > 0, "No test runs loaded!"

    # 2. Test hierarchy tree
    tree = get_hierarchy_tree()
    print(f"[*] Hierarchy Projects: {list(tree.get('hierarchy', {}).keys())}")
    assert "hierarchy" in tree, "Hierarchy tree missing 'hierarchy' key!"

    # 3. Test multi-release comparison analysis with hierarchy
    analysis_all = build_comparison_analysis(limit=5, item_type_filter="")
    assert analysis_all.get("success") is True, f"Comparison all failed: {analysis_all.get('message')}"
    print(f"[*] Comparison with ALL items: {len(analysis_all.get('transaction_comparisons', []))} items analyzed.")

    analysis_tx = build_comparison_analysis(limit=5, item_type_filter="TRANSACTIONS_ONLY")
    assert analysis_tx.get("success") is True, f"Comparison tx only failed: {analysis_tx.get('message')}"
    print(f"[*] Comparison with TRANSACTIONS ONLY: {len(analysis_tx.get('transaction_comparisons', []))} transactions analyzed.")

    analysis_req = build_comparison_analysis(limit=5, item_type_filter="HTTP_REQUEST")
    assert analysis_req.get("success") is True, f"Comparison requests only failed: {analysis_req.get('message')}"
    print(f"[*] Comparison with HTTP REQUESTS ONLY: {len(analysis_req.get('transaction_comparisons', []))} requests analyzed.")

    analysis = analysis_tx

    meta = analysis.get("metadata", {})
    kpis = analysis.get("executive_kpis", {})
    concl = analysis.get("deterministic_conclusions", {})
    rankings = analysis.get("rankings", {})
    change_points = analysis.get("change_points", [])
    percentiles = analysis.get("distribution_percentiles", [])

    print(f"    - Baseline: {meta.get('baseline_release')} ({meta.get('baseline_id')})")
    print(f"    - Current:  {meta.get('current_release')} ({meta.get('current_id')})")
    print(f"    - Releases Compared: {meta.get('releases_compared_count')}")
    print(f"    - Transactions Analyzed: {meta.get('transactions_compared_count')}")
    print(f"    - Avg RT Baseline -> Current: {kpis.get('avg_rt_baseline'):.2f}ms -> {kpis.get('avg_rt_current'):.2f}ms ({kpis.get('avg_rt_delta_pct'):+.2f}%)")
    print(f"    - SLA Pass Rate: {kpis.get('sla_pass_rate_baseline'):.1f}% -> {kpis.get('sla_pass_rate_current'):.1f}% ({kpis.get('sla_pass_rate_delta'):+.1f} pts)")
    print(f"    - Most Degraded Transaction: {concl.get('most_degraded')} ({concl.get('most_degraded_pct'):+.2f}%)")
    print(f"    - Slowest Transaction: {concl.get('slowest_transaction')}")
    print(f"    - Total Change Points Tracked: {len(change_points)}")
    print(f"    - Percentile Distribution Rows: {len(percentiles)}")

    # 4. Verify 5-D rankings exist
    assert "slowest" in rankings, "Ranking 1 (slowest) missing"
    assert "degradation" in rankings, "Ranking 2 (degradation) missing"
    assert "sla_breach" in rankings, "Ranking 3 (sla_breach) missing"
    assert "most_improved" in rankings, "Ranking 4 (most_improved) missing"
    assert "business_risk" in rankings, "Ranking 5 (business_risk) missing"
    print("[*] Verified 5-Dimensional Rankings.")

    # 5. Test AI Insights generator
    ai_res = generate_comparison_ai_insights(analysis)
    print(f"[*] AI Insights Source: {ai_res.get('source')}")
    print(f"    - Executive Bullets Count: {len(ai_res.get('executive_bullets', []))}")
    print(f"    - Trend Observation: {ai_res.get('trend_observation')}")

    # 6. Test HTML Report Generation
    html = generate_professional_comparison_html(analysis, view_mode="all")
    assert "<!DOCTYPE html>" in html, "HTML report missing doctype"
    assert "Performance Release Comparison" in html, "HTML report missing header title"
    print(f"[*] Generated HTML Comparison Report successfully ({len(html)} bytes).")

    out_file = _ROOT / "Results" / "html" / "test_verification_comparison.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    print(f"[*] Saved test report to {out_file}")

    print("\n[SUCCESS] All automated verification checks passed successfully!")


if __name__ == "__main__":
    test_comparison()
