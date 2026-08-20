/* trend.js — Frontend JavaScript Controller for JmeterAI Trend & Comparison Engine */

let trendHierarchy = {};

document.addEventListener("DOMContentLoaded", () => {
    initTrendModule();
});

function initTrendModule() {
    loadHierarchy();
    loadCompareRunsList();
}

async function loadHierarchy() {
    try {
        const res = await fetch("/api/trend/hierarchy");
        const data = await res.json();
        if (data.success && data.hierarchy) {
            trendHierarchy = data.hierarchy;
            populateProjectDropdown();
        }
    } catch (err) {
        console.error("Failed to load hierarchy:", err);
    }
}

function populateProjectDropdown() {
    const projSelect = document.getElementById("trend-project-select");
    if (!projSelect) return;

    projSelect.innerHTML = '<option value="">All Projects</option>';
    Object.keys(trendHierarchy).forEach(proj => {
        const opt = document.createElement("option");
        opt.value = proj;
        opt.textContent = proj;
        projSelect.appendChild(opt);
    });

    projSelect.addEventListener("change", onProjectChange);
    fetchAndRenderTrendData();
}

function onProjectChange() {
    const projSelect = document.getElementById("trend-project-select");
    const storySelect = document.getElementById("trend-story-select");
    const txSelect = document.getElementById("trend-tx-select");

    const selectedProj = projSelect.value;
    storySelect.innerHTML = '<option value="">All User Stories</option>';
    txSelect.innerHTML = '<option value="">All Transactions</option>';

    if (selectedProj && trendHierarchy[selectedProj]) {
        Object.keys(trendHierarchy[selectedProj]).forEach(story => {
            const opt = document.createElement("option");
            opt.value = story;
            opt.textContent = story;
            storySelect.appendChild(opt);
        });
    }

    storySelect.removeEventListener("change", onStoryChange);
    storySelect.addEventListener("change", onStoryChange);
    fetchAndRenderTrendData();
}

function onStoryChange() {
    const projSelect = document.getElementById("trend-project-select");
    const storySelect = document.getElementById("trend-story-select");
    const txSelect = document.getElementById("trend-tx-select");

    const selectedProj = projSelect.value;
    const selectedStory = storySelect.value;
    txSelect.innerHTML = '<option value="">All Transactions</option>';

    if (selectedProj && selectedStory && trendHierarchy[selectedProj] && trendHierarchy[selectedProj][selectedStory]) {
        trendHierarchy[selectedProj][selectedStory].forEach(tx => {
            const opt = document.createElement("option");
            opt.value = tx;
            opt.textContent = tx;
            txSelect.appendChild(opt);
        });
    }

    txSelect.removeEventListener("change", fetchAndRenderTrendData);
    txSelect.addEventListener("change", fetchAndRenderTrendData);
    fetchAndRenderTrendData();
}

