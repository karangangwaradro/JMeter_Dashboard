/* trend.js — Lightweight Historical Trend Analysis Controller */

let currentTrendData = null;
let trendHierarchy = {};

document.addEventListener("DOMContentLoaded", () => {
    initTrendModule();
});

function initTrendModule() {
    loadTrendHierarchy();
}

async function loadTrendHierarchy() {
    try {
        const res = await fetch("/api/trend/hierarchy");
        const data = await res.json();
        if (data.success && data.hierarchy) {
            trendHierarchy = data.hierarchy;
            populateTrendFilters();
        }
    } catch (err) {
        console.error("Failed to load hierarchy for trend:", err);
    }
}

function populateTrendFilters() {
    const projSelect = document.getElementById("trend-project-select");
    if (!projSelect) return;

    projSelect.innerHTML = '<option value="">All Projects</option>';
    Object.keys(trendHierarchy).forEach(proj => {
        const opt = document.createElement("option");
        opt.value = proj;
        opt.textContent = proj;
        projSelect.appendChild(opt);
    });

    updateTrendStoryOptions();
    fetchAndRenderTrend();
}

function onTrendProjectChange() {
    updateTrendStoryOptions();
    fetchAndRenderTrend();
}

function updateTrendStoryOptions() {
    const projSelect = document.getElementById("trend-project-select");
    const storySelect = document.getElementById("trend-story-select");
    if (!storySelect) return;

    const selectedProj = projSelect ? projSelect.value : "";
    const curVal = storySelect.value;
    storySelect.innerHTML = '<option value="">All User Stories</option>';

    let storiesToPopulate = new Set();
    if (selectedProj && trendHierarchy[selectedProj]) {
        Object.keys(trendHierarchy[selectedProj]).forEach(s => storiesToPopulate.add(s));
    } else {
        Object.values(trendHierarchy).forEach(projStories => {
            Object.keys(projStories).forEach(s => storiesToPopulate.add(s));
        });
    }

    Array.from(storiesToPopulate).sort().forEach(story => {
        const opt = document.createElement("option");
        opt.value = story;
        opt.textContent = story;
        if (story === curVal) opt.selected = true;
        storySelect.appendChild(opt);
    });
}

