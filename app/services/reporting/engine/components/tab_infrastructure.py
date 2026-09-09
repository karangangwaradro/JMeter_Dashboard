#!/usr/bin/env python3
"""Tab 6: Infrastructure metrics & client-server correlation."""
import json
import re

def render_tab_infrastructure(ctx: dict) -> str:
    """Render this HTML section from context."""
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

    return f"""<div id="rpt-infra" class="tab-pane hidden">
        {tab_infra_panel_html}
        
        <!-- 1. Top Health KPI Cards -->
        <div class="section glass-panel" style="margin-bottom:1.5rem; position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('azure-kpi-cards')" title="How to read Azure Telemetry KPIs">ℹ️</button>
            <h3 style="margin:0 0 1rem 0; font-size:1.05rem; font-weight:700; padding-right:2.5rem;">🖥️ Azure Host Infrastructure Telemetry</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #f59e0b;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK CPU UTILIZATION</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_cpu_val}%</div>
                    <div style="font-size: 0.7rem; color: {'#ef4444' if peak_cpu_val >= 80 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ High CPU Pressure' if peak_cpu_val >= 80 else 'Healthy'}</div>
                </div>

                <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #3b82f6;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK MEMORY UTILIZATION</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_mem_val}%</div>
                    <div style="font-size: 0.7rem; color: {'#ef4444' if peak_mem_val >= 80 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ High Memory Pressure' if peak_mem_val >= 80 else 'Healthy'}</div>
                </div>

                <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #8b5cf6;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">PEAK DISK QUEUE DEPTH</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{peak_disk_q_val}</div>
                    <div style="font-size: 0.7rem; color: {'#ef4444' if peak_disk_q_val >= 5.0 else '#10b981'}; margin-top: 0.2rem;">{'⚠️ Storage Contention' if peak_disk_q_val >= 5.0 else 'Optimal I/O'}</div>
                </div>

                <div class="glass-panel" style="padding: 1.1rem; border-radius: 12px; border-left: 4px solid #10b981;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted);">SYSTEM AVAILABILITY</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: var(--text); margin-top: 0.2rem;">{min_avail_val}%</div>
                    <div style="font-size: 0.7rem; color: {'#10b981' if min_avail_val >= 99.5 else '#ef4444'}; margin-top: 0.2rem;">{'Operational SLA' if min_avail_val >= 99.5 else 'Degraded During Peak'}</div>
                </div>
            </div>
        </div>

        <!-- 2. Main Resource Utilization (CPU & Memory) - Full Width -->
        <div class="chart-box glass-panel" style="position: relative; min-height: 380px; margin-bottom: 1.5rem; padding: 1.25rem; {azure_section_style}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 0.75rem;">
                <div>
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">🖥️ Azure Resource Utilization (CPU &amp; Memory)</h3>
                    <p style="margin:0.2rem 0 0 0; font-size:0.78rem; color:var(--muted);">Dual-line time series tracking host resource pressure thresholds</p>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:0.75rem; font-weight:600; background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); padding:0.25rem 0.6rem; border-radius:12px;">Threshold Bands: 80% / 90%</span>
                    <button class="chart-info-btn" onclick="openGraphModal('azure-cpu-mem')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
            </div>
            
            <div style="position: relative; height: 310px; width: 100%;">
                <canvas id="azChart"></canvas>
            </div>
            
            <p style="margin-top:0.8rem; font-size:0.78rem; color:var(--muted); background:var(--surface2); padding:0.5rem 0.8rem; border-radius:6px; border-left:3px solid var(--accent);">
                <strong>Conclusion:</strong> The server experienced a significant resource utilization spike, with CPU reaching {peak_cpu_val}% and memory reaching {peak_mem_val}%, indicating elevated host-level contention.
            </p>
            {infra_observation_html}
        </div>

        <!-- 3. Dual Charts Grid: Workload vs Resource & Performance Impact -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Workload vs Resource (Throughput vs CPU) -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">📈 Workload vs CPU Utilization</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Aligning JMeter request throughput against Azure host CPU %</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('workload-cpu')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="workloadCpuChart"></canvas>
                </div>
            </div>

            <!-- Performance Impact (Throughput vs Response Time) -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">⚡ Throughput vs Response Time</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Analyzing capacity limits as request load increases</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('tp-rt-impact')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="tpRtChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 4. Storage & Network Subsystem Grid -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Storage I/O & Queue Depth -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">💾 Disk I/O &amp; Queue Contention</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Disk Read/Write throughput (MB/s) vs Disk Queue Depth</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('disk-io')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="diskChart"></canvas>
                </div>
            </div>

            <!-- Network Throughput -->
            <div class="chart-box glass-panel" style="position: relative; min-height: 320px; padding: 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                    <div>
                        <h3 style="margin:0; font-size:1rem; font-weight:700;">🌐 Network Throughput (In/Out)</h3>
                        <p style="margin:0.2rem 0 0 0; font-size:0.75rem; color:var(--muted);">Inbound and Outbound network data transfer rate</p>
                    </div>
                    <button class="chart-info-btn" onclick="openGraphModal('network-tp')" title="How to read this graph &amp; use filters">ℹ️</button>
                </div>
                <div style="position: relative; height: 240px; width: 100%;">
                    <canvas id="netChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 5. Correlation Matrix & Event Timeline Grid -->
        <div class="chart-grid" style="margin-bottom: 1.5rem;">
            <!-- Correlation Matrix Table -->
            <div class="chart-box glass-panel" style="padding: 1.2rem; position:relative;">
                <button class="chart-info-btn" onclick="openGraphModal('infra-correlation')" title="How to read Correlation Matrix">ℹ️</button>
                <div style="padding-right:2.5rem;">
                    <h3 style="margin:0; font-size:1rem; font-weight:700; margin-bottom: 0.3rem;">📊 Infrastructure Correlation Matrix</h3>
                    <p style="font-size:0.75rem; color:var(--muted); margin-bottom: 0.8rem;">Pearson correlation coefficients (r) dynamically calculated from run telemetry</p>
                </div>
                
                <table style="width:100%; border-collapse:collapse; font-size:0.78rem; text-align:center;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border); background:var(--surface2);">
                            <th style="padding:0.4rem; text-align:left;">Signal</th>
                            <th style="padding:0.4rem;">CPU</th>
                            <th style="padding:0.4rem;">Memory</th>
                            <th style="padding:0.4rem;">Throughput</th>
                            <th style="padding:0.4rem;">Resp Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">CPU %</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_mem) >= 0.7 else 'var(--text)'};">{r_cpu_mem:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_tp) >= 0.7 else 'var(--text)'};">{r_cpu_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_rt) >= 0.7 else 'var(--text)'};">{r_cpu_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Memory %</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_mem) >= 0.7 else 'var(--text)'};">{r_cpu_mem:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_tp) >= 0.7 else 'var(--text)'};">{r_mem_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_rt) >= 0.7 else 'var(--text)'};">{r_mem_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Throughput</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_tp) >= 0.7 else 'var(--text)'};">{r_cpu_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_tp) >= 0.7 else 'var(--text)'};">{r_mem_tp:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_tp_rt) >= 0.7 else 'var(--text)'}; background:rgba(16,185,129,0.15);">{r_tp_rt:.2f}</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:0.4rem; font-weight:600; text-align:left;">Resp Time</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_cpu_rt) >= 0.7 else 'var(--text)'};">{r_cpu_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_mem_rt) >= 0.7 else 'var(--text)'};">{r_mem_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; color:{'#10b981' if abs(r_tp_rt) >= 0.7 else 'var(--text)'}; background:rgba(16,185,129,0.15);">{r_tp_rt:.2f}</td>
                            <td style="padding:0.4rem; font-weight:700; background:rgba(59,130,246,0.15);">1.00</td>
                        </tr>
                    </tbody>
                </table>
                <p style="font-size:0.7rem; color:var(--muted); margin-top:0.6rem;">💡 <em>Calculated correlation between request volume and response latency: <strong>r = {r_tp_rt:.2f}</strong>.</em></p>
            </div>

            <!-- Chronological Event Progression Timeline -->
            <div class="chart-box glass-panel" style="padding: 1.2rem; position:relative;">
                <button class="chart-info-btn" onclick="openGraphModal('timeline-events')" title="How to read Incident Timeline">ℹ️</button>
                <div style="padding-right:2.5rem;">
                    <h3 style="margin:0; font-size:1rem; font-weight:700; margin-bottom: 0.3rem;">⏱️ Performance Incident Timeline</h3>
                    <p style="font-size:0.75rem; color:var(--muted); margin-bottom: 0.8rem;">Sequential degradation events during test execution</p>
                </div>
                
                <div style="display:flex; flex-direction:column; gap:0.6rem; font-size:0.78rem;">
                    {timeline_html}
                </div>
            </div>
        </div>

        <!-- 6. AI Infrastructure Diagnostic Summary Card -->
        <div class="chart-box glass-panel ai-sub-card" style="padding: 1.25rem; border-left: 4px solid var(--accent); margin-bottom: 1.5rem; position:relative;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <h3 style="margin:0; font-size:1.05rem; font-weight:700;">🧠 Infrastructure Diagnostic Analysis</h3>
                    <button class="chart-info-btn" onclick="openGraphModal('infra-findings')" title="How to read Diagnostic Analysis">ℹ️</button>
                </div>
                {_build_validation_badge("infra_diagnostic_card")}
            </div>
            
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-top:0.85rem; font-size:0.78rem;">
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#ef4444; margin-bottom:0.2rem;">🔴 Primary Signal</div>
                    <p style="margin:0; color:var(--text);">CPU utilization reached <strong>{peak_cpu_val}%</strong> peak pressure during high-throughput interval.</p>
                </div>
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#f59e0b; margin-bottom:0.2rem;">Associated Signals</div>
                    <p style="margin:0; color:var(--text);">Memory reached <strong>{peak_mem_val}%</strong>, Disk Queue depth reached <strong>{peak_disk_q_val}</strong>, and SLA breaches occurred.</p>
                </div>
                <div style="background:var(--surface2); padding:0.75rem; border-radius:8px; border:1px solid var(--border);">
                    <div style="font-weight:700; color:#3b82f6; margin-bottom:0.2rem;">🔍 Likely Root Cause</div>
                    <p style="margin:0; color:var(--text);">Workload-driven host CPU &amp; memory contention under concurrent user load.</p>
                </div>
            </div>
        </div>

        <!-- Correlation Findings List -->
        <div class="section glass-panel" style="position:relative;">
            <button class="chart-info-btn" onclick="openGraphModal('corr-findings')" title="How to read Correlation Findings">ℹ️</button>
            <h2 style="margin:0 0 1rem 0; padding-right:2.5rem;">🔗 Client ↔ Server Correlation Findings</h2>
            {corr_html}
        </div>
    </div>

    <!-- TAB 7: Run Comparison -->
    """
