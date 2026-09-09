// modules/reports.js — Historical Runs Catalog & Recompile Actions
import { api } from '../core/api.js';
import { state } from '../core/state.js';

export async function loadRuns() {
    try {
        const data = await api.get("/api/runs");
        state.allRunsData = data.runs || [];

        const searchInput = document.getElementById("report-search-input");
        const query = searchInput ? searchInput.value : "";
        filterReportsUI(query);

        loadPublishedReports();
    } catch (err) {
        console.error("Failed to load runs:", err);
    }
}

export function filterReportsUI(query) {
    const term = (query || "").toLowerCase().trim();
    const tbody = document.getElementById("runs-tbody");
    if (!tbody) return;

    if (!state.allRunsData || state.allRunsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No test execution history recorded yet.</td></tr>';
        return;
    }

    const filtered = state.allRunsData.filter(run => {
        if (!term) return true;
        return (
            (run.id || "").toLowerCase().includes(term) ||
            (run.jmx_name || "").toLowerCase().includes(term) ||
            (run.status || "").toLowerCase().includes(term) ||
            (run.timestamp || "").toLowerCase().includes(term)
        );
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No reports match your search query.</td></tr>';
        return;
    }

    renderRunsTable(filtered);
}

export function renderRunsTable(runs) {
    const tbody = document.getElementById("runs-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    runs.forEach(run => {
        const tr = document.createElement("tr");
        tr.className = "clickable-row";
        const badgeClass = run.status === "passed" ? "badge-passed" : run.status === "warning" ? "badge-warning" : "badge-failed";

        tr.onclick = (e) => {
            if (e.target.closest("button") || e.target.closest("a")) return;
            if (run.report_file) {
                const targetUrl = run.report_file.startsWith("http")
                    ? run.report_file
                    : run.report_file.startsWith("/Results")
                        ? run.report_file
                        : `/Results/html/${run.report_file.replace(/^html\//, '')}`;
                window.open(targetUrl, "_blank");
            }
        };

        tr.title = run.report_file ? `Click to open HTML report for ${run.id}` : "Report generating...";

        tr.innerHTML = `
            <td><code>${run.id}</code></td>
            <td><strong>${run.jmx_name}</strong></td>
            <td style="white-space: nowrap; font-size: 0.78rem;">${run.timestamp}</td>
            <td style="text-align: center;">${run.users}</td>
            <td style="text-align: right;">${run.total_samples ? run.total_samples.toLocaleString() : 0}</td>
            <td style="text-align: center;">${run.has_azure ? '✅ Yes' : '➖ No'}</td>
            <td style="text-align: center;">${run.has_ai_insights ? '🤖 AI' : '📊 Rule'}</td>
            <td style="text-align: center;"><span class="badge ${badgeClass}">${run.status.toUpperCase()}</span></td>
            <td style="text-align: right;" onclick="event.stopPropagation();">
                <div class="action-btn-group">
                    <button type="button" class="icon-action-btn" title="Recompile Report (⚡)" onclick="event.stopPropagation(); recompileSingleRunUI('${run.id}')">⚡</button>
                    <button type="button" class="icon-action-btn btn-delete-icon" title="Delete Report & Files (🗑️)" onclick="event.stopPropagation(); deleteRunUI('${run.id}')">🗑️</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

export async function loadPublishedReports() {
    try {
        const data = await api.get("/api/reports");
        const tbody = document.getElementById("published-reports-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        const pubList = data.published_reports || [];
        if (pubList.length > 0) {
            pubList.forEach(r => {
                const tr = document.createElement("tr");
                const dtStr = new Date(r.created_at * 1000).toLocaleString();
                const kbStr = (r.size / 1024).toFixed(1) + " KB";
                tr.innerHTML = `
                    <td><code>${r.name}</code></td>
                    <td>${dtStr}</td>
                    <td>${kbStr}</td>
                    <td>
                        <a href="${r.url}" target="_blank" class="btn btn-secondary" style="padding: 0.3rem 0.8rem; font-size: 0.75rem; background: #10b981; color: #fff; font-weight:700;">🌐 View Published Report</a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No published reports yet. Open a draft report and click "Publish Report".</td></tr>';
        }
    } catch (err) {
        console.error("Failed to load published reports:", err);
    }
}