async function fetchAndRenderTrend() {
    const proj = document.getElementById("trend-project-select")?.value || "";
    const story = document.getElementById("trend-story-select")?.value || "";
    const itemType = document.getElementById("trend-type-select")?.value || "TRANSACTIONS_ONLY";
    const limit = document.getElementById("trend-limit-select")?.value || "10";

    const url = `/api/trend/analysis?project=${encodeURIComponent(proj)}&user_story=${encodeURIComponent(story)}&item_type=${encodeURIComponent(itemType)}&limit=${limit}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            currentTrendData = data;
            renderTrendUI(data);
        } else {
            console.warn("Trend analysis unsuccessful:", data.message);
        }
    } catch (err) {
        console.error("Failed to fetch trend analysis:", err);
    }
}

function renderTrendUI(data) {
    const kpis = data.kpis || {};
    const obs = data.ai_observations || [];
    const nodes = data.release_nodes || [];
    const multi = data.multi_series || {};
    const heatmap = data.heatmap || {};
    const sevDist = data.severity_distribution || [];
    const bVsC = data.baseline_vs_current || [];

    // 1. Release Ribbon
    renderTrendReleaseRibbon(nodes);

    // 2. Management KPI Cards
    const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    setTxt("trend-kpi-current-rt", `${kpis.current_rt?.toFixed(1) || 0} ms`);
    const trendDeltaEl = document.getElementById("trend-kpi-delta");
    if (trendDeltaEl) {
        const d = kpis.overall_trend_pct || 0;
        trendDeltaEl.className = `trend-kpi-delta ${d > 0 ? 'delta-degraded' : 'delta-improved'}`;
        trendDeltaEl.textContent = `${d > 0 ? '↑' : '↓'} ${Math.abs(d).toFixed(1)}% across ${kpis.releases_analyzed} releases`;
    }
    setTxt("trend-kpi-sla-pass", `${kpis.current_sla_pass_rate?.toFixed(1) || 100}%`);
    setTxt("trend-kpi-sla-status", `Status: ${kpis.current_sla_status || 'Good'}`);
    setTxt("trend-kpi-best-rel", kpis.best_release || "R1");
    setTxt("trend-kpi-worst-rel", kpis.worst_release || "R1");

    // 3. AI Observations
    const obsList = document.getElementById("trend-ai-bullets");
    if (obsList) {
        obsList.innerHTML = obs.map(o => `<li>${o.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</li>`).join("");
    }

    // 4. Graph 1: Multi-Series Dynamic Performance Trend Explorer
    populateTrendMultiSelectDropdown(multi);
    renderTrendActiveChips(multi);
    renderMultiSeriesTrendChart(multi, nodes);

    // 5. Graph 2: SLA Compliance Trend
    renderTrendGraph2_SLA(nodes);

    // 6. Graph 3: Heatmap Matrix
    renderTrendGraph3_Heatmap(heatmap);

    // 7. Graph 5: Severity Distribution Stack
    renderTrendGraph5_SeverityStack(sevDist);

    // 8. Graph 6: Baseline vs Current Summary
    renderTrendGraph6_BaselineVsCurrent(bVsC);
}

function renderTrendReleaseRibbon(nodes) {
    const container = document.getElementById("trend-release-ribbon");
    if (!container || !nodes) return;

    container.innerHTML = nodes.map((n, i) => `
        <div class="rel-ribbon-node ${n.is_current ? 'node-current' : (n.is_baseline ? 'node-baseline' : '')}">
            <div class="rel-ribbon-code">${n.code}</div>
            <div class="rel-ribbon-users">${n.users} Users</div>
            <div style="font-size:0.75rem; font-weight:700; color:#0284c7; margin-top:2px;">${n.avg_rt.toFixed(0)}ms</div>
        </div>
        ${i < nodes.length - 1 ? '<div class="rel-ribbon-arrow">→</div>' : ''}
    `).join("");
}

// Multi-Series Selection State
let selectedTrendSeriesKeys = new Set(["overall"]);
let selectedTrendMetric = "avg_rt"; // "avg_rt" | "p95" | "p90" | "tps" | "error_rate"

const TREND_SERIES_PALETTE = [
    "#0284c7", // Sky Blue
    "#10b981", // Emerald Green
    "#8b5cf6", // Violet
    "#f59e0b", // Amber
    "#ef4444", // Crimson Red
    "#06b6d4", // Cyan
    "#ec4899", // Pink
    "#6366f1", // Indigo
    "#14b8a6", // Teal
    "#f97316", // Orange
    "#84cc16", // Lime
    "#a855f7"  // Purple
];

// Document click listener to close dropdown when clicking outside
document.addEventListener("click", (e) => {
    const wrap = document.querySelector(".trend-multiselect-wrap");
    const dropdown = document.getElementById("trend-multiselect-dropdown");
    if (wrap && dropdown && !wrap.contains(e.target)) {
        dropdown.classList.add("hidden");
    }
});

function toggleTrendMultiSelectDropdown() {
    const dropdown = document.getElementById("trend-multiselect-dropdown");
    if (dropdown) dropdown.classList.toggle("hidden");
}

function onTrendExplorerMetricChange() {
    const select = document.getElementById("trend-explorer-metric-select");
    if (select) {
        selectedTrendMetric = select.value;
        if (currentTrendData) {
            renderMultiSeriesTrendChart(currentTrendData.multi_series, currentTrendData.release_nodes);
        }
    }
}

function filterTrendMultiSelectOptions(query) {
    const q = (query || "").toLowerCase();
    document.querySelectorAll(".trend-ms-item").forEach(item => {
        const text = item.getAttribute("data-text") || "";
        item.style.display = text.toLowerCase().includes(q) ? "flex" : "none";
    });
}

function populateTrendMultiSelectDropdown(multiSeries) {
    const list = document.getElementById("trend-ms-options-list");
    const badge = document.getElementById("trend-selected-count-badge");
    if (!list || !multiSeries) return;

    let html = `
    <div class="trend-ms-category-title">Overall Scenario</div>
    <label class="trend-ms-item" data-text="Overall Scenario">
        <input type="checkbox" value="overall" ${selectedTrendSeriesKeys.has("overall") ? "checked" : ""} onchange="onTrendSeriesCheckboxChange(this)">
        <div class="trend-ms-item-label">
            <span class="badge badge-good" style="font-size:0.68rem;">OVERALL</span>
            <strong>Overall Scenario</strong>
        </div>
    </label>
    `;

    // Stories
    const stories = multiSeries.stories || {};
    const storyKeys = Object.keys(stories);
    if (storyKeys.length > 0) {
        html += `<div class="trend-ms-category-title">User Stories</div>`;
        storyKeys.forEach(sName => {
            const key = `story:${sName}`;
            html += `
            <label class="trend-ms-item" data-text="Story ${sName}">
                <input type="checkbox" value="${key}" ${selectedTrendSeriesKeys.has(key) ? "checked" : ""} onchange="onTrendSeriesCheckboxChange(this)">
                <div class="trend-ms-item-label">
                    <span class="badge badge-main-tx" style="font-size:0.68rem;">STORY</span>
                    <span>${sName}</span>
                </div>
            </label>
            `;
        });
    }

    // Transactions
    const txs = multiSeries.transactions || {};
    const txKeys = Object.keys(txs);
    if (txKeys.length > 0) {
        html += `<div class="trend-ms-category-title">Individual Transactions</div>`;
        txKeys.forEach(txName => {
            const t = txs[txName];
            const key = `tx:${txName}`;
            const bCls = t.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (t.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
            const bLbl = t.item_type === "MAIN_TRANSACTION" ? "MAIN" : (t.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");
            html += `
            <label class="trend-ms-item" data-text="${txName} ${t.user_story}">
                <input type="checkbox" value="${key}" ${selectedTrendSeriesKeys.has(key) ? "checked" : ""} onchange="onTrendSeriesCheckboxChange(this)">
                <div class="trend-ms-item-label">
                    <span class="badge ${bCls}" style="font-size:0.68rem;">${bLbl}</span>
                    <span title="${txName}">${txName}</span>
                </div>
            </label>
            `;
        });
    }

    list.innerHTML = html;
    if (badge) badge.textContent = selectedTrendSeriesKeys.size;
}

function onTrendSeriesCheckboxChange(cb) {
    if (cb.checked) {
        selectedTrendSeriesKeys.add(cb.value);
    } else {
        selectedTrendSeriesKeys.delete(cb.value);
        if (selectedTrendSeriesKeys.size === 0) {
            selectedTrendSeriesKeys.add("overall");
            const overallCb = document.querySelector('input[value="overall"]');
            if (overallCb) overallCb.checked = true;
        }
    }
    updateTrendMultiSelectUI();
}

function quickSelectTrendSeries(type) {
    selectedTrendSeriesKeys.clear();
    if (!currentTrendData || !currentTrendData.multi_series) return;
    const ms = currentTrendData.multi_series;

    if (type === "overall") {
        selectedTrendSeriesKeys.add("overall");
    } else if (type === "all_stories") {
        Object.keys(ms.stories || {}).forEach(s => selectedTrendSeriesKeys.add(`story:${s}`));
    } else if (type === "top_tx") {
        const txs = Object.values(ms.transactions || {});
        txs.sort((a,b) => {
            const avgA = (a.data || []).reduce((acc, x) => acc + x.avg_rt, 0) / Math.max((a.data || []).length, 1);
            const avgB = (b.data || []).reduce((acc, x) => acc + x.avg_rt, 0) / Math.max((b.data || []).length, 1);
            return avgB - avgA;
        });
        txs.slice(0, 5).forEach(t => selectedTrendSeriesKeys.add(`tx:${t.name}`));
    } else if (type === "clear") {
        selectedTrendSeriesKeys.add("overall");
    }

    // Update checkboxes
    document.querySelectorAll(".trend-ms-item input[type='checkbox']").forEach(cb => {
        cb.checked = selectedTrendSeriesKeys.has(cb.value);
    });

    updateTrendMultiSelectUI();
}

function removeTrendSeries(key) {
    selectedTrendSeriesKeys.delete(key);
    if (selectedTrendSeriesKeys.size === 0) {
        selectedTrendSeriesKeys.add("overall");
    }
    document.querySelectorAll(".trend-ms-item input[type='checkbox']").forEach(cb => {
        cb.checked = selectedTrendSeriesKeys.has(cb.value);
    });
    updateTrendMultiSelectUI();
}

function updateTrendMultiSelectUI() {
    const badge = document.getElementById("trend-selected-count-badge");
    if (badge) badge.textContent = selectedTrendSeriesKeys.size;
    if (currentTrendData) {
        renderTrendActiveChips(currentTrendData.multi_series);
        renderMultiSeriesTrendChart(currentTrendData.multi_series, currentTrendData.release_nodes);
    }
}

function getSeriesMeta(key, multiSeries) {
    if (key === "overall") {
        return { name: "Overall Scenario", type: "OVERALL", data: multiSeries.overall.data };
    }
    if (key.startsWith("story:")) {
        const sName = key.replace("story:", "");
        return multiSeries.stories[sName] || { name: sName, type: "STORY", data: [] };
    }
    if (key.startsWith("tx:")) {
        const txName = key.replace("tx:", "");
        return multiSeries.transactions[txName] || { name: txName, type: "TX", data: [] };
    }
    return { name: key, type: "UNKNOWN", data: [] };
}

function renderTrendActiveChips(multiSeries) {
    const container = document.getElementById("trend-active-chips-container");
    if (!container || !multiSeries) return;

    let colorIdx = 0;
    const chipsHtml = Array.from(selectedTrendSeriesKeys).map(key => {
        const meta = getSeriesMeta(key, multiSeries);
        const color = TREND_SERIES_PALETTE[colorIdx % TREND_SERIES_PALETTE.length];
        colorIdx++;

        return `
        <div class="trend-series-chip" style="border-left: 3px solid ${color};">
            <span class="trend-chip-dot" style="background:${color};"></span>
            <span title="${meta.name}">${meta.name}</span>
            <button type="button" class="trend-chip-remove" onclick="removeTrendSeries('${key}')" title="Remove series">✕</button>
        </div>
        `;
    }).join("");

    container.innerHTML = chipsHtml || '<span style="font-size:0.8rem; color:#94a3b8;">No series selected (select at least one above).</span>';
}

function renderMultiSeriesTrendChart(multiSeries, releaseNodes) {
    const container = document.getElementById("trend-chart-rt");
    if (!container || !multiSeries || !releaseNodes || releaseNodes.length === 0) return;

    const metric = selectedTrendMetric;
    const metricLabels = {
        "avg_rt": { label: "Average Response Time", unit: "ms" },
        "p95": { label: "P95 Latency", unit: "ms" },
        "p90": { label: "P90 Latency", unit: "ms" },
        "tps": { label: "Throughput", unit: " TPS" },
        "error_rate": { label: "Error Rate", unit: "%" }
    };
    const mInfo = metricLabels[metric] || { label: "Response Time", unit: "ms" };

    // Build active series objects
    let colorIdx = 0;
    const activeSeries = Array.from(selectedTrendSeriesKeys).map(key => {
        const meta = getSeriesMeta(key, multiSeries);
        const color = TREND_SERIES_PALETTE[colorIdx % TREND_SERIES_PALETTE.length];
        colorIdx++;
        return {
            key: key,
            name: meta.name,
            type: meta.type,
            color: color,
            data: (meta.data || []).map(pt => ({
                release: pt.release,
                run_id: pt.run_id,
                users: pt.users,
                val: pt[metric] !== undefined ? pt[metric] : (pt.avg_rt || 0)
            }))
        };
    });

    // Calculate chart bounds
    const allVals = activeSeries.flatMap(s => s.data.map(d => d.val));
    const rawMax = Math.max(...allVals, 1);
    const yMax = rawMax > 0 ? (metric === "error_rate" ? Math.max(rawMax * 1.3, 5) : rawMax * 1.25) : 10;
    const yMin = 0;

    const w = 840, h = 340;
    const padL = 60, padR = 40, padT = 30, padB = 45;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const numReleases = releaseNodes.length;
    const stepX = plotW / Math.max(numReleases - 1, 1);

    // Y Gridlines (4 horizontal lines)
    let gridHtml = "";
    for (let i = 0; i <= 4; i++) {
        const yVal = (yMax / 4) * i;
        const cy = padT + plotH - (yVal / yMax) * plotH;
        gridHtml += `
        <line x1="${padL}" y1="${cy}" x2="${w - padR}" y2="${cy}" stroke="#f1f5f9" stroke-width="1.5" stroke-dasharray="4,4"/>
        <text x="${padL - 10}" y="${cy + 4}" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="end">${yVal.toFixed(yMax < 5 ? 2 : 0)}${mInfo.unit}</text>
        `;
    }

    // X Axis ticks (Release nodes)
    let xTicksHtml = releaseNodes.map((n, i) => {
        const cx = padL + i * stepX;
        return `
        <line x1="${cx}" y1="${padT + plotH}" x2="${cx}" y2="${padT + plotH + 6}" stroke="#cbd5e1" stroke-width="1.5"/>
        <text x="${cx}" y="${padT + plotH + 20}" fill="#0f172a" font-size="12" font-weight="800" text-anchor="middle">${n.code}</text>
        <text x="${cx}" y="${padT + plotH + 34}" fill="#64748b" font-size="10" font-weight="600" text-anchor="middle">${n.users} Users</text>
        `;
    }).join("");

    // Render each series line & data points
    let seriesLinesHtml = "";
    let dataPointsHtml = "";

    activeSeries.forEach(s => {
        const pts = s.data.map((d, i) => {
            const cx = padL + i * stepX;
            const cy = padT + plotH - (Math.max(d.val, 0) / yMax) * plotH;
            return { cx, cy, val: d.val, release: d.release, users: d.users, run_id: d.run_id };
        });

        const pointsStr = pts.map(p => `${p.cx},${p.cy}`).join(" ");

        seriesLinesHtml += `
        <polyline points="${pointsStr}" fill="none" stroke="${s.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>
        `;

        pts.forEach(p => {
            const showVal = activeSeries.length <= 3;
            dataPointsHtml += `
            <g class="trend-pt-group" style="cursor:pointer;" data-title="${s.name}" data-val="${p.val.toFixed(metric==='error_rate'?2:1)}${mInfo.unit}" data-rel="${p.release}" data-users="${p.users}">
                <circle cx="${p.cx}" cy="${p.cy}" r="6" fill="${s.color}" stroke="#ffffff" stroke-width="2.5" class="trend-chart-pt"/>
                ${showVal ? `<text x="${p.cx}" y="${p.cy - 10}" fill="#0f172a" font-size="10.5" font-weight="800" text-anchor="middle">${p.val.toFixed(metric==='error_rate'?2:0)}${mInfo.unit}</text>` : ''}
            </g>
            `;
        });
    });

    container.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" style="width:100%; height:100%; overflow:visible;">
        ${gridHtml}
        <line x1="${padL}" y1="${padT + plotH}" x2="${w - padR}" y2="${padT + plotH}" stroke="#cbd5e1" stroke-width="1.5"/>
        ${xTicksHtml}
        ${seriesLinesHtml}
        ${dataPointsHtml}
    </svg>
    <div id="trend-chart-tooltip" class="trend-chart-tooltip" style="opacity:0;"></div>
    `;

    // Interactive Hover Tooltip Event
    container.querySelectorAll(".trend-pt-group").forEach(g => {
        g.addEventListener("mouseenter", (e) => {
            const tt = document.getElementById("trend-chart-tooltip");
            if (!tt) return;
            const title = g.getAttribute("data-title");
            const val = g.getAttribute("data-val");
            const rel = g.getAttribute("data-rel");
            const users = g.getAttribute("data-users");
            tt.innerHTML = `<strong>${rel} (${users} Users)</strong><br/><span style="color:#38bdf8;">${title}:</span> <strong>${val}</strong>`;
            tt.style.opacity = "1";
        });
        g.addEventListener("mousemove", (e) => {
            const tt = document.getElementById("trend-chart-tooltip");
            if (!tt) return;
            const rect = container.getBoundingClientRect();
            tt.style.left = `${e.clientX - rect.left}px`;
            tt.style.top = `${e.clientY - rect.top}px`;
        });
        g.addEventListener("mouseleave", () => {
            const tt = document.getElementById("trend-chart-tooltip");
            if (tt) tt.style.opacity = "0";
        });
    });
}

function renderTrendGraph2_SLA(nodes) {
    const container = document.getElementById("trend-chart-sla");
    if (!container || !nodes || nodes.length === 0) return;

    const w = 480, h = 200, pad = 35;
    const barWidth = Math.min(36, (w - pad * 2) / (nodes.length * 1.5));
    const step = (w - pad * 2) / nodes.length;

    let barsHtml = nodes.map((n, i) => {
        const x = pad + i * step + (step - barWidth) / 2;
        const passH = Math.max((n.sla_pass_rate / 100) * (h - pad * 2), 4);
        const y = h - pad - passH;
        const color = n.sla_pass_rate >= 90 ? "#059669" : (n.sla_pass_rate >= 75 ? "#d97706" : "#dc2626");

        return `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${passH}" fill="${color}" rx="4"/>
        <text x="${x + barWidth/2}" y="${y - 6}" fill="#0f172a" font-size="10.5" font-weight="800" text-anchor="middle">${n.sla_pass_rate.toFixed(0)}%</text>
        <text x="${x + barWidth/2}" y="${h - 10}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">${n.code}</text>
        `;
    }).join("");

    container.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" style="width:100%; height:100%;">
        <line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" stroke="#cfd7e0" stroke-width="1"/>
        ${barsHtml}
    </svg>
    `;
}

function renderTrendGraph3_Heatmap(heatmap) {
    const container = document.getElementById("trend-heatmap-container");
    if (!container || !heatmap) return;

    const headers = (heatmap.releases || []).map(r => `<th>${r}</th>`).join("");
    const rows = (heatmap.matrix || []).map(row => {
        const cells = row.values.map((v, i) => {
            const sev = row.severities[i];
            const cls = sev === "PASS" ? "cell-pass" : (sev === "LOW" || sev === "MODERATE" ? "cell-warning" : "cell-critical");
            return `<td class="heatmap-cell ${cls}">${v.toFixed(0)} ms</td>`;
        }).join("");

        const depth = row.depth || 0;
        const indent = depth * 16;
        const bCls = row.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (row.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
        const bLbl = row.item_type === "MAIN_TRANSACTION" ? "MAIN" : (row.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");

        return `<tr><td><div style="padding-left:${indent}px; display:flex; align-items:center; gap:0.4rem;"><span class="badge ${bCls}">${bLbl}</span><span><strong>${row.transaction}</strong></span></div></td>${cells}</tr>`;
    }).join("");

    container.innerHTML = `
    <table class="heatmap-matrix-table">
        <thead><tr><th>Hierarchy Item</th>${headers}</tr></thead>
        <tbody>${rows}</tbody>
    </table>
    `;
}

function renderTrendGraph5_SeverityStack(sevDist) {
    const container = document.getElementById("trend-chart-sev-stack");
    if (!container || !sevDist) return;

    container.innerHTML = sevDist.map(item => {
        const tot = item.total || 1;
        const pPct = ((item.counts.PASS || 0) / tot) * 100;
        const lPct = ((item.counts.LOW || 0) / tot) * 100;
        const mPct = ((item.counts.MODERATE || 0) / tot) * 100;
        const hPct = ((item.counts.HIGH || 0) / tot) * 100;
        const cPct = ((item.counts.CRITICAL || 0) / tot) * 100;

        return `
        <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.6rem;">
            <div style="width:40px; font-weight:bold; font-size:0.85rem; color:#64748b;">${item.release}</div>
            <div style="flex:1; height:18px; background:#f1f5f9; border-radius:4px; overflow:hidden; display:flex;">
                <div style="width:${pPct}%; background:#059669;" title="Pass: ${item.counts.PASS}"></div>
                <div style="width:${lPct}%; background:#d97706;" title="Low: ${item.counts.LOW}"></div>
                <div style="width:${mPct}%; background:#ea580c;" title="Moderate: ${item.counts.MODERATE}"></div>
                <div style="width:${hPct}%; background:#dc2626;" title="High: ${item.counts.HIGH}"></div>
                <div style="width:${cPct}%; background:#991b1b;" title="Critical: ${item.counts.CRITICAL}"></div>
            </div>
            <div style="width:65px; font-size:0.75rem; color:#64748b; text-align:right;">${item.counts.PASS}/${tot} Pass</div>
        </div>
        `;
    }).join("");
}

function renderTrendGraph6_BaselineVsCurrent(bVsC) {
    const container = document.getElementById("trend-bar-compare-container");
    if (!container || !bVsC) return;

    const maxVal = Math.max(...bVsC.map(t => Math.max(t.baseline_rt, t.current_rt)), 50);

    container.innerHTML = bVsC.slice(0, 10).map(t => {
        const basePct = (t.baseline_rt / maxVal) * 100;
        const currPct = (t.current_rt / maxVal) * 100;
        const d = t.delta_pct;
        const col = d > 0 ? "#dc2626" : "#059669";
        const bCls = t.item_type === "MAIN_TRANSACTION" ? "badge-main-tx" : (t.item_type === "SUB_TRANSACTION" ? "badge-sub-tx" : "badge-req");
        const bLbl = t.item_type === "MAIN_TRANSACTION" ? "MAIN" : (t.item_type === "SUB_TRANSACTION" ? "SUB" : "REQ");

        return `
        <div class="bar-compare-row">
            <div class="bar-compare-name" title="${t.transaction}">
                <span class="badge ${bCls}">${bLbl}</span>
                <span>${t.transaction}</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill-base" style="width:${basePct}%;" title="Baseline: ${t.baseline_rt.toFixed(0)}ms"></div>
                <div class="bar-fill-curr" style="width:${currPct}%;" title="Current: ${t.current_rt.toFixed(0)}ms"></div>
            </div>
            <div style="text-align:right; font-weight:bold; font-size:0.82rem; color:${col};">
                ${d > 0 ? '+' : ''}${d.toFixed(1)}%
            </div>
        </div>
        `;
    }).join("");
}

async function exportTrendDashboardHTML() {
    const proj = document.getElementById("trend-project-select")?.value || "";
    const story = document.getElementById("trend-story-select")?.value || "";
    const itemType = document.getElementById("trend-type-select")?.value || "TRANSACTIONS_ONLY";
    const limit = document.getElementById("trend-limit-select")?.value || "10";

    try {
        const res = await fetch("/api/trend/generate-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project: proj,
                user_story: story,
                item_type: itemType,
                limit: limit
            })
        });
        const data = await res.json();
        if (data.success && data.url) {
            window.open(data.url, "_blank");
        } else {
            alert("Failed to export trend dashboard: " + (data.message || "Unknown error"));
        }
    } catch (e) {
        alert("Export error: " + e.message);
    }
}
