#!/usr/bin/env python3
"""Edit mode, report publishing (publishReport), and human validation checks."""
import json
import re

def get_interactions_js(ctx: dict) -> str:
    """Return JS chunk from context."""
    SEVERITY_BADGES = ctx.get("SEVERITY_BADGES")
    _build_validation_badge = ctx.get("_build_validation_badge")
    _clean_client_text = ctx.get("_clean_client_text")
    _format_as_pointers = ctx.get("_format_as_pointers")
    ai_badge = ctx.get("ai_badge")
    ai_badge_color = ctx.get("ai_badge_color")
    ai_chat_history_json = ctx.get("ai_chat_history_json")
    ai_insights = ctx.get("ai_insights")
    ai_source = ctx.get("ai_source")
    all_apdex_scores = ctx.get("all_apdex_scores")
    all_findings = ctx.get("all_findings")
    all_recommendations = ctx.get("all_recommendations")
    apdex_below_25_count = ctx.get("apdex_below_25_count")
    apdex_below_50_count = ctx.get("apdex_below_50_count")
    apdex_score_str = ctx.get("apdex_score_str")
    area = ctx.get("area")
    assessment = ctx.get("assessment")
    assessment_html = ctx.get("assessment_html")
    avg_rt = ctx.get("avg_rt")
    avg_v = ctx.get("avg_v")
    avg_val = ctx.get("avg_val")
    azure_configured = ctx.get("azure_configured")
    azure_data = ctx.get("azure_data")
    azure_section_style = ctx.get("azure_section_style")
    azure_ts = ctx.get("azure_ts")
    b = ctx.get("b")
    b_color = ctx.get("b_color")
    b_desc = ctx.get("b_desc")
    b_name = ctx.get("b_name")
    b_title = ctx.get("b_title")
    badge = ctx.get("badge")
    badge_html = ctx.get("badge_html")
    baseline_text = ctx.get("baseline_text")
    bi = ctx.get("bi")
    bottleneck = ctx.get("bottleneck")
    bottleneck_cards_html = ctx.get("bottleneck_cards_html")
    bottleneck_items = ctx.get("bottleneck_items")
    breached_tcs = ctx.get("breached_tcs")
    c = ctx.get("c")
    c_cls_id = ctx.get("c_cls_id")
    c_err_sum = ctx.get("c_err_sum")
    c_eval = ctx.get("c_eval")
    c_p95_max = ctx.get("c_p95_max")
    c_samplers_table = ctx.get("c_samplers_table")
    c_tp_avg = ctx.get("c_tp_avg")
    c_vu_val = ctx.get("c_vu_val")
    calc_pearson_r = ctx.get("calc_pearson_r")
    calculate_apdex = ctx.get("calculate_apdex")
    calculate_apdex_from_summary = ctx.get("calculate_apdex_from_summary")
    cap = ctx.get("cap")
    cap_err_rate_val = ctx.get("cap_err_rate_val")
    cap_html = ctx.get("cap_html")
    cap_p95_str = ctx.get("cap_p95_str")
    cap_p95_val = ctx.get("cap_p95_val")
    cap_peak_tps = ctx.get("cap_peak_tps")
    cap_safe_operating = ctx.get("cap_safe_operating")
    cap_section_style = ctx.get("cap_section_style")
    cap_status_color = ctx.get("cap_status_color")
    cap_status_text = ctx.get("cap_status_text")
    capacity_rating = ctx.get("capacity_rating")
    chart_observations = ctx.get("chart_observations")
    child_html = ctx.get("child_html")
    child_tcs = ctx.get("child_tcs")
    child_tx_subrows = ctx.get("child_tx_subrows")
    chunk_err = ctx.get("chunk_err")
    chunk_p95 = ctx.get("chunk_p95")
    chunk_tp = ctx.get("chunk_tp")
    chunk_vus = ctx.get("chunk_vus")
    clean_name_t = ctx.get("clean_name_t")
    cleaned_entry = ctx.get("cleaned_entry")
    cleaned_error_details = ctx.get("cleaned_error_details")
    color = ctx.get("color")
    concl_items = ctx.get("concl_items")
    concurrency_est = ctx.get("concurrency_est")
    concurrency_metric_note = ctx.get("concurrency_metric_note")
    confidence_areas = ctx.get("confidence_areas")
    confidence_table_rows = ctx.get("confidence_table_rows")
    corr_html = ctx.get("corr_html")
    correlation = ctx.get("correlation")
    correlation_insights = ctx.get("correlation_insights")
    cpu_v = ctx.get("cpu_v")
    crit_avg_rt = ctx.get("crit_avg_rt")
    crit_breaches = ctx.get("crit_breaches")
    crit_max_rt = ctx.get("crit_max_rt")
    crit_p95_rt = ctx.get("crit_p95_rt")
    crit_pct = ctx.get("crit_pct")
    crit_tx_count = ctx.get("crit_tx_count")
    crit_tx_list = ctx.get("crit_tx_list")
    crit_tx_table_html = ctx.get("crit_tx_table_html")
    critical_tx_list = ctx.get("critical_tx_list")
    critical_tx_list_json = ctx.get("critical_tx_list_json")
    critical_tx_rows = ctx.get("critical_tx_rows")
    cur_t = ctx.get("cur_t")
    data_quality_findings = ctx.get("data_quality_findings")
    data_quality_html = ctx.get("data_quality_html")
    default_err = ctx.get("default_err")
    default_rt = ctx.get("default_rt")
    dev_items = ctx.get("dev_items")
    dev_label = ctx.get("dev_label")
    dev_pct = ctx.get("dev_pct")
    deviation_chart_labels = ctx.get("deviation_chart_labels")
    deviation_chart_labels_json = ctx.get("deviation_chart_labels_json")
    deviation_chart_values = ctx.get("deviation_chart_values")
    deviation_chart_values_json = ctx.get("deviation_chart_values_json")
    display_label_names = ctx.get("display_label_names")
    display_labels = ctx.get("display_labels")
    display_total_errors = ctx.get("display_total_errors")
    display_ts_map = ctx.get("display_ts_map")
    enrich_findings_with_ai = ctx.get("enrich_findings_with_ai")
    entry = ctx.get("entry")
    err_counts_json = ctx.get("err_counts_json")
    err_findings_html = ctx.get("err_findings_html")
    err_info = ctx.get("err_info")
    err_items = ctx.get("err_items")
    err_k = ctx.get("err_k")
    err_key = ctx.get("err_key")
    err_labels_json = ctx.get("err_labels_json")
    err_pct = ctx.get("err_pct")
    err_rates_json = ctx.get("err_rates_json")
    err_v = ctx.get("err_v")
    err_val = ctx.get("err_val")
    error_details_raw = ctx.get("error_details_raw")
    error_donut_counts = ctx.get("error_donut_counts")
    error_donut_labels = ctx.get("error_donut_labels")
    error_drill_data = ctx.get("error_drill_data")
    error_drill_json = ctx.get("error_drill_json")
    error_rate = ctx.get("error_rate")
    error_types_sorted = ctx.get("error_types_sorted")
    ev = ctx.get("ev")
    evidence_items = ctx.get("evidence_items")
    exec_ai_augmented_html = ctx.get("exec_ai_augmented_html")
    exec_assessment_badge = ctx.get("exec_assessment_badge")
    exec_assessment_color = ctx.get("exec_assessment_color")
    exec_assessment_html = ctx.get("exec_assessment_html")
    exec_conclusions_html = ctx.get("exec_conclusions_html")
    exec_intel = ctx.get("exec_intel")
    exec_kpi_strip_html = ctx.get("exec_kpi_strip_html")
    exec_obs_table_html = ctx.get("exec_obs_table_html")
    exec_overview_pointers_html = ctx.get("exec_overview_pointers_html")
    exec_raw_overview = ctx.get("exec_raw_overview")
    exec_recs_html = ctx.get("exec_recs_html")
    exec_summary = ctx.get("exec_summary")
    execution_time = ctx.get("execution_time")
    f = ctx.get("f")
    fid = ctx.get("fid")
    filtered_occs = ctx.get("filtered_occs")
    final_time_points = ctx.get("final_time_points")
    finding = ctx.get("finding")
    finding_html = ctx.get("finding_html")
    findings_json = ctx.get("findings_json")
    findings_result = ctx.get("findings_result")
    fmsg_lower = ctx.get("fmsg_lower")
    generate_findings = ctx.get("generate_findings")
    has_global_err_breach = ctx.get("has_global_err_breach")
    has_global_rt_breach = ctx.get("has_global_rt_breach")
    i = ctx.get("i")
    idx = ctx.get("idx")
    idx_i = ctx.get("idx_i")
    idx_t = ctx.get("idx_t")
    infra = ctx.get("infra")
    infra_analysis = ctx.get("infra_analysis")
    infra_findings_html = ctx.get("infra_findings_html")
    infra_obs = ctx.get("infra_obs")
    infra_observation_html = ctx.get("infra_observation_html")
    item = ctx.get("item")
    jmx_full_tree = ctx.get("jmx_full_tree")
    jmx_name = ctx.get("jmx_name")
    k = ctx.get("k")
    k_lower = ctx.get("k_lower")
    key_findings_html = ctx.get("key_findings_html")
    keywords_t = ctx.get("keywords_t")
    kpis_dict = ctx.get("kpis_dict")
    l_key = ctx.get("l_key")
    l_name = ctx.get("l_name")
    l_ts = ctx.get("l_ts")
    l_val = ctx.get("l_val")
    label_ts_json = ctx.get("label_ts_json")
    label_ts_map = ctx.get("label_ts_map")
    labels = ctx.get("labels")
    labels_by_tg = ctx.get("labels_by_tg")
    labels_rows = ctx.get("labels_rows")
    lbl = ctx.get("lbl")
    lbl_t = ctx.get("lbl_t")
    ldata = ctx.get("ldata")
    ldata_item = ctx.get("ldata_item")
    linked_recs_html = ctx.get("linked_recs_html")
    lname = ctx.get("lname")
    load_sla_targets = ctx.get("load_sla_targets")
    matched_table_children = ctx.get("matched_table_children")
    mem_v = ctx.get("mem_v")
    metrics = ctx.get("metrics")
    min_avail_val = ctx.get("min_avail_val")
    min_len = ctx.get("min_len")
    minor_pct = ctx.get("minor_pct")
    mock_path = ctx.get("mock_path")
    mod_pct = ctx.get("mod_pct")
    msg_lower = ctx.get("msg_lower")
    n_points = ctx.get("n_points")
    num_steps = ctx.get("num_steps")
    obs_clean = ctx.get("obs_clean")
    obs_rows = ctx.get("obs_rows")
    occ = ctx.get("occ")
    overall_apdex = ctx.get("overall_apdex")
    overall_assessment = ctx.get("overall_assessment")
    overall_err_pct = ctx.get("overall_err_pct")
    overall_fail = ctx.get("overall_fail")
    overall_pass = ctx.get("overall_pass")
    overall_rc = ctx.get("overall_rc")
    overall_rc_html = ctx.get("overall_rc_html")
    overall_samples = ctx.get("overall_samples")
    overall_users = ctx.get("overall_users")
    p90_val = ctx.get("p90_val")
    p95_val = ctx.get("p95_val")
    p_recs_html = ctx.get("p_recs_html")
    parse_jmx_full_tree = ctx.get("parse_jmx_full_tree")
    parse_jmx_hierarchy = ctx.get("parse_jmx_hierarchy")
    parse_jmx_thread_groups = ctx.get("parse_jmx_thread_groups")
    parsed = ctx.get("parsed")
    passed_pct = ctx.get("passed_pct")
    pct_labels_items = ctx.get("pct_labels_items")
    pct_names = ctx.get("pct_names")
    pct_p50 = ctx.get("pct_p50")
    pct_p90 = ctx.get("pct_p90")
    pct_p95 = ctx.get("pct_p95")
    pct_p99 = ctx.get("pct_p99")
    peak_concurrency_est = ctx.get("peak_concurrency_est")
    peak_cpu_val = ctx.get("peak_cpu_val")
    peak_disk_q_val = ctx.get("peak_disk_q_val")
    peak_mem_val = ctx.get("peak_mem_val")
    perf_intel = ctx.get("perf_intel")
    placeholder = ctx.get("placeholder")
    present_tcs = ctx.get("present_tcs")
    present_tcs_data = ctx.get("present_tcs_data")
    priority_actions_html = ctx.get("priority_actions_html")
    r_cpu_mem = ctx.get("r_cpu_mem")
    r_cpu_rt = ctx.get("r_cpu_rt")
    r_cpu_tp = ctx.get("r_cpu_tp")
    r_mem_rt = ctx.get("r_mem_rt")
    r_mem_tp = ctx.get("r_mem_tp")
    r_tp_rt = ctx.get("r_tp_rt")
    ramp_up_sec = ctx.get("ramp_up_sec")
    ramp_up_text = ctx.get("ramp_up_text")
    raw_avail = ctx.get("raw_avail")
    raw_cpu = ctx.get("raw_cpu")
    raw_disk_q = ctx.get("raw_disk_q")
    raw_disk_read = ctx.get("raw_disk_read")
    raw_disk_write = ctx.get("raw_disk_write")
    raw_mem = ctx.get("raw_mem")
    raw_net_in = ctx.get("raw_net_in")
    raw_net_out = ctx.get("raw_net_out")
    raw_r = ctx.get("raw_r")
    recs_html = ctx.get("recs_html")
    recs_json = ctx.get("recs_json")
    roadmap_html = ctx.get("roadmap_html")
    roadmap_section_style = ctx.get("roadmap_section_style")
    root_cause = ctx.get("root_cause")
    rt_band_counts = ctx.get("rt_band_counts")
    rt_band_labels = ctx.get("rt_band_labels")
    rt_bands = ctx.get("rt_bands")
    rt_findings_html = ctx.get("rt_findings_html")
    rt_hist_counts = ctx.get("rt_hist_counts")
    rt_hist_labels = ctx.get("rt_hist_labels")
    rt_obs = ctx.get("rt_obs")
    rt_observation_html = ctx.get("rt_observation_html")
    rt_v = ctx.get("rt_v")
    run_id = ctx.get("run_id")
    s_end = ctx.get("s_end")
    s_start = ctx.get("s_start")
    safe_title = ctx.get("safe_title")
    sample_fail = ctx.get("sample_fail")
    sample_pass = ctx.get("sample_pass")
    sample_tot = ctx.get("sample_tot")
    score = ctx.get("score")
    score_color = ctx.get("score_color")
    script_users = ctx.get("script_users")
    seen_times = ctx.get("seen_times")
    sev = ctx.get("sev")
    sev_color = ctx.get("sev_color")
    sev_icon = ctx.get("sev_icon")
    sev_label = ctx.get("sev_label")
    sev_str = ctx.get("sev_str")
    short_display = ctx.get("short_display")
    short_title = ctx.get("short_title")
    sla_breach_100_count = ctx.get("sla_breach_100_count")
    sla_breach_20_count = ctx.get("sla_breach_20_count")
    sla_breach_50_count = ctx.get("sla_breach_50_count")
    sla_breach_count = ctx.get("sla_breach_count")
    sla_breaches = ctx.get("sla_breaches")
    sla_breaches_html = ctx.get("sla_breaches_html")
    sla_compliance_pct = ctx.get("sla_compliance_pct")
    sla_crit_count = ctx.get("sla_crit_count")
    sla_explanation = ctx.get("sla_explanation")
    sla_minor_count = ctx.get("sla_minor_count")
    sla_mod_count = ctx.get("sla_mod_count")
    sla_pass_count = ctx.get("sla_pass_count")
    sla_ref_json = ctx.get("sla_ref_json")
    sla_ref_series = ctx.get("sla_ref_series")
    sla_status_badge = ctx.get("sla_status_badge")
    sla_targets = ctx.get("sla_targets")
    split_words_t = ctx.get("split_words_t")
    staging_rows_html = ctx.get("staging_rows_html")
    start_epoch_ms = ctx.get("start_epoch_ms")
    status = ctx.get("status")
    status_color = ctx.get("status_color")
    steady_state_sec = ctx.get("steady_state_sec")
    steady_state_text = ctx.get("steady_state_text")
    step_steady = ctx.get("step_steady")
    stg_chunks = ctx.get("stg_chunks")
    stg_name = ctx.get("stg_name")
    summary = ctx.get("summary")
    t = ctx.get("t")
    t_data = ctx.get("t_data")
    t_err_target = ctx.get("t_err_target")
    t_name = ctx.get("t_name")
    t_p90 = ctx.get("t_p90")
    t_target = ctx.get("t_target")
    tab_error_intel = ctx.get("tab_error_intel")
    tab_error_panel_html = ctx.get("tab_error_panel_html")
    tab_infra_intel = ctx.get("tab_infra_intel")
    tab_infra_panel_html = ctx.get("tab_infra_panel_html")
    tab_rt_intel = ctx.get("tab_rt_intel")
    tab_rt_panel_html = ctx.get("tab_rt_panel_html")
    tab_tx_intel = ctx.get("tab_tx_intel")
    tab_tx_panel_html = ctx.get("tab_tx_panel_html")
    tail_analysis = ctx.get("tail_analysis")
    target_rt_val = ctx.get("target_rt_val")
    target_sla_val = ctx.get("target_sla_val")
    target_ts_len = ctx.get("target_ts_len")
    tc = ctx.get("tc")
    tc_avg = ctx.get("tc_avg")
    tc_breached = ctx.get("tc_breached")
    tc_count = ctx.get("tc_count")
    tc_data = ctx.get("tc_data")
    tc_dev = ctx.get("tc_dev")
    tc_err_rate = ctx.get("tc_err_rate")
    tc_errors = ctx.get("tc_errors")
    tc_keys = ctx.get("tc_keys")
    tc_ordered = ctx.get("tc_ordered")
    tc_p90 = ctx.get("tc_p90")
    tc_set = ctx.get("tc_set")
    tc_target = ctx.get("tc_target")
    tc_to_samplers = ctx.get("tc_to_samplers")
    test_dur_formatted = ctx.get("test_dur_formatted")
    test_dur_sec = ctx.get("test_dur_sec")
    tg = ctx.get("tg")
    tg_avg_rt = ctx.get("tg_avg_rt")
    tg_compliance_pct = ctx.get("tg_compliance_pct")
    tg_configs = ctx.get("tg_configs")
    tg_dur = ctx.get("tg_dur")
    tg_err_rate = ctx.get("tg_err_rate")
    tg_errors = ctx.get("tg_errors")
    tg_filter_options = ctx.get("tg_filter_options")
    tg_iters = ctx.get("tg_iters")
    tg_name = ctx.get("tg_name")
    tg_p90 = ctx.get("tg_p90")
    tg_passed_count = ctx.get("tg_passed_count")
    tg_rows_html = ctx.get("tg_rows_html")
    tg_share_pct = ctx.get("tg_share_pct")
    tg_specific = ctx.get("tg_specific")
    tg_to_tcs_json = ctx.get("tg_to_tcs_json")
    tg_to_tcs_map = ctx.get("tg_to_tcs_map")
    tg_to_transactions = ctx.get("tg_to_transactions")
    tg_total_samples = ctx.get("tg_total_samples")
    tg_tps = ctx.get("tg_tps")
    tg_u = ctx.get("tg_u")
    timeline_events = ctx.get("timeline_events")
    timeline_html = ctx.get("timeline_html")
    title_clean = ctx.get("title_clean")
    title_low = ctx.get("title_low")
    top_labels = ctx.get("top_labels")
    total_duration_min = ctx.get("total_duration_min")
    total_errors_all = ctx.get("total_errors_all")
    total_iterations = ctx.get("total_iterations")
    total_tg_users = ctx.get("total_tg_users")
    total_transactions_count = ctx.get("total_transactions_count")
    total_tx_count = ctx.get("total_tx_count")
    total_tx_executions = ctx.get("total_tx_executions")
    tp_obs = ctx.get("tp_obs")
    tp_observation_html = ctx.get("tp_observation_html")
    tp_v = ctx.get("tp_v")
    ts = ctx.get("ts")
    ts_active_threads = ctx.get("ts_active_threads")
    ts_avail_json = ctx.get("ts_avail_json")
    ts_avg_rt = ctx.get("ts_avg_rt")
    ts_cpu = ctx.get("ts_cpu")
    ts_disk_q_json = ctx.get("ts_disk_q_json")
    ts_disk_read_json = ctx.get("ts_disk_read_json")
    ts_disk_write_json = ctx.get("ts_disk_write_json")
    ts_errors = ctx.get("ts_errors")
    ts_labels = ctx.get("ts_labels")
    ts_lbls_list = ctx.get("ts_lbls_list")
    ts_memory = ctx.get("ts_memory")
    ts_net_in_json = ctx.get("ts_net_in_json")
    ts_net_out_json = ctx.get("ts_net_out_json")
    ts_p95_rt = ctx.get("ts_p95_rt")
    ts_p99_rt = ctx.get("ts_p99_rt")
    ts_rt_raw = ctx.get("ts_rt_raw")
    ts_throughput = ctx.get("ts_throughput")
    ts_tp_raw = ctx.get("ts_tp_raw")
    ts_vus_list = ctx.get("ts_vus_list")
    tx_apdex = ctx.get("tx_apdex")
    tx_breached_count = ctx.get("tx_breached_count")
    tx_chart_fail = ctx.get("tx_chart_fail")
    tx_chart_fail_json = ctx.get("tx_chart_fail_json")
    tx_chart_labels = ctx.get("tx_chart_labels")
    tx_chart_labels_json = ctx.get("tx_chart_labels_json")
    tx_chart_pass = ctx.get("tx_chart_pass")
    tx_chart_pass_json = ctx.get("tx_chart_pass_json")
    tx_chart_values = ctx.get("tx_chart_values")
    tx_dev_map = ctx.get("tx_dev_map")
    tx_dev_map_json = ctx.get("tx_dev_map_json")
    tx_finding_badges = ctx.get("tx_finding_badges")
    tx_findings_html = ctx.get("tx_findings_html")
    tx_findings_map = ctx.get("tx_findings_map")
    tx_name = ctx.get("tx_name")
    tx_options_data = ctx.get("tx_options_data")
    tx_options_html = ctx.get("tx_options_html")
    tx_options_json = ctx.get("tx_options_json")
    tx_rt_hierarchy_data = ctx.get("tx_rt_hierarchy_data")
    tx_rt_hierarchy_json = ctx.get("tx_rt_hierarchy_json")
    tx_sla_json = ctx.get("tx_sla_json")
    tx_sla_map = ctx.get("tx_sla_map")
    tx_stat_rows_html = ctx.get("tx_stat_rows_html")
    tx_stats_table_html = ctx.get("tx_stats_table_html")
    tx_summary = ctx.get("tx_summary")
    tx_summary_bottom_fail_cells = ctx.get("tx_summary_bottom_fail_cells")
    tx_summary_bottom_pass_cells = ctx.get("tx_summary_bottom_pass_cells")
    tx_summary_bottom_table_cols = ctx.get("tx_summary_bottom_table_cols")
    tx_summary_bottom_table_html = ctx.get("tx_summary_bottom_table_html")
    tx_under_sla = ctx.get("tx_under_sla")
    us_options_data = ctx.get("us_options_data")
    us_options_json = ctx.get("us_options_json")
    us_select_options_html = ctx.get("us_select_options_html")
    users = ctx.get("users")
    vu = ctx.get("vu")
    vu_ramp_data = ctx.get("vu_ramp_data")
    vu_ramp_data_json = ctx.get("vu_ramp_data_json")
    vu_ramp_labels = ctx.get("vu_ramp_labels")
    vu_ramp_labels_json = ctx.get("vu_ramp_labels_json")
    vu_time_points = ctx.get("vu_time_points")
    wrapper_tc = ctx.get("wrapper_tc")

    return f"""async function publishReport() {{
        if (!confirm("Are you sure you want to publish this report?\\n\\nThis will remove edit mode and save a permanent, clean, non-editable published report file.")) return;

        const editBadge = document.getElementById('editModeBadge');
        const publishBtn = document.getElementById('publishBtn');
        if (editBadge) editBadge.style.display = 'none';
        if (publishBtn) publishBtn.style.display = 'none';

        // Strip contenteditable attributes for clean non-editable HTML
        document.querySelectorAll('[contenteditable]').forEach(el => {{
            el.removeAttribute('contenteditable');
        }});

        // Clean canvases to prevent Chart.js sizing glitches on reload
        document.querySelectorAll('canvas').forEach(c => {{
            c.removeAttribute('style');
            c.removeAttribute('width');
            c.removeAttribute('height');
            c.className = '';
        }});

        // Comparison Tab Handling in Published Report:
        const compContainer = document.getElementById('compare-content-container');
        const hasActiveComparison = compContainer && compContainer.style.display !== 'none' && compContainer.children.length > 0;
        
        if (hasActiveComparison) {{
            // Keep the comparison tab baked in, but remove the interactive selector and empty placeholder
            const selBar = document.getElementById('compare-selector-bar');
            const emptyState = document.getElementById('compare-empty-state');
            if (selBar) selBar.remove();
            if (emptyState) emptyState.remove();
        }} else {{
            // No baseline was selected -> completely remove the comparison tab button and pane
            const compNavBtn = document.getElementById('nav-btn-comparison');
            const compPane = document.getElementById('rpt-compare');
            if (compNavBtn) compNavBtn.remove();
            if (compPane) compPane.remove();
        }}

        // Mark document container as published
        document.documentElement.classList.add('published-mode');

        const fullHtml = "<!DOCTYPE html>\\n" + document.documentElement.outerHTML;
        const currentPath = window.location.pathname;
        const fileName = currentPath.substring(currentPath.lastIndexOf('/') + 1) || 'report.html';
        const pubFileName = fileName.replace('.html', '_published.html');

        try {{
            const res = await fetch('/api/save-published-report', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ report_name: pubFileName, html_content: fullHtml }})
            }});
            const data = await res.json();
            if (data.success) {{
                alert("🎉 Report Published Successfully!\\n\\nSaved to: Results/Published/" + data.file + "\\n\\nYou will now be redirected to the published non-editable report.");
                window.location.href = data.url || ('/Results/Published/' + data.file);
            }} else {{
                alert("Error publishing report: " + data.message);
                if (editBadge) editBadge.style.display = 'inline-block';
                if (publishBtn) publishBtn.style.display = 'inline-block';
            }}
        }} catch (err) {{
            alert("Failed to reach server: " + err.message);
            if (editBadge) editBadge.style.display = 'inline-block';
            if (publishBtn) publishBtn.style.display = 'inline-block';
        }}
    }}

    function toggleTheme() {{
        const isLight = document.documentElement.classList.toggle('light-mode');
        document.body.classList.toggle('light-mode', isLight);
        safeSetStorage('jmeter_ai_theme', isLight ? 'light' : 'dark');
    }}

    function toggleAiValidation(checkbox, valId) {{
        const isChecked = checkbox.checked;
        const label = document.getElementById(`val_lbl_${{valId}}`) || checkbox.closest('.human-val-label');
        if (label) {{
            label.classList.toggle('validated', isChecked);
            const textSpan = label.querySelector('.human-val-text');
            if (textSpan) {{
                if (valId === 'major_ai_augmented') {{
                    textSpan.textContent = isChecked ? 'Validated: All Augmented Analysis' : 'Validate All Augmented Analysis';
                }} else {{
                    textSpan.textContent = isChecked ? 'Validated by Performance Engineer' : 'Validate as Performance Engineer';
                }}
            }}
        }}

        if (valId === 'major_ai_augmented') {{
            document.querySelectorAll('.human-val-checkbox').forEach(cb => {{
                if (cb !== checkbox) {{
                    cb.checked = isChecked;
                    const subId = cb.getAttribute('data-val-id');
                    const subLabel = document.getElementById(`val_lbl_${{subId}}`) || cb.closest('.human-val-label');
                    if (subLabel) {{
                        subLabel.classList.toggle('validated', isChecked);
                        const subText = subLabel.querySelector('.human-val-text');
                        if (subText) subText.textContent = isChecked ? 'Validated by Performance Engineer' : 'Validate as Performance Engineer';
                    }}
                    const card = cb.closest('.ai-sub-card');
                    if (card) card.classList.toggle('card-validated', isChecked);
                }}
            }});
        }}

        const card = checkbox.closest('.ai-sub-card');
        if (card) {{
            card.classList.toggle('card-validated', isChecked);
        }}
    }}

    if (safeGetStorage('jmeter_ai_theme') === 'light') {{
        document.documentElement.classList.add('light-mode');
        document.body.classList.add('light-mode');
    }}

    if (typeof Chart !== 'undefined') {{
        const chartFont = {{ family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 11 }};
        const gridColor = 'rgba(71, 85, 105, 0.25)';
        const textColor = '#94a3b8';
        Chart.defaults.color = textColor;
        Chart.defaults.font = chartFont;

    const overallTs = {{
        avg_rt: {ts_avg_rt},
        p95_rt: {ts_p95_rt},
        p99_rt: {ts_p99_rt},
        throughput: {ts_throughput},
        errors: {ts_errors}
    }};

    const labelTsMap = {label_ts_json};
    
    // Critical Transactions Tracking & Deterministic Colors
    const criticalTxSet = new Set();
    const initialCriticals = {critical_tx_list_json};
    initialCriticals.forEach(t => criticalTxSet.add(t));

    // Critical Transactions Response Time Chart
    let critTxChartObj = null;
    const critCanvas = document.getElementById('critTxChart') || document.getElementById('chart-rt-exec');
    if (critCanvas) {{
        critTxChartObj = new Chart(critCanvas, {{
            type: 'line',
            data: {{
                labels: {ts_labels},
                datasets: []
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ font: {{ weight: '600' }} }} }},
                    tooltip: {{ mode: 'index', intersect: false }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: textColor, maxTicksLimit: 10 }} }},
                    y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Response Time (ms)', color: textColor }} }}
                }}
            }}
        }});
    }}

    const fixedColors = ['#38bdf8', '#f59e0b', '#10b981', '#a855f7', '#ef4444', '#ec4899', '#06b6d4', '#84cc16'];
    function getTxColor(name) {{
        let hash = 0;
        for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
        return fixedColors[Math.abs(hash) % fixedColors.length];
    }}

    const targetSlaVal = {target_sla_val};



    function createChartMultiSelect(container, config) {{
        const target = typeof container === 'string' ? document.getElementById(container) : container;
        if (!target) return null;
        target.innerHTML = '';

        const items = config.items || [];
        const overallLabel = config.overallLabel || 'All Transactions (Overall)';
        const allowOverall = config.allowOverall !== false;
        let selectedSet = new Set((config.initialSelected || (allowOverall ? ['ALL'] : [])).map(String));
        if (selectedSet.size === 0 && allowOverall) selectedSet.add('ALL');

        const wrap = document.createElement('div');
        wrap.className = 'chart-ms-wrap';
        if (config.maxWidth) wrap.style.maxWidth = config.maxWidth;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chart-ms-btn';

        const btnText = document.createElement('span');
        btnText.className = 'chart-ms-btn-text';

        const badge = document.createElement('span');
        badge.className = 'chart-ms-badge';
        badge.style.display = 'none';

        const arrow = document.createElement('span');
        arrow.style.cssText = 'font-size:0.65rem; color:var(--muted); margin-left:0.3rem;';
        arrow.textContent = '▼';

        btn.appendChild(btnText);
        btn.appendChild(badge);
        btn.appendChild(arrow);
        wrap.appendChild(btn);

        const dropdown = document.createElement('div');
        dropdown.className = 'chart-ms-dropdown';

        // Search input
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'chart-ms-search';
        searchInput.placeholder = config.placeholder || '🔍 Search...';
        dropdown.appendChild(searchInput);

        // Actions toolbar
        const actionsBar = document.createElement('div');
        actionsBar.className = 'chart-ms-actions';

        if (allowOverall) {{
            const overallBtn = document.createElement('button');
            overallBtn.type = 'button';
            overallBtn.className = 'chart-ms-action-btn';
            overallBtn.textContent = '🌐 Overall';
            overallBtn.onclick = (e) => {{
                e.preventDefault();
                e.stopPropagation();
                selectedSet.clear();
                selectedSet.add('ALL');
                updateUI();
                if (config.onChange) config.onChange(Array.from(selectedSet));
            }};
            actionsBar.appendChild(overallBtn);
        }}

        const selectAllBtn = document.createElement('button');
        selectAllBtn.type = 'button';
        selectAllBtn.className = 'chart-ms-action-btn';
        selectAllBtn.textContent = '☑️ Select All';
        selectAllBtn.onclick = (e) => {{
            e.preventDefault();
            e.stopPropagation();
            selectedSet.clear();
            items.forEach(it => selectedSet.add(String(it.id)));
            updateUI();
            if (config.onChange) config.onChange(Array.from(selectedSet));
        }};
        actionsBar.appendChild(selectAllBtn);

        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'chart-ms-action-btn';
        clearBtn.textContent = '✖️ Clear';
        clearBtn.onclick = (e) => {{
            e.preventDefault();
            e.stopPropagation();
            selectedSet.clear();
            if (allowOverall) selectedSet.add('ALL');
            updateUI();
            if (config.onChange) config.onChange(Array.from(selectedSet));
        }};
        actionsBar.appendChild(clearBtn);

        dropdown.appendChild(actionsBar);

        // Options List container
        const listEl = document.createElement('div');
        listEl.className = 'chart-ms-list';
        dropdown.appendChild(listEl);
        wrap.appendChild(dropdown);
        target.appendChild(wrap);

        function renderOptions(filterText = '') {{
            listEl.innerHTML = '';
            const q = filterText.trim().toLowerCase();

            if (allowOverall && (!q || overallLabel.toLowerCase().includes(q))) {{
                const isAllSelected = selectedSet.has('ALL');
                const row = document.createElement('label');
                row.className = 'chart-ms-item';
                row.style.fontWeight = isAllSelected ? '700' : '500';
                row.innerHTML = `
                    <input type="checkbox" value="ALL" ${{isAllSelected ? 'checked' : ''}}>
                    <span style="color:var(--accent); font-weight:700;">🌐</span>
                    <span class="chart-ms-item-text" title="${{overallLabel}}">${{overallLabel}}</span>
                `;
                const cb = row.querySelector('input');
                cb.onchange = () => {{
                    if (cb.checked) {{
                        selectedSet.clear();
                        selectedSet.add('ALL');
                    }} else {{
                        selectedSet.delete('ALL');
                    }}
                    updateUI();
                    if (config.onChange) config.onChange(Array.from(selectedSet));
                }};
                listEl.appendChild(row);
            }}

            items.forEach(it => {{
                const itName = it.name || it.shortName || String(it.id);
                if (q && !itName.toLowerCase().includes(q) && !(it.sla && String(it.sla).includes(q))) {{
                    return;
                }}
                const isSelected = selectedSet.has(String(it.id)) || selectedSet.has(itName);
                const color = it.color || getTxColor(itName);
                const slaText = it.sla ? ` <span style="font-size:0.68rem; color:var(--muted);">(SLA: ${{it.sla}}ms)</span>` : '';
                const row = document.createElement('label');
                row.className = 'chart-ms-item';
                row.innerHTML = `
                    <input type="checkbox" value="${{it.id}}" ${{isSelected ? 'checked' : ''}}>
                    <span class="chart-ms-color-dot" style="background:${{color}};"></span>
                    <span class="chart-ms-item-text" title="${{itName}}">${{it.shortName || itName}}${{slaText}}</span>
                `;
                const cb = row.querySelector('input');
                cb.onchange = () => {{
                    if (cb.checked) {{
                        selectedSet.delete('ALL');
                        selectedSet.add(String(it.id));
                    }} else {{
                        selectedSet.delete(String(it.id));
                        selectedSet.delete(itName);
                        if (selectedSet.size === 0 && allowOverall) {{
                            selectedSet.add('ALL');
                        }}
                    }}
                    updateUI();
                    if (config.onChange) config.onChange(Array.from(selectedSet));
                }};
                listEl.appendChild(row);
            }});

            if (listEl.children.length === 0) {{
                const empty = document.createElement('div');
                empty.style.cssText = 'font-size:0.75rem; color:var(--muted); text-align:center; padding:0.6rem;';
                empty.textContent = 'No matching items';
                listEl.appendChild(empty);
            }}
        }}

        function updateUI() {{
            if (selectedSet.has('ALL') || (allowOverall && selectedSet.size === 0)) {{
                btnText.textContent = overallLabel;
                btnText.title = overallLabel;
                badge.style.display = 'none';
            }} else if (selectedSet.size === 1) {{
                const selId = Array.from(selectedSet)[0];
                const found = items.find(it => String(it.id) === selId || it.name === selId);
                const name = found ? (found.shortName || found.name) : selId;
                btnText.textContent = name;
                btnText.title = found ? found.name : selId;
                badge.textContent = '1';
                badge.style.display = 'inline-block';
            }} else {{
                btnText.textContent = `${{selectedSet.size}} Selected`;
                btnText.title = `${{selectedSet.size}} items selected`;
                badge.textContent = String(selectedSet.size);
                badge.style.display = 'inline-block';
            }}
            renderOptions(searchInput.value);
        }}

        searchInput.oninput = () => {{
            renderOptions(searchInput.value);
        }};

        btn.onclick = (e) => {{
            e.preventDefault();
            e.stopPropagation();
            const isOpen = dropdown.classList.contains('open');
            document.querySelectorAll('.chart-ms-dropdown.open').forEach(d => d.classList.remove('open'));
            if (!isOpen) {{
                dropdown.classList.add('open');
                searchInput.value = '';
                renderOptions('');
                setTimeout(() => searchInput.focus(), 50);
            }}
        }};

        updateUI();

        return {{
            getSelected: () => Array.from(selectedSet),
            setSelected: (newIds) => {{
                selectedSet.clear();
                (newIds || []).forEach(id => selectedSet.add(String(id)));
                if (selectedSet.size === 0 && allowOverall) selectedSet.add('ALL');
                updateUI();
            }},
            setItems: (newItems) => {{
                items.length = 0;
                newItems.forEach(it => items.push(it));
                updateUI();
            }}
        }};
    }}

    // Global listener to close dropdowns when clicking outside
    document.addEventListener('click', (e) => {{
        if (!e.target.closest('.chart-ms-wrap')) {{
            document.querySelectorAll('.chart-ms-dropdown.open').forEach(d => d.classList.remove('open'));
        }}
    }});

    function renderCritTxChips() {{
        const container = document.getElementById('crit-tx-chip-container');
        if (!container) return;
        container.innerHTML = '';

        if (!initialCriticals || initialCriticals.length === 0) return;

        const allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.style.cssText = 'padding:0.25rem 0.6rem; font-size:0.75rem; border-radius:12px; border:1px solid var(--border); background:var(--surface2); color:var(--text); cursor:pointer; font-weight:600;';
        allBtn.innerText = 'Show All';
        allBtn.onclick = (e) => {{
            e.preventDefault();
            initialCriticals.forEach(t => criticalTxSet.add(t));
            renderCritTxChips();
            updateCriticalTxChart();
        }};
        container.appendChild(allBtn);

        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.style.cssText = 'padding:0.25rem 0.6rem; font-size:0.75rem; border-radius:12px; border:1px solid var(--border); background:var(--surface2); color:var(--text); cursor:pointer; font-weight:600; margin-right:0.25rem;';
        clearBtn.innerText = 'Clear All';
        clearBtn.onclick = (e) => {{
            e.preventDefault();
            criticalTxSet.clear();
            renderCritTxChips();
            updateCriticalTxChart();
        }};
        container.appendChild(clearBtn);

        initialCriticals.forEach(txName => {{
            const isSelected = criticalTxSet.has(txName);
            const color = getTxColor(txName);
            const txSla = txSlaMap[txName] ? ' (SLA: ' + txSlaMap[txName] + 'ms)' : '';
            const shortName = (txName.length > 25 ? txName.substring(0, 22) + '...' : txName) + txSla;

            const chip = document.createElement('button');
            chip.type = 'button';
            chip.title = txName + txSla;
            chip.style.cssText = `padding:0.25rem 0.65rem; font-size:0.75rem; border-radius:12px; border:1px solid ${{isSelected ? color : 'var(--border)'}}; background:${{isSelected ? color + '22' : 'transparent'}}; color:${{isSelected ? color : 'var(--muted)'}}; cursor:pointer; font-weight:${{isSelected ? '700' : '500'}}; transition:all 0.15s;`;
            chip.innerText = (isSelected ? '● ' : '○ ') + shortName;
            chip.onclick = (e) => {{
                e.preventDefault();
                if (criticalTxSet.has(txName)) {{
                    criticalTxSet.delete(txName);
                }} else {{
                    criticalTxSet.add(txName);
                }}
                renderCritTxChips();
                updateCriticalTxChart();
            }};
            container.appendChild(chip);
        }});
    }}

    const txSlaMap = {tx_sla_json};

    function updateCriticalTxChart() {{
        if (!critTxChartObj) return;
        const datasets = [];

        // Transaction Lines with SLA target embedded in the index/label
        criticalTxSet.forEach(txName => {{
            let tsData = null;
            if (labelTsMap[txName] && labelTsMap[txName].ts_avg_rt) {{
                tsData = labelTsMap[txName].ts_avg_rt;
            }} else {{
                Object.values(labelTsMap).forEach(entry => {{
                    if (entry && (entry.label === txName || entry.name === txName)) {{
                        tsData = entry.ts_avg_rt;
                    }}
                }});
            }}
            if (tsData && tsData.length > 0) {{
                const color = getTxColor(txName);
                const txSla = txSlaMap[txName] ? ' (SLA: ' + txSlaMap[txName] + 'ms)' : '';
                const shortLabel = (txName.length > 25 ? txName.substring(0, 22) + '...' : txName) + txSla;
                datasets.push({{
                    label: shortLabel,
                    data: [...tsData],
                    borderColor: color,
                    backgroundColor: color,
                    borderWidth: 2.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 3.5,
                    pointHoverRadius: 6
                }});
            }}
        }});

        critTxChartObj.data.datasets = datasets;
        critTxChartObj.update('active');
    }}

    renderCritTxChips();

    function toggleCriticalTx(txName, isChecked) {{
        if (isChecked) {{
            criticalTxSet.add(txName);
        }} else {{
            criticalTxSet.delete(txName);
        }}
        updateCriticalTxChart();
    }}

    // Initial render of critical transactions chart
    updateCriticalTxChart();

    // Response Time Chart Instance
    const rtChartObj = new Chart(document.getElementById('rtChart'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'Avg RT (Overall)', data: overallTs.avg_rt, borderColor: '#6366f1', borderWidth: 2.5, fill: false, tension: 0.3, pointRadius: 2.5 }},
                {{ label: 'P95 RT (Overall)', data: overallTs.p95_rt, borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'P99 RT (Overall)', data: overallTs.p99_rt, borderColor: '#ef4444', borderWidth: 1.5, borderDash: [5,3], fill: false, tension: 0.3, pointRadius: 1.5 }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'top', labels: {{ color: textColor, font: {{ weight: '600' }} }} }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{ grid: {{ display: false }}, ticks: {{ color: textColor, font: {{ weight: '600' }} }} }},
                y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'ms', color: textColor }} }}
            }}
        }}
    }});

    function updateRtChart(selectedKeys) {{
        const isAll = !selectedKeys || selectedKeys.length === 0 || selectedKeys.includes('ALL');
        let datasets = [];

        if (isAll) {{
            datasets = [
                {{ label: 'Avg RT (Overall)', data: [...overallTs.avg_rt], borderColor: '#6366f1', borderWidth: 2.5, fill: false, tension: 0.3, pointRadius: 2.5 }},
                {{ label: 'P95 RT (Overall)', data: [...overallTs.p95_rt], borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'P99 RT (Overall)', data: [...overallTs.p99_rt], borderColor: '#ef4444', borderWidth: 1.5, borderDash: [5,3], fill: false, tension: 0.3, pointRadius: 1.5 }}
            ];
        }} else if (selectedKeys.length === 1) {{
            const key = selectedKeys[0];
            const entry = labelTsMap[key] || Object.values(labelTsMap).find(e => e.label === key || e.name === key);
            const txName = entry ? entry.label : key;
            const color = getTxColor(txName);
            const d = entry ? {{ avg_rt: entry.ts_avg_rt || [], p95_rt: entry.ts_p95_rt || [], p99_rt: entry.ts_p99_rt || [] }} : overallTs;

            datasets = [
                {{ label: `${{txName}} (Avg RT)`, data: [...d.avg_rt], borderColor: color, borderWidth: 2.5, fill: false, tension: 0.3, pointRadius: 3.5, pointBackgroundColor: color }},
                {{ label: `${{txName}} (P95 RT)`, data: [...d.p95_rt], borderColor: '#f59e0b', borderWidth: 2, borderDash: [4,2], fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: `${{txName}} (P99 RT)`, data: [...d.p99_rt], borderColor: '#ef4444', borderWidth: 1.5, borderDash: [5,3], fill: false, tension: 0.3, pointRadius: 1.5 }}
            ];
        }} else {{
            // MULTIPLE transactions selected! Plot an Avg RT line for EACH transaction
            selectedKeys.forEach(key => {{
                const entry = labelTsMap[key] || Object.values(labelTsMap).find(e => e.label === key || e.name === key);
                if (!entry || !entry.ts_avg_rt) return;
                const txName = entry.label;
                const color = getTxColor(txName);
                const txSla = txSlaMap[txName] ? ` (SLA: ${{txSlaMap[txName]}}ms)` : '';
                const shortLabel = (txName.length > 25 ? txName.substring(0, 22) + '...' : txName) + txSla;

                datasets.push({{
                    label: shortLabel,
                    data: [...entry.ts_avg_rt],
                    borderColor: color,
                    backgroundColor: color,
                    borderWidth: 2.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 3.5,
                    pointHoverRadius: 6,
                    pointBackgroundColor: color,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5
                }});
            }});
        }}

        rtChartObj.data.datasets = datasets;
        rtChartObj.update('active');
    }}

    // Throughput Chart Instance (Line Graph)
    const hasInitialErrors = overallTs.errors && overallTs.errors.some(e => e > 0);
    const tpDatasets = [
        {{
            label: 'Throughput (req/s)',
            data: overallTs.throughput,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.12)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#6366f1',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }}
    ];
    if (hasInitialErrors) {{
        tpDatasets.push({{
            label: 'Errors',
            data: overallTs.errors,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.10)',
            fill: true,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }});
    }}

    const tpChartObj = new Chart(document.getElementById('tpChart'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: tpDatasets
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ weight: '600' }} }} }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{ grid: {{ color: 'rgba(255,255,255,0.04)' }}, ticks: {{ color: textColor, font: {{ weight: '600' }} }} }},
                y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: 'Throughput (req/s)', color: textColor }}, beginAtZero: true }}
            }}
        }}
    }});

    function updateTpChart(selectedKeys) {{
        const isAll = !selectedKeys || selectedKeys.length === 0 || selectedKeys.includes('ALL');
        let datasets = [];
        let totalTp = 0;
        let peakTp = 0;
        let totalErrs = 0;
        let samplePointsCount = 0;

        if (isAll) {{
            datasets.push({{
                label: 'Overall Throughput (req/s)',
                data: [...overallTs.throughput],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.12)',
                fill: true,
                tension: 0.35,
                borderWidth: 2.5,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#6366f1',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }});
            if (hasInitialErrors && overallTs.errors) {{
                datasets.push({{
                    label: 'Overall Errors',
                    data: [...overallTs.errors],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.10)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }});
            }}
            const tpArr = overallTs.throughput || [];
            const errArr = overallTs.errors || [];
            totalTp = tpArr.reduce((a,b)=>a+b, 0);
            peakTp = tpArr.length ? Math.max(...tpArr) : 0;
            totalErrs = errArr.reduce((a,b)=>a+b, 0);
            samplePointsCount = tpArr.length;
        }} else if (selectedKeys.length === 1) {{
            const key = selectedKeys[0];
            const entry = labelTsMap[key] || Object.values(labelTsMap).find(e => e.label === key || e.name === key);
            const txName = entry ? entry.label : key;
            const color = getTxColor(txName);
            const tpData = (entry && entry.ts_throughput) ? entry.ts_throughput : [];
            const errData = (entry && entry.ts_errors) ? entry.ts_errors : [];

            datasets.push({{
                label: (txName.length > 28 ? txName.substring(0, 25) + '...' : txName) + ' (Throughput)',
                data: [...tpData],
                borderColor: color,
                backgroundColor: color + '22',
                fill: true,
                tension: 0.35,
                borderWidth: 2.5,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: color,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }});
            const hasErr = errData.some(e => e > 0);
            if (hasErr) {{
                datasets.push({{
                    label: (txName.length > 28 ? txName.substring(0, 25) + '...' : txName) + ' (Errors)',
                    data: [...errData],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.10)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }});
            }}
            totalTp = tpData.reduce((a,b)=>a+b, 0);
            peakTp = tpData.length ? Math.max(...tpData) : 0;
            totalErrs = errData.reduce((a,b)=>a+b, 0);
            samplePointsCount = tpData.length;
        }} else {{
            // Multiple transactions selected! Plot each transaction throughput line
            let aggTpSumByTime = null;
            selectedKeys.forEach(key => {{
                const entry = labelTsMap[key] || Object.values(labelTsMap).find(e => e.label === key || e.name === key);
                if (!entry) return;
                const txName = entry.label;
                const color = getTxColor(txName);
                const tpData = entry.ts_throughput || [];
                const errData = entry.ts_errors || [];

                datasets.push({{
                    label: (txName.length > 28 ? txName.substring(0, 25) + '...' : txName),
                    data: [...tpData],
                    borderColor: color,
                    backgroundColor: color + '15',
                    fill: false,
                    tension: 0.35,
                    borderWidth: 2.5,
                    pointRadius: 3.5,
                    pointHoverRadius: 6,
                    pointBackgroundColor: color,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }});

                if (!aggTpSumByTime) {{
                    aggTpSumByTime = new Array(tpData.length).fill(0);
                }}
                tpData.forEach((v, i) => {{ aggTpSumByTime[i] += v; }});
                totalErrs += errData.reduce((a,b)=>a+b, 0);
            }});

            if (aggTpSumByTime && aggTpSumByTime.length > 0) {{
                totalTp = aggTpSumByTime.reduce((a,b)=>a+b, 0);
                peakTp = Math.max(...aggTpSumByTime);
                samplePointsCount = aggTpSumByTime.length;
            }}
        }}

        tpChartObj.data.datasets = datasets;
        tpChartObj.update('active');

        // Dynamically update the 4 KPI chips above the chart
        if (samplePointsCount > 0) {{
            const avgVal = Math.round(totalTp / samplePointsCount);
            const peakVal = Math.round(peakTp);
            const totalSamples = totalTp * 10;
            const errRateVal = totalSamples > 0 ? (totalErrs / totalSamples * 100).toFixed(2) : '0.00';

            const kpiAvg = document.getElementById('tpKpiAvg');
            const kpiPeak = document.getElementById('tpKpiPeak');
            const kpiErr = document.getElementById('tpKpiErr');
            const kpiTrend = document.getElementById('tpKpiTrend');
            if (kpiAvg) kpiAvg.innerText = avgVal + ' req/s';
            if (kpiPeak) kpiPeak.innerText = peakVal + ' req/s';
            if (kpiErr) {{
                kpiErr.innerText = errRateVal + '%';
                kpiErr.style.color = parseFloat(errRateVal) > 0 ? 'var(--red)' : 'var(--green)';
            }}
            if (kpiTrend) {{
                if (isAll) {{
                    const diffPct = peakVal > 0 ? Math.round((peakVal - avgVal)/peakVal * 100) : 0;
                    if (diffPct >= 15) {{
                        kpiTrend.innerText = '↓ ' + diffPct + '% from Peak';
                        kpiTrend.style.color = 'var(--red)';
                    }} else {{
                        kpiTrend.innerText = '🟢 Stable';
                        kpiTrend.style.color = 'var(--green)';
                    }}
                }} else {{
                    kpiTrend.innerText = `${{selectedKeys.length}} Selected`;
                    kpiTrend.style.color = 'var(--accent)';
                }}
            }}
        }}
    }}

    // Mount Throughput and Response Time multi-select widgets
    const chartTxOptionsData = {tx_options_json};
    const tpMs = createChartMultiSelect('tpMultiSelectContainer', {{
        items: chartTxOptionsData,
        overallLabel: 'All Transactions (Overall)',
        initialSelected: ['ALL'],
        maxWidth: '280px',
        placeholder: '🔍 Search transactions...',
        onChange: (selectedIds) => {{
            updateTpChart(selectedIds);
        }}
    }});

    const rtMs = createChartMultiSelect('rtMultiSelectContainer', {{
        items: chartTxOptionsData,
        overallLabel: 'All Transactions (Overall)',
        initialSelected: ['ALL'],
        maxWidth: '280px',
        placeholder: '🔍 Search transactions...',
        onChange: (selectedIds) => {{
            updateRtChart(selectedIds);
        }}
    }});

    // ── Hierarchical Transaction & Sub-Transaction Multi-View Line Chart Manager ──
    """