async function fetchAndRenderTrendData() {
    const proj = document.getElementById("trend-project-select")?.value || "";
    const story = document.getElementById("trend-story-select")?.value || "";
    const tx = document.getElementById("trend-tx-select")?.value || "";
    const limit = document.getElementById("trend-limit-select")?.value || "10";

    try {
        const url = `/api/trend/analysis?project=${encodeURIComponent(proj)}&user_story=${encodeURIComponent(story)}&transaction=${encodeURIComponent(tx)}&limit=${limit}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            renderHealthScore(data.summary, data.series);
            renderSparklineCharts(data.series);
        }
    } catch (err) {
        console.error("Error fetching trend data:", err);
    }
}

function renderHealthScore(summary, series) {
    const scoreVal = document.getElementById("health-score-num");
    const scoreCircle = document.getElementById("health-score-circle");
    if (!scoreVal || !scoreCircle) return;

    const currentScore = summary.current_health || 0;
    scoreVal.textContent = currentScore;
    scoreCircle.style.setProperty("--score-pct", `${currentScore}%`);

    const latest = series[series.length - 1] || {};
    const breakdown = latest.health_breakdown || {};

    document.getElementById("hb-rt").textContent = breakdown.response_time || "100";
    document.getElementById("hb-p95").textContent = breakdown.p95 || "100";
    document.getElementById("hb-tp").textContent = breakdown.throughput || "100";
    document.getElementById("hb-err").textContent = breakdown.error_rate || "100";
    document.getElementById("hb-sla").textContent = breakdown.sla_compliance || "100";
}

function renderSparklineCharts(series) {
    if (!series || !series.length) return;

    const labels = series.map((s, i) => s.run_id ? s.run_id.replace("run_", "R") : `R${i+1}`);
    
    drawSvgSparkline("chart-svg-rt", series.map(s => s.avg_rt), "#38bdf8");
    drawSvgSparkline("chart-svg-p95", series.map(s => s.p95_rt), "#c084fc");
    drawSvgSparkline("chart-svg-tp", series.map(s => s.throughput), "#34d399");
    drawSvgSparkline("chart-svg-err", series.map(s => s.error_rate), "#f87171");
}

function drawSvgSparkline(containerId, dataPoints, color) {
    const svg = document.getElementById(containerId);
    if (!svg) return;

    if (!dataPoints.length) {
        svg.innerHTML = '<text x="50%" y="50%" fill="#64748b" text-anchor="middle">No data available</text>';
        return;
    }

    const width = 400;
    const height = 120;
    const padding = 15;

    const minVal = Math.min(...dataPoints);
    const maxVal = Math.max(...dataPoints);
    const range = (maxVal - minVal) || 1;

    const points = dataPoints.map((val, idx) => {
        const x = padding + (idx / Math.max(1, dataPoints.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((val - minVal) / range) * (height - 2 * padding);
        return { x, y, val };
    });

    const polylineStr = points.map(p => `${p.x},${p.y}`).join(" ");
    
    let dotsHtml = points.map(p => `
        <circle cx="${p.x}" cy="${p.y}" r="4" fill="${color}" stroke="#0f172a" stroke-width="2">
            <title>${p.val}</title>
        </circle>
    `).join("");

    svg.innerHTML = `
        <polyline fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${polylineStr}" />
        ${dotsHtml}
    `;
}

/* Compare Runs Module */
async function loadCompareRunsList() {
    try {
        const res = await fetch("/api/runs");
        const data = await res.json();
        const runs = data.runs || [];

        const grid = document.getElementById("compare-runs-grid");
        if (!grid) return;

        grid.innerHTML = "";
        runs.forEach((r, idx) => {
            const card = document.createElement("label");
            card.className = "run-checkbox-card";
            const checked = idx >= runs.length - 5 ? "checked" : "";
            card.innerHTML = `
                <input type="checkbox" value="${r.id}" ${checked}>
                <div>
                    <div style="font-weight: 700; color: #f8fafc;">${r.id}</div>
                    <div style="font-size: 0.75rem; color: #94a3b8;">${r.jmx_name || 'Script'} • ${r.users} Users</div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load runs for comparison:", err);
    }
}

async function executeRunComparison() {
    const checkboxes = document.querySelectorAll("#compare-runs-grid input[type='checkbox']:checked");
    const selectedIds = Array.from(checkboxes).map(cb => cb.value);

    if (selectedIds.length === 0) {
        alert("Please select at least 1 test run to compare.");
        return;
    }

    try {
        const res = await fetch("/api/trend/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_ids: selectedIds })
        });
        const data = await res.json();
        if (data.success) {
            renderComparisonResults(data);
        }
    } catch (err) {
        console.error("Comparison request failed:", err);
    }
}

function renderComparisonResults(data) {
    const tableHeader = document.getElementById("compare-table-header");
    const tableBody = document.getElementById("compare-table-body");
    const insightBox = document.getElementById("compare-insight-callout");
    if (!tableHeader || !tableBody || !insightBox) return;

    // Build Headers
    let headerHtml = "<th>Metric</th>";
    data.runs.forEach(r => {
        headerHtml += `<th>${r.id}<br><span style="font-size:0.75rem; color:#64748b;">${r.users} users</span></th>`;
    });
    headerHtml += "<th style='text-align:center;'>Overall Trend</th>";
    tableHeader.innerHTML = headerHtml;

    // Build Rows
    let rowsHtml = "";
    data.comparison_matrix.forEach(row => {
        let valsTd = row.values.map(v => `<td style="text-align:right;">${v} ${row.unit}</td>`).join("");
        let color = row.status === "improved" ? "#34d399" : (row.status === "degraded" ? "#f87171" : "#94a3b8");
        rowsHtml += `
            <tr>
                <td><strong>${row.metric}</strong></td>
                ${valsTd}
                <td style="text-align:center; font-weight:700; color:${color};">${row.trend_str}</td>
            </tr>
        `;
    });
    tableBody.innerHTML = rowsHtml;
    insightBox.innerHTML = data.load_normalization_insight || "Comparison calculated successfully.";
}

async function generateComparisonReportFile() {
    const checkboxes = document.querySelectorAll("#compare-runs-grid input[type='checkbox']:checked");
    const selectedIds = Array.from(checkboxes).map(cb => cb.value);

    try {
        const res = await fetch("/api/trend/compare-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_ids: selectedIds })
        });
        const data = await res.json();
        if (data.success && data.url) {
            window.open(data.url, "_blank");
        }
    } catch (err) {
        console.error("Failed to generate report file:", err);
    }
}
