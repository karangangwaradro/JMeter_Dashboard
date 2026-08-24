/* compare.js — Interactive Controller for Professional 2-Run Comparison Workspace */

let currentCompareRunsData = null;
let compareHierarchy = {};
let currentTxSortMode = "degradation"; // "degradation" | "delta_pct" | "rt_b"

document.addEventListener("DOMContentLoaded", () => {
    initCompareRunsModule();
});

function initCompareRunsModule() {
    loadCompareRunsList();
    loadCompareHierarchy();
}

async function loadCompareHierarchy() {
    try {
        const res = await fetch("/api/trend/hierarchy");
        const data = await res.json();
        if (data.success && data.hierarchy) {
            compareHierarchy = data.hierarchy;
            populateCompareStoryOptions();
        }
    } catch (e) {
        console.error("Failed to load hierarchy for compare:", e);
    }
}

async function loadCompareRunsList() {
    try {
        const res = await fetch("/api/comparison/runs");
        const data = await res.json();
        if (data.success && data.runs && data.runs.length > 0) {
            populateCompareRunDropdowns(data.runs);
        }
    } catch (e) {
        console.error("Failed to load runs for comparison:", e);
    }
}

function populateCompareRunDropdowns(runs) {
    const selA = document.getElementById("comp-run-a-select");
    const selB = document.getElementById("comp-run-b-select");
    if (!selA || !selB) return;

    selA.innerHTML = "";
    selB.innerHTML = "";

    runs.forEach((r, idx) => {
        const title = `${r.id} (${r.users || 1} Users — ${r.timestamp ? r.timestamp.slice(0, 16) : ''})`;
        const optA = document.createElement("option");
        optA.value = r.id;
        optA.textContent = title;

        const optB = document.createElement("option");
        optB.value = r.id;
        optB.textContent = title;

        selA.appendChild(optA);
        selB.appendChild(optB);
    });

    if (runs.length >= 2) {
        selA.selectedIndex = 1;
        selB.selectedIndex = 0;
    } else {
        selA.selectedIndex = 0;
        selB.selectedIndex = 0;
    }

    fetchAndRenderRunComparison();
}

function swapComparisonRuns() {
    const selA = document.getElementById("comp-run-a-select");
    const selB = document.getElementById("comp-run-b-select");
    if (!selA || !selB) return;

    const tmp = selA.value;
    selA.value = selB.value;
    selB.value = tmp;

    fetchAndRenderRunComparison();
}

function populateCompareStoryOptions() {
    const storySel = document.getElementById("comp-run-story-select");
    if (!storySel) return;

    storySel.innerHTML = '<option value="">All User Stories</option>';
    const stories = new Set();
    Object.values(compareHierarchy).forEach(pStories => {
        Object.keys(pStories).forEach(s => stories.add(s));
    });

    Array.from(stories).sort().forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        storySel.appendChild(opt);
    });
}

