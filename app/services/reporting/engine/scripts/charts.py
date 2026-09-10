#!/usr/bin/env python3
"""Chart.js charts: hierarchical response times, error donuts, and VU ramp-up profile."""
import json
import re

def get_charts_js(ctx: dict) -> str:
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

    return f"""const txRtHierarchyData = {tx_rt_hierarchy_json};
    let txRtChartPanels = [];
    let nextTxRtPanelId = 1;

    // Metric visual configuration and styling
    const txRtMetricColorMap = {{
        'avg_rt': {{ line: '#6366f1', fill: 'rgba(99, 102, 241, 0.12)', label: 'Average RT (ms)', unit: 'ms' }},
        'p90': {{ line: '#f59e0b', fill: 'rgba(245, 158, 11, 0.12)', label: '90th Percentile (P90) (ms)', unit: 'ms' }},
        'p95': {{ line: '#ef4444', fill: 'rgba(239, 68, 68, 0.12)', label: '95th Percentile (P95) (ms)', unit: 'ms' }},
        'max_rt': {{ line: '#ec4899', fill: 'rgba(236, 72, 153, 0.12)', label: 'Max Response Time (ms)', unit: 'ms' }},
        'min_rt': {{ line: '#10b981', fill: 'rgba(16, 185, 129, 0.12)', label: 'Min Response Time (ms)', unit: 'ms' }},
        'error_rate': {{ line: '#dc2626', fill: 'rgba(220, 38, 38, 0.12)', label: 'Error Rate (%)', unit: '%' }},
        'count': {{ line: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.12)', label: 'Sample Count', unit: 'samples' }}
    }};

    // Custom Data Labels Plugin for Line Points
    const txRtLineLabelsPlugin = {{
        id: 'txRtLineLabelsPlugin',
        afterDatasetsDraw(chart) {{
            const {{ ctx }} = chart;
            ctx.save();
            const isDark = document.documentElement.classList.contains('dark');
            ctx.font = '600 10.5px Inter, sans-serif';
            ctx.fillStyle = isDark ? '#f1f5f9' : '#1f2328';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            chart.data.datasets.forEach((dataset, datasetIndex) => {{
                const meta = chart.getDatasetMeta(datasetIndex);
                if (!meta.hidden) {{
                    meta.data.forEach((element, index) => {{
                        const val = dataset.data[index];
                        if (val !== null && val !== undefined && !isNaN(val)) {{
                            let formatted = '';
                            const metric = chart.config._metricKey || 'avg_rt';
                            if (metric === 'error_rate') {{
                                formatted = Number(val).toFixed(2) + '%';
                            }} else if (metric === 'count') {{
                                formatted = Math.round(val).toLocaleString();
                            }} else {{
                                formatted = Math.round(val).toLocaleString() + ' ms';
                            }}
                            const x = element.x;
                            const y = element.y - 6;
                            ctx.fillText(formatted, x, y);
                        }}
                    }});
                }}
            }});
            ctx.restore();
        }}
    }};

    function addTxRtChartView(initialMetric) {{
        const container = document.getElementById('txRtChartsContainer');
        if (!container) return;

        const panelId = nextTxRtPanelId++;
        const defaultMetric = initialMetric || (txRtChartPanels.length === 1 ? 'p90' : (txRtChartPanels.length === 2 ? 'max_rt' : 'avg_rt'));

        const cardEl = document.createElement('div');
        cardEl.id = `tx-rt-panel-${{panelId}}`;
        cardEl.className = 'glass-panel';
        cardEl.style.cssText = 'background:var(--surface1); border:1px solid var(--border); border-radius:10px; padding:1.25rem; position:relative; width:100%; box-sizing:border-box;';

        const canRemove = txRtChartPanels.length > 0;

        cardEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.6rem; border-bottom:1px solid var(--border); padding-bottom:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:0.3rem;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">User Journey:</label>
                        <select id="txRtUsSelect-${{panelId}}" onchange="onPanelUsChange(${{panelId}}, this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.3rem 0.6rem; border-radius:6px; font-size:0.75rem; font-weight:600; outline:none; cursor:pointer;">
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem; position:relative;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">Transaction:</label>
                        <div id="txRtTxMultiSelectContainer-${{panelId}}"></div>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem;">
                        <label style="font-size:0.75rem; font-weight:700; color:var(--muted); white-space:nowrap;">Metric:</label>
                        <select id="txRtMetricSelect-${{panelId}}" onchange="onPanelMetricChange(${{panelId}}, this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:0.3rem 0.6rem; border-radius:6px; font-size:0.75rem; font-weight:700; outline:none; cursor:pointer;">
                            <option value="avg_rt" ${{defaultMetric === 'avg_rt' ? 'selected' : ''}}>Average RT (ms)</option>
                            <option value="p90" ${{defaultMetric === 'p90' ? 'selected' : ''}}>90th Percentile (P90) (ms)</option>
                            <option value="p95" ${{defaultMetric === 'p95' ? 'selected' : ''}}>95th Percentile (P95) (ms)</option>
                            <option value="max_rt" ${{defaultMetric === 'max_rt' ? 'selected' : ''}}>Max Response Time (ms)</option>
                            <option value="min_rt" ${{defaultMetric === 'min_rt' ? 'selected' : ''}}>Min Response Time (ms)</option>
                            <option value="error_rate" ${{defaultMetric === 'error_rate' ? 'selected' : ''}}>Error Rate (%)</option>
                            <option value="count" ${{defaultMetric === 'count' ? 'selected' : ''}}>Sample Count</option>
                        </select>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button type="button" onclick="duplicateTxRtView(${{panelId}})" title="Capture current filtered view as a frozen snapshot comparison" style="background:var(--surface2); border:1px solid var(--border); color:var(--text); font-size:0.72rem; font-weight:600; padding:0.25rem 0.6rem; border-radius:4px; cursor:pointer; display:inline-flex; align-items:center; gap:0.25rem;">📸 Snapshot</button>
                    ${{canRemove ? `<button type="button" onclick="removeTxRtChartView(${{panelId}})" title="Close this chart view" style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); color:#ef4444; font-size:0.75rem; font-weight:700; padding:0.25rem 0.55rem; border-radius:4px; cursor:pointer;">✕</button>` : ''}}
                </div>
            </div>
            <div id="txRtBreadcrumb-${{panelId}}" style="font-size:0.75rem; font-weight:600; color:var(--muted); margin-bottom:0.5rem; display:flex; align-items:center; gap:0.3rem;">
            </div>
            <div style="position:relative; height:320px; width:100%;">
                <canvas id="chart-tx-rt-canvas-${{panelId}}"></canvas>
            </div>
        `;

        container.appendChild(cardEl);

        const panelObj = {{
            id: panelId,
            us: 'ALL',
            txs: ['ALL'],
            metric: defaultMetric,
            chartObj: null,
            msInstance: null
        }};
        txRtChartPanels.push(panelObj);

        // Populate User Journeys
        const usSelect = document.getElementById(`txRtUsSelect-${{panelId}}`);
        if (usSelect) {{
            usSelect.innerHTML = '<option value="ALL">All User Journeys</option>';
            if (txRtHierarchyData.user_stories) {{
                txRtHierarchyData.user_stories.forEach(us => {{
                    const opt = document.createElement('option');
                    opt.value = us.name;
                    opt.textContent = us.name;
                    usSelect.appendChild(opt);
                }});
            }}
        }}

        // Create Chart.js Line Instance
        const canvas = document.getElementById(`chart-tx-rt-canvas-${{panelId}}`);
        const mInfo = txRtMetricColorMap[defaultMetric] || txRtMetricColorMap['avg_rt'];

        const chartObj = new Chart(canvas, {{
            type: 'line',
            data: {{
                labels: [],
                datasets: [
                    {{
                        label: mInfo.label,
                        data: [],
                        borderColor: mInfo.line,
                        backgroundColor: mInfo.fill,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: mInfo.line,
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                const val = ctx.parsed.y;
                                const curM = panelObj.metric;
                                if (curM === 'error_rate') return `Error Rate: ${{Number(val).toFixed(2)}}%`;
                                if (curM === 'count') return `Count: ${{Math.round(val).toLocaleString()}} samples`;
                                return `${{mInfo.label}}: ${{Math.round(val).toLocaleString()}} ms`;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255,255,255,0.04)' }},
                        ticks: {{
                            color: textColor,
                            font: {{ weight: '600', size: 9.5 }},
                            maxRotation: 25
                        }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        ticks: {{
                            color: textColor,
                            callback: function(val) {{
                                const curM = panelObj.metric;
                                if (curM === 'error_rate') return val + '%';
                                if (curM === 'count') return val.toLocaleString();
                                return val.toLocaleString() + ' ms';
                            }}
                        }},
                        title: {{ display: true, text: mInfo.label, color: textColor }},
                        grace: '18%',
                        beginAtZero: true
                    }}
                }}
            }},
            plugins: [txRtLineLabelsPlugin]
        }});

        chartObj.config._metricKey = defaultMetric;
        panelObj.chartObj = chartObj;

        populatePanelTxDropdown(panelId);
        updatePanelChart(panelId);
    }}

    function populatePanelTxDropdown(panelId) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        const msContainer = document.getElementById(`txRtTxMultiSelectContainer-${{panelId}}`);
        if (!msContainer) return;

        let txList = [];
        if (panel.us === 'ALL') {{
            txList = txRtHierarchyData.all_transactions || [];
        }} else {{
            const foundUs = (txRtHierarchyData.user_stories || []).find(u => u.name === panel.us);
            if (foundUs) txList = foundUs.transactions || [];
        }}

        const msItems = txList.map(t => {{
            const subCount = (t.children || []).length;
            const suffix = subCount > 0 ? ` (${{subCount}} sub-req)` : '';
            return {{
                id: t.name,
                name: t.name,
                shortName: (t.name.length > 25 ? t.name.substring(0, 22) + '...' : t.name) + suffix,
                color: getTxColor(t.name)
            }};
        }});

        const overallLabel = panel.us === 'ALL' ? 'All Transactions (Overview)' : `All in ${{panel.us}}`;

        panel.msInstance = createChartMultiSelect(msContainer, {{
            items: msItems,
            overallLabel: overallLabel,
            initialSelected: panel.txs || ['ALL'],
            maxWidth: '260px',
            placeholder: '🔍 Search transactions...',
            onChange: (selectedIds) => {{
                panel.txs = selectedIds;
                updatePanelChart(panelId);
            }}
        }});
    }}

    function onPanelUsChange(panelId, val) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        panel.us = val;
        panel.txs = ['ALL'];
        populatePanelTxDropdown(panelId);
        updatePanelChart(panelId);
    }}

    function onPanelMetricChange(panelId, val) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel) return;
        panel.metric = val;
        updatePanelChart(panelId);
    }}

    function duplicateActiveOrAddTxRtView() {{
        const activePanel = txRtChartPanels.find(p => !p.isSnapshot) || txRtChartPanels[0];
        if (activePanel) {{
            duplicateTxRtView(activePanel.id);
        }} else {{
            addTxRtChartView('avg_rt');
        }}
    }}

    function duplicateTxRtView(sourcePanelId) {{
        const src = txRtChartPanels.find(p => p.id === sourcePanelId);
        if (!src || !src.chartObj) return;

        const container = document.getElementById('txRtChartsContainer');
        if (!container) return;

        const panelId = nextTxRtPanelId++;
        const mInfo = txRtMetricColorMap[src.metric] || txRtMetricColorMap['avg_rt'];

        let srcUsLabel = src.us === 'ALL' ? 'All User Journeys' : src.us;
        let srcTxLabel = 'All Transactions';
        const selectedTxs = src.txs || ['ALL'];
        if (!selectedTxs.includes('ALL') && selectedTxs.length > 0) {{
            if (selectedTxs.length === 1) {{
                srcTxLabel = selectedTxs[0];
            }} else {{
                srcTxLabel = `${{selectedTxs.length}} Transactions Selected`;
            }}
        }}

        const srcBreadcrumb = document.getElementById(`txRtBreadcrumb-${{sourcePanelId}}`);
        const breadcrumbHtml = srcBreadcrumb ? srcBreadcrumb.innerHTML : '';

        const cardEl = document.createElement('div');
        cardEl.id = `tx-rt-panel-${{panelId}}`;
        cardEl.className = 'glass-panel tx-rt-snapshot-panel';
        cardEl.style.cssText = 'background:var(--surface1); border:1px solid rgba(99,102,241,0.35); border-left:4px solid var(--accent); border-radius:10px; padding:1.25rem; position:relative; width:100%; box-sizing:border-box; box-shadow:0 4px 16px rgba(0,0,0,0.06);';

        cardEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.6rem; border-bottom:1px solid var(--border); padding-bottom:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                    <span style="font-size:0.75rem; font-weight:800; color:var(--accent); background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); padding:0.25rem 0.65rem; border-radius:6px; display:inline-flex; align-items:center; gap:0.35rem;">
                        📸 Snapshot
                    </span>
                    <span style="font-size:0.75rem; font-weight:700; color:var(--text); background:var(--surface2); border:1px solid var(--border); padding:0.25rem 0.55rem; border-radius:6px;">
                        ${{mInfo.label}}
                    </span>
                    <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.25rem 0.55rem; border-radius:6px;">
                        📁 ${{srcUsLabel}}
                    </span>
                    <span style="font-size:0.75rem; font-weight:600; color:var(--muted); background:var(--surface2); border:1px solid var(--border); padding:0.25rem 0.55rem; border-radius:6px;">
                        📊 ${{srcTxLabel}}
                    </span>
                </div>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <button type="button" onclick="removeTxRtChartView(${{panelId}})" title="Close this snapshot comparison" style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); color:#ef4444; font-size:0.75rem; font-weight:700; padding:0.25rem 0.6rem; border-radius:4px; cursor:pointer; display:inline-flex; align-items:center; gap:0.25rem;">✕ Close Snapshot</button>
                </div>
            </div>
            <div id="txRtBreadcrumb-${{panelId}}" style="font-size:0.75rem; font-weight:600; color:var(--muted); margin-bottom:0.5rem; display:flex; align-items:center; gap:0.3rem;">
                ${{breadcrumbHtml}}
            </div>
            <div style="position:relative; height:320px; width:100%;">
                <canvas id="chart-tx-rt-canvas-${{panelId}}"></canvas>
            </div>
        `;

        const srcCard = document.getElementById(`tx-rt-panel-${{sourcePanelId}}`);
        if (srcCard && srcCard.nextSibling) {{
            container.insertBefore(cardEl, srcCard.nextSibling);
        }} else {{
            container.appendChild(cardEl);
        }}

        const srcLabels = [...(src.chartObj.data.labels || [])];
        const srcDatasets = src.chartObj.data.datasets.map(ds => ({{
            label: ds.label,
            data: [...(ds.data || [])],
            borderColor: ds.borderColor,
            backgroundColor: ds.backgroundColor,
            fill: ds.fill !== undefined ? ds.fill : true,
            tension: ds.tension !== undefined ? ds.tension : 0.35,
            borderWidth: ds.borderWidth || 2.5,
            pointRadius: ds.pointRadius || 5,
            pointHoverRadius: ds.pointHoverRadius || 7,
            pointBackgroundColor: ds.pointBackgroundColor || ds.borderColor,
            pointBorderColor: ds.pointBorderColor || '#ffffff',
            pointBorderWidth: ds.pointBorderWidth || 1.5
        }}));

        const canvas = document.getElementById(`chart-tx-rt-canvas-${{panelId}}`);
        const isDark = document.documentElement.classList.contains('dark');
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';
        const textColor = isDark ? '#94a3b8' : '#64748b';

        const chartObj = new Chart(canvas, {{
            type: 'line',
            data: {{
                labels: srcLabels,
                datasets: srcDatasets
            }},
            plugins: [txRtLineLabelsPlugin],
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                        labels: {{
                            color: textColor,
                            font: {{ weight: '600', size: 11 }}
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{
                            color: textColor,
                            font: {{ weight: '600' }}
                        }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        ticks: {{ color: textColor }},
                        title: {{
                            display: true,
                            text: mInfo.label,
                            color: textColor
                        }}
                    }}
                }}
            }}
        }});
        chartObj.config._metricKey = src.metric;

        const panelObj = {{
            id: panelId,
            isSnapshot: true,
            sourceId: sourcePanelId,
            us: src.us,
            txs: [...src.txs],
            metric: src.metric,
            chartObj: chartObj,
            msInstance: null
        }};
        txRtChartPanels.push(panelObj);
    }}

    function removeTxRtChartView(panelId) {{
        const idx = txRtChartPanels.findIndex(p => p.id === panelId);
        if (idx === -1) return;
        const panel = txRtChartPanels[idx];
        if (panel.chartObj) {{
            panel.chartObj.destroy();
        }}
        txRtChartPanels.splice(idx, 1);
        const card = document.getElementById(`tx-rt-panel-${{panelId}}`);
        if (card) card.remove();
    }}

    function updatePanelChart(panelId) {{
        const panel = txRtChartPanels.find(p => p.id === panelId);
        if (!panel || !panel.chartObj || panel.isSnapshot) return;

        const breadcrumbEl = document.getElementById(`txRtBreadcrumb-${{panelId}}`);
        let items = [];
        const selectedTxs = panel.txs || ['ALL'];
        const isAll = selectedTxs.length === 0 || selectedTxs.includes('ALL');

        if (!isAll) {{
            if (selectedTxs.length === 1) {{
                const targetTxName = selectedTxs[0];
                let targetTx = null;
                if (txRtHierarchyData.all_transactions) {{
                    targetTx = txRtHierarchyData.all_transactions.find(t => t.name === targetTxName);
                }}
                if (!targetTx && txRtHierarchyData.user_stories) {{
                    for (const us of txRtHierarchyData.user_stories) {{
                        const found = (us.transactions || []).find(t => t.name === targetTxName);
                        if (found) {{ targetTx = found; break; }}
                    }}
                }}

                if (targetTx && targetTx.children && targetTx.children.length > 0) {{
                    items = targetTx.children;
                    if (breadcrumbEl) {{
                        breadcrumbEl.innerHTML = `<span>Context:</span> <span style="color:var(--text);">${{panel.us === 'ALL' ? 'All Stories' : panel.us}}</span> &rarr; <span style="color:var(--accent); font-weight:700;">📂 ${{targetTx.name}}</span> &rarr; <span style="color:var(--text); font-weight:700;">🔍 ${{items.length}} Child Requests</span>`;
                    }}
                }} else if (targetTx) {{
                    items = [targetTx];
                    if (breadcrumbEl) {{
                        breadcrumbEl.innerHTML = `<span>Context:</span> <span style="color:var(--text);">${{panel.us === 'ALL' ? 'All Stories' : panel.us}}</span> &rarr; <span style="color:var(--accent); font-weight:700;">📂 ${{targetTx.name}}</span>`;
                    }}
                }}
            }} else {{
                // Multiple specific transactions selected
                const foundItems = [];
                selectedTxs.forEach(txName => {{
                    let targetTx = null;
                    if (txRtHierarchyData.all_transactions) {{
                        targetTx = txRtHierarchyData.all_transactions.find(t => t.name === txName);
                    }}
                    if (!targetTx && txRtHierarchyData.user_stories) {{
                        for (const us of txRtHierarchyData.user_stories) {{
                            const found = (us.transactions || []).find(t => t.name === txName);
                            if (found) {{ targetTx = found; break; }}
                        }}
                    }}
                    if (targetTx) foundItems.push(targetTx);
                }});
                items = foundItems;
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Showing:</span> <span style="color:var(--accent); font-weight:700;">📁 ${{panel.us === 'ALL' ? 'All Stories' : panel.us}}</span> &rarr; <span style="color:var(--text); font-weight:700;">${{items.length}} Selected Transactions</span>`;
                }}
            }}
        }} else {{
            if (panel.us === 'ALL') {{
                items = txRtHierarchyData.all_transactions || [];
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Showing:</span> <span style="color:var(--accent); font-weight:700;">🌐 All User Journeys</span> &rarr; <span style="color:var(--text); font-weight:700;">${{items.length}} Main Transactions</span>`;
                }}
            }} else {{
                const foundUs = (txRtHierarchyData.user_stories || []).find(u => u.name === panel.us);
                items = foundUs ? (foundUs.transactions || []) : [];
                if (breadcrumbEl) {{
                    breadcrumbEl.innerHTML = `<span>Showing:</span> <span style="color:var(--accent); font-weight:700;">📁 ${{panel.us}}</span> &rarr; <span style="color:var(--text); font-weight:700;">${{items.length}} Transactions</span>`;
                }}
            }}
        }}

        const labels = items.map(item => item.name.length > 28 ? item.name.substring(0, 25) + '...' : item.name);
        const dataValues = items.map(item => {{
            const v = item[panel.metric];
            return v !== undefined && v !== null ? v : 0;
        }});

        const mInfo = txRtMetricColorMap[panel.metric] || txRtMetricColorMap['avg_rt'];

        panel.chartObj.config._metricKey = panel.metric;
        panel.chartObj.data.labels = labels;
        panel.chartObj.data.datasets[0].label = mInfo.label;
        panel.chartObj.data.datasets[0].data = dataValues;
        panel.chartObj.data.datasets[0].borderColor = mInfo.line;
        panel.chartObj.data.datasets[0].backgroundColor = mInfo.fill;
        panel.chartObj.data.datasets[0].pointBackgroundColor = mInfo.line;
        panel.chartObj.options.scales.y.title.text = mInfo.label;

        panel.chartObj.update('active');
    }}

    // Initialize primary line chart view
    addTxRtChartView('avg_rt');

    // SLA Deviation by Transaction Diverging Horizontal Bar Chart
    const tgToTcsMap = {tg_to_tcs_json};
    const txDevMap = {tx_dev_map_json};
    const initialDevLabels = {deviation_chart_labels_json};
    const initialDevVals = {deviation_chart_values_json};

    function getSlaDevColor(val) {{
        if (val > 100) return {{ bg: '#ef4444', border: '#dc2626' }}; // Red (> 100% breach)
        if (val > 50)  return {{ bg: '#f97316', border: '#ea580c' }}; // Amber (50% - 100% breach)
        if (val > 0)   return {{ bg: '#eab308', border: '#ca8a04' }}; // Yellow (0% - 50% breach)
        return {{ bg: '#10b981', border: '#059669' }};                // Green (<= 0% met target)
    }}

    const initialDevColors = initialDevVals.map(getSlaDevColor);

    const slaDevChartObj = new Chart(document.getElementById('chart-sla-deviation-exec'), {{
        type: 'bar',
        data: {{
            labels: initialDevLabels,
            datasets: [
                {{
                    label: 'SLA Deviation (%)',
                    data: initialDevVals,
                    backgroundColor: initialDevColors.map(c => c.bg),
                    borderColor: initialDevColors.map(c => c.border),
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.65
                }}
            ]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{
                            const val = ctx.parsed.x;
                            const status = val > 100 ? ' (Critical Breach)' : (val > 50 ? ' (Significant Breach)' : (val > 0 ? ' (Minor Breach)' : ' (Met SLA)'));
                            return (val > 0 ? '+' : '') + val + '% deviation from SLA' + status;
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ color: gridColor }},
                    ticks: {{
                        color: textColor,
                        callback: function(val) {{ return (val > 0 ? '+' : '') + val + '%'; }}
                    }},
                    title: {{ display: true, text: 'Deviation from SLA Limit (%)', color: textColor }}
                }},
                y: {{
                    grid: {{ display: false }},
                    ticks: {{ color: textColor, font: {{ weight: '600', size: 11 }} }}
                }}
            }}
        }}
    }});

    function filterSlaDevByUs(selectedUs) {{
        if (!slaDevChartObj) return;

        const selectedList = Array.isArray(selectedUs) ? selectedUs : [selectedUs];
        let filteredItems = [];

        if (selectedList.includes('ALL') || selectedList.length === 0) {{
            // Show all transactions sorted by worst deviation %
            filteredItems = Object.values(txDevMap);
        }} else {{
            // Filter to child transactions belonging to the selected User Journeys
            const allAllowedTcs = new Set();
            selectedList.forEach(us => {{
                const childTcs = tgToTcsMap[us] || [];
                childTcs.forEach(tc => allAllowedTcs.add(tc));
            }});
            filteredItems = Object.values(txDevMap).filter(item => allAllowedTcs.has(item.label));
        }}

        filteredItems.sort((a, b) => b.dev_pct - a.dev_pct);

        const newLabels = filteredItems.map(item => item.label.length > 35 ? item.label.substring(0, 32) + '...' : item.label);
        const newVals   = filteredItems.map(item => item.dev_pct);
        const newColors = newVals.map(getSlaDevColor);

        slaDevChartObj.data.labels = newLabels;
        slaDevChartObj.data.datasets[0].data = newVals;
        slaDevChartObj.data.datasets[0].backgroundColor = newColors.map(c => c.bg);
        slaDevChartObj.data.datasets[0].borderColor = newColors.map(c => c.border);
        slaDevChartObj.update('active');
    }}

    // Mount SLA Deviation User Journey multi-select widget
    const usDevOptionsData = {us_options_json};
    const usDevMs = createChartMultiSelect('usDevMultiSelectContainer', {{
        items: usDevOptionsData,
        overallLabel: 'All User Journeys',
        initialSelected: ['ALL'],
        maxWidth: '280px',
        placeholder: '🔍 Search user journeys...',
        onChange: (selectedIds) => {{
            filterSlaDevByUs(selectedIds);
        }}
    }});

    // Chart.js Data Labels Plugin to draw exact sample counts on top of bars
    const txSummaryDataLabelsPlugin = {{
        id: 'txSummaryDataLabelsPlugin',
        afterDatasetsDraw(chart) {{
            const {{ ctx }} = chart;
            ctx.save();
            const isDark = document.documentElement.classList.contains('dark');
            ctx.font = '700 11px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            chart.data.datasets.forEach((dataset, datasetIndex) => {{
                const meta = chart.getDatasetMeta(datasetIndex);
                if (!meta.hidden) {{
                    meta.data.forEach((element, index) => {{
                        const val = dataset.data[index];
                        if (val !== null && val !== undefined && !isNaN(val)) {{
                            if (datasetIndex === 1 && val === 0) return; // Don't draw 0 for Fail
                            const formatted = val.toLocaleString();
                            const x = element.x;
                            const y = element.y - 4;
                            ctx.fillStyle = datasetIndex === 0 
                                ? (isDark ? '#34d399' : '#059669') 
                                : '#ef4444';
                            ctx.fillText(formatted, x, y);
                        }}
                    }});
                }}
            }});
            ctx.restore();
        }}
    }};

    // Transaction Summary Grouped Bar Chart (Pass vs Fail with Numbers on Bars)
    const txSummaryCanvasEl = document.getElementById('chart-tx-summary-bar');
    if (txSummaryCanvasEl) {{
        new Chart(txSummaryCanvasEl, {{
            type: 'bar',
            data: {{
                labels: {tx_chart_labels_json},
                datasets: [
                    {{
                        label: 'Pass Samples',
                        data: {tx_chart_pass_json},
                        backgroundColor: 'rgba(16, 185, 129, 0.85)',
                        borderColor: '#059669',
                        borderWidth: 1.5,
                        borderRadius: 5,
                        barPercentage: 0.62,
                        categoryPercentage: 0.65
                    }},
                    {{
                        label: 'Fail Samples',
                        data: {tx_chart_fail_json},
                        backgroundColor: 'rgba(239, 68, 68, 0.85)',
                        borderColor: '#dc2626',
                        borderWidth: 1.5,
                        borderRadius: 5,
                        barPercentage: 0.62,
                        categoryPercentage: 0.65
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                layout: {{
                    padding: {{
                        top: 25,
                        bottom: 5
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{ weight: '700', size: 12 }},
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 16,
                            color: textColor
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        padding: 10,
                        callbacks: {{
                            label: function(ctx) {{
                                const label = ctx.dataset.label || '';
                                const val = ctx.raw || 0;
                                const chart = ctx.chart;
                                const pass = chart.data.datasets[0].data[ctx.dataIndex] || 0;
                                const fail = (chart.data.datasets[1] && chart.data.datasets[1].data[ctx.dataIndex]) || 0;
                                const total = pass + fail;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0';
                                return `${{label}}: ${{val.toLocaleString()}} (${{pct}}%)`;
                            }},
                            footer: function(tooltipItems) {{
                                if (tooltipItems.length > 0) {{
                                    const idx = tooltipItems[0].dataIndex;
                                    const chart = tooltipItems[0].chart;
                                    const pass = chart.data.datasets[0].data[idx] || 0;
                                    const fail = (chart.data.datasets[1] && chart.data.datasets[1].data[idx]) || 0;
                                    const total = pass + fail;
                                    const errRate = total > 0 ? ((fail / total) * 100).toFixed(2) : '0.00';
                                    return `Total: ${{total.toLocaleString()}} samples | Error Rate: ${{errRate}}%`;
                                }}
                                return '';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ maxRotation: 25, font: {{ weight: '600', size: 11 }}, color: textColor }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        beginAtZero: true,
                        grace: '12%',
                        ticks: {{
                            color: textColor,
                            callback: function(val) {{ return val.toLocaleString(); }}
                        }},
                        title: {{ display: true, text: 'Sample Count', color: textColor, font: {{ weight: '700' }} }}
                    }}
                }}
            }},
            plugins: [txSummaryDataLabelsPlugin]
        }});
    }}



    new Chart(document.getElementById('chart-infra-exec'), {{
        type: 'line',
        data: {{
            labels: {ts_labels},
            datasets: [
                {{ label: 'CPU %', data: {ts_cpu}, borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'Memory %', data: {ts_memory}, borderColor: '#3b82f6', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2 }}
            ]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ grid: {{ color: gridColor }}, min: 0, max: 100 }}, x: {{ grid: {{ display: false }} }} }} }}
    }});

    // ── Charts & Analytics Tab ─────────────────────────────────────────────────
    // 1. SLA Deviation & Severity Donut Chart
    new Chart(document.getElementById('slaDonut'), {{
        type: 'doughnut',
        data: {{
            labels: ['Passed', 'Minor Breach', 'Moderate Breach', 'Critical Breach'],
            datasets: [{{
                data: [{tx_under_sla}, {sla_minor_count}, {sla_mod_count}, {sla_crit_count}],
                backgroundColor: [
                    '#10b981',  // Passed - Emerald Green
                    '#f59e0b',  // Minor - Amber
                    '#f97316',  // Moderate - Orange
                    '#ef4444'   // Critical - Red
                ],
                borderColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
                borderWidth: 1,
                hoverOffset: 4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            cutout: '76%',
            plugins: {{
                legend: {{ display: false }}
            }}
        }}
    }});

    // 3. Error Rate by Transaction (horizontal bar)
    if ({err_labels_json}.length > 0) {{
        new Chart(document.getElementById('errChart'), {{
            type: 'bar',
            data: {{
                labels: {err_labels_json},
                datasets: [{{
                    label: 'Error Rate (%)',
                    data: {err_rates_json},
                    backgroundColor: 'rgba(239,68,68,0.75)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }}, title: {{ display: true, text: '%', color: textColor }} }},
                    y: {{ grid: {{ display: false }}, ticks: {{ color: textColor, font: {{ size: 10 }} }} }}
                }}
            }}
        }});
    }} else {{
        const errEl = document.getElementById('errChart');
        if (errEl) {{ errEl.parentElement.innerHTML += '<p style="color:var(--green);text-align:center;margin-top:2rem;">✅ No transactions with errors</p>'; errEl.style.display='none'; }}
    }}

    // ── Error Distribution Donut / Pie Charts (Executive Summary & Error Tab) ──
    const errDonutLabels = {error_donut_labels};
    const errDonutCounts = {error_donut_counts};
    const errDrillData = {error_drill_json};
    const errDonutColors = ['#ef4444','#f97316','#f59e0b','#8b5cf6','#3b82f6','#06b6d4','#10b981','#ec4899','#84cc16','#64748b'];
    const startEpochMs = {start_epoch_ms};
    const displayTotalErrors = {display_total_errors};

    function initErrorDonutInstances() {{
        const configs = [
            {{ canvasId: 'chart-errors-exec', legendId: 'execErrorDonutLegend', contentId: 'execErrorContent' }},
            {{ canvasId: 'errorDonutChart', legendId: 'errorDonutLegend', contentId: null }}
        ];

        configs.forEach(cfg => {{
            const canvasEl = document.getElementById(cfg.canvasId);
            if (!canvasEl) return;

            if (errDonutLabels.length > 0) {{
                new Chart(canvasEl, {{
                    type: 'doughnut',
                    data: {{
                        labels: errDonutLabels,
                        datasets: [{{
                            data: errDonutCounts,
                            backgroundColor: errDonutColors.slice(0, errDonutLabels.length),
                            borderColor: errDonutColors.slice(0, errDonutLabels.length).map(c => c + '88'),
                            borderWidth: 2,
                            hoverOffset: 8,
                            hoverBorderWidth: 3
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '68%',
                        plugins: {{
                            legend: {{ display: false }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(ctx) {{
                                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                        const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : '0';
                                        return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
                                    }}
                                }}
                            }}
                        }},
                        onClick: function(evt, elements) {{
                            if (elements.length > 0) {{
                                const idx = elements[0].index;
                                const errorKey = errDonutLabels[idx];
                                showErrorDrillDown(errorKey, errDonutColors[idx % errDonutColors.length]);
                            }}
                        }}
                    }}
                }});

                // Build custom legend
                const legendEl = document.getElementById(cfg.legendId);
                if (legendEl) {{
                    legendEl.innerHTML = '';
                    const totalAll = errDonutCounts.reduce((a, b) => a + b, 0);
                    errDonutLabels.forEach((label, i) => {{
                        const pct = totalAll > 0 ? ((errDonutCounts[i] / totalAll) * 100).toFixed(1) : '0';
                        const color = errDonutColors[i % errDonutColors.length];
                        const item = document.createElement('div');
                        item.style.cssText = 'display:flex; align-items:center; gap:0.4rem; cursor:pointer; padding:0.15rem 0; transition:opacity 0.15s;';
                        item.innerHTML = `<span style="width:10px; height:10px; border-radius:50%; background:${{color}}; flex-shrink:0;"></span><span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{label}}">${{label.length > 28 ? label.substring(0,25)+'...' : label}}</span><span style="margin-left:auto; font-weight:700; color:${{color}}; flex-shrink:0;">${{errDonutCounts[i]}}</span>`;
                        item.onclick = () => showErrorDrillDown(label, color);
                        item.onmouseenter = () => {{ item.style.opacity = '0.7'; }};
                        item.onmouseleave = () => {{ item.style.opacity = '1'; }};
                        legendEl.appendChild(item);
                    }});
                }}
            }} else if (displayTotalErrors > 0) {{
                // Legacy fallback
                const parent = cfg.contentId ? document.getElementById(cfg.contentId) : canvasEl.parentElement.parentElement;
                if (parent) {{
                    parent.innerHTML = `
                        <div style="text-align:center; padding:2rem 1rem; color:var(--muted);">
                            <div style="font-size:2.5rem; margin-bottom:0.5rem; opacity:0.7;">⚠️</div>
                            <div style="font-size:1.1rem; font-weight:700; color:var(--text);">${{displayTotalErrors}} Errors Detected</div>
                            <div style="font-size:0.82rem; margin-top:0.3rem;">Granular error distribution is not available for this run.<br>Please re-execute the test to capture detailed error analytics.</div>
                        </div>`;
                }}
            }} else {{
                // Zero errors success state
                const parent = cfg.contentId ? document.getElementById(cfg.contentId) : canvasEl.parentElement.parentElement;
                if (parent) {{
                    parent.innerHTML = `
                        <div style="text-align:center; padding:2rem 1rem; color:var(--muted);">
                            <div style="font-size:2.5rem; margin-bottom:0.5rem;">✅</div>
                            <div style="font-size:1.1rem; font-weight:700; color:#10b981;">Zero Errors Detected</div>
                            <div style="font-size:0.82rem; color:var(--muted); margin-top:0.3rem;">All requests completed successfully during this test execution.</div>
                        </div>`;
                }}
            }}
        }});
    }}

    initErrorDonutInstances();

    function showErrorDrillDown(errorKey, accentColor) {{
        const panels = [document.getElementById('errorDrillPanel'), document.getElementById('execErrorDrillPanel')].filter(Boolean);
        if (panels.length === 0) return;
        const data = errDrillData[errorKey];
        if (!data) {{ panels.forEach(p => p.innerHTML = '<p style="color:var(--muted); text-align:center;">No drill-down data available for this error.</p>'); return; }}

        const txEntries = Object.entries(data.transactions || {{}});
        const failureNote = data.failure_message ? `<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:6px; padding:0.5rem 0.75rem; margin-bottom:0.75rem; font-size:0.78rem; color:#ef4444; word-break:break-word;">⚠️ <strong>Assertion/Failure:</strong> ${{data.failure_message}}</div>` : '';

        let txTableRows = '';
        txEntries.forEach(([txName, info]) => {{
            const firstTime = info.first_ts && startEpochMs ? new Date(info.first_ts).toLocaleTimeString() : '-';
            const lastTime = info.last_ts && startEpochMs ? new Date(info.last_ts).toLocaleTimeString() : '-';
            txTableRows += `
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:0.4rem 0.5rem; font-weight:600; font-size:0.78rem; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{txName}}">${{txName.length > 35 ? txName.substring(0,32)+'...' : txName}}</td>
                    <td style="padding:0.4rem; text-align:center; font-weight:700; color:${{accentColor}};">${{info.count}}</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.avg_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.min_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center;">${{info.max_rt}} ms</td>
                    <td style="padding:0.4rem; text-align:center; font-size:0.75rem; color:var(--muted);">${{firstTime}}</td>
                    <td style="padding:0.4rem; text-align:center; font-size:0.75rem; color:var(--muted);">${{lastTime}}</td>
                </tr>`;
        }});

        panels.forEach(panel => {{
            panel.style.display = 'block';
            panel.style.alignItems = 'stretch';
            panel.style.justifyContent = 'flex-start';
            panel.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; gap:0.5rem;">
                    <div style="display:flex; align-items:center; gap:0.5rem; min-width:0;">
                        <span style="width:12px; height:12px; border-radius:50%; background:${{accentColor}}; flex-shrink:0;"></span>
                        <strong style="font-size:0.9rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{errorKey}}">${{errorKey}}</strong>
                    </div>
                    <span style="font-size:0.78rem; font-weight:700; background:${{accentColor}}18; border:1px solid ${{accentColor}}44; padding:0.2rem 0.6rem; border-radius:10px; color:${{accentColor}}; flex-shrink:0;">${{data.total}} occurrences</span>
                </div>
                ${{failureNote}}
                <div style="font-size:0.78rem; color:var(--muted); margin-bottom:0.5rem;">
                    ${{data.code ? '<strong>HTTP Code:</strong> ' + data.code + ' &nbsp;|&nbsp; ' : ''}}<strong>Affected Requests:</strong> ${{txEntries.length}}
                </div>
                <div style="overflow-x:auto; border-radius:6px; border:1px solid var(--border);">
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                        <thead>
                            <tr style="background:var(--bg); border-bottom:2px solid var(--border);">
                                <th style="padding:0.45rem 0.5rem; text-align:left; font-weight:700; font-size:0.75rem; color:var(--muted);">Request / Sampler</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Errors</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Avg RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Min RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Max RT</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">First</th>
                                <th style="padding:0.45rem; text-align:center; font-weight:700; font-size:0.75rem; color:var(--muted);">Last</th>
                            </tr>
                        </thead>
                        <tbody>${{txTableRows}}</tbody>
                    </table>
                </div>
            `;
        }});
    }}

    // ── Load & Capacity: Virtual User Ramp-Up & Workload Profile Stepped Chart ──
    const vuRampLabels = {vu_ramp_labels_json};
    const vuRampData = {vu_ramp_data_json};
    const elVuRamp = document.getElementById('chartVuRampUp');
    if (elVuRamp && vuRampLabels.length > 0) {{
        new Chart(elVuRamp, {{
            type: 'line',
            data: {{
                labels: vuRampLabels,
                datasets: [
                    {{
                        label: 'Active Virtual Users (VUs)',
                        data: vuRampData,
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.18)',
                        borderWidth: 2.5,
                        fill: true,
                        stepped: false,
                        tension: 0,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#38bdf8',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                        align: 'center',
                        labels: {{
                            color: textColor,
                            font: {{ weight: '700', size: 12 }},
                            usePointStyle: false,
                            boxWidth: 24,
                            boxHeight: 12
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        callbacks: {{
                            label: function(ctx) {{
                                return 'Active Concurrency: ' + ctx.raw + ' VUs';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: gridColor }},
                        ticks: {{ color: textColor, font: {{ weight: '600', size: 10.5 }} }},
                        title: {{ display: true, text: 'Elapsed Test Time (HH:MM:SS / MM:SS)', color: textColor, font: {{ weight: '700' }} }}
                    }},
                    y: {{
                        grid: {{ color: gridColor }},
                        beginAtZero: true,
                        ticks: {{
                            color: textColor,
                            stepSize: 1,
                            callback: function(val) {{ return val + ' VU'; }}
                        }},
                        title: {{ display: true, text: 'Virtual Users (VUs)', color: textColor, font: {{ weight: '700' }} }}
                    }}
                }}
            }}
        }});
    }}



    // Azure Infrastructure Diagnostic Suite Charts
    const azCpu = {ts_cpu};
    const azMem = {ts_memory};
    const azDiskQ = {ts_disk_q_json};
    const azDiskRead = {ts_disk_read_json};
    const azDiskWrite = {ts_disk_write_json};
    const azNetIn = {ts_net_in_json};
    const azNetOut = {ts_net_out_json};

    if (azCpu.length > 0) {{
        // 1. CPU & Memory Utilization (Full Width)
        new Chart(document.getElementById('azChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'CPU %', data: azCpu, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.12)', borderWidth: 2.5, fill: true, tension: 0.3, pointRadius: 3 }},
                    {{ label: 'Memory %', data: azMem, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.12)', borderWidth: 2.5, fill: true, tension: 0.3, pointRadius: 3 }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ min: 0, max: 100, grid: {{ color: gridColor }}, title: {{ display: true, text: '%' }} }}, x: {{ grid: {{ display: false }} }} }} }}
        }});

        // 2. Workload vs CPU Utilization
        new Chart(document.getElementById('workloadCpuChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Throughput (req/s)', data: overallTs.throughput.slice(0, azCpu.length), borderColor: '#6366f1', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'CPU %', data: azCpu, borderColor: '#ef4444', borderWidth: 2, borderDash: [4,4], fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'req/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', min: 0, max: 100, title: {{ display: true, text: 'CPU %' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 3. Throughput vs Response Time
        new Chart(document.getElementById('tpRtChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Throughput (req/s)', data: overallTs.throughput.slice(0, azCpu.length), borderColor: '#10b981', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'Avg RT (ms)', data: overallTs.avg_rt.slice(0, azCpu.length), borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'req/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Avg RT (ms)' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 4. Disk I/O & Queue Depth
        new Chart(document.getElementById('diskChart'), {{
            type: 'bar',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ type: 'bar', label: 'Disk Read (MB/s)', data: azDiskRead, backgroundColor: 'rgba(59,130,246,0.6)', yAxisID: 'y' }},
                    {{ type: 'bar', label: 'Disk Write (MB/s)', data: azDiskWrite, backgroundColor: 'rgba(16,185,129,0.6)', yAxisID: 'y' }},
                    {{ type: 'line', label: 'Queue Depth', data: azDiskQ, borderColor: '#ef4444', borderWidth: 2, fill: false, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'MB/s' }}, grid: {{ color: gridColor }} }},
                    y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Queue Depth' }}, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // 5. Network Throughput
        new Chart(document.getElementById('netChart'), {{
            type: 'line',
            data: {{
                labels: {ts_labels}.slice(0, azCpu.length),
                datasets: [
                    {{ label: 'Network In (MB)', data: azNetIn, borderColor: '#06b6d4', backgroundColor: 'rgba(6,182,212,0.12)', borderWidth: 2, fill: true, tension: 0.3 }},
                    {{ label: 'Network Out (MB)', data: azNetOut, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.12)', borderWidth: 2, fill: true, tension: 0.3 }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                scales: {{
                    y: {{ grid: {{ color: gridColor }}, title: {{ display: true, text: 'MB' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    }}
    }} else {{
        console.warn("Chart.js library is not available. Connect to the internet or ensure CDN scripts are permitted to render charts.");
        document.querySelectorAll('canvas').forEach(c => {{
            const p = c.parentElement;
            if (p && !p.querySelector('.chart-fallback-msg')) {{
                const msg = document.createElement('div');
                msg.className = 'chart-fallback-msg';
                msg.style.cssText = 'text-align:center; padding:2rem 1rem; color:var(--muted); font-size:0.85rem;';
                msg.innerHTML = '<div style="font-size:1.5rem; margin-bottom:0.4rem;">📊</div><div>Chart library (Chart.js) is not available.<br>Please connect to the internet or allow external CDN scripts to view interactive charts.</div>';
                p.appendChild(msg);
            }}
        }});
    }}
    
    // ── Edit Mode Logic ──
    let editMode = false;
    function toggleEditMode() {{
        editMode = !editMode;
        document.body.classList.toggle('edit-mode-active', editMode);
        const editBtn = document.getElementById('editBtn');
        if (editBtn) editBtn.innerText = editMode ? '💾 Save Edits' : '✏️ Edit Report';
        const badge = document.getElementById('editModeBadge');
        if (badge) badge.style.display = editMode ? 'inline-block' : 'none';
        
        document.querySelectorAll('[data-editable]').forEach(el => {{
            el.setAttribute('contenteditable', editMode ? 'true' : 'false');
        }});
    }}
    
    // ── Human Validation Persistence Logic ──
    const reportRunId = "{run_id}";
    function toggleAiValidation(checkbox, valId) {{
        const isChecked = checkbox.checked;
        const label = document.getElementById('val_lbl_' + valId) || checkbox.closest('.human-val-label');
        const textSpan = label ? label.querySelector('.human-val-text') : null;
        const card = checkbox.closest('.ai-sub-card, .glass-panel, .rec-card, .section');

        if (label) {{
            if (isChecked) {{
                label.classList.add('validated');
                if (textSpan) textSpan.textContent = 'Validated by Performance Engineer';
            }} else {{
                label.classList.remove('validated');
                if (textSpan) textSpan.textContent = 'Validate as Performance Engineer';
            }}
        }}
        if (card) {{
            if (isChecked) card.classList.add('card-validated');
            else card.classList.remove('card-validated');
        }}

        // If major container is checked, propagate to direct sub-validations
        if (valId === 'major_ai_augmented' && isChecked) {{
            document.querySelectorAll('.ai-augmented-section .human-val-checkbox').forEach(c => {{
                if (c !== checkbox && !c.checked) {{
                    c.checked = true;
                    const subValId = c.getAttribute('data-val-id');
                    if (subValId) toggleAiValidation(c, subValId);
                }}
            }});
        }}

        try {{
            const key = 'pe_val_' + reportRunId + '_' + valId;
            if (isChecked) {{
                localStorage.setItem(key, JSON.stringify({{ validated: true, timestamp: new Date().toISOString() }}));
            }} else {{
                localStorage.removeItem(key);
            }}
        }} catch (e) {{
            console.warn('LocalStorage error saving validation status:', e);
        }}
    }}

    function initHumanValidations() {{
        document.querySelectorAll('.human-val-checkbox').forEach(cb => {{
            const valId = cb.getAttribute('data-val-id');
            if (!valId) return;
            try {{
                const key = 'pe_val_' + reportRunId + '_' + valId;
                const saved = localStorage.getItem(key);
                if (saved) {{
                    const parsed = JSON.parse(saved);
                    if (parsed && parsed.validated) {{
                        cb.checked = true;
                        cb.setAttribute('checked', 'checked');
                        toggleAiValidation(cb, valId);
                    }}
                }}
            }} catch (e) {{}}
        }});
    }}

    // ── Contextual Section-Level AI Chat State & Methods ──
    const initialAiChatHistory = {ai_chat_history_json};
    const aiChatHistories = Object.assign({{}}, initialAiChatHistory || {{}});
    const pendingPatches = {{}};

    function toggleAiChat(sectionId) {{
        const drawer = document.getElementById('aiChatDrawer_' + sectionId);
        if (!drawer) return;
        
        const isOpening = !drawer.classList.contains('open');
        if (isOpening) {{
            // Close any other open drawers
            document.querySelectorAll('.ai-chat-drawer.open').forEach(d => {{
                if (d !== drawer) d.classList.remove('open');
            }});
            drawer.classList.add('open');
            renderChatMessages(sectionId);
            setTimeout(() => {{
                const input = document.getElementById('aiChatInput_' + sectionId);
                if (input) input.focus();
            }}, 150);
        }} else {{
            drawer.classList.remove('open');
            if (drawer.classList.contains('expanded')) {{
                drawer.classList.remove('expanded');
                const maxBtn = document.getElementById('aiChatMaxBtn_' + sectionId);
                if (maxBtn) {{
                    maxBtn.innerHTML = '⛶';
                    maxBtn.title = 'Maximize Chat Window';
                }}
            }}
        }}
    }}

    function toggleAiChatMaximize(sectionId) {{
        const drawer = document.getElementById('aiChatDrawer_' + sectionId);
        if (!drawer) return;
        const maxBtn = document.getElementById('aiChatMaxBtn_' + sectionId);
        const isExp = drawer.classList.toggle('expanded');
        if (maxBtn) {{
            maxBtn.innerHTML = isExp ? '❐' : '⛶';
            maxBtn.title = isExp ? 'Restore Window Size' : 'Maximize Chat Window';
        }}
    }}

    function handleAiChatKey(event, sectionId) {{
        if (event.key === 'Enter' && !event.shiftKey) {{
            event.preventDefault();
            sendAiChatMessage(sectionId);
        }}
    }}

    function escapeHtmlText(text) {{
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }}

    function formatAiReply(text) {{
        if (!text) return '';
        let s = escapeHtmlText(text);
        s = s.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
        s = s.replace(/\\*(.*?)\\*/g, '<em>$1</em>');
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        s = s.replace(/\\n\\n/g, '<br/><br/>');
        s = s.replace(/\\n- /g, '<br/>• ');
        s = s.replace(/\\n/g, '<br/>');
        return s;
    }}

    function parseAiReplyWithPatch(text, sectionId, msgIndex) {{
        if (!text) return {{ html: '', patch: null }};
        
        let rawText = text;
        let patchData = null;

        // 1. Check for markdown fence ```action:patch_section or ```json
        let startIdx = rawText.indexOf('```action:patch_section');
        if (startIdx === -1) startIdx = rawText.indexOf('```json');
        if (startIdx !== -1) {{
            const endIdx = rawText.indexOf('```', startIdx + 3);
            if (endIdx !== -1) {{
                const block = rawText.substring(startIdx, endIdx + 3);
                const jsonText = block.replace(/^```[a-zA-Z0-9_:-]*/, '').replace(/```$/, '').trim();
                if (jsonText.includes('"section_id"') || jsonText.includes('"content"')) {{
                    try {{
                        const parsed = JSON.parse(jsonText);
                        if (parsed && (parsed.section_id || parsed.content)) {{
                            patchData = parsed;
                            if (!patchData.section_id) patchData.section_id = sectionId;
                            rawText = rawText.replace(block, '').trim();
                        }}
                    }} catch (e) {{
                        console.warn('Could not parse action:patch_section JSON:', e);
                    }}
                }}
            }}
        }}

        // 2. Check for tool-call format:
        // 2. Check for tool-call format:
        //    <|tool_call_start|>[action(action='patch_section', template='{...}')]<|tool_call_end|>
        //    or [patch_section(section_id='...', content=...)]
        if (!patchData) {{
            const toolRegex = /(?:<\\|tool_call_start\\|>)?\\s*\\[(?:action|patch_section)\\s*\\([\\s\\S]*?\\)\\]\\s*(?:<\\|tool_call_end\\|>)?|<\\|tool_call_start\\|>[\\s\\S]*?<\\|tool_call_end\\|>/i;
            const match = rawText.match(toolRegex);
            if (match) {{
                const toolBlock = match[0];
                let jsonStr = null;
                const tmSingle = toolBlock.match(/template\\s*=\\s*'([\\s\\S]*?)'(?:\\s*,|\\s*\\))/);
                const tmDouble = toolBlock.match(/template\\s*=\\s*"([\\s\\S]*?)"(?:\\s*,|\\s*\\))/);
                if (tmSingle) {{
                    jsonStr = tmSingle[1];
                }} else if (tmDouble) {{
                    jsonStr = tmDouble[1];
                }} else {{
                    const fb = toolBlock.indexOf('{{');
                    const lb = toolBlock.lastIndexOf('}}');
                    if (fb !== -1 && lb !== -1 && lb > fb) {{
                        jsonStr = toolBlock.substring(fb, lb + 1);
                    }}
                }}

                if (jsonStr) {{
                    try {{
                        try {{
                            patchData = JSON.parse(jsonStr);
                        }} catch (e1) {{
                            const unescaped = jsonStr.replace(/\\\\"/g, '"').replace(/\\\\'/g, "'");
                            patchData = JSON.parse(unescaped);
                        }}
                    }} catch (e) {{
                        console.warn('Could not parse tool-call JSON:', e);
                    }}
                }}

                // Direct fallback for patch_section(section_id=..., content=...)
                if (!patchData) {{
                    const secMatch = toolBlock.match(/section_id\\s*=\\s*['"]([^'"]+)['"]/);
                    const sec = secMatch ? secMatch[1] : sectionId;
                    const contentStart = toolBlock.indexOf('content=');
                    if (contentStart !== -1) {{
                        let contentRaw = toolBlock.substring(contentStart + 8).trim();
                        contentRaw = contentRaw.replace(/\\s*(?:<\\|tool_call_end\\|>)?\\s*\\)?\\s*\\]?\\s*$/, '').trim();
                        try {{
                            let jsonCandidate = contentRaw.replace(/'/g, '"');
                            patchData = {{ section_id: sec, content: JSON.parse(jsonCandidate) }};
                        }} catch (pe) {{
                            patchData = {{ section_id: sec, content: contentRaw }};
                        }}
                    }}
                }}

                if (patchData && (patchData.section_id || patchData.content)) {{
                    if (!patchData.section_id) patchData.section_id = sectionId;
                    rawText = rawText.replace(toolBlock, '').trim();
                }} else {{
                    rawText = rawText.replace(/<\\|tool_call_start\\|>|<\\|tool_call_end\\|>/g, '').trim();
                }}
            }}
        }}

        // Clean any leftover tool tokens
        rawText = rawText.replace(/<\\|tool_call_start\\|>|<\\|tool_call_end\\|>/g, '').trim();

        if (!rawText && patchData) {{
            rawText = "I have prepared the updated points for this section based on your request. Review the preview below and click **Apply to Report** to update the report in place.";
        }}

        if (patchData && patchData.content && typeof patchData.content === 'string') {{
            const targetSec = patchData.section_id || sectionId;
            if (targetSec === 'exec_overview' || targetSec === 'exec_conclusions') {{
                if (patchData.content.includes('\\n- ') || patchData.content.includes('\\n• ') || patchData.content.includes('\\n* ')) {{
                    patchData.content = patchData.content.split(/\\n[-•*]\\s+/).map(s => s.replace(/^[-•*]\\s+/, '').trim()).filter(Boolean);
                }} else if (patchData.content.includes('\\n\\n')) {{
                    patchData.content = patchData.content.split(/\\n\\n+/).map(s => s.trim()).filter(Boolean);
                }} else {{
                    patchData.content = [patchData.content.trim()];
                }}
            }}
        }}

        
        let html = formatAiReply(rawText);
        
        if (patchData) {{
            const patchKey = sectionId + '_' + (msgIndex || Date.now());
            pendingPatches[patchKey] = patchData;
            const targetSec = patchData.section_id || sectionId;
            const previewHtml = generatePatchPreviewHtml(patchKey, targetSec, patchData.content);
            
            html += `
                <div class="patch-action-box">
                    <div class="patch-action-title">
                        <span>⚡</span>
                        <span>Proposed In-Place Update</span>
                    </div>
                    ${{previewHtml}}
                    <button class="patch-apply-btn" id="patchBtn_${{patchKey}}" onclick="applySectionPatch('${{patchKey}}', '${{sectionId}}')">
                        <span>✨ Apply to Report</span>
                    </button>
                </div>
            `;
        }}
        
        return {{ html, patch: patchData }};
    }}

    function generatePatchPreviewHtml(patchKey, targetSec, content) {{
        let previewHtml = '';
        if (Array.isArray(content) && content.length > 0 && typeof content[0] === 'string') {{
            const items = content.map(b => `<li style="margin-bottom:0.35rem; line-height:1.45;">${{escapeHtmlText(b)}}</li>`).join('');
            previewHtml = `
                <div class="patch-preview-wrap">
                    <div class="patch-preview-label">
                        <span>📝 Generated Content Preview</span>
                        <span class="patch-edit-badge">✏️ Click to edit directly</span>
                    </div>
                    <ul id="preview_bullets_${{patchKey}}" class="patch-preview-bullets" contenteditable="true">
                        ${{items}}
                    </ul>
                </div>
            `;
        }} else if (targetSec === 'exec_observations' && Array.isArray(content)) {{
            const rows = content.map((row, idx) => `
                <div class="patch-preview-obs-item">
                    <div class="patch-preview-obs-cat">${{escapeHtmlText(row.category || '')}}</div>
                    <div class="patch-preview-obs-text" id="preview_obs_text_${{patchKey}}_${{idx}}" contenteditable="true">${{(row.observation || '').replace(/\\n/g, '<br/>')}}</div>
                </div>
            `).join('');
            previewHtml = `
                <div class="patch-preview-wrap">
                    <div class="patch-preview-label">
                        <span>📝 Generated Observations Preview</span>
                        <span class="patch-edit-badge">✏️ Click to edit directly</span>
                    </div>
                    <div id="preview_obs_${{patchKey}}" class="patch-preview-obs-list">
                        ${{rows}}
                    </div>
                </div>
            `;
        }} else if (targetSec === 'exec_recommendations' && Array.isArray(content)) {{
            const recs = content.map((r, idx) => `
                <div class="patch-preview-rec-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
                        <span style="font-weight:700; color:var(--text);" id="preview_rec_title_${{patchKey}}_${{idx}}" contenteditable="true">${{r.badge || '💡'}} ${{escapeHtmlText(r.title || '')}}</span>
                        <span class="patch-priority-chip">${{escapeHtmlText(r.priority || 'Medium')}}</span>
                    </div>
                    <div style="font-size:0.75rem; margin-bottom:0.25rem;" id="preview_rec_detail_${{patchKey}}_${{idx}}" contenteditable="true"><strong>Action:</strong> ${{escapeHtmlText(r.detail || '')}}</div>
                    <div style="font-size:0.73rem; color:var(--accent);" id="preview_rec_impact_${{patchKey}}_${{idx}}" contenteditable="true"><strong>Impact:</strong> ${{escapeHtmlText(r.business_impact || r.impact || '')}}</div>
                </div>
            `).join('');
            previewHtml = `
                <div class="patch-preview-wrap">
                    <div class="patch-preview-label">
                        <span>📝 Generated Recommendations Preview</span>
                        <span class="patch-edit-badge">✏️ Click to edit directly</span>
                    </div>
                    <div id="preview_recs_${{patchKey}}" class="patch-preview-rec-list">
                        ${{recs}}
                    </div>
                </div>
            `;
        }} else if (content && typeof content === 'object') {{
            const summaryHtml = content.summary ? `<div style="margin-bottom:0.4rem;"><strong style="font-size:0.73rem; color:var(--text); text-transform:uppercase;">Summary:</strong><div id="preview_tab_summary_${{patchKey}}" style="font-size:0.8rem; line-height:1.45;" contenteditable="true">${{escapeHtmlText(content.summary)}}</div></div>` : '';
            const obsList = content.observations || content.highlights || [];
            const recList = content.recommendations || [];
            const obsItems = obsList.map(o => `<li style="margin-bottom:0.3rem;">${{escapeHtmlText(o)}}</li>`).join('');
            const recItems = recList.map(r => `<li style="margin-bottom:0.3rem;">${{escapeHtmlText(r)}}</li>`).join('');
            previewHtml = `
                <div class="patch-preview-wrap">
                    <div class="patch-preview-label">
                        <span>📝 Generated Insights Preview</span>
                        <span class="patch-edit-badge">✏️ Click to edit directly</span>
                    </div>
                    ${{summaryHtml}}
                    <div style="margin-bottom:0.4rem;">
                        <strong style="font-size:0.73rem; color:var(--accent); text-transform:uppercase;">Observations:</strong>
                        <ul id="preview_tab_obs_${{patchKey}}" class="patch-preview-bullets" contenteditable="true">${{obsItems}}</ul>
                    </div>
                    <div>
                        <strong style="font-size:0.73rem; color:var(--green); text-transform:uppercase;">Recommendations:</strong>
                        <ul id="preview_tab_recs_${{patchKey}}" class="patch-preview-bullets" contenteditable="true">${{recItems}}</ul>
                    </div>
                </div>
            `;
        }}
        return previewHtml;
    }}

    async function applySectionPatch(patchKey, sectionId) {{
        const patch = pendingPatches[patchKey];
        const btn = document.getElementById('patchBtn_' + patchKey);
        if (!patch) return;

        const targetSec = patch.section_id || sectionId;
        const initialContent = patch.content;
        let content = initialContent;

        // Extract any direct user edits from the live preview DOM
        if (targetSec === 'exec_overview' || targetSec === 'exec_conclusions') {{
            const previewUl = document.getElementById('preview_bullets_' + patchKey);
            if (previewUl) {{
                const listItems = Array.from(previewUl.querySelectorAll('li')).map(li => li.innerText.trim()).filter(Boolean);
                if (listItems.length > 0) content = listItems;
            }}
        }} else if (targetSec === 'exec_observations') {{
            const previewObs = document.getElementById('preview_obs_' + patchKey);
            if (previewObs && Array.isArray(initialContent)) {{
                content = initialContent.map((row, idx) => {{
                    const el = document.getElementById(`preview_obs_text_${{patchKey}}_${{idx}}`);
                    return {{
                        category: row.category,
                        observation: el ? el.innerText.trim() : row.observation
                    }};
                }});
            }}
        }} else if (targetSec === 'exec_recommendations') {{
            const previewRecs = document.getElementById('preview_recs_' + patchKey);
            if (previewRecs && Array.isArray(initialContent)) {{
                content = initialContent.map((r, idx) => {{
                    const titleEl = document.getElementById(`preview_rec_title_${{patchKey}}_${{idx}}`);
                    const detailEl = document.getElementById(`preview_rec_detail_${{patchKey}}_${{idx}}`);
                    const impactEl = document.getElementById(`preview_rec_impact_${{patchKey}}_${{idx}}`);
                    
                    let titleText = titleEl ? titleEl.innerText.trim() : r.title;
                    titleText = titleText.replace(/^[^a-zA-Z0-9\\s]+/, '').trim();
                    
                    let detailText = detailEl ? detailEl.innerText.replace(/^Action:\\s*/i, '').trim() : r.detail;
                    let impactText = impactEl ? impactEl.innerText.replace(/^Impact:\\s*/i, '').trim() : r.business_impact;


                    return {{
                        badge: r.badge || '💡',
                        title: titleText || r.title,
                        priority: r.priority || 'Medium',
                        detail: detailText || r.detail,
                        business_impact: impactText || r.business_impact || r.impact
                    }};
                }});
            }}
        }} else if (['tab_tx_stats', 'tab_rt_stats', 'tab_error_stats', 'tab_infra_stats', 'tab_comparison', 'compare'].includes(targetSec)) {{
            const summaryDiv = document.getElementById('preview_tab_summary_' + patchKey);
            const obsUl = document.getElementById('preview_tab_obs_' + patchKey);
            const recUl = document.getElementById('preview_tab_recs_' + patchKey);
            let summaryText = initialContent.summary || '';
            let obsList = initialContent.observations || initialContent.highlights || [];
            let recList = initialContent.recommendations || [];
            if (summaryDiv) summaryText = summaryDiv.innerText.trim();
            if (obsUl) obsList = Array.from(obsUl.querySelectorAll('li')).map(li => li.innerText.trim()).filter(Boolean);
            if (recUl) recList = Array.from(recUl.querySelectorAll('li')).map(li => li.innerText.trim()).filter(Boolean);
            content = {{ summary: summaryText, observations: obsList, highlights: obsList, recommendations: recList }};
        }}

        try {{
            if (btn) {{
                btn.disabled = true;
                btn.innerHTML = '<span>⏳ Applying...</span>';
            }}

            // 1. Live DOM Patching
            let updatedEl = null;

            if (targetSec === 'exec_overview') {{
                const ul = document.getElementById('content_exec_overview');
                if (ul && Array.isArray(content)) {{
                    ul.innerHTML = content.map(b => `<li style="margin-bottom:0.4rem; line-height:1.65;">${{escapeHtmlText(b)}}</li>`).join('');
                    updatedEl = ul.closest('.ai-sub-card');
                }}
            }} else if (targetSec === 'exec_conclusions') {{
                const ul = document.getElementById('content_exec_conclusions');
                if (ul && Array.isArray(content)) {{
                    ul.innerHTML = content.map(b => `<li style="margin-bottom:0.4rem; line-height:1.65;">${{escapeHtmlText(b)}}</li>`).join('');
                    updatedEl = ul.closest('.ai-sub-card');
                }}
            }} else if (targetSec === 'exec_observations') {{
                const tbody = document.getElementById('content_exec_observations');
                if (tbody && Array.isArray(content)) {{
                    tbody.innerHTML = content.map(row => {{
                        const obsText = (row.observation || '').replace(/\\n/g, '<br/>');
                        return `
                            <tr style="border-bottom:1px solid var(--border);">
                                <td style="font-weight:700; width:26%; vertical-align:top; font-size:0.84rem; color:var(--text); padding:0.75rem 0.9rem;">${{escapeHtmlText(row.category || '')}}</td>
                                <td style="width:74%; vertical-align:top; font-size:0.84rem; line-height:1.6; color:var(--text); padding:0.75rem 0.9rem;" contenteditable="true">${{obsText}}</td>
                            </tr>
                        `;
                    }}).join('');
                    updatedEl = tbody.closest('.ai-sub-card');
                }}
            }} else if (targetSec === 'exec_recommendations') {{
                const recContainer = document.getElementById('content_exec_recommendations');
                if (recContainer && Array.isArray(content)) {{
                    recContainer.innerHTML = content.map(r => {{
                        const rBadge = r.badge || '💡';
                        const rTitle = escapeHtmlText(r.title || '');
                        const rDetail = escapeHtmlText(r.detail || '');
                        const rPriority = escapeHtmlText(r.priority || 'Medium');
                        const rImpact = escapeHtmlText(r.business_impact || r.impact || 'Mitigates transaction latency spikes.');
                        return `
                            <div style="background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:0.95rem 1.15rem; margin-bottom:0.85rem;">
                                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem; flex-wrap:wrap;">
                                    <span style="font-size:1.05rem;">${{rBadge}}</span>
                                    <strong style="font-size:0.92rem; font-weight:700; color:var(--text);" contenteditable="true">${{rTitle}}</strong>
                                    <span style="font-size:0.7rem; font-weight:700; text-transform:uppercase; padding:0.15rem 0.5rem; border-radius:4px; background:var(--surface2); border:1px solid var(--border); color:var(--muted); margin-left:auto;">${{rPriority}}</span>
                                </div>
                                <p style="margin:0 0 0.55rem 0; font-size:0.86rem; line-height:1.55; color:var(--text);" contenteditable="true"><strong>Technical Action:</strong> ${{rDetail}}</p>
                                <div style="background:var(--accent-bg); border-left:3px solid var(--accent); padding:0.5rem 0.8rem; border-radius:4px; font-size:0.83rem; line-height:1.5; color:var(--text);">
                                    <strong style="color:var(--accent);">💼 Business Impact:</strong> <span contenteditable="true">${{rImpact}}</span>
                                </div>
                            </div>
                        `;
                    }}).join('');
                    updatedEl = recContainer.closest('.ai-sub-card');
                }}
            }} else if (['tab_comparison', 'compare'].includes(targetSec)) {{
                if (content && typeof content === 'object') {{
                    const summaryEl = document.getElementById('comp-ai-summary');
                    const obsUl = document.getElementById('comp-ai-highlights');
                    const recUl = document.getElementById('comp-ai-recommendations');
                    if (summaryEl && content.summary) {{
                        summaryEl.innerHTML = escapeHtmlText(content.summary);
                    }}
                    const obsItems = content.observations || content.highlights || [];
                    if (obsUl && Array.isArray(obsItems)) {{
                        obsUl.innerHTML = obsItems.map(o => `<li style="margin-bottom:0.35rem;">${{escapeHtmlText(o)}}</li>`).join('');
                    }}
                    if (recUl && Array.isArray(content.recommendations)) {{
                        recUl.innerHTML = content.recommendations.map(r => `<li style="margin-bottom:0.35rem;">${{escapeHtmlText(r)}}</li>`).join('');
                    }}
                    updatedEl = document.getElementById('comp-ai-panel') || document.getElementById('compare-content-container');
                }}
            }} else if (['tab_tx_stats', 'tab_rt_stats', 'tab_error_stats', 'tab_infra_stats'].includes(targetSec)) {{
                if (content && typeof content === 'object') {{
                    const obsUl = document.getElementById('content_obs_' + targetSec);
                    const recUl = document.getElementById('content_recs_' + targetSec);
                    if (obsUl && Array.isArray(content.observations)) {{
                        obsUl.innerHTML = content.observations.map(o => `<li style="margin-bottom:0.35rem;">${{escapeHtmlText(o)}}</li>`).join('');
                    }}
                    if (recUl && Array.isArray(content.recommendations)) {{
                        recUl.innerHTML = content.recommendations.map(r => `<li style="margin-bottom:0.35rem;">${{escapeHtmlText(r)}}</li>`).join('');
                    }}
                    if (obsUl) updatedEl = obsUl.closest('.ai-sub-card') || obsUl.closest('.glass-panel');
                }}
            }}

            // Highlight the updated section in the report
            if (updatedEl) {{
                updatedEl.classList.remove('section-just-updated');
                void updatedEl.offsetWidth; // trigger reflow
                updatedEl.classList.add('section-just-updated');
                updatedEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}


            // 2. Persist to Backend result.json
            const res = await fetch('/api/ai-chat/patch-section', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    run_id: reportRunId,
                    section_id: targetSec,
                    content: content
                }})
            }});
            const data = await res.json();

            if (btn) {{
                btn.className = 'patch-apply-btn applied';
                btn.innerHTML = '<span>✅ Applied to Report</span>';
            }}
        }} catch (err) {{
            console.error('Error applying section patch:', err);
            if (btn) {{
                btn.disabled = false;
                btn.innerHTML = '<span>❌ Failed to Apply</span>';
            }}
        }}
    }}

    function renderChatMessages(sectionId) {{
        const container = document.getElementById('aiChatMessages_' + sectionId);
        if (!container) return;
        
        const history = aiChatHistories[sectionId] || [];
        if (!history || history.length === 0) return;
        
        let html = '';
        history.forEach((msg, idx) => {{
            if (msg.role === 'user') {{
                html += `<div class="ai-chat-bubble-user">${{escapeHtmlText(msg.content)}}</div>`;
            }} else {{
                const parsed = parseAiReplyWithPatch(msg.content, sectionId, idx);
                html += `<div class="ai-chat-bubble-ai">${{parsed.html}}</div>`;
            }}
        }});
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    }}

    async function sendAiChatMessage(sectionId) {{
        const input = document.getElementById('aiChatInput_' + sectionId);
        const sendBtn = document.getElementById('aiChatSendBtn_' + sectionId);
        const container = document.getElementById('aiChatMessages_' + sectionId);
        if (!input || !container) return;
        
        const text = input.value.trim();
        if (!text) return;
        
        input.value = '';
        if (sendBtn) sendBtn.disabled = true;
        
        if (!aiChatHistories[sectionId]) aiChatHistories[sectionId] = [];
        
        // Remove welcome screen if present
        const welcome = container.querySelector('.ai-chat-welcome');
        if (welcome) welcome.remove();

        aiChatHistories[sectionId].push({{ role: 'user', content: text }});
        
        // Append user bubble
        const userDiv = document.createElement('div');
        userDiv.className = 'ai-chat-bubble-user';
        userDiv.textContent = text;
        container.appendChild(userDiv);
        
        // Append typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'ai-chat-bubble-ai ai-chat-typing';
        typingDiv.id = 'aiChatTyping_' + sectionId;
        typingDiv.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
        container.appendChild(typingDiv);
        container.scrollTop = container.scrollHeight;
        
        try {{
            const priorHistory = aiChatHistories[sectionId].slice(0, -1);
            const chatPayload = {{
                run_id: reportRunId,
                section_id: sectionId,
                message: text,
                history: priorHistory
            }};
            if (sectionId === 'tab_comparison' || sectionId === 'compare') {{
                chatPayload.baseline_id = window.currentComparisonBaselineId || '';
            }}
            const res = await fetch('/api/ai-chat/message', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(chatPayload)
            }});
            
            const data = await res.json();
            typingDiv.remove();
            
            if (data.success && data.reply) {{
                aiChatHistories[sectionId].push({{ role: 'assistant', content: data.reply }});
                const aiDiv = document.createElement('div');
                aiDiv.className = 'ai-chat-bubble-ai';
                const parsed = parseAiReplyWithPatch(data.reply, sectionId, aiChatHistories[sectionId].length - 1);
                aiDiv.innerHTML = parsed.html;
                container.appendChild(aiDiv);
            }} else {{
                const errDiv = document.createElement('div');
                errDiv.className = 'ai-chat-bubble-ai';
                errDiv.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                errDiv.style.color = '#ef4444';
                errDiv.textContent = '❌ ' + (data.message || 'Error getting response from AI.');
                container.appendChild(errDiv);
            }}
        }} catch (err) {{
            typingDiv.remove();
            const errDiv = document.createElement('div');
            errDiv.className = 'ai-chat-bubble-ai';
            errDiv.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            errDiv.style.color = '#ef4444';
            errDiv.textContent = '❌ Connection failed: ' + err.message;
            container.appendChild(errDiv);
        }} finally {{
            if (sendBtn) sendBtn.disabled = false;
            container.scrollTop = container.scrollHeight;
            if (input) input.focus();
        }}
    }}

    function quickAiPrompt(sectionId, promptText) {{
        const input = document.getElementById('aiChatInput_' + sectionId);
        if (input) {{
            input.value = promptText;
            sendAiChatMessage(sectionId);
        }}
    }}

    async function clearAiChat(sectionId) {{
        if (!confirm('Are you sure you want to clear the chat history for this section?')) return;
        aiChatHistories[sectionId] = [];
        const container = document.getElementById('aiChatMessages_' + sectionId);
        if (container) {{
            container.innerHTML = `
                <div class="ai-chat-welcome">
                    <div class="ai-welcome-avatar">🧹</div>
                    <div class="ai-welcome-title">Chat Cleared</div>
                    <div class="ai-welcome-sub">Ask any new question or prompt the agent to rewrite and update this section.</div>
                </div>
            `;
        }}
        try {{
            await fetch('/api/ai-chat/clear', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ run_id: reportRunId, section_id: sectionId }})
            }});
        }} catch (e) {{
            console.warn('Error clearing backend chat history:', e);
        }}
    }}

    function initAiChatDrawers() {{
        ['exec_overview', 'exec_observations', 'exec_conclusions', 'exec_recommendations', 'executive', 'tab_tx_stats', 'tab_rt_stats', 'tab_error_stats', 'tab_infra_stats', 'tab_comparison'].forEach(secId => {{
            if (aiChatHistories[secId] && aiChatHistories[secId].length > 0) {{
                renderChatMessages(secId);
            }}
        }});
        initChatDrawerResizing();
    }}

    function initChatDrawerResizing() {{
        const drawers = document.querySelectorAll('.ai-chat-drawer');
        drawers.forEach(drawer => {{
            if (drawer.dataset.resizeInit) return;
            drawer.dataset.resizeInit = 'true';

            const handlesConfig = [
                {{ cls: 'ai-chat-resize-handle-nw', title: 'Drag corner to resize', dir: 'nw' }},
                {{ cls: 'ai-chat-resize-edge-n', title: 'Drag edge to resize height', dir: 'n' }},
                {{ cls: 'ai-chat-resize-edge-w', title: 'Drag edge to resize width', dir: 'w' }},
                {{ cls: 'ai-chat-resize-handle-se', title: 'Drag corner to resize', dir: 'se' }},
                {{ cls: 'ai-chat-resize-edge-s', title: 'Drag edge to resize height', dir: 's' }},
                {{ cls: 'ai-chat-resize-edge-e', title: 'Drag edge to resize width', dir: 'e' }}
            ];

            handlesConfig.forEach(h => {{
                let el = drawer.querySelector('.' + h.cls);
                if (!el) {{
                    el = document.createElement('div');
                    el.className = h.cls;
                    el.title = h.title;
                    drawer.prepend(el);
                }}
                bindResizeHandle(drawer, el, h.dir);
            }});

            const header = drawer.querySelector('.ai-chat-header');
            if (header) {{
                const secId = drawer.getAttribute('data-section-id') || drawer.id.replace('aiChatDrawer_', '');
                let maxBtn = drawer.querySelector('#aiChatMaxBtn_' + secId);
                if (!maxBtn) {{
                    const btnWrap = header.querySelector('div[style*="display:flex"]') || header.lastElementChild;
                    if (btnWrap) {{
                        maxBtn = document.createElement('button');
                        maxBtn.id = 'aiChatMaxBtn_' + secId;
                        maxBtn.className = 'ai-chat-hdr-btn';
                        maxBtn.innerHTML = '⛶';
                        maxBtn.title = 'Maximize Chat Window';
                        maxBtn.onclick = () => toggleAiChatMaximize(secId);
                        btnWrap.insertBefore(maxBtn, btnWrap.firstChild);
                    }}
                }}
            }}
        }});
    }}

    function bindResizeHandle(drawer, handleEl, dir) {{
        handleEl.addEventListener('pointerdown', e => {{
            e.preventDefault();
            e.stopPropagation();

            if (drawer.classList.contains('expanded')) {{
                drawer.classList.remove('expanded');
                const secId = drawer.getAttribute('data-section-id') || drawer.id.replace('aiChatDrawer_', '');
                const maxBtn = document.getElementById('aiChatMaxBtn_' + secId);
                if (maxBtn) {{
                    maxBtn.innerHTML = '⛶';
                    maxBtn.title = 'Maximize Chat Window';
                }}
            }}

            const startX = e.clientX;
            const startY = e.clientY;
            const startWidth = drawer.offsetWidth;
            const startHeight = drawer.offsetHeight;

            drawer.classList.add('is-resizing');
            document.body.style.userSelect = 'none';

            function onPointerMove(moveEvt) {{
                let newW = startWidth;
                let newH = startHeight;

                if (dir === 'nw') {{
                    newW = startWidth + (startX - moveEvt.clientX);
                    newH = startHeight + (startY - moveEvt.clientY);
                }} else if (dir === 'n') {{
                    newH = startHeight + (startY - moveEvt.clientY);
                }} else if (dir === 'w') {{
                    newW = startWidth + (startX - moveEvt.clientX);
                }} else if (dir === 'se') {{
                    newW = startWidth + (moveEvt.clientX - startX);
                    newH = startHeight + (moveEvt.clientY - startY);
                }} else if (dir === 's') {{
                    newH = startHeight + (moveEvt.clientY - startY);
                }} else if (dir === 'e') {{
                    newW = startWidth + (moveEvt.clientX - startX);
                }}

                const maxW = Math.min(window.innerWidth - 30, 1400);
                const maxH = Math.min(window.innerHeight - 30, 1200);
                newW = Math.max(380, Math.min(maxW, newW));
                newH = Math.max(420, Math.min(maxH, newH));

                drawer.style.width = newW + 'px';
                drawer.style.height = newH + 'px';
            }}

            function onPointerUp() {{
                drawer.classList.remove('is-resizing');
                document.body.style.userSelect = '';
                window.removeEventListener('pointermove', onPointerMove);
                window.removeEventListener('pointerup', onPointerUp);
            }}

            window.addEventListener('pointermove', onPointerMove);
            window.addEventListener('pointerup', onPointerUp);
        }});
    }}



    // Disable contenteditable on load, mark elements, init validations & chat
    document.addEventListener("DOMContentLoaded", () => {{
        document.querySelectorAll('[contenteditable="true"]').forEach(el => {{
            el.setAttribute('data-editable', 'true');
            el.setAttribute('contenteditable', 'false');
        }});
        initHumanValidations();
        initAiChatDrawers();
    }});

    // ── Finding Drawer Logic ──
    const findingsData = {findings_json};
    const recsData = {recs_json};

    function showFinding(fid) {{
        const finding = findingsData.find(f => f.id === fid);
        if (!finding) return;
        
        let html = `<h2 style="margin-top:0; color:var(--text); font-size:1.4rem;">${{finding.id}}</h2>`;
        html += `<p style="font-size:1.1rem; font-weight:700; margin-bottom:1.5rem; color:var(--text);">${{finding.title}}</p>`;
        
        html += `<div class="drawer-section"><div class="drawer-h">Observation</div><p style="font-size:0.9rem; margin:0;">${{finding.observation}}</p></div>`;
        
        if (finding.evidence && finding.evidence.length > 0) {{
            html += `<div class="drawer-section"><div class="drawer-h">Evidence</div>`;
            finding.evidence.forEach(e => {{
                html += `<div style="background:var(--surface2); padding:0.5rem; border-radius:6px; margin-bottom:0.4rem; font-size:0.85rem;"><strong>${{e.metric}}:</strong> ${{e.value}} <span style="color:var(--muted); font-size:0.8rem; float:right;">${{e.source}}</span></div>`;
            }});
            html += `</div>`;
        }}

        if (finding.interpretation) {{
            html += `<div class="drawer-section"><div class="drawer-h">Interpretation</div><p style="font-size:0.9rem; margin:0;">${{finding.interpretation}}</p></div>`;
        }}
        
        if (finding.root_cause_assessment) {{
            html += `<div class="drawer-section"><div class="drawer-h">Root Cause Assessment</div><p style="font-size:0.9rem; margin:0;">${{finding.root_cause_assessment}}</p>`;
            if (finding.confidence && finding.confidence.specific_root_cause) {{
                html += `<div style="font-size:0.8rem; margin-top:0.3rem; color:var(--muted);"><strong>Confidence:</strong> ${{finding.confidence.specific_root_cause}}</div>`;
            }}
            html += `</div>`;
        }}

        if (finding.impact) {{
            html += `<div class="drawer-section"><div class="drawer-h">Impact</div><p style="font-size:0.9rem; margin:0;">${{finding.impact}}</p></div>`;
        }}

        // Find linked recommendation
        const rec = recsData.find(r => r.triggered_by && r.triggered_by.includes(fid));
        if (rec) {{
            html += `<div class="drawer-section" style="background:rgba(16,185,129,0.1); padding:1rem; border-radius:8px; border-left:4px solid #10b981;">
                <div class="drawer-h" style="color:#10b981;">Recommendation: ${{rec.id}}</div>
                <p style="font-weight:700; margin:0 0 0.5rem 0; font-size:0.9rem;">${{rec.title}}</p>
                <p style="font-size:0.85rem; margin:0 0 0.5rem 0;">${{rec.why}}</p>`;
            if (rec.action && rec.action.length > 0) {{
                html += `<ul style="font-size:0.85rem; padding-left:1.2rem; margin-bottom:0.5rem;">`;
                rec.action.forEach(a => html += `<li>${{a}}</li>`);
                html += `</ul>`;
            }}
            if (rec.validation) {{
                html += `<div style="font-size:0.85rem; margin-top:0.5rem;"><strong>Validation:</strong> ${{rec.validation}}</div>`;
            }}
            html += `</div>`;
        }}

        document.getElementById('drawerContent').innerHTML = html;
        document.getElementById('findingDrawerOverlay').style.display = 'block';
        setTimeout(() => document.getElementById('findingDrawer').classList.add('open'), 10);
    }}

    function closeFinding() {{
        document.getElementById('findingDrawer').classList.remove('open');
        setTimeout(() => document.getElementById('findingDrawerOverlay').style.display = 'none', 300);
    }}

    // ── Graph & Section Guide Modal Logic ──
    const graphGuides = {{
        'tx-summary': {{
            title: '📊 Transaction Summary',
            what: 'Shows total request samples split into Passed (green) and Failed (red) executions for each test script.',
            howToRead: [
                'Taller green bars indicate high execution volume with successful assertions.',
                'Any red bars highlight transaction failures or assertion breaches.',
                'Exact sample counts are printed directly on top of each bar for instant reading.'
            ],
            filters: 'Hover over bars to view percentage breakdown and script error rate. Click "Pass Samples" or "Fail Samples" in the bottom legend to toggle datasets.'
        }},
        'tx-rt-breakdown': {{
            title: '⏱️ Transaction &amp; Sub-Transaction Response Time Breakdown',
            what: 'Hierarchical response time analysis from high-level User Journeys down to individual child HTTP requests and sub-transactions.',
            howToRead: [
                'Data labels on top of bars display the exact response time in milliseconds.',
                'Allows pinpointing which sub-request is responsible for overall transaction slowness.'
            ],
            filters: 'Use <strong>User Journey</strong> dropdown to isolate a flow, <strong>Transaction</strong> to drill down into child requests, and <strong>Metric</strong> to switch between Average RT, P90, P95, and Max RT.'
        }},
        'sla-deviation': {{
            title: '🎯 SLA Deviation by Transaction (% from Target SLA)',
            what: 'Diverging diagnostic chart measuring percentage deviation of each transaction\\'s P90 latency from its SLA target.',
            howToRead: [
                '<strong>Green bars (left/negative):</strong> Within acceptable SLA target (healthy).',
                '<strong>Red bars (right/positive):</strong> Exceeding SLA threshold (breached).'
            ],
            filters: 'Use the <strong>Filter User Journey</strong> dropdown to isolate transactions in a specific user journey. Hover over bars to see the exact percentage deviation and target.'
        }},
        'error-distribution': {{
            title: '🔴 Error Distribution &amp; Analysis',
            what: 'Interactive donut chart breaking down all failed requests grouped by HTTP status code, assertion failure message, or error category.',
            howToRead: [
                'Larger slices represent the predominant error types causing test degradation.',
                'Center text shows the total count of errors captured during the test.'
            ],
            filters: '<strong>Click any slice or legend item</strong> to populate the right-hand drill-down panel with affected transactions, timestamps, and assertion details.'
        }},
        'server-side': {{
            title: '🖥️ Server Side CPU &amp; Memory Utilization',
            what: 'Simultaneous dual-line time series tracking host CPU utilization (%) in amber and Memory utilization (%) in blue.',
            howToRead: [
                'Values sustained above 80% indicate high resource pressure.',
                'Spikes aligning with test load indicate infrastructure bottlenecks.'
            ],
            filters: 'Hover along the timeline to inspect synchronized CPU and Memory % at any specific test second.'
        }},
        'concurrency': {{
            title: '👥 Virtual User Ramp-Up &amp; Workload Profile',
            what: 'Workload concurrency profile displaying ramp-up steps, steady-state duration, and active virtual users across the test timeline.',
            howToRead: [
                'Shows initial VU start, incremental user ramp distribution, and sustained steady-state plateau.',
                'Sudden drops or stalls indicate test-runner connection aborts or application crashes.'
            ],
            filters: 'Hover over data points to check active user concurrency at each interval.'
        }},
        'throughput': {{
            title: '📊 Throughput &amp; Errors Over Time',
            what: 'Request throughput (req/sec in blue/indigo) and error occurrences (in red) minute-by-minute throughout the execution.',
            howToRead: [
                'Throughput should remain steady or scale with concurrent user ramp-up.',
                'Red bars indicate the exact timeframe when errors occurred.'
            ],
            filters: 'Use the top-right <strong>Multi-Select Transaction</strong> filter to select and compare multiple transactions at once, search by name, or view the overall test.'
        }},
        'rt-over-time': {{
            title: '📈 Response Time Trend Over Time',
            what: 'Multi-line timeline tracking Average RT (indigo), 95th Percentile P95 (amber), and 99th Percentile P99 (red dashed).',
            howToRead: [
                'Flat, low lines indicate stable performance under load.',
                'Rising slopes or sharp spikes reveal latency degradation or server queueing.'
            ],
            filters: 'Use the top-right <strong>Multi-Select Transaction</strong> filter to select multiple transactions to compare their response time curves side-by-side on the same timeline.'
        }},
        'critical-tx': {{
            title: '🔥 Critical Transaction Response Time',
            what: 'Response time trends for high-priority or slowest transactions plotted alongside dashed red SLA target lines.',
            howToRead: [
                'Lines rising above the dashed red SLA line signify performance SLA breaches.',
                'Summary badges at top show critical count, average, P95, and max response times.'
            ],
            filters: 'Click the <strong>Transaction Chips</strong> above the chart to toggle specific transactions on/off, or click "Show All".'
        }},
        'rt-hist': {{
            title: '📊 Response Time Distribution Histogram',
            what: 'Request count distribution grouped into response time latency buckets (from <500ms up to >5000ms).',
            howToRead: [
                'Skew towards green/blue buckets (<500ms-1s) means fast user experience.',
                'Skew towards amber/red (>2s) shows tail latency delays affecting users.'
            ],
            filters: 'Hover over each latency bucket bar to see exact request volume and distribution.'
        }},
        'top-tx': {{
            title: '🏷️ Top Transactions by Response Time',
            what: 'Horizontal bar ranking of slowest transactions ordered by average response time.',
            howToRead: [
                'Quickly identifies top optimization candidates and slowest user actions in the application.'
            ],
            filters: 'Hover over bars to inspect average response times in milliseconds.'
        }},
        'sla-donut': {{
            title: 'SLA Deviation &amp; Breach Severity Donut',
            what: 'Overall SLA compliance score and distribution of transactions across SLA severity categories (Passed, Minor, Moderate, Critical).',
            howToRead: [
                'Center percentage shows overall SLA compliance (>=85% is passing).',
                'Side cards break down exact transaction counts in each breach tier.'
            ],
            filters: 'Hover over donut segments to inspect individual tier counts.'
        }},
        'error-rate-tx': {{
            title: '🔴 Error Rate by Transaction (%)',
            what: 'Horizontal bar chart showing failure rate percentage for transactions that experienced errors.',
            howToRead: [
                'Highlights which specific transactions suffered the highest failure rates during the test.'
            ],
            filters: 'Hover over bars to view exact failure percentages.'
        }},
        'azure-cpu-mem': {{
            title: '🖥️ Azure Resource Utilization (CPU &amp; Memory)',
            what: 'Full-width dual time series of server CPU % (amber) and Memory % (blue) with threshold bands (80% and 90%).',
            howToRead: [
                'Sustained periods above 80% indicate resource starvation causing response time degradation.'
            ],
            filters: 'Hover across the timeline to see exact CPU and memory % at each sample timestamp.'
        }},
        'workload-cpu': {{
            title: '📈 Workload vs CPU Utilization',
            what: 'Dual-axis chart comparing JMeter request throughput (req/s on left axis) against Azure CPU % (on right axis).',
            howToRead: [
                'Reveals whether CPU utilization scales proportionally with client load or saturates early.'
            ],
            filters: 'Hover across points to compare req/sec against host CPU load simultaneously.'
        }},
        'tp-rt-impact': {{
            title: '⚡ Throughput vs Response Time',
            what: 'Request throughput (req/s) plotted against Average Response Time (ms).',
            howToRead: [
                'If throughput flattens while response time climbs, the application has reached its maximum capacity/saturation point.'
            ],
            filters: 'Hover to inspect throughput and latency correlation at any second.'
        }},
        'disk-io': {{
            title: '💾 Disk I/O &amp; Queue Contention',
            what: 'Disk Read (MB/s) and Write (MB/s) bars alongside Disk Queue Depth line on secondary axis.',
            howToRead: [
                'Queue Depth > 2-5 indicates disk I/O bottlenecks and storage queueing delays.'
            ],
            filters: 'Hover over bars and line to inspect storage transfer rates and queue length.'
        }},
        'network-tp': {{
            title: '🌐 Network Throughput (In/Out)',
            what: 'Inbound (cyan) and Outbound (purple) network transfer volume in megabytes over time.',
            howToRead: [
                'Highlights network bandwidth usage and identifies potential network saturation.'
            ],
            filters: 'Hover across timestamps to check network MB transferred at each point.'
        }},
        'test-config': {{
            title: '📋 Test Configuration Details',
            what: 'Execution metadata detailing test environment, objective, start/end timestamps, duration, and target user load.',
            howToRead: [
                'Verifies that test execution adhered to the planned test plan configuration.',
                'Editable cells allow customizing objective, release version, or environment before report distribution.'
            ],
            filters: 'Editable fields can be modified directly in the browser and saved.'
        }},
        'perf-scorecard': {{
            title: '📈 Performance Scorecard &amp; SLA Violation Summary',
            what: 'Executive scorecard quantifying user satisfaction (APDEX) and response time SLA breach counts grouped by breach severity tiers.',
            howToRead: [
                'APDEX &ge; 0.85 indicates healthy overall user experience.',
                'Breach cards highlight transactions violating SLAs by &gt;20%, &gt;50%, and &gt;100% over threshold.'
            ],
            filters: 'Click into the Response Time &amp; SLA tabs for per-transaction root-cause analysis.'
        }},
        'exec-overview': {{
            title: '🎯 AI Powered Executive Overview',
            what: 'Executive level synthesis generated by AI highlighting release readiness, SLA compliance, error posture, and key risk findings.',
            howToRead: [
                'Presents bullet points designed for engineering leadership and release sign-off.',
                'Each bullet is editable and backed by human validation controls.'
            ],
            filters: 'Click the "Human Validated" badge to confirm and persist reviewer sign-off.'
        }},
        'obs-table': {{
            title: '📋 High-Level Performance Observations',
            what: 'Categorized diagnostic observations linking client-side performance, response times, errors, and server infrastructure signals.',
            howToRead: [
                'Each row pairs a performance domain with concrete metric evidence.',
                'Allows rapid scanning across Throughput, Latency, Errors, and Host Health.'
            ],
            filters: 'Click into table cells to edit text or notes directly in the browser.'
        }},
        'conclusions': {{
            title: '📌 Key Conclusions',
            what: 'Definitive test outcome conclusions based on aggregated metric thresholds and SLA benchmarks.',
            howToRead: [
                'Summarizes whether the build passed or failed non-functional requirements.',
                'Identifies specific transactions requiring performance tuning.'
            ],
            filters: 'Editable bullet points with human validation approval tracking.'
        }},
        'recommendations': {{
            title: '💡 Prioritized Recommendations',
            what: 'Ranked technical actions paired with estimated business impact to remediate bottlenecks and prevent production outages.',
            howToRead: [
                'Each recommendation provides technical steps (e.g. indexing, thread pool tuning) and business justification.',
                'Priority tags (High, Medium, Low) guide sprint planning and triage.'
            ],
            filters: 'Technical actions and business impacts are editable in place.'
        }},
        'ai-augmented': {{
            title: '🧠 AI Augmented Analysis',
            what: 'Multi-layer artificial intelligence analysis integrating test observations, statistical deviations, and infrastructure correlations.',
            howToRead: [
                'Combines quantitative load statistics with generative root-cause analysis.',
                'Includes validation workflow badges for QA and performance leads.'
            ],
            filters: 'Use "Validate All Augmented Analysis" to approve all AI findings at once.'
        }},
        'tab-ai-insights': {{
            title: '🧠 Tab-Level AI Insights &amp; Recommendations',
            what: 'Context-specific AI intelligence focused on the current tab\\'s metrics (Load, Latency, Errors, or Infrastructure).',
            howToRead: [
                'Left panel highlights key domain observations with metric data points.',
                'Right panel suggests domain-specific remediation and tuning strategies.'
            ],
            filters: 'Edit points directly in browser; use Human Validation badge to mark verified.'
        }},
        'user-journey-breakdown': {{
            title: '👥 User Journey Concurrency Allocation &amp; Capacity',
            what: 'Breakdown of configured Thread Groups / User Journeys with user allocation, generated throughput, P90 latency, and SLA compliance status.',
            howToRead: [
                'Allows verifying whether user concurrency distribution aligned with business workload models.',
                'Identifies which specific user flow had the highest error rate or lowest SLA compliance.'
            ],
            filters: 'Compare journeys side-by-side across Concurrency, Throughput, and Latency columns.'
        }},
        'tx-stats-table': {{
            title: '📋 Transaction Statistics Table',
            what: 'Tabular matrix of all executed test scripts showing duration, user count, total samples, pass/fail counts, and error percentages.',
            howToRead: [
                'Green counts indicate passed samples; red counts indicate assertions or HTTP failures.',
                'Error Percentage (%) quickly reveals problematic scripts.'
            ],
            filters: 'Header badges display overall test sample totals and pass/fail summary.'
        }},
        'latency-kpis': {{
            title: '⏱️ Response Time &amp; Latency Percentiles',
            what: 'Top-level latency summary metrics showing Average Response Time, 95th Percentile (P95), and 99th Percentile (P99).',
            howToRead: [
                'Average RT shows the mean execution latency across all requests.',
                'P95 and P99 represent tail latency — 95% and 99% of user actions finished within this duration.'
            ],
            filters: 'Use the charts below to view time series trends and per-transaction percentiles.'
        }},
        'rt-percentiles-table': {{
            title: '📋 Per-Transaction Breakdown &amp; SLA Targets',
            what: 'Hierarchical multi-level table containing detailed response times (Avg, P90, Min, Max), error rates, SLA thresholds, and percentage deviations.',
            howToRead: [
                'Click ▶ / ▼ expanders on parent transactions to drill into child HTTP requests.',
                'Deviation % shows how far actual P90 exceeded target SLA (positive red is a breach).',
                'APDEX column rates user satisfaction for each individual transaction.'
            ],
            filters: 'Use <strong>Unit</strong> dropdown to toggle Milliseconds (ms) vs Seconds (s), and <strong>User Journey</strong> filter to isolate specific flows.'
        }},
        'critical-tx-table': {{
            title: '🚨 Critical Transactions &amp; Deviations',
            what: 'Filtered subset listing only transactions that failed SLA thresholds or exhibited severe deviation (>30%).',
            howToRead: [
                'Instantly isolates problematic transactions requiring engineering investigation.',
                'Shows SLA target vs actual P90 and total breach percentage.'
            ],
            filters: 'Click on transaction names to trace related error logs or latency graphs.'
        }},
        'sla-error-kpis': {{
            title: '🔴 Error Rate &amp; SLA Breaches Summary',
            what: 'High-level reliability cards showing the global test error rate (%) and total number of transactions that breached SLAs.',
            howToRead: [
                'Error Rate < 1% is passing (green), 1-5% warning (yellow), >5% failing (red).',
                'SLA Breaches count shows how many transactions failed either latency or error rate targets.'
            ],
            filters: 'Drill down using the Error Distribution donut and SLA compliance tables below.'
        }},
        'sla-targets-table': {{
            title: '🚨 SLA Breach Analysis &amp; Corresponding HTTP Requests',
            what: 'Comprehensive diagnostic listing every SLA-breached transaction along with its child HTTP request breakdown and failure metrics.',
            howToRead: [
                'Identifies the exact backend API call or resource causing the parent transaction SLA violation.',
                'Shows target threshold, actual measured response time, and breach ratio.'
            ],
            filters: 'Review child HTTP requests to pinpoint slow endpoints (GET, POST, etc.).'
        }},
        'azure-kpi-cards': {{
            title: '🖥️ Azure Host Infrastructure Telemetry',
            what: 'Host-level infrastructure health indicators tracking Peak CPU %, Peak Memory %, Peak Disk Queue Depth, and System Availability %.',
            howToRead: [
                'Peak CPU &ge; 80% indicates CPU starvation and thread scheduling delays.',
                'Disk Queue Depth &ge; 5 indicates storage I/O bottleneck.',
                'Availability < 99.5% indicates server-side downtime or unresponsiveness.'
            ],
            filters: 'Review time-series charts below to correlate host spikes with JMeter throughput.'
        }},
        'infra-correlation': {{
            title: '📊 Infrastructure Correlation Matrix',
            what: 'Pearson correlation coefficients (r) mathematically calculated between JMeter load metrics (Throughput, Latency) and Host telemetry (CPU, Memory).',
            howToRead: [
                'Values near +1.0 indicate strong positive correlation (e.g. CPU increases as throughput increases).',
                'Green highlights indicate strong statistically significant relationships (|r| &ge; 0.70).'
            ],
            filters: 'Helps prove whether response time degradation was caused by server resource exhaustion.'
        }},
        'timeline-events': {{
            title: '⏱️ Performance Incident Timeline',
            what: 'Chronological event stream logging significant system transitions, ramp-up milestones, resource saturation alerts, and error spikes.',
            howToRead: [
                'Follows the sequence of events from test start to ramp-up, peak load, incident occurrences, and test cooldown.',
                'Helps establish causal timelines (e.g. CPU exceeded 85% at 00:15, followed by 500 errors at 00:18).'
            ],
            filters: 'Read events chronologically to reconstruct system behavior under test.'
        }},
        'infra-findings': {{
            title: '🧠 Infrastructure Diagnostic Analysis &amp; Findings',
            what: 'Automated diagnostic synthesis connecting client-side metrics with server-side telemetry to diagnose root causes.',
            howToRead: [
                'Highlights Primary Signal (e.g. CPU spike), Associated Signals (Memory, Queue Depth), and Likely Root Cause.',
                'Gives performance engineers an immediate root-cause hypothesis backed by data.'
            ],
            filters: 'Cross-reference with client-side error breakdown and transaction percentiles.'
        }},
        'corr-findings': {{
            title: '🔗 Client ↔ Server Correlation Findings',
            what: 'Detailed finding statements evaluating the interaction between application workload demand and backend server capacity.',
            howToRead: [
                'Each finding evaluates capacity limits, saturation points, or resource headroom.',
                'Click "View Finding Details" for full interpretation, impact, and linked recommendations.'
            ],
            filters: 'Click finding cards to open the deep-dive slide-out drawer.'
        }},
        'comp-selector': {{
            title: '⚖️ Baseline vs Current Execution Selector',
            what: 'Selects a historical test run as the benchmark baseline (Run A) against the current execution (Run B) to compute exact differential performance telemetry.',
            howToRead: [
                'Choose any prior execution from the dropdown to immediately calculate delta percentages and regression status.',
                'The system automatically saves your comparison draft so state, chart selections, and customized insights persist across page reloads.',
                'Click "✕ Clear" at any time to reset the comparison view to its clean initial state.'
            ],
            filters: 'Use the dropdown to switch baselines. Saved drafts update in real time.'
        }},
        'comp-ai-assessment': {{
            title: '🤖 AI Comparative Performance Assessment',
            what: 'Grounded artificial intelligence synthesis analyzing differential metrics, iteration parity, regression severity, and targeted engineering remediation.',
            howToRead: [
                'Top risk badge (LOW, MODERATE, HIGH RISK) reflects overall regression posture.',
                'Quick metric chips highlight percentage shifts in Response Time, SLA Compliance, Error Delta, and Throughput.',
                'Key Differential Insights list high-impact architectural shifts, impact, and actionable takeaways.'
            ],
            filters: 'All narrative text and bullet points are contenteditable in Draft Mode. Use the "Ask AI" button to prompt the Comparison Differential AI Agent.'
        }},
        'comp-kpis': {{
            title: '📋 Comparative Key Performance Indicators (Parity &amp; Deltas)',
            what: 'Side-by-side scorecard comparing completed iterations, request volume, throughput (TPS), response times (Avg, P90, P95, P99), and reliability metrics.',
            howToRead: [
                'Values formatted as <code>Baseline ➔ Current</code> with color-coded delta percentage badges.',
                'Green badges indicate performance improvements or reduced latencies/errors.',
                'Red badges indicate regressions, higher latencies, or error increases.'
            ],
            filters: 'Review iteration parity to verify if test duration and sample sizes are statistically comparable.'
        }},
        'comp-explorer': {{
            title: '📈 Modular Comparative Performance Explorer',
            what: 'Full-width multi-metric visual explorer comparing transaction metrics side-by-side or as diverging differential bars and lines.',
            howToRead: [
                'Switch metrics via the <strong>Metric</strong> dropdown (Average RT, P95, P90, P99, Variance %, TPS, Error Rate, Samples).',
                'Toggle chart representations using the <strong>Chart Type</strong> buttons: Diverging Bar (📊), Divergence Line (📈), or Filled Area (📉).',
                'Filter by <strong>User Story / Journey</strong> or view <strong>Top Regressed / Top Improved</strong> transactions.',
                'Type in the <strong>Search</strong> box to filter specific transactions in real time.'
            ],
            filters: 'Use Metric, Filter, and Chart Type controls in the top toolbar to customize the visualization.'
        }},
        'comp-distribution': {{
            title: '📊 Latency Distribution &amp; Percentile Curves Comparison',
            what: 'Comparative request distribution across latency buckets (&lt;500ms, 500ms-1s, 1s-2s, 2s-3s, 3s-5s, &gt;5s) and Cumulative Percentile Curves (P50 ➔ P99).',
            howToRead: [
                '<strong>Latency Buckets (Histogram):</strong> Shows request volume distribution shifting between fast (<500ms) and slow (>2s) tiers.',
                '<strong>Percentile Curves:</strong> Overlays Baseline vs Current latency growth curves alongside the SLA Target threshold line to pinpoint where tail latency diverges.'
            ],
            filters: 'Use the <strong>Histogram / Percentile Curve</strong> toggle button in the header to switch views.'
        }},
        'comp-tps-errors': {{
            title: '⚡ Throughput (TPS) &amp; Error Rate Comparative Shift',
            what: 'Side-by-side evaluation of transaction throughput capacity alongside error rate shifts between baseline and current test executions.',
            howToRead: [
                'Compares generated request throughput (req/sec) against failure rates per transaction.',
                'Identifies whether throughput degradation was caused by rising error rates or server queueing.'
            ],
            filters: 'Hover over bars to view exact TPS and error percentage values.'
        }},
        'comp-sla-matrix': {{
            title: '🎯 4-Quadrant SLA Transition Matrix',
            what: 'Evaluates SLA state shifts for all transactions between baseline and current runs across four quadrants: Pass ➔ Pass, Pass ➔ Fail, Fail ➔ Pass, and Fail ➔ Fail.',
            howToRead: [
                '<strong>🟢 Pass ➔ Pass:</strong> Transactions that consistently met SLA targets across both runs.',
                '<strong>🔴 Pass ➔ Fail (NEW BREACHES):</strong> Newly regressed transactions requiring immediate remediation.',
                '<strong>🟢 Fail ➔ Pass (RESOLVED):</strong> Previously breached transactions that recovered within SLA.',
                '<strong>🟠 Fail ➔ Fail (PERSISTENT):</strong> Chronic SLA violations requiring deep performance tuning.'
            ],
            filters: '<strong>Click any matrix card</strong> to instantly filter the Critical Transactions Table below to only that specific transition quadrant!'
        }},
        'comp-rt-table': {{
            title: '📋 Per-Transaction Differential Analytics Table',
            what: 'Granular comparison table listing all transactions with status badges, Baseline vs Current averages, millisecond diffs, percentage changes, P90/P95 latencies, and SLA targets.',
            howToRead: [
                'Status badges classify transactions as IMPROVED, REGRESSED, or UNCHANGED.',
                'Diff (ms) and Change % columns show exact performance variance with color indicators.',
                'P90/P95 columns verify tail latency compliance against target SLAs.'
            ],
            filters: 'Use the <strong>Search input</strong> and quick <strong>Filter Chips</strong> (All, Improved, Regressed, Breached, Unchanged) above the table to filter rows.'
        }},
        'comp-crit-table': {{
            title: '🚨 Critical Transactions &amp; SLA Transitions Table',
            what: 'Focus table dedicated to business-critical transactions, showing SLA target, Baseline P90, Current P90, Breach Margins, and Transition classifications.',
            howToRead: [
                'Breach margin shows exact milliseconds exceeded above the SLA threshold (e.g. +450ms).',
                'Transition pills highlight resolved vs newly breached critical user journeys.'
            ],
            filters: 'Click the 4-Quadrant Matrix cards above to filter this table by transition category.'
        }},
        'calc-methodology': {{
            title: '📐 Calculation Methodology &amp; Reliability Framework',
            what: 'Mathematical formulas and industry-standard definitions used across all metrics in this report.',
            howToRead: [
                'Explains APDEX formula: (Satisfied + (Tolerating / 2)) / Total.',
                'Defines SLA Deviation %: ((Actual P90 - Target P90) / Target P90) * 100.',
                'Details Percentiles (P90, P95, P99) and Little\\'s Law Concurrency calculations.'
            ],
            filters: 'Use as a standard reference for metric auditing and methodology alignment.'
        }}
    }};

    """
