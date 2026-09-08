#!/usr/bin/env python3
"""Run comparison engine: baseline selection, differential loading, and delta badges."""
import json
import re

def get_comparison_js(ctx: dict) -> str:
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
    comparison_draft_json = ctx.get("comparison_draft_json", "{}")

    return f"""
    // ── Comparison State & Draft Persistence ──
    const embeddedComparisonDraft = {comparison_draft_json};
    window.currentComparisonBaselineId = null;
    window.currentComparisonData = null;
    let compAutoSaveTimeout = null;

    // Active chart instances & control states
    window.compChartExplorer = null;
    window.compChartDistribution = null;
    window.compChartTpsErrors = null;
    // Legacy aliases for compatibility
    window.compChartVariance = null;
    window.compChartTps = null;
    window.compChartErr = null;

    window.compExplorerState = {{
        metric: 'variance_pct',
        filter: 'all',
        chartType: 'bar',
        search: ''
    }};
    window.compDistState = {{
        type: 'buckets'
    }};
    window.compTpsState = {{
        chartType: 'bar'
    }};
    window.compActiveMatrixKey = null;
    window.compTableFilterStatus = 'ALL';
    window.compTableSearchQuery = '';

    function showCompDraftBadge(text, isSaved) {{
        const badge = document.getElementById('comp-draft-badge');
        if (!badge) return;
        badge.textContent = text || '💾 Draft Auto-Saved';
        badge.style.display = 'inline-flex';
        if (isSaved) {{
            badge.style.background = 'rgba(16, 185, 129, 0.15)';
            badge.style.color = '#10b981';
            badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        }} else {{
            badge.style.background = 'rgba(56, 189, 248, 0.15)';
            badge.style.color = '#0284c7';
            badge.style.borderColor = 'rgba(56, 189, 248, 0.3)';
        }}
    }}

    function hideCompDraftBadge() {{
        const badge = document.getElementById('comp-draft-badge');
        if (badge) badge.style.display = 'none';
    }}

    function collectComparisonCustomEdits() {{
        const aiSummary = document.getElementById('comp-ai-summary');
        const aiHighlights = document.getElementById('comp-ai-highlights');
        const aiRecs = document.getElementById('comp-ai-recommendations');
        const findingsCont = document.getElementById('comp-ai-findings-container');

        return {{
            summary_html: aiSummary ? aiSummary.innerHTML : '',
            highlights_html: aiHighlights ? aiHighlights.innerHTML : '',
            recommendations_html: aiRecs ? aiRecs.innerHTML : '',
            findings_html: findingsCont ? findingsCont.innerHTML : ''
        }};
    }}

    function persistComparisonDraft(baselineId, data, customEdits) {{
        const currentRunId = "{run_id}";
        if (!baselineId) return;

        const draftObj = {{
            current_id: currentRunId,
            baseline_id: baselineId,
            updated_at: new Date().toISOString(),
            data: data || window.currentComparisonData || {{}},
            custom_edits: customEdits || collectComparisonCustomEdits()
        }};

        try {{
            localStorage.setItem('rpt_comp_draft_' + currentRunId, JSON.stringify(draftObj));
        }} catch (e) {{
            console.warn("LocalStorage draft save note:", e);
        }}

        fetch('/api/comparison/draft', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(draftObj)
        }}).then(r => r.json()).then(res => {{
            if (res && res.success) {{
                showCompDraftBadge('💾 Draft Auto-Saved', true);
            }}
        }}).catch(err => {{
            showCompDraftBadge('💾 Draft Saved (Local)', true);
        }});
    }}

    function scheduleComparisonDraftAutoSave() {{
        if (!window.currentComparisonBaselineId) return;
        showCompDraftBadge('⏳ Saving Draft...', false);
        if (compAutoSaveTimeout) clearTimeout(compAutoSaveTimeout);
        compAutoSaveTimeout = setTimeout(() => {{
            persistComparisonDraft(window.currentComparisonBaselineId, window.currentComparisonData, collectComparisonCustomEdits());
        }}, 500);
    }}

    function bindComparisonEditableListeners() {{
        ['comp-ai-summary', 'comp-ai-highlights', 'comp-ai-recommendations', 'comp-ai-findings-container'].forEach(id => {{
            const el = document.getElementById(id);
            if (el && !el._draftBound) {{
                el._draftBound = true;
                el.addEventListener('input', scheduleComparisonDraftAutoSave);
                el.addEventListener('blur', scheduleComparisonDraftAutoSave);
            }}
        }});
    }}

    async function initComparisonTab() {{
        const baselineSelect = document.getElementById('compareBaselineSelect');
        if (!baselineSelect) return;

        if (document.documentElement.classList.contains('published-mode')) return;

        const currentRunId = "{run_id}";

        try {{
            const res = await fetch('/api/compare-runs/list');
            const data = await res.json();
            const runs = data.runs || [];
            
            baselineSelect.innerHTML = '<option value="">-- Choose a Baseline Run --</option>';
            
            runs.forEach(r => {{
                if (r.id !== currentRunId) {{
                    const opt = document.createElement('option');
                    opt.value = r.id;
                    const dateStr = r.execution_time ? ` (${{r.execution_time}})` : '';
                    const usersStr = r.users ? ` [${{r.users}} Users]` : '';
                    opt.textContent = `${{r.id}}${{usersStr}}${{dateStr}}`;
                    baselineSelect.appendChild(opt);
                }}
            }});
        }} catch (e) {{
            console.warn("Could not load available runs for comparison selector:", e);
        }}

        let draftToRestore = null;
        if (embeddedComparisonDraft && (embeddedComparisonDraft.baseline_id || embeddedComparisonDraft.baselineId)) {{
            draftToRestore = embeddedComparisonDraft;
        }}

        try {{
            const localSaved = localStorage.getItem('rpt_comp_draft_' + currentRunId);
            if (localSaved) {{
                const parsedLocal = JSON.parse(localSaved);
                if (parsedLocal && (parsedLocal.baseline_id || parsedLocal.baselineId)) {{
                    draftToRestore = parsedLocal;
                }}
            }}
        }} catch (e) {{}}

        if (!draftToRestore) {{
            try {{
                const dRes = await fetch(`/api/comparison/draft?current_id=${{encodeURIComponent(currentRunId)}}`);
                if (dRes.ok) {{
                    const dData = await dRes.json();
                    if (dData.success && dData.draft) {{
                        draftToRestore = dData.draft;
                    }}
                }}
            }} catch (e) {{}}
        }}

        if (draftToRestore) {{
            const bId = draftToRestore.baseline_id || draftToRestore.baselineId;
            if (bId) {{
                baselineSelect.value = bId;
                const cEdits = draftToRestore.custom_edits || draftToRestore.customEdits;
                if (draftToRestore.data && draftToRestore.data.scorecard) {{
                    renderComparisonData(draftToRestore.data, cEdits, bId);
                }} else {{
                    await loadReportComparison(bId, null, cEdits);
                }}
                showCompDraftBadge('💾 Draft Auto-Saved', true);
            }}
        }}
    }}

    async function onBaselineSelectionChange() {{
        const baselineSelect = document.getElementById('compareBaselineSelect');
        const baselineId = baselineSelect ? baselineSelect.value : '';
        if (!baselineId) {{
            clearReportComparison();
            return;
        }}
        await loadReportComparison(baselineId);
    }}

    async function loadReportComparison(baselineId, useCachedData = null, customEdits = null) {{
        window.currentComparisonBaselineId = baselineId;
        const currentRunId = "{run_id}";

        try {{
            let data = useCachedData;
            if (!data) {{
                const res = await fetch(`/api/compare-runs?baseline_id=${{encodeURIComponent(baselineId)}}&current_id=${{encodeURIComponent(currentRunId)}}`);
                data = await res.json();
                if (!data.success) {{
                    alert("Failed to load comparison: " + (data.message || "Unknown error"));
                    return;
                }}
            }}

            window.currentComparisonData = data;
            renderComparisonData(data, customEdits, baselineId);
            persistComparisonDraft(baselineId, data, customEdits);

        }} catch (e) {{
            alert("Error rendering comparison: " + e.message);
        }}
    }}

    function renderComparisonData(data, customEdits = null, baselineId = null) {{
        if (baselineId) window.currentComparisonBaselineId = baselineId;
        window.currentComparisonData = data;

        const emptyState = document.getElementById('compare-empty-state');
        const contentContainer = document.getElementById('compare-content-container');
        const clearBtn = document.getElementById('clearCompareBtn');

        const sc = data.scorecard || {{}};
        const ai = data.ai_insights || {{}};
        const txs = data.transaction_comparisons || [];
        const critTxs = data.critical_transactions || [];
        const transitions = data.sla_transitions || {{}};

        // 1. AI Insights & Assessment
        const panel = document.getElementById('comp-ai-panel');
        if (panel && ai.risk_color) {{
            panel.style.borderLeftColor = ai.risk_color;
        }}
        const aiRiskBadge = document.getElementById('comp-ai-risk-badge');
        if (aiRiskBadge) {{
            aiRiskBadge.textContent = ai.risk_level || 'UNKNOWN';
            aiRiskBadge.style.background = ai.risk_color || 'var(--muted)';
            aiRiskBadge.style.color = '#fff';
        }}
        const statusIcon = document.getElementById('comp-ai-status-icon');
        if (statusIcon) {{
            const r = (ai.risk_level || '').toUpperCase();
            statusIcon.textContent = (r.includes('HIGH') || r.includes('CRIT')) ? '🔴' : (r.includes('MED') || r.includes('MOD')) ? '🟡' : (r.includes('LOW')) ? '🟢' : '⚖️';
        }}
        const statusText = document.getElementById('comp-ai-status-text');
        if (statusText) {{
            statusText.textContent = ai.status_text || ai.status_badge || 'Comparative Differential Analysis';
            if (ai.risk_color) statusText.style.color = ai.risk_color;
        }}

        const aiSummary = document.getElementById('comp-ai-summary');
        if (aiSummary) {{
            if (customEdits && customEdits.summary_html) {{
                aiSummary.innerHTML = customEdits.summary_html;
            }} else if (ai.executive_summary && ai.executive_summary.trim()) {{
                aiSummary.innerHTML = ai.executive_summary;
            }} else {{
                aiSummary.innerHTML = '<span style="color:var(--muted); font-style:italic;">AI comparative insights unavailable.</span>';
            }}
        }}

        const deltaChips = document.getElementById('comp-ai-delta-chips');
        if (deltaChips) {{
            const rtPct = sc.rt_change_pct ?? 0;
            const slaChange = sc.sla_pass_change_pp ?? 0;
            const errChange = sc.err_change_pp ?? 0;
            const tpsPct = sc.tps_change_pct ?? 0;

            const rtColor = rtPct <= -5 ? '#10b981' : rtPct >= 5 ? '#ef4444' : '#64748b';
            const slaColor = slaChange >= 0 ? '#10b981' : '#ef4444';
            const errColor = errChange <= 0 ? '#10b981' : '#ef4444';
            const tpsColor = tpsPct >= 0 ? '#10b981' : '#ef4444';

            deltaChips.innerHTML = `
                <span style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.35rem 0.75rem; font-weight:700;">
                    ⏱️ Avg RT: <span style="color:${{rtColor}};">${{rtPct > 0 ? '+' : ''}}${{rtPct}}%</span>
                </span>
                <span style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.35rem 0.75rem; font-weight:700;">
                    🎯 SLA Compliance: <span style="color:${{slaColor}};">${{slaChange >= 0 ? '+' : ''}}${{slaChange}} pp</span>
                </span>
                <span style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.35rem 0.75rem; font-weight:700;">
                    🔴 Error Delta: <span style="color:${{errColor}};">${{errChange >= 0 ? '+' : ''}}${{errChange}} pp</span>
                </span>
                <span style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.35rem 0.75rem; font-weight:700;">
                    ⚡ Throughput: <span style="color:${{tpsColor}};">${{tpsPct >= 0 ? '+' : ''}}${{tpsPct}}%</span>
                </span>
            `;
        }}

        const aiHighlights = document.getElementById('comp-ai-highlights');
        if (aiHighlights) {{
            if (customEdits && customEdits.highlights_html) {{
                aiHighlights.innerHTML = customEdits.highlights_html;
            }} else if (ai.highlights && ai.highlights.length) {{
                aiHighlights.innerHTML = ai.highlights.map(h => `<li style="margin-bottom:0.35rem;">${{h}}</li>`).join('');
            }} else {{
                aiHighlights.innerHTML = '<li style="color:var(--muted); font-style:italic;">No AI comparative observations generated.</li>';
            }}
        }}

        const aiRecs = document.getElementById('comp-ai-recommendations');
        if (aiRecs) {{
            if (customEdits && customEdits.recommendations_html) {{
                aiRecs.innerHTML = customEdits.recommendations_html;
            }} else if (ai.recommendations && ai.recommendations.length) {{
                aiRecs.innerHTML = ai.recommendations.map(r => `<li style="margin-bottom:0.35rem;">${{r}}</li>`).join('');
            }} else {{
                aiRecs.innerHTML = '<li style="color:var(--muted); font-style:italic;">No AI comparative recommendations generated.</li>';
            }}
        }}

        const findingsSec = document.getElementById('comp-ai-findings-section');
        const findingsCont = document.getElementById('comp-ai-findings-container');
        if (findingsSec && findingsCont) {{
            if (ai.findings && ai.findings.length > 0) {{
                const topFindings = ai.findings.slice(0, 4);
                findingsCont.innerHTML = topFindings.map(f => {{
                    const sev = (f.severity || 'info').toLowerCase();
                    const sevColor = sev === 'critical' ? '#ef4444' : sev === 'high' ? '#f97316' : sev === 'medium' ? '#eab308' : '#3b82f6';
                    const sevIcon = sev === 'critical' ? '🔴' : sev === 'high' ? '🟠' : sev === 'medium' ? '🟡' : '🔵';
                    const catBadge = f.category ? `<span style="font-size:0.7rem; font-weight:600; color:var(--muted); background:var(--surface); border:1px solid var(--border); padding:0.1rem 0.4rem; border-radius:4px;">${{f.category}}</span>` : '';
                    
                    const actionText = f.recommendation || f.takeaway || '';
                    const actionHtml = actionText ? `<div style="display:inline-flex; align-items:center; gap:0.35rem; margin-top:0.25rem; font-size:0.78rem; color:var(--green); font-weight:600;"><span style="font-size:0.68rem; background:rgba(16,185,129,0.15); padding:0.08rem 0.35rem; border-radius:4px; border:1px solid rgba(16,185,129,0.3);">🎯 Action</span> ${{actionText}}</div>` : '';

                    const obsText = f.observation || f.insight || f.title || '';

                    return `
                        <div style="background:var(--surface2); border:1px solid var(--border); border-left:3px solid ${{sevColor}}; border-radius:8px; padding:0.65rem 0.95rem; display:flex; justify-content:space-between; align-items:center; gap:0.75rem; flex-wrap:wrap;">
                            <div style="flex:1; min-width:260px;">
                                <div style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.2rem; flex-wrap:wrap;">
                                    <span>${{sevIcon}}</span>
                                    <strong style="font-size:0.86rem; color:var(--text);">${{f.title || 'Insight'}}</strong>
                                    ${{catBadge}}
                                </div>
                                <div style="font-size:0.8rem; line-height:1.45; color:var(--text);" contenteditable="true">${{obsText}}</div>
                                ${{actionHtml}}
                            </div>
                            <div style="display:flex; align-items:center; gap:0.4rem; flex-shrink:0;">
                                <span style="font-size:0.68rem; font-weight:700; color:${{sevColor}}; text-transform:uppercase; background:var(--surface); border:1px solid var(--border); padding:0.15rem 0.45rem; border-radius:4px;">${{f.severity || 'INFO'}}</span>
                            </div>
                        </div>
                    `;
                }}).join('');
                findingsSec.style.display = 'block';
            }} else if (customEdits && customEdits.findings_html) {{
                findingsCont.innerHTML = customEdits.findings_html;
                findingsSec.style.display = 'block';
            }} else {{
                findingsCont.innerHTML = '';
                findingsSec.style.display = 'none';
            }}
        }}

        // 2. Iteration Stats
        const elIterA = document.getElementById('comp-kpi-iter-a');
        const elIterB = document.getElementById('comp-kpi-iter-b');
        const elBadgeIter = document.getElementById('comp-badge-iter');
        if (elIterA) elIterA.textContent = sc.run_a_iter ?? '-';
        if (elIterB) elIterB.textContent = sc.run_b_iter ?? '-';
        if (elBadgeIter) {{
            const pct = sc.iter_change_pct || 0;
            elBadgeIter.textContent = `${{pct >= 0 ? '+' : ''}}${{pct}}%`;
            elBadgeIter.className = `comp-delta-badge ${{pct >= 0 ? 'improved' : 'degraded'}}`;
        }}

        const elReqA = document.getElementById('comp-kpi-req-a');
        const elReqB = document.getElementById('comp-kpi-req-b');
        const elBadgeReq = document.getElementById('comp-badge-req');
        if (elReqA) elReqA.textContent = (sc.run_a_req || 0).toLocaleString();
        if (elReqB) elReqB.textContent = (sc.run_b_req || 0).toLocaleString();
        if (elBadgeReq) {{
            const pct = sc.req_change_pct || 0;
            elBadgeReq.textContent = `${{pct >= 0 ? '+' : ''}}${{pct}}%`;
            elBadgeReq.className = `comp-delta-badge ${{pct >= 0 ? 'improved' : 'degraded'}}`;
        }}

        const elTpsA = document.getElementById('comp-kpi-tps-a');
        const elTpsB = document.getElementById('comp-kpi-tps-b');
        const elBadgeTps = document.getElementById('comp-badge-tps');
        if (elTpsA) elTpsA.textContent = `${{sc.run_a_tps ?? 0}} TPS`;
        if (elTpsB) elTpsB.textContent = `${{sc.run_b_tps ?? 0}} TPS`;
        if (elBadgeTps) {{
            const pct = sc.tps_change_pct || 0;
            elBadgeTps.textContent = `${{pct >= 0 ? '+' : ''}}${{pct}}%`;
            elBadgeTps.className = `comp-delta-badge ${{pct >= 0 ? 'improved' : 'degraded'}}`;
        }}

        // 3. Response Time KPIs
        const elRtA = document.getElementById('comp-kpi-rt-a');
        const elRtB = document.getElementById('comp-kpi-rt-b');
        const elBadgeRt = document.getElementById('comp-badge-rt');
        if (elRtA) elRtA.textContent = `${{sc.run_a_rt ?? 0}}ms`;
        if (elRtB) elRtB.textContent = `${{sc.run_b_rt ?? 0}}ms`;
        if (elBadgeRt) {{
            const pct = sc.rt_change_pct || 0;
            elBadgeRt.textContent = `${{pct > 0 ? '+' : ''}}${{pct}}%`;
            elBadgeRt.className = `comp-delta-badge ${{pct <= -5 ? 'improved' : pct >= 5 ? 'degraded' : 'neutral'}}`;
        }}

        const elP90A = document.getElementById('comp-kpi-p90-a');
        const elP90B = document.getElementById('comp-kpi-p90-b');
        const elBadgeP90 = document.getElementById('comp-badge-p90');
        if (elP90A) elP90A.textContent = `${{sc.run_a_p90 ?? 0}}ms`;
        if (elP90B) elP90B.textContent = `${{sc.run_b_p90 ?? 0}}ms`;
        if (elBadgeP90) {{
            const pct = sc.p90_change_pct || 0;
            elBadgeP90.textContent = `${{pct > 0 ? '+' : ''}}${{pct}}%`;
            elBadgeP90.className = `comp-delta-badge ${{pct <= -5 ? 'improved' : pct >= 5 ? 'degraded' : 'neutral'}}`;
        }}

        const elP95A = document.getElementById('comp-kpi-p95-a');
        const elP95B = document.getElementById('comp-kpi-p95-b');
        const elBadgeP95 = document.getElementById('comp-badge-p95');
        if (elP95A) elP95A.textContent = `${{sc.run_a_p95 ?? 0}}ms`;
        if (elP95B) elP95B.textContent = `${{sc.run_b_p95 ?? 0}}ms`;
        if (elBadgeP95) {{
            const pct = sc.p95_change_pct || 0;
            elBadgeP95.textContent = `${{pct > 0 ? '+' : ''}}${{pct}}%`;
            elBadgeP95.className = `comp-delta-badge ${{pct <= -5 ? 'improved' : pct >= 5 ? 'degraded' : 'neutral'}}`;
        }}

        const elP99A = document.getElementById('comp-kpi-p99-a');
        const elP99B = document.getElementById('comp-kpi-p99-b');
        if (elP99A) elP99A.textContent = `${{sc.run_a_p99 ?? 0}}ms`;
        if (elP99B) elP99B.textContent = `${{sc.run_b_p99 ?? 0}}ms`;

        // 4. Error KPIs
        const elErrA = document.getElementById('comp-kpi-err-a');
        const elErrB = document.getElementById('comp-kpi-err-b');
        const elBadgeErr = document.getElementById('comp-badge-err-rate');
        if (elErrA) elErrA.textContent = `${{sc.run_a_err_rate ?? 0}}%`;
        if (elErrB) elErrB.textContent = `${{sc.run_b_err_rate ?? 0}}%`;
        if (elBadgeErr) {{
            const pp = sc.err_change_pp || 0;
            elBadgeErr.textContent = `${{pp > 0 ? '+' : ''}}${{pp}} pp`;
            elBadgeErr.className = `comp-delta-badge ${{pp <= 0 ? 'improved' : 'degraded'}}`;
        }}

        const elErrCntA = document.getElementById('comp-kpi-errcnt-a');
        const elErrCntB = document.getElementById('comp-kpi-errcnt-b');
        if (elErrCntA) elErrCntA.textContent = (sc.run_a_err_count ?? 0).toLocaleString();
        if (elErrCntB) elErrCntB.textContent = (sc.run_b_err_count ?? 0).toLocaleString();

        // 5. SLA Transition Matrix Counts
        const cntPassPass = document.getElementById('comp-cnt-pass-pass');
        const cntPassFail = document.getElementById('comp-cnt-pass-fail');
        const cntFailPass = document.getElementById('comp-cnt-fail-pass');
        const cntFailFail = document.getElementById('comp-cnt-fail-fail');
        if (cntPassPass) cntPassPass.textContent = (transitions.pass_to_pass || []).length;
        if (cntPassFail) cntPassFail.textContent = (transitions.pass_to_fail || []).length;
        if (cntFailPass) cntFailPass.textContent = (transitions.fail_to_pass || []).length;
        if (cntFailFail) cntFailFail.textContent = (transitions.fail_to_fail || []).length;

        // Reset matrix active filter
        window.compActiveMatrixKey = null;
        const activeFilterLabel = document.getElementById('comp-crit-active-filter-label');
        if (activeFilterLabel) activeFilterLabel.textContent = 'Showing All Critical Transactions';
        const activeMatrixIndicator = document.getElementById('comp-active-matrix-filter');
        if (activeMatrixIndicator) activeMatrixIndicator.style.display = 'none';
        ['matrix-btn-pass-pass', 'matrix-btn-pass-fail', 'matrix-btn-fail-pass', 'matrix-btn-fail-fail',
         'comp-box-pass-pass', 'comp-box-pass-fail', 'comp-box-fail-pass', 'comp-box-fail-fail'].forEach(id => {{
            const el = document.getElementById(id);
            if (el) el.classList.remove('active-filter');
        }});

        // Table filter chips count badges
        const cntAll = txs.length;
        const cntImp = txs.filter(t => t.status === 'IMPROVED' || (t.rt_pct_change !== undefined && t.rt_pct_change < 0)).length;
        const cntReg = txs.filter(t => t.status === 'REGRESSED' || (t.rt_pct_change !== undefined && t.rt_pct_change > 0)).length;
        const cntBrch = txs.filter(t => t.is_critical || t.sla_passed_b === false || t.sla_transition === 'PASS_TO_FAIL' || t.sla_transition === 'FAIL_TO_FAIL').length;
        const cntUnch = txs.filter(t => t.status === 'UNCHANGED' || t.rt_pct_change === 0 || (t.rt_pct_change >= -2 && t.rt_pct_change <= 2)).length;

        const elCntAll = document.getElementById('cnt-tbl-all');
        const elCntImp = document.getElementById('cnt-tbl-improved');
        const elCntReg = document.getElementById('cnt-tbl-regressed');
        const elCntBrch = document.getElementById('cnt-tbl-breached');
        const elCntUnch = document.getElementById('cnt-tbl-unchanged');
        if (elCntAll) elCntAll.textContent = cntAll;
        if (elCntImp) elCntImp.textContent = cntImp;
        if (elCntReg) elCntReg.textContent = cntReg;
        if (elCntBrch) elCntBrch.textContent = cntBrch;
        if (elCntUnch) elCntUnch.textContent = cntUnch;

        // Sync Explorer controls
        const metricSel = document.getElementById('comp-explorer-metric-select') || document.getElementById('comp-metric-select');
        const filterSel = document.getElementById('comp-explorer-filter-select') || document.getElementById('comp-filter-select');
        if (metricSel && window.compExplorerState.metric) metricSel.value = window.compExplorerState.metric;
        if (filterSel && window.compExplorerState.filter) filterSel.value = window.compExplorerState.filter;

        // 6. Populate Tables
        renderCompRtTable(txs);
        renderCompCriticalTable(critTxs.length ? critTxs : txs);

        // 7. Render All Modular Full-Width Charts
        renderCompExplorerChart();
        renderCompDistributionChart();
        renderCompTpsErrorsChart();

        // Bind auto-save listeners on editable fields
        bindComparisonEditableListeners();

        // Toggle visibility
        if (emptyState) emptyState.style.display = 'none';
        if (contentContainer) contentContainer.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'inline-block';

        // Resize Chart.js
        window.dispatchEvent(new Event('resize'));
    }}

    // ── Modular Graph 1: Comparative Multi-Metric Explorer ──
    function onCompExplorerMetricChange(val) {{
        const sel = document.getElementById('comp-explorer-metric-select') || document.getElementById('comp-metric-select');
        window.compExplorerState.metric = val || (sel ? sel.value : 'variance_pct');
        renderCompExplorerChart();
    }}

    function onCompExplorerFilterChange(val) {{
        const sel = document.getElementById('comp-explorer-filter-select') || document.getElementById('comp-filter-select');
        window.compExplorerState.filter = val || (sel ? sel.value : 'all');
        renderCompExplorerChart();
    }}

    function onCompExplorerChartTypeChange(type) {{
        window.compExplorerState.chartType = type;
        ['comp-type-bar', 'comp-type-line', 'comp-type-area', 'comp-charttype-bar', 'comp-charttype-line', 'comp-charttype-area'].forEach(id => {{
            const btn = document.getElementById(id);
            if (btn) btn.classList.remove('active');
        }});
        const activeBtn = document.getElementById(`comp-type-${{type}}`) || document.getElementById(`comp-charttype-${{type}}`);
        if (activeBtn) activeBtn.classList.add('active');
        renderCompExplorerChart();
    }}

    function onCompExplorerSearch(query) {{
        window.compExplorerState.search = (query || '').toLowerCase().trim();
        renderCompExplorerChart();
    }}

    function renderCompExplorerChart() {{
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('chart-comp-variance');
        if (!canvas || !window.currentComparisonData) return;

        const txs = window.currentComparisonData.transaction_comparisons || [];
        const state = window.compExplorerState;

        // 1. Filter Transactions
        let filtered = [...txs];
        if (state.search) {{
            filtered = filtered.filter(t => (t.label || '').toLowerCase().includes(state.search));
        }}

        if (state.filter === 'regressed') {{
            const regList = filtered.filter(t => t.status === 'REGRESSED' || (t.rt_pct_change !== undefined && t.rt_pct_change > 0) || (t.rt_diff_ms !== undefined && t.rt_diff_ms > 0));
            regList.sort((a, b) => (b.rt_pct_change || 0) - (a.rt_pct_change || 0));
            filtered = regList.length > 0 ? regList.slice(0, 20) : [...filtered].sort((a, b) => (b.rt_b || 0) - (a.rt_b || 0)).slice(0, 10);
        }} else if (state.filter === 'improved') {{
            const impList = filtered.filter(t => t.status === 'IMPROVED' || (t.rt_pct_change !== undefined && t.rt_pct_change < 0) || (t.rt_diff_ms !== undefined && t.rt_diff_ms < 0));
            impList.sort((a, b) => (a.rt_pct_change || 0) - (b.rt_pct_change || 0));
            filtered = impList.length > 0 ? impList.slice(0, 20) : [...filtered].sort((a, b) => (a.rt_b || 0) - (b.rt_b || 0)).slice(0, 10);
        }} else if (state.filter === 'critical' || state.filter === 'breached') {{
            const critList = filtered.filter(t => t.is_critical || t.sla_passed_b === false || t.sla_transition === 'PASS_TO_FAIL' || t.sla_transition === 'FAIL_TO_FAIL');
            filtered = critList.length > 0 ? critList.slice(0, 20) : filtered.slice(0, 15);
        }} else if (state.filter === 'top10_rt') {{
            filtered.sort((a, b) => (b.rt_b || 0) - (a.rt_b || 0));
            filtered = filtered.slice(0, 10);
        }} else if (state.filter === 'top10_tps') {{
            filtered.sort((a, b) => (b.tps_b || 0) - (a.tps_b || 0));
            filtered = filtered.slice(0, 10);
        }} else {{
            // 'all'
            if (filtered.length > 25) {{
                filtered = filtered.slice(0, 25);
            }}
        }}

        const labels = filtered.map(t => t.label.length > 28 ? t.label.substring(0, 26) + '...' : t.label);

        // 2. Build Datasets based on selected metric
        let datasets = [];
        let yAxisLabel = '';
        let isDivergingPct = false;

        const metric = state.metric || 'variance_pct';
        const isArea = state.chartType === 'area';
        const chartType = isArea ? 'line' : (state.chartType || 'bar');

        if (metric === 'variance_pct' || metric === 'rt_pct_change') {{
            isDivergingPct = true;
            yAxisLabel = 'Response Time Variance (%)';
            const dataVals = filtered.map(t => t.rt_pct_change || 0);
            datasets = [{{
                label: 'RT Variance %',
                data: dataVals,
                backgroundColor: chartType === 'line' 
                    ? (isArea ? 'rgba(239, 68, 68, 0.25)' : 'transparent') 
                    : dataVals.map(v => v > 0 ? 'rgba(239, 68, 68, 0.75)' : 'rgba(16, 185, 129, 0.75)'),
                borderColor: chartType === 'line' 
                    ? '#dc2626' 
                    : dataVals.map(v => v > 0 ? '#dc2626' : '#059669'),
                borderWidth: chartType === 'line' ? 2.5 : 1,
                borderRadius: chartType === 'bar' ? 4 : 0,
                fill: isArea,
                tension: 0.35,
                pointRadius: chartType === 'line' ? 5 : 0,
                pointHoverRadius: chartType === 'line' ? 7 : 0,
                pointBackgroundColor: dataVals.map(v => v > 0 ? '#dc2626' : '#059669')
            }}];
        }} else if (metric === 'rt_diff_ms') {{
            yAxisLabel = 'Response Time Delta (ms)';
            const dataVals = filtered.map(t => t.rt_diff_ms || 0);
            datasets = [{{
                label: 'RT Delta (ms)',
                data: dataVals,
                backgroundColor: chartType === 'line' 
                    ? (isArea ? 'rgba(56, 189, 248, 0.25)' : 'transparent') 
                    : dataVals.map(v => v > 0 ? 'rgba(239, 68, 68, 0.75)' : 'rgba(16, 185, 129, 0.75)'),
                borderColor: chartType === 'line' 
                    ? '#0284c7' 
                    : dataVals.map(v => v > 0 ? '#dc2626' : '#059669'),
                borderWidth: chartType === 'line' ? 2.5 : 1,
                borderRadius: chartType === 'bar' ? 4 : 0,
                fill: isArea,
                tension: 0.35,
                pointRadius: chartType === 'line' ? 5 : 0,
                pointHoverRadius: chartType === 'line' ? 7 : 0,
                pointBackgroundColor: dataVals.map(v => v > 0 ? '#dc2626' : '#059669')
            }}];
        }} else if (metric === 'avg_rt' || metric === 'p90' || metric === 'p95' || metric === 'p99') {{
            const keyA = metric === 'avg_rt' ? 'rt_a' : metric === 'p90' ? 'p90_a' : metric === 'p95' ? 'p95_a' : 'p99_a';
            const keyB = metric === 'avg_rt' ? 'rt_b' : metric === 'p90' ? 'p90_b' : metric === 'p95' ? 'p95_b' : 'p99_b';
            const metricName = metric.toUpperCase();
            yAxisLabel = `${{metricName}} Response Time (ms)`;

            datasets = [
                {{
                    label: `Baseline ${{metricName}} (ms)`,
                    data: filtered.map(t => t[keyA] || 0),
                    backgroundColor: isArea ? 'rgba(100, 116, 139, 0.25)' : 'rgba(100, 116, 139, 0.7)',
                    borderColor: '#64748b',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }},
                {{
                    label: `Current ${{metricName}} (ms)`,
                    data: filtered.map(t => t[keyB] || 0),
                    backgroundColor: isArea ? 'rgba(56, 189, 248, 0.25)' : 'rgba(56, 189, 248, 0.75)',
                    borderColor: '#0284c7',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }}
            ];
        }} else if (metric === 'tps') {{
            yAxisLabel = 'Throughput (TPS)';
            datasets = [
                {{
                    label: 'Baseline TPS',
                    data: filtered.map(t => t.tps_a || 0),
                    backgroundColor: isArea ? 'rgba(100, 116, 139, 0.25)' : 'rgba(100, 116, 139, 0.7)',
                    borderColor: '#64748b',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }},
                {{
                    label: 'Current TPS',
                    data: filtered.map(t => t.tps_b || 0),
                    backgroundColor: isArea ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.75)',
                    borderColor: '#059669',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }}
            ];
        }} else if (metric === 'error_rate' || metric === 'err_rate') {{
            yAxisLabel = 'Error Rate (%)';
            datasets = [
                {{
                    label: 'Baseline Error %',
                    data: filtered.map(t => t.err_rate_a || 0),
                    backgroundColor: isArea ? 'rgba(100, 116, 139, 0.25)' : 'rgba(100, 116, 139, 0.7)',
                    borderColor: '#64748b',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }},
                {{
                    label: 'Current Error %',
                    data: filtered.map(t => t.err_rate_b || 0),
                    backgroundColor: isArea ? 'rgba(239, 68, 68, 0.25)' : 'rgba(239, 68, 68, 0.75)',
                    borderColor: '#dc2626',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }}
            ];
        }} else if (metric === 'count') {{
            yAxisLabel = 'Request Execution Count';
            datasets = [
                {{
                    label: 'Baseline Count',
                    data: filtered.map(t => t.count_a || 0),
                    backgroundColor: isArea ? 'rgba(100, 116, 139, 0.25)' : 'rgba(100, 116, 139, 0.7)',
                    borderColor: '#64748b',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }},
                {{
                    label: 'Current Count',
                    data: filtered.map(t => t.count_b || 0),
                    backgroundColor: isArea ? 'rgba(139, 92, 246, 0.25)' : 'rgba(139, 92, 246, 0.75)',
                    borderColor: '#7c3aed',
                    borderWidth: 2,
                    borderRadius: chartType === 'bar' ? 4 : 0,
                    fill: isArea,
                    tension: 0.3,
                    pointRadius: chartType === 'line' ? 4 : 0
                }}
            ];
        }}

        if (compChartExplorer) compChartExplorer.destroy();

        compChartExplorer = new Chart(canvas, {{
            type: chartType,
            data: {{
                labels: labels,
                datasets: datasets
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: datasets.length > 1,
                        position: 'top',
                        labels: {{ color: '#94a3b8', font: {{ family: 'Inter', size: 12 }} }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                const val = ctx.raw;
                                const suffix = isDivergingPct ? '%' : (metric === 'error_rate' || metric === 'err_rate') ? '%' : (metric.includes('rt') || metric.includes('p9')) ? ' ms' : '';
                                return ` ${{ctx.dataset.label}}: ${{val > 0 && isDivergingPct ? '+' : ''}}${{val}}${{suffix}}`;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(148, 163, 184, 0.08)' }},
                        ticks: {{ color: '#94a3b8', maxRotation: 45, minRotation: 0 }}
                    }},
                    y: {{
                        title: {{ display: true, text: yAxisLabel, color: '#94a3b8' }},
                        grid: {{ color: 'rgba(148, 163, 184, 0.15)' }},
                        ticks: {{
                            color: '#94a3b8',
                            callback: v => isDivergingPct ? `${{v}}%` : (metric === 'error_rate' || metric === 'err_rate') ? `${{v}}%` : v
                        }}
                    }}
                }}
            }}
        }});

        compChartVariance = compChartExplorer; // Alias
    }}

    // ── Modular Graph 2: Latency Distribution & Cumulative Percentiles ──
    function onCompDistributionTypeChange(type) {{
        window.compDistState.type = type;
        ['comp-dist-bucket-btn', 'comp-dist-curve-btn', 'comp-disttype-buckets', 'comp-disttype-percentiles'].forEach(id => {{
            const btn = document.getElementById(id);
            if (btn) btn.classList.remove('active');
        }});
        const activeBtn = type === 'buckets'
            ? (document.getElementById('comp-dist-bucket-btn') || document.getElementById('comp-disttype-buckets'))
            : (document.getElementById('comp-dist-curve-btn') || document.getElementById('comp-disttype-percentiles'));
        if (activeBtn) activeBtn.classList.add('active');
        renderCompDistributionChart();
    }}

    function renderCompDistributionChart() {{
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('chart-comp-distribution');
        if (!canvas || !window.currentComparisonData) return;

        const data = window.currentComparisonData;
        const txs = data.transaction_comparisons || [];
        const sc = data.scorecard || {{}};
        const isBuckets = window.compDistState.type === 'buckets';

        if (compChartDistribution) compChartDistribution.destroy();

        if (isBuckets) {{
            // Histogram of Latency Buckets
            const buckets = [
                {{ label: '< 500ms', max: 500, min: 0 }},
                {{ label: '500ms - 1s', max: 1000, min: 500 }},
                {{ label: '1s - 2s', max: 2000, min: 1000 }},
                {{ label: '2s - 3s', max: 3000, min: 2000 }},
                {{ label: '3s - 5s', max: 5000, min: 3000 }},
                {{ label: '> 5s', max: Infinity, min: 5000 }}
            ];

            const baselineCounts = buckets.map(b => txs.filter(t => (t.rt_a || 0) >= b.min && (t.rt_a || 0) < b.max).length);
            const currentCounts = buckets.map(b => txs.filter(t => (t.rt_b || 0) >= b.min && (t.rt_b || 0) < b.max).length);

            compChartDistribution = new Chart(canvas, {{
                type: 'bar',
                data: {{
                    labels: buckets.map(b => b.label),
                    datasets: [
                        {{
                            label: 'Baseline Transactions',
                            data: baselineCounts,
                            backgroundColor: 'rgba(100, 116, 139, 0.7)',
                            borderColor: '#64748b',
                            borderWidth: 1,
                            borderRadius: 4
                        }},
                        {{
                            label: 'Current Transactions',
                            data: currentCounts,
                            backgroundColor: 'rgba(16, 185, 129, 0.75)',
                            borderColor: '#059669',
                            borderWidth: 1,
                            borderRadius: 4
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: '#94a3b8' }} }},
                        tooltip: {{
                            callbacks: {{
                                label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.raw}} transactions`
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }},
                        y: {{
                            title: {{ display: true, text: 'Number of Transactions', color: '#94a3b8' }},
                            grid: {{ color: 'rgba(148, 163, 184, 0.15)' }},
                            ticks: {{ color: '#94a3b8', stepSize: 1 }}
                        }}
                    }}
                }}
            }});
        }} else {{
            // Cumulative Percentiles Curves (P50, P75, P90, P95, P98, P99)
            const pLabels = ['P50 (Median)', 'P75', 'P90', 'P95', 'P98', 'P99'];
            
            // Estimate or use real percentile values from scorecard / txs
            const p50A = sc.run_a_rt || 0;
            const p90A = sc.run_a_p90 || 0;
            const p95A = sc.run_a_p95 || 0;
            const p99A = sc.run_a_p99 || (p95A * 1.15);
            const p75A = Math.round((p50A + p90A) / 2);
            const p98A = Math.round((p95A + p99A) / 2);

            const p50B = sc.run_b_rt || 0;
            const p90B = sc.run_b_p90 || 0;
            const p95B = sc.run_b_p95 || 0;
            const p99B = sc.run_b_p99 || (p95B * 1.15);
            const p75B = Math.round((p50B + p90B) / 2);
            const p98B = Math.round((p95B + p99B) / 2);

            const baselinePts = [p50A, p75A, p90A, p95A, p98A, p99A];
            const currentPts = [p50B, p75B, p90B, p95B, p98B, p99B];

            compChartDistribution = new Chart(canvas, {{
                type: 'line',
                data: {{
                    labels: pLabels,
                    datasets: [
                        {{
                            label: 'Baseline Percentile Curve',
                            data: baselinePts,
                            borderColor: '#64748b',
                            backgroundColor: 'rgba(100, 116, 139, 0.15)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            pointRadius: 5,
                            fill: true,
                            tension: 0.35
                        }},
                        {{
                            label: 'Current Percentile Curve',
                            data: currentPts,
                            borderColor: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.2)',
                            borderWidth: 2.5,
                            pointRadius: 6,
                            pointHoverRadius: 8,
                            fill: true,
                            tension: 0.35
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: '#94a3b8' }} }},
                        tooltip: {{
                            callbacks: {{
                                label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.raw}} ms`
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(148, 163, 184, 0.08)' }}, ticks: {{ color: '#94a3b8' }} }},
                        y: {{
                            title: {{ display: true, text: 'Response Time (ms)', color: '#94a3b8' }},
                            grid: {{ color: 'rgba(148, 163, 184, 0.15)' }},
                            ticks: {{ color: '#94a3b8' }}
                        }}
                    }}
                }}
            }});
        }}
    }}

    // ── Modular Graph 3: Throughput & Error Rate Dual-Axis ──
    function onCompTpsChartTypeChange(type) {{
        window.compTpsState.chartType = type;
        const btnBar = document.getElementById('comp-tps-bar-btn') || document.getElementById('comp-tpstype-bar');
        const btnLine = document.getElementById('comp-tps-line-btn') || document.getElementById('comp-tpstype-line');
        if (btnBar) btnBar.classList.toggle('active', type === 'bar');
        if (btnLine) btnLine.classList.toggle('active', type === 'line');
        renderCompTpsErrorsChart();
    }}

    function renderCompTpsErrorsChart() {{
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('chart-comp-throughput');
        if (!canvas || !window.currentComparisonData) return;

        const txs = (window.currentComparisonData.transaction_comparisons || []).slice(0, 16);
        const labels = txs.map(t => t.label.length > 22 ? t.label.substring(0, 20) + '...' : t.label);
        const isLine = window.compTpsState.chartType === 'line';

        if (compChartTpsErrors) compChartTpsErrors.destroy();

        compChartTpsErrors = new Chart(canvas, {{
            type: isLine ? 'line' : 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Baseline TPS',
                        data: txs.map(t => t.tps_a || 0),
                        backgroundColor: isLine ? 'transparent' : 'rgba(56, 189, 248, 0.65)',
                        borderColor: '#0284c7',
                        borderWidth: isLine ? 2 : 1,
                        borderRadius: isLine ? 0 : 4,
                        tension: 0.3,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Current TPS',
                        data: txs.map(t => t.tps_b || 0),
                        backgroundColor: isLine ? 'transparent' : 'rgba(16, 185, 129, 0.75)',
                        borderColor: '#059669',
                        borderWidth: isLine ? 2.5 : 1,
                        borderRadius: isLine ? 0 : 4,
                        tension: 0.3,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Baseline Error %',
                        data: txs.map(t => t.err_rate_a || 0),
                        type: 'line',
                        borderColor: '#64748b',
                        backgroundColor: 'transparent',
                        borderDash: [4, 4],
                        pointRadius: 4,
                        yAxisID: 'y1'
                    }},
                    {{
                        label: 'Current Error %',
                        data: txs.map(t => t.err_rate_b || 0),
                        type: 'line',
                        borderColor: '#ef4444',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 5,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'top', labels: {{ color: '#94a3b8' }} }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8', maxRotation: 45 }} }},
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{ display: true, text: 'Throughput (TPS)', color: '#94a3b8' }},
                        grid: {{ color: 'rgba(148, 163, 184, 0.12)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{ display: true, text: 'Error Rate (%)', color: '#ef4444' }},
                        grid: {{ drawOnChartArea: false }},
                        ticks: {{ color: '#ef4444', callback: v => `${{v}}%` }}
                    }}
                }}
            }}
        }});

        compChartTps = compChartTpsErrors;
    }}

    // ── SLA 4-Quadrant Matrix Filter Controller ──
    function filterCompCriticalByTransition(key) {{
        if (!window.currentComparisonData) return;
        const allCrit = window.currentComparisonData.critical_transactions || window.currentComparisonData.transaction_comparisons || [];
        const activeLabel = document.getElementById('comp-crit-active-filter-label');
        const activeIndicator = document.getElementById('comp-active-matrix-filter');
        const filterName = document.getElementById('comp-active-filter-name');

        const titleMap = {{
            'PASS_TO_PASS': '🟢 Pass ➔ Pass (Consistently Healthy)',
            'PASS_TO_FAIL': '🔴 Pass ➔ Fail (NEW REGRESSION BREACHES)',
            'FAIL_TO_PASS': '🟢 Fail ➔ Pass (RESOLVED SLA RECOVERIES)',
            'FAIL_TO_FAIL': '🟠 Fail ➔ Fail (Persistent Violations)'
        }};

        // Toggle if clicked already active or if 'ALL'
        if (!key || key === 'ALL' || window.compActiveMatrixKey === key) {{
            window.compActiveMatrixKey = null;
            if (activeLabel) activeLabel.textContent = 'Showing All Critical Transactions';
            if (activeIndicator) activeIndicator.style.display = 'none';
            ['matrix-btn-pass-pass', 'matrix-btn-pass-fail', 'matrix-btn-fail-pass', 'matrix-btn-fail-fail',
             'comp-box-pass-pass', 'comp-box-pass-fail', 'comp-box-fail-pass', 'comp-box-fail-fail'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.classList.remove('active-filter');
            }});
            renderCompCriticalTable(allCrit);
            return;
        }}

        window.compActiveMatrixKey = key;
        const suffix = key.toLowerCase().replace(/_/g, '-');
        ['matrix-btn-pass-pass', 'matrix-btn-pass-fail', 'matrix-btn-fail-pass', 'matrix-btn-fail-fail',
         'comp-box-pass-pass', 'comp-box-pass-fail', 'comp-box-fail-pass', 'comp-box-fail-fail'].forEach(id => {{
            const el = document.getElementById(id);
            if (el) el.classList.toggle('active-filter', id.endsWith(suffix));
        }});

        if (activeLabel) activeLabel.textContent = `Filtered by: ${{titleMap[key] || key}}`;
        if (activeIndicator) {{
            activeIndicator.style.display = 'inline-flex';
            if (filterName) filterName.textContent = titleMap[key] || key;
        }}

        const filtered = allCrit.filter(t => t.sla_transition === key);
        renderCompCriticalTable(filtered);
    }}

    function resetCompMatrixFilter() {{
        filterCompCriticalByTransition('ALL');
    }}

    function renderCompCriticalTable(items) {{
        const critTbody = document.getElementById('comp-critical-tbody');
        if (!critTbody) return;

        if (!items || items.length === 0) {{
            critTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--muted); padding:1.5rem;">No critical transactions matching this quadrant filter.</td></tr>`;
            return;
        }}

        critTbody.innerHTML = items.map(t => {{
            const transPill = t.sla_transition === 'PASS_TO_PASS' ? '<span class="comp-delta-badge improved">🟢 Pass ➔ Pass</span>'
                : t.sla_transition === 'PASS_TO_FAIL' ? '<span class="comp-delta-badge degraded">🔴 Pass ➔ Fail (NEW BREACH)</span>'
                : t.sla_transition === 'FAIL_TO_PASS' ? '<span class="comp-delta-badge improved">🟢 Fail ➔ Pass (RESOLVED)</span>'
                : '<span class="comp-delta-badge neutral">🟠 Fail ➔ Fail</span>';
            return `
                <tr>
                    <td style="font-weight:700;">${{t.label}}</td>
                    <td style="text-align:right; color:var(--muted);">${{t.target_rt || '-'}} ms</td>
                    <td style="text-align:right;">${{t.p90_a || '-'}} ms</td>
                    <td style="text-align:right; font-weight:700; color:${{t.sla_passed_b ? 'var(--green)' : 'var(--red)'}};">${{t.p90_b || '-'}} ms</td>
                    <td style="text-align:right; color:${{t.breach_margin_ms > 0 ? 'var(--red)' : 'var(--green)'}};">${{t.breach_margin_ms > 0 ? '+' + t.breach_margin_ms + ' ms' : '0 ms'}}</td>
                    <td>${{transPill}}</td>
                </tr>
            `;
        }}).join('');
    }}

    // ── Response Time Detailed Table Filters & Search ──
    function filterCompTableByStatus(status) {{
        window.compTableFilterStatus = status;
        document.querySelectorAll('.comp-filter-chips-bar .comp-filter-chip, #comp-table-status-filters .comp-filter-chip').forEach(btn => {{
            btn.classList.remove('active');
        }});
        const activeChip = document.getElementById(`chip-tbl-${{status.toLowerCase()}}`) || document.querySelector(`[data-status="${{status}}"]`);
        if (activeChip) activeChip.classList.add('active');
        applyCompTableFilters();
    }}

    function filterCompTableBySearch(query) {{
        window.compTableSearchQuery = (query || '').toLowerCase().trim();
        applyCompTableFilters();
    }}

    function applyCompTableFilters() {{
        if (!window.currentComparisonData) return;
        const txs = window.currentComparisonData.transaction_comparisons || [];
        const status = window.compTableFilterStatus || 'ALL';
        const q = window.compTableSearchQuery || '';

        let filtered = txs.filter(t => {{
            const matchesQuery = !q || (t.label || '').toLowerCase().includes(q);
            if (!matchesQuery) return false;

            if (status === 'ALL') return true;
            if (status === 'REGRESSED') return t.status === 'REGRESSED' || (t.rt_pct_change !== undefined && t.rt_pct_change > 0);
            if (status === 'IMPROVED') return t.status === 'IMPROVED' || (t.rt_pct_change !== undefined && t.rt_pct_change < 0);
            if (status === 'BREACHED') return t.is_critical || t.sla_passed_b === false || t.sla_transition === 'PASS_TO_FAIL' || t.sla_transition === 'FAIL_TO_FAIL';
            if (status === 'UNCHANGED') return t.status === 'UNCHANGED' || t.rt_pct_change === 0 || (t.rt_pct_change >= -2 && t.rt_pct_change <= 2);
            if (status === 'PASS_TO_FAIL') return t.sla_transition === 'PASS_TO_FAIL';
            if (status === 'FAIL_TO_PASS') return t.sla_transition === 'FAIL_TO_PASS';
            return true;
        }});

        renderCompRtTable(filtered);
    }}

    function renderCompRtTable(txs) {{
        const rtTbody = document.getElementById('comp-rt-tbody');
        if (!rtTbody) return;

        if (!txs || txs.length === 0) {{
            rtTbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:var(--muted); padding:1.5rem;">No transaction data found matching search or filter criteria.</td></tr>`;
            return;
        }}

        rtTbody.innerHTML = txs.map(t => {{
            const badgeCls = t.status === 'IMPROVED' ? 'improved' : t.status === 'REGRESSED' ? 'degraded' : 'neutral';
            const diffSign = (t.rt_diff_ms || 0) > 0 ? '+' : '';
            const pctSign = (t.rt_pct_change || 0) > 0 ? '+' : '';
            return `
                <tr>
                    <td style="font-weight:600;">${{t.label}}</td>
                    <td><span class="comp-delta-badge ${{badgeCls}}">${{t.status}}</span></td>
                    <td style="text-align:right;">${{t.rt_a}} ms</td>
                    <td style="text-align:right; font-weight:700;">${{t.rt_b}} ms</td>
                    <td style="text-align:right; color:${{t.rt_diff_ms > 0 ? 'var(--red)' : 'var(--green)'}};">${{diffSign}}${{t.rt_diff_ms}} ms</td>
                    <td style="text-align:right; font-weight:700; color:${{t.rt_pct_change > 0 ? 'var(--red)' : 'var(--green)'}};">${{pctSign}}${{t.rt_pct_change}}%</td>
                    <td style="text-align:right;">${{t.p90_a}} ms</td>
                    <td style="text-align:right;">${{t.p90_b}} ms</td>
                    <td style="text-align:right; color:var(--muted);">${{t.target_rt || '-'}} ms</td>
                </tr>
            `;
        }}).join('');
    }}

    function clearReportComparison() {{
        const currentRunId = "{run_id}";
        window.currentComparisonBaselineId = null;
        window.currentComparisonData = null;

        if (compChartExplorer) {{ compChartExplorer.destroy(); compChartExplorer = null; }}
        if (compChartDistribution) {{ compChartDistribution.destroy(); compChartDistribution = null; }}
        if (compChartTpsErrors) {{ compChartTpsErrors.destroy(); compChartTpsErrors = null; }}
        compChartVariance = null;
        compChartTps = null;
        compChartErr = null;

        // Clear LocalStorage draft
        try {{
            localStorage.removeItem('rpt_comp_draft_' + currentRunId);
        }} catch (e) {{}}

        // Clear Server draft
        fetch('/api/comparison/clear-draft', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ current_id: currentRunId }})
        }}).catch(() => {{}});

        hideCompDraftBadge();

        const emptyState = document.getElementById('compare-empty-state');
        const contentContainer = document.getElementById('compare-content-container');
        const clearBtn = document.getElementById('clearCompareBtn');
        const baselineSelect = document.getElementById('compareBaselineSelect');

        if (emptyState) {{ emptyState.style.display = 'block'; }}
        if (contentContainer) {{ contentContainer.style.display = 'none'; }}
        if (clearBtn) {{ clearBtn.style.display = 'none'; }}
        if (baselineSelect) {{ baselineSelect.value = ''; }}
    }}

    // Initialize Comparison on Page Load
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initComparisonTab);
    }} else {{
        initComparisonTab();
    }}
    """