export function recompileLatestReportUI() {
    openRecompileModal(null);
}

export function recompileSingleRunUI(runId) {
    openRecompileModal(runId);
}

export async function openRecompileModal(runId = null) {
    state.currentRecompileTargetRunId = runId;
    const modal = document.getElementById("recompile-modal");
    const targetLabel = document.getElementById("recompile-modal-target");
    const statusBox = document.getElementById("recompile-status-bar");
    const submitBtn = document.getElementById("recompile-submit-btn");
    const cancelBtn = document.getElementById("recompile-cancel-btn");

    if (statusBox) statusBox.classList.add("hidden");
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "⚡ Start Recompilation";
    }
    if (cancelBtn) cancelBtn.disabled = false;

    if (targetLabel) {
        targetLabel.textContent = runId ? `Target: Execution ${runId}` : "Target: Most Recent Execution";
    }

    try {
        const data = await api.get("/api/ai-config");
        const provElem = document.getElementById("recompile-active-provider");
        const modelElem = document.getElementById("recompile-active-model");
        if (provElem) provElem.textContent = (data.provider || "gemini").toUpperCase();
        if (modelElem) modelElem.textContent = data.model || "gemini-2.5-flash";
    } catch (e) { }

    if (modal) modal.classList.remove("hidden");
}

export function closeRecompileModal() {
    const modal = document.getElementById("recompile-modal");
    if (modal) modal.classList.add("hidden");
}

export function toggleRecompileAiOption(checked) {
    const meta = document.getElementById("recompile-ai-meta");
    if (meta) {
        meta.style.opacity = checked ? "1" : "0.4";
    }
}

export async function executeRecompile() {
    const regenAi = document.getElementById("recompile-ai-checkbox")?.checked ?? true;
    const statusBox = document.getElementById("recompile-status-bar");
    const statusText = document.getElementById("recompile-status-text");
    const submitBtn = document.getElementById("recompile-submit-btn");
    const cancelBtn = document.getElementById("recompile-cancel-btn");

    if (statusBox) statusBox.classList.remove("hidden");
    if (statusText) {
        statusText.textContent = regenAi
            ? "Re-parsing metrics & generating fresh AI insights from LLM... please wait."
            : "Recompiling HTML dashboard... please wait.";
    }
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-inline"></span> Recompiling...';
    }
    if (cancelBtn) cancelBtn.disabled = true;

    try {
        const data = await api.post("/api/recompile-report", {
            run_id: state.currentRecompileTargetRunId || "",
            regenerate_ai: regenAi
        });
        if (data.success) {
            closeRecompileModal();
            alert(data.message || "Report recompiled successfully!");
            loadRuns();
        } else {
            alert("Failed to recompile report: " + (data.message || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to recompile report: " + err.message);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "⚡ Start Recompilation";
        }
        if (cancelBtn) cancelBtn.disabled = false;
        if (statusBox) statusBox.classList.add("hidden");
    }
}

export async function deleteRunUI(runId) {
    if (!confirm(`Are you sure you want to delete report '${runId}' and ALL associated files (.html, .json, .jtl, azure JSON)?`)) return;

    try {
        const data = await api.post("/api/delete-run", { run_id: runId });
        alert(data.message);
        loadRuns();
    } catch (err) {
        alert("Failed to delete report: " + err);
    }
}

export async function loadReports() {
    // Supplementary stub
}

window.loadRuns = loadRuns;
window.filterReportsUI = filterReportsUI;
window.renderRunsTable = renderRunsTable;
window.loadPublishedReports = loadPublishedReports;
window.recompileLatestReportUI = recompileLatestReportUI;
window.recompileSingleRunUI = recompileSingleRunUI;
window.openRecompileModal = openRecompileModal;
window.closeRecompileModal = closeRecompileModal;
window.toggleRecompileAiOption = toggleRecompileAiOption;
window.executeRecompile = executeRecompile;
window.deleteRunUI = deleteRunUI;
window.loadReports = loadReports;