async function fetchAndRenderRunComparison() {
    const runA = document.getElementById("comp-run-a-select")?.value || "";
    const runB = document.getElementById("comp-run-b-select")?.value || "";
    const story = document.getElementById("comp-run-story-select")?.value || "";
    const iType = document.getElementById("comp-run-type-select")?.value || "TRANSACTIONS_ONLY";

    if (!runA || !runB) return;

    const url = `/api/comparison/data?run_a=${encodeURIComponent(runA)}&run_b=${encodeURIComponent(runB)}&user_story=${encodeURIComponent(story)}&item_type=${encodeURIComponent(iType)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            currentCompareRunsData = data;
            renderRunComparisonUI(data);
        } else {
            console.warn("Comparison response unsuccessful:", data.message);
        }
    } catch (e) {
        console.error("Error fetching run comparison:", e);
    }
}

function renderRunComparisonUI(data) {
    const meta = data.metadata || {};
    const card = data.scorecard || {};
    const obs = data.graph_observations || {};
    const findings = data.ai_findings || [];
    const rows = data.transaction_comparisons || [];
    const trans = data.sla_transitions || {};
    const rankings = data.rankings || {};

    // 0. Executive Findings
    const bulletsList = document.getElementById("compare-ai-bullets");
    if (bulletsList) {
        bulletsList.innerHTML = findings.map(b => `<li>${b.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</li>`).join("");
    }

    // 1. Overall Performance Split Cards
    renderOverallPerformanceCards(card, obs);

    // 2. Response Time Change % (Hero Diverging Chart)
    renderDivergingRtChange(rows, obs);

    // 3. SLA Compliance Comparison (100% Stacked Bar)
    renderSlaComplianceStacked(card, obs);

    // 4. SLA Status Transition Matrix (4-Quadrant)
    renderSlaTransitionMatrix(trans, obs);

    // 5. Throughput & Error Rate Comparison
    renderThroughputAndErrorCharts(rows, card, obs);

    // 6. Percentile Distribution Progression
    renderPercentileProgression(rows, obs);

    // 7. Transaction Performance Heatmap Matrix
    renderTxPerformanceHeatmap(rows, obs);

    // 8. Detailed Comparison Table & Rankings
    renderCompareMainTable(rows);
    renderCompareRankings(rankings);
}

// 1. Overall Performance Split Cards
function renderOverallPerformanceCards(card, obs) {
    const container = document.getElementById("comp-overall-cards-container");
    const obsEl = document.getElementById("comp-obs-overall");
    if (!container || !card) return;

    const cards = [
        { title: "Average Response Time", valA: card.run_a_rt, valB: card.run_b_rt, delta: card.rt_change_pct, unit: "ms", inv: false },
        { title: "P95 Response Time", valA: card.run_a_p95, valB: card.run_b_p95, delta: card.p95_change_pct, unit: "ms", inv: false },
        { title: "P99 Response Time", valA: card.run_a_p99, valB: card.run_b_p99, delta: card.p99_change_pct, unit: "ms", inv: false },
        { title: "Aggregate Throughput", valA: card.run_a_tps, valB: card.run_b_tps, delta: card.tps_change_pct, unit: " TPS", inv: true },
        { title: "Error Rate", valA: card.run_a_err, valB: card.run_b_err, delta: card.err_change_pp, unit: "%", isPp: true, inv: false }
    ];

    container.innerHTML = cards.map(c => {
        const isBad = c.inv ? c.delta < 0 : c.delta > 0;
        const isGood = c.inv ? c.delta > 0 : c.delta < 0;
        const dClass = isBad ? "delta-degraded" : (isGood ? "delta-improved" : "delta-neutral");
        const sign = c.delta > 0 ? "+" : "";

        return `
        <div class="split-perf-card">
            <div class="split-perf-lbl">${c.title}</div>
            <div class="split-perf-val">${c.valA.toFixed(1)}${c.unit} → ${c.valB.toFixed(1)}${c.unit}</div>
            <div class="split-perf-delta ${dClass}">
                ${sign}${c.delta.toFixed(2)}${c.isPp ? ' pp' : '%'}
            </div>
        </div>
        `;
    }).join("");

    if (obsEl) obsEl.textContent = obs.overall_performance || "";
}

// Hero Diverging Chart: Response Time Change %
let currentDivergingSortMode = "degradation"; // "degradation" | "delta_pct" | "hierarchy"

function setDivergingSortMode(mode) {
    currentDivergingSortMode = mode;
    document.querySelectorAll(".sort-btn-tx").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
    });
    if (currentCompareRunsData) {
        renderDivergingRtChange(currentCompareRunsData.transaction_comparisons, currentCompareRunsData.graph_observations);
    }
}

function renderDivergingRtChange(rows, obs) {
    const container = document.getElementById("comp-diverging-rt-container");
    const obsEl = document.getElementById("comp-obs-diverging");
    if (!container || !rows) return;

    let sorted = [...rows];
    if (currentDivergingSortMode === "degradation") {
        sorted.sort((a,b) => b.rt_delta_pct - a.rt_delta_pct);
    } else if (currentDivergingSortMode === "delta_pct") {
        sorted.sort((a,b) => Math.abs(b.rt_delta_pct) - Math.abs(a.rt_delta_pct));
    }
    // "hierarchy" keeps the original JMX order

    const maxDelta = Math.max(...rows.map(r => Math.abs(r.rt_delta_pct)), 10);

    container.innerHTML = sorted.map(r => {
        const d = r.rt_delta_pct;
        const bCls = r.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (r.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
        const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN" : (r.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");
        const barW = Math.min((Math.abs(d) / maxDelta) * 100, 100);

        return `
        <div class="diverging-row">
            <div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:flex; align-items:center; gap:0.3rem;" title="${r.transaction}">
                <span class="badge ${bCls}">${bLbl}</span>
                <strong>${r.transaction}</strong>
            </div>
            <div class="diverging-left-lane">
                ${d < 0 ? `<div class="diverging-bar-imp" style="width:${barW}%;" title="Improvement: ${d.toFixed(1)}%"></div>` : ''}
            </div>
            <div class="diverging-right-lane">
                ${d > 0 ? `<div class="diverging-bar-deg" style="width:${barW}%;" title="Degradation: +${d.toFixed(1)}%"></div>` : ''}
            </div>
            <div style="text-align:right; font-weight:bold; color:${d > 0 ? '#dc2626' : (d < 0 ? '#059669' : '#64748b')};">
                ${d > 0 ? '+' : ''}${d.toFixed(1)}%
            </div>
        </div>
        `;
    }).join("");

    if (obsEl) obsEl.textContent = obs.rt_change_diverging || "";
}

// 4. SLA Compliance Comparison (100% Stacked Bar)
function renderSlaComplianceStacked(card, obs) {
    const container = document.getElementById("comp-sla-stacked-container");
    const obsEl = document.getElementById("comp-obs-sla-stacked");
    if (!container || !card) return;

    const aPass = card.run_a_sla_pass;
    const aBreach = Math.max(0, 100 - aPass);
    const bPass = card.run_b_sla_pass;
    const bBreach = Math.max(0, 100 - bPass);

    container.innerHTML = `
    <div style="margin-bottom:0.75rem;">
        <div style="font-size:0.75rem; font-weight:bold; color:#64748b; margin-bottom:0.2rem;">Run A (Baseline) — ${aPass.toFixed(1)}% Pass Rate</div>
        <div class="sla-stacked-bar-track">
            <div class="sla-stack-pass" style="width:${aPass}%;">${aPass.toFixed(0)}% Pass</div>
            <div class="sla-stack-breach" style="width:${aBreach}%;">${aBreach > 0 ? aBreach.toFixed(0) + '% Breach' : ''}</div>
        </div>
    </div>
    <div>
        <div style="font-size:0.75rem; font-weight:bold; color:#64748b; margin-bottom:0.2rem;">Run B (Target) — ${bPass.toFixed(1)}% Pass Rate</div>
        <div class="sla-stacked-bar-track">
            <div class="sla-stack-pass" style="width:${bPass}%;">${bPass.toFixed(0)}% Pass</div>
            <div class="sla-stack-breach" style="width:${bBreach}%;">${bBreach > 0 ? bBreach.toFixed(0) + '% Breach' : ''}</div>
        </div>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.75rem; font-size:0.85rem; font-weight:700;">
        <span>Compliance Shift: ${aPass.toFixed(1)}% → ${bPass.toFixed(1)}%</span>
        <span style="color:${card.sla_pass_change_pp >= 0 ? '#059669' : '#dc2626'};">${card.sla_pass_change_pp > 0 ? '+' : ''}${card.sla_pass_change_pp.toFixed(1)} pp</span>
    </div>
    `;

    if (obsEl) obsEl.textContent = obs.sla_compliance_stacked || "";
}

// 5. SLA Status Transition Matrix (4-Quadrant)
function renderSlaTransitionMatrix(trans, obs) {
    const setBox = (id, count) => {
        const el = document.getElementById(id);
        if (el) el.textContent = count;
    };

    setBox("trans-cnt-pass-pass", trans.persistent_passes?.length || 0);
    setBox("trans-cnt-pass-fail", trans.new_breaches?.length || 0);
    setBox("trans-cnt-fail-pass", trans.resolved_breaches?.length || 0);
    setBox("trans-cnt-fail-fail", trans.persistent_breaches?.length || 0);

    const obsEl = document.getElementById("comp-obs-sla-transition");
    if (obsEl) obsEl.textContent = obs.sla_transition_matrix || "";
}

// 5. Throughput & Error Rate Comparison
function renderThroughputAndErrorCharts(rows, card, obs) {
    const tpsContainer = document.getElementById("comp-tps-container");
    const tpsObsEl = document.getElementById("comp-obs-throughput");
    const errContainer = document.getElementById("comp-err-container");

    if (tpsContainer && rows) {
        const maxTps = Math.max(...rows.map(r => Math.max(r.run_a_tps, r.run_b_tps)), 10);
        tpsContainer.innerHTML = rows.map(r => {
            const pctA = (r.run_a_tps / maxTps) * 100;
            const pctB = (r.run_b_tps / maxTps) * 100;
            const d = r.tps_delta_pct;
            const bCls = r.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (r.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
            const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN" : (r.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");
            return `
            <div class="grouped-bar-row">
                <div style="font-size:0.8rem; font-weight:600; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:flex; align-items:center; gap:0.35rem;" title="${r.transaction}">
                    <span class="badge ${bCls}">${bLbl}</span>
                    <span>${r.transaction}</span>
                </div>
                <div class="grouped-bar-track">
                    <div class="bar-fill-a" style="width:${pctA}%;" title="Run A: ${r.run_a_tps.toFixed(1)} TPS"></div>
                    <div class="bar-fill-b" style="width:${pctB}%; background:#059669;" title="Run B: ${r.run_b_tps.toFixed(1)} TPS"></div>
                </div>
                <div style="text-align:right; font-weight:bold; font-size:0.8rem; color:${d >= 0 ? '#059669' : '#dc2626'};">${d > 0 ? '+' : ''}${d.toFixed(1)}%</div>
            </div>
            `;
        }).join("");
    }

    if (errContainer && rows) {
        const maxErr = Math.max(...rows.map(r => Math.max(r.run_a_err, r.run_b_err)), 5);
        errContainer.innerHTML = rows.map(r => {
            const pctA = (r.run_a_err / maxErr) * 100;
            const pctB = (r.run_b_err / maxErr) * 100;
            const d = r.err_delta_pp;
            const bCls = r.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (r.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
            const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN" : (r.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");
            return `
            <div class="grouped-bar-row">
                <div style="font-size:0.8rem; font-weight:600; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:flex; align-items:center; gap:0.35rem;" title="${r.transaction}">
                    <span class="badge ${bCls}">${bLbl}</span>
                    <span>${r.transaction}</span>
                </div>
                <div class="grouped-bar-track">
                    <div class="bar-fill-a" style="width:${pctA}%;" title="Run A: ${r.run_a_err.toFixed(2)}%"></div>
                    <div class="bar-fill-b" style="width:${pctB}%; background:#dc2626;" title="Run B: ${r.run_b_err.toFixed(2)}%"></div>
                </div>
                <div style="text-align:right; font-weight:bold; font-size:0.8rem; color:${d > 0 ? '#dc2626' : (d < 0 ? '#059669' : '#64748b')};">${d > 0 ? '+' : ''}${d.toFixed(2)} pp</div>
            </div>
            `;
        }).join("");
    }

    if (tpsObsEl) tpsObsEl.textContent = obs.throughput_grouped || "";
}

// 8. Percentile Distribution Progression (P50 -> P90 -> P95 -> P99)
function renderPercentileProgression(rows, obs) {
    const tbody = document.getElementById("comp-pct-tbody");
    const obsEl = document.getElementById("comp-obs-percentiles");
    if (!tbody || !rows) return;

    tbody.innerHTML = rows.slice(0, 12).map(r => {
        const p = r.percentiles;
        const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN" : (r.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");
        return `
        <tr>
            <td><strong>[${bLbl}] ${r.transaction}</strong></td>
            <td style="text-align:right;">${p.p50.run_a.toFixed(0)}ms → ${p.p50.run_b.toFixed(0)}ms <small style="color:${p.p50.delta_pct > 0 ? '#dc2626' : '#059669'};">(${p.p50.delta_pct > 0 ? '+' : ''}${p.p50.delta_pct.toFixed(1)}%)</small></td>
            <td style="text-align:right;">${p.p90.run_a.toFixed(0)}ms → ${p.p90.run_b.toFixed(0)}ms <small style="color:${p.p90.delta_pct > 0 ? '#dc2626' : '#059669'};">(${p.p90.delta_pct > 0 ? '+' : ''}${p.p90.delta_pct.toFixed(1)}%)</small></td>
            <td style="text-align:right; font-weight:bold;">${p.p95.run_a.toFixed(0)}ms → ${p.p95.run_b.toFixed(0)}ms <small style="color:${p.p95.delta_pct > 0 ? '#dc2626' : '#059669'};">(${p.p95.delta_pct > 0 ? '+' : ''}${p.p95.delta_pct.toFixed(1)}%)</small></td>
            <td style="text-align:right;">${p.p99.run_a.toFixed(0)}ms → ${p.p99.run_b.toFixed(0)}ms <small style="color:${p.p99.delta_pct > 0 ? '#dc2626' : '#059669'};">(${p.p99.delta_pct > 0 ? '+' : ''}${p.p99.delta_pct.toFixed(1)}%)</small></td>
        </tr>
        `;
    }).join("");

    if (obsEl) obsEl.textContent = obs.percentile_distribution || "";
}

// 9. Transaction Performance Heatmap Matrix (Tx x [RT, P95, TPS, Errors, SLA])
function renderTxPerformanceHeatmap(rows, obs) {
    const tbody = document.getElementById("comp-matrix-tbody");
    const obsEl = document.getElementById("comp-obs-matrix");
    if (!tbody || !rows) return;

    tbody.innerHTML = rows.map(r => {
        const s = r.matrix_states;
        const getPill = (st, txt) => {
            const cls = st === "improved" ? "state-pill-imp" : (st === "degraded" ? "state-pill-deg" : "state-pill-unch");
            return `<span class="state-pill ${cls}">${txt}</span>`;
        };

        const bCls = r.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (r.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
        const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN" : (r.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");

        return `
        <tr>
            <td><div style="display:flex; align-items:center; gap:0.35rem;"><span class="badge ${bCls}">${bLbl}</span><strong>${r.transaction}</strong></div></td>
            <td style="text-align:center;">${getPill(s.rt, r.rt_delta_pct > 0 ? '+' + r.rt_delta_pct.toFixed(1) + '%' : r.rt_delta_pct.toFixed(1) + '%')}</td>
            <td style="text-align:center;">${getPill(s.p95, r.percentiles.p95.delta_pct > 0 ? '+' + r.percentiles.p95.delta_pct.toFixed(1) + '%' : r.percentiles.p95.delta_pct.toFixed(1) + '%')}</td>
            <td style="text-align:center;">${getPill(s.tps, r.tps_delta_pct > 0 ? '+' + r.tps_delta_pct.toFixed(1) + '%' : r.tps_delta_pct.toFixed(1) + '%')}</td>
            <td style="text-align:center;">${getPill(s.errors, r.err_delta_pp > 0 ? '+' + r.err_delta_pp.toFixed(2) + 'pp' : '0.00pp')}</td>
            <td style="text-align:center;"><span class="badge badge-${r.run_b_status === 'Pass' ? 'good' : 'critical'}">${r.run_b_status}</span></td>
        </tr>
        `;
    }).join("");

    if (obsEl) obsEl.textContent = obs.tx_performance_heatmap || "";
}

// 10. Detailed Table & Rankings
function renderCompareMainTable(rows) {
    const tbody = document.getElementById("compare-main-tbody");
    if (!tbody || !rows) return;

    tbody.innerHTML = rows.map(r => {
        const d = r.rt_delta_pct;
        const dCol = d > 0 ? "#dc2626" : "#059669";
        const depth = r.depth || 0;
        const indent = depth * 18;
        const bCls = r.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (r.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
        const bLbl = r.item_type === "MAIN_TRANSACTION" ? "MAIN TX" : (r.item_type === "SUB_TRANSACTION" ? "SUB TX" : "REQ");
        const stCls = r.status_change === "New Breach" ? "badge-status-new-breach" : (r.status_change === "Resolved Breach" ? "badge-status-resolved" : (r.status_change === "Degraded" ? "badge-status-degraded" : (r.status_change === "Improved" ? "badge-status-improved" : "badge-status-unchanged")));

        return `
        <tr>
            <td>
                <div style="padding-left:${indent}px; display:flex; align-items:center; gap:0.4rem;">
                    <span class="badge ${bCls}">${bLbl}</span>
                    <span>${depth > 0 ? '↳ ' : ''}<strong>${r.is_critical ? '🔥 ' : ''}${r.transaction}</strong></span>
                </div>
            </td>
            <td><small style="color:#64748b;">${r.user_story}</small></td>
            <td style="text-align:right;">${r.run_a_rt.toFixed(2)} ms</td>
            <td style="text-align:right;">${r.run_b_rt.toFixed(2)} ms</td>
            <td style="text-align:right; font-weight:bold; color:${dCol};">${d > 0 ? '+' : ''}${d.toFixed(2)}%</td>
            <td style="text-align:right;">${r.run_a_tps.toFixed(2)} / ${r.run_b_tps.toFixed(2)}</td>
            <td style="text-align:right;">${r.sla_target.toFixed(0)} ms</td>
            <td style="text-align:center;"><span class="badge badge-${r.run_a_status === 'Pass' ? 'good' : 'critical'}">${r.run_a_status}</span></td>
            <td style="text-align:center;"><span class="badge badge-${r.run_b_status === 'Pass' ? 'good' : 'critical'}">${r.run_b_status}</span></td>
            <td style="text-align:center;"><span class="badge ${stCls}">${r.status_change}</span></td>
        </tr>
        `;
    }).join("");
}

function switchCompareRankingsTab(tabKey) {
    document.querySelectorAll(".compare-rank-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-tab") === tabKey);
    });
    if (currentCompareRunsData && currentCompareRunsData.rankings) {
        renderCompareRankingsTable(tabKey, currentCompareRunsData.rankings[tabKey]);
    }
}

function renderCompareRankings(rankings) {
    if (!rankings) return;
    renderCompareRankingsTable("biggest_degradation", rankings.biggest_degradation);
}

function renderCompareRankingsTable(type, list) {
    const tbody = document.getElementById("compare-rank-tbody");
    if (!tbody || !list) return;

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#64748b;">No items recorded in this ranking.</td></tr>';
        return;
    }

    tbody.innerHTML = list.map(item => {
        let metricCol = "";
        if (type === "biggest_degradation") {
            metricCol = `<span style="color:#dc2626; font-weight:bold;">+${item.delta_pct.toFixed(2)}%</span> (${item.run_a_rt.toFixed(0)}ms → ${item.run_b_rt.toFixed(0)}ms)`;
        } else if (type === "biggest_improvement") {
            metricCol = `<span style="color:#059669; font-weight:bold;">-${item.improvement_pct.toFixed(2)}%</span> (${item.run_a_rt.toFixed(0)}ms → ${item.run_b_rt.toFixed(0)}ms)`;
        } else if (type === "largest_sla_breach") {
            metricCol = `<span style="color:#dc2626; font-weight:bold;">+${item.breach_margin_ms.toFixed(0)}ms</span> over SLA (${item.sla_target}ms)`;
        } else if (type === "largest_throughput_change") {
            metricCol = `<span style="font-weight:bold;">${item.tps_delta_pct > 0 ? '+' : ''}${item.tps_delta_pct.toFixed(2)}%</span> (${item.run_a_tps.toFixed(2)} → ${item.run_b_tps.toFixed(2)} TPS)`;
        } else {
            metricCol = `<span style="color:#dc2626; font-weight:bold;">${item.err_delta_pp > 0 ? '+' : ''}${item.err_delta_pp.toFixed(2)} pp</span> (${item.run_b_errors} errors in Run B)`;
        }

        return `
        <tr>
            <td style="font-weight:bold; width:50px;">#${item.rank}</td>
            <td><strong>${item.transaction}</strong></td>
            <td><span class="badge ${item.item_type === 'MAIN_TRANSACTION' ? 'badge-main-tx' : (item.item_type === 'SUB_TRANSACTION' ? 'badge-sub-tx' : 'badge-req')}">${item.item_type === 'MAIN_TRANSACTION' ? 'MAIN TX' : (item.item_type === 'SUB_TRANSACTION' ? 'SUB TX' : 'REQ')}</span></td>
            <td style="text-align:right;">${metricCol}</td>
        </tr>
        `;
    }).join("");
}

async function exportRunComparisonHTML() {
    const runA = document.getElementById("comp-run-a-select")?.value || "";
    const runB = document.getElementById("comp-run-b-select")?.value || "";
    const story = document.getElementById("comp-run-story-select")?.value || "";
    const iType = document.getElementById("comp-run-type-select")?.value || "TRANSACTIONS_ONLY";

    try {
        const res = await fetch("/api/comparison/generate-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                run_a: runA,
                run_b: runB,
                user_story: story,
                item_type: iType
            })
        });
        const data = await res.json();
        if (data.success && data.url) {
            window.open(data.url, "_blank");
        } else {
            alert("Failed to export report: " + (data.message || "Unknown error"));
        }
    } catch (e) {
        alert("Export error: " + e.message);
    }
}
