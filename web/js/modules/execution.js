// modules/execution.js — Test Execution & Real-Time Polling Loop
import { api } from '../core/api.js';
import { state } from '../core/state.js';
import { switchTab } from '../core/router.js';
import { loadRuns, loadReports } from './reports.js';
import { collectThreadGroupConfigs } from './dashboard.js';

let pipelinePollInterval = null;
let pipelineStartTime = 0;
let pipelineElapsedTimer = null;
window.pipelineCanDismiss = false;

export function openPipelineModal(tool, targetName) {
    window.pipelineCanDismiss = false;

    // Show inline pipeline stepper on dashboard
    const inlineContainer = document.getElementById("inline-pipeline-container");
    if (inlineContainer) {
        inlineContainer.classList.remove("hidden");
        inlineContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // Also show modal if available
    const modal = document.getElementById("pipeline-progress-modal");
    if (modal) {
        modal.classList.remove("hidden");
    }

    // Reset Elements
    const elementsToReset = [
        { target: "pipeline-target-name", inline: "inline-pipeline-title", text: targetName || "Performance Execution" },
        { target: "pipeline-tool-badge", inline: null, text: (tool || "jmeter").toUpperCase() },
    ];

    elementsToReset.forEach(e => {
        const el = document.getElementById(e.target);
        if (el) el.textContent = e.text;
        if (e.inline) {
            const inl = document.getElementById(e.inline);
            if (inl) inl.textContent = e.text;
        }
    });

    const statusBadge = document.getElementById("pipeline-status-badge");
    const inlineStatusBadge = document.getElementById("inline-pipeline-status-badge");
    [statusBadge, inlineStatusBadge].forEach(badge => {
        if (badge) {
            badge.textContent = "RUNNING";
            badge.style.background = "#dbeafe";
            badge.style.color = "#1d4ed8";
        }
    });

    const progressFill = document.getElementById("pipeline-progress-fill");
    const inlineProgressFill = document.getElementById("inline-pipeline-progress-fill");
    [progressFill, inlineProgressFill].forEach(pf => {
        if (pf) pf.style.width = "5%";
    });

    const closeBtn = document.getElementById("pipeline-close-btn");
    const closeXBtn = document.getElementById("pipeline-close-x-btn");
    const viewReportBtn = document.getElementById("pipeline-view-report-btn");
    const inlineViewReportBtn = document.getElementById("inline-pipeline-view-report-btn");
    const inlineSpinner = document.getElementById("inline-pipeline-spinner");

    if (closeBtn) closeBtn.style.display = "none";
    if (closeXBtn) closeXBtn.style.display = "none";
    if (viewReportBtn) viewReportBtn.style.display = "none";
    if (inlineViewReportBtn) inlineViewReportBtn.classList.add("hidden");
    if (inlineSpinner) inlineSpinner.style.display = "inline-block";

    const footerStatus = document.getElementById("pipeline-footer-status");
    const inlineFooterStatus = document.getElementById("inline-pipeline-footer-status");
    [footerStatus, inlineFooterStatus].forEach(fs => {
        if (fs) fs.textContent = "Initializing pipeline stages...";
    });

    const terminalBody = document.getElementById("pipeline-terminal-body");
    const inlineTerminalBody = document.getElementById("inline-pipeline-terminal-body");
    const initLogHtml = '<div class="pipeline-log-row"><span class="pipeline-log-ts">[00:00.000]</span><span class="pipeline-log-stage">[INIT]</span><span class="pipeline-log-msg">Pipeline initialized.</span></div>';
    if (terminalBody) terminalBody.innerHTML = initLogHtml;
    if (inlineTerminalBody) inlineTerminalBody.innerHTML = initLogHtml;

    const logCount = document.getElementById("pipeline-log-count");
    const inlineLogCount = document.getElementById("inline-pipeline-log-count");
    [logCount, inlineLogCount].forEach(lc => {
        if (lc) lc.textContent = "1 event";
    });

    // Reset stage items in both views
    const stageIds = ["ingestion", "parsing", "sla", "ai_insights", "storage", "reporting"];
    stageIds.forEach(id => {
        ["stage-", "inline-stage-"].forEach(prefix => {
            const item = document.getElementById(`${prefix}${id}`);
            const timeBadge = document.getElementById(`${prefix}time-${id}`);
            const icon = document.getElementById(`${prefix}icon-${id}`);

            if (item) item.className = "pipeline-stage-item stage-pending";
            if (timeBadge) timeBadge.textContent = "--";
            if (icon) {
                const defaults = { ingestion: "📥", parsing: "🔄", sla: "⚖️", ai_insights: "🧠", storage: "💾", reporting: "📊" };
                icon.textContent = defaults[id] || "⏳";
            }
        });
    });

    // Start timer badge for both views
    pipelineStartTime = Date.now();
    if (pipelineElapsedTimer) clearInterval(pipelineElapsedTimer);
    pipelineElapsedTimer = setInterval(() => {
        const elapsedSec = Math.floor((Date.now() - pipelineStartTime) / 1000);
        const mins = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
        const secs = String(elapsedSec % 60).padStart(2, "0");
        const timerText = `${mins}:${secs}`;
        const timerBadge = document.getElementById("pipeline-live-timer");
        const inlineTimerBadge = document.getElementById("inline-pipeline-timer");
        if (timerBadge) timerBadge.textContent = timerText;
        if (inlineTimerBadge) inlineTimerBadge.textContent = timerText;
    }, 500);
}

export function closePipelineModal() {
    const modal = document.getElementById("pipeline-progress-modal");
    if (modal) modal.classList.add("hidden");
    if (pipelineElapsedTimer) {
        clearInterval(pipelineElapsedTimer);
        pipelineElapsedTimer = null;
    }
    if (pipelinePollInterval) {
        clearInterval(pipelinePollInterval);
        pipelinePollInterval = null;
    }
}

export function togglePipelineLogs(target = "modal") {
    const isInline = target === "inline";
    const bodyId = isInline ? "inline-pipeline-terminal-body" : "pipeline-terminal-body";
    const toggleId = isInline ? "inline-pipeline-log-toggle-icon" : "pipeline-log-toggle-icon";
    const body = document.getElementById(bodyId);
    const toggle = document.getElementById(toggleId);
    if (!body) return;
    if (body.classList.contains("hidden")) {
        body.classList.remove("hidden");
        if (toggle) toggle.textContent = "▼ Collapse";
    } else {
        body.classList.add("hidden");
        if (toggle) toggle.textContent = "▲ Expand";
    }
}

export function updatePipelineModal(data) {
    if (!data) return;

    const stages = data.stages || [];
    const statusBadge = document.getElementById("pipeline-status-badge");
    const inlineStatusBadge = document.getElementById("inline-pipeline-status-badge");
    const progressFill = document.getElementById("pipeline-progress-fill");
    const inlineProgressFill = document.getElementById("inline-pipeline-progress-fill");
    const footerStatus = document.getElementById("pipeline-footer-status");
    const inlineFooterStatus = document.getElementById("inline-pipeline-footer-status");
    const closeBtn = document.getElementById("pipeline-close-btn");
    const closeXBtn = document.getElementById("pipeline-close-x-btn");
    const viewReportBtn = document.getElementById("pipeline-view-report-btn");
    const inlineViewReportBtn = document.getElementById("inline-pipeline-view-report-btn");
    const inlineSpinner = document.getElementById("inline-pipeline-spinner");
    const terminalBody = document.getElementById("pipeline-terminal-body");
    const inlineTerminalBody = document.getElementById("inline-pipeline-terminal-body");
    const logCount = document.getElementById("pipeline-log-count");
    const inlineLogCount = document.getElementById("inline-pipeline-log-count");

    let completedCount = 0;
    const stageIcons = {
        ingestion: "📥",
        parsing: "🔄",
        sla: "⚖️",
        ai_insights: "🧠",
        storage: "💾",
        reporting: "📊"
    };

    stages.forEach(st => {
        ["stage-", "inline-stage-"].forEach(prefix => {
            const item = document.getElementById(`${prefix}${st.id}`);
            const timeBadge = document.getElementById(`${prefix}time-${st.id}`);
            const detail = document.getElementById(`${prefix}detail-${st.id}`);
            const icon = document.getElementById(`${prefix}icon-${st.id}`);

            if (item) {
                item.className = `pipeline-stage-item stage-${st.status}`;
            }
            if (timeBadge) {
                if (st.elapsed_ms > 0) {
                    timeBadge.textContent = st.elapsed_ms >= 1000 ? `${(st.elapsed_ms / 1000).toFixed(1)}s` : `${st.elapsed_ms}ms`;
                } else if (st.status === "running") {
                    timeBadge.textContent = "Running...";
                }
            }
            if (detail && st.detail) {
                detail.textContent = st.detail;
            }
            if (icon) {
                if (st.status === "completed") icon.textContent = "✓";
                else if (st.status === "running") icon.innerHTML = '<span class="spinner-inline" style="border-top-color:#ffffff; border-color:rgba(255,255,255,0.3); width:14px; height:14px;"></span>';
                else if (st.status === "failed") icon.textContent = "✕";
                else icon.textContent = stageIcons[st.id] || "⏳";
            }
        });

        if (st.status === "completed") completedCount++;
    });

    const pct = Math.min(100, Math.round((completedCount / (stages.length || 6)) * 100));
    const finalWidth = data.overall_status === "completed" ? "100%" : `${Math.max(5, pct)}%`;
    [progressFill, inlineProgressFill].forEach(pf => {
        if (pf) pf.style.width = finalWidth;
    });

    // Render Logs to both terminal streams
    const logs = data.logs || [];
    [logCount, inlineLogCount].forEach(lc => {
        if (lc) lc.textContent = `${logs.length} events`;
    });

    if (logs.length > 0) {
        const logHtml = logs.map(l => `
            <div class="pipeline-log-row">
                <span class="pipeline-log-ts">[${l.timestamp}]</span>
                <span class="pipeline-log-stage">[${(l.stage || "INFO").toUpperCase()}]</span>
                <span class="pipeline-log-msg level-${l.level || 'INFO'}">${l.message}</span>
            </div>
        `).join("");

        if (terminalBody) {
            terminalBody.innerHTML = logHtml;
            terminalBody.scrollTop = terminalBody.scrollHeight;
        }
        if (inlineTerminalBody) {
            inlineTerminalBody.innerHTML = logHtml;
            inlineTerminalBody.scrollTop = inlineTerminalBody.scrollHeight;
        }
    }

    if (data.overall_status === "completed") {
        window.pipelineCanDismiss = true;
        [statusBadge, inlineStatusBadge].forEach(sb => {
            if (sb) {
                sb.textContent = "COMPLETED";
                sb.style.background = "#dcfce7";
                sb.style.color = "#15803d";
            }
        });
        const durationSec = (data.total_elapsed_ms / 1000).toFixed(1);
        [footerStatus, inlineFooterStatus].forEach(fs => {
            if (fs) fs.textContent = `Completed in ${durationSec}s`;
        });
        if (inlineSpinner) inlineSpinner.style.display = "none";
        if (closeBtn) closeBtn.style.display = "inline-flex";
        if (closeXBtn) closeXBtn.style.display = "inline-flex";

        if (data.report_url) {
            if (viewReportBtn) {
                viewReportBtn.href = data.report_url;
                viewReportBtn.style.display = "inline-flex";
            }
            if (inlineViewReportBtn) {
                inlineViewReportBtn.href = data.report_url;
                inlineViewReportBtn.classList.remove("hidden");
            }
        }
    } else if (data.overall_status === "failed") {
        window.pipelineCanDismiss = true;
        [statusBadge, inlineStatusBadge].forEach(sb => {
            if (sb) {
                sb.textContent = "FAILED";
                sb.style.background = "#fee2e2";
                sb.style.color = "#b91c1c";
            }
        });
        const errMsg = `Error: ${data.error_message || "Pipeline failed"}`;
        [footerStatus, inlineFooterStatus].forEach(fs => {
            if (fs) fs.textContent = errMsg;
        });
        if (inlineSpinner) inlineSpinner.style.display = "none";
        if (closeBtn) closeBtn.style.display = "inline-flex";
        if (closeXBtn) closeXBtn.style.display = "inline-flex";
    } else {
        if (data.current_stage_id) {
            const stageText = `Executing stage: ${data.current_stage_id.replace('_', ' ').toUpperCase()}...`;
            [footerStatus, inlineFooterStatus].forEach(fs => {
                if (fs) fs.textContent = stageText;
            });
        }
    }
}

export function startPipelineTracking(runId, tool, targetName) {
    openPipelineModal(tool, targetName);

    if (pipelinePollInterval) clearInterval(pipelinePollInterval);

    pipelinePollInterval = setInterval(async () => {
        try {
            const url = runId ? `/api/pipeline/status?run_id=${encodeURIComponent(runId)}` : "/api/pipeline/status";
            const data = await api.get(url);

            if (data && data.stages && data.stages.length > 0) {
                updatePipelineModal(data);

                if (data.overall_status === "completed" || data.overall_status === "failed") {
                    clearInterval(pipelinePollInterval);
                    pipelinePollInterval = null;
                    if (pipelineElapsedTimer) {
                        clearInterval(pipelineElapsedTimer);
                        pipelineElapsedTimer = null;
                    }
                    loadRuns();
                    loadReports();
                }
            }
        } catch (err) {
            console.warn("Pipeline polling ping:", err);
        }
    }, 450);
}

export async function handleRunTest(e) {
    if (e) e.preventDefault();

    const tool = document.getElementById("tool-select") ? document.getElementById("tool-select").value : "jmeter";
    const method = document.getElementById("ingest-select") ? document.getElementById("ingest-select").value : "local";

    if (method === "file_upload") {
        const fileInput = document.getElementById("raw-result-file");
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            alert("Please choose a raw result file to upload (.jtl, .json, .csv, .zip).");
            return;
        }
        const file = fileInput.files[0];
        const scenarioName = document.getElementById("raw-test-name") ? document.getElementById("raw-test-name").value : "";
        const slaSelect = document.getElementById("raw-sla-select");
        const slaFile = slaSelect ? slaSelect.value : "";
        const formData = new FormData();
        formData.append("file", file);
        formData.append("tool", tool);
        if (scenarioName) formData.append("test_name", scenarioName);
        if (slaFile) formData.append("sla_file", slaFile);

        // Open live pipeline progress stepper modal immediately
        startPipelineTracking(null, tool, scenarioName || file.name);

        const btn = document.getElementById("btn-launch-test");
        try {
            if (btn) btn.textContent = "Processing Pipeline...";
            const data = await api.upload("/api/ingest/upload", formData);
            if (data.success) {
                // Ensure tracker captures completion with exact report_url
                if (data.run_id) {
                    const statusRes = await api.get(`/api/pipeline/status?run_id=${encodeURIComponent(data.run_id)}`);
                    if (statusRes) updatePipelineModal(statusRes);
                }
                loadRuns();
                loadReports();
            } else {
                alert("Upload failed: " + (data.message || JSON.stringify(data)));
            }
        } catch (err) {
            console.error("Upload ingestion error: ", err);
        } finally {
            if (btn) btn.textContent = "Upload & Generate Report";
        }
        return;
    }

    if (method === "direct_api" || method === "mcp") {
        const testId = document.getElementById("cloud-test-id") ? document.getElementById("cloud-test-id").value.trim() : "";
        const users = document.getElementById("cloud-virtual-users") ? parseInt(document.getElementById("cloud-virtual-users").value, 10) : 10;
        if (!testId) {
            alert("Please enter a valid Test ID or Master ID.");
            return;
        }

        startPipelineTracking(null, tool, `${tool.toUpperCase()} ID: ${testId}`);

        try {
            const endpoint = method === "mcp" ? "/api/ingest/mcp" : "/api/ingest/api";
            const data = await api.post(endpoint, {
                tool: tool,
                identifier: testId,
                users: users
            });
            if (data.success) {
                if (data.run_id) {
                    const statusRes = await api.get(`/api/pipeline/status?run_id=${encodeURIComponent(data.run_id)}`);
                    if (statusRes) updatePipelineModal(statusRes);
                }
                loadRuns();
                loadReports();
            } else {
                alert("Ingestion error: " + (data.message || JSON.stringify(data)));
            }
        } catch (err) {
            console.error("Ingestion request failed: ", err);
        }
        return;
    }

    const payload = collectThreadGroupConfigs();
    if (!payload || payload.thread_groups.length === 0) return;

    const btn = document.getElementById("btn-launch-test");
    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Launching Test...";
        }

        const data = await api.post("/api/run-test", payload);

        if (data.success) {
            switchTab("tab-live");
            startLivePolling(payload.jmx);
        } else {
            alert("Error: " + (data.message || JSON.stringify(data)));
        }
    } catch (err) {
        alert("Failed to launch test: " + err);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Execute Performance Test";
        }
    }
}

export async function startLivePolling(jmxName) {
    const subtitle = document.getElementById("live-test-subtitle");
    const badge = document.getElementById("live-indicator-badge");
    const stopBtn = document.getElementById("btn-stop-test");
    const statsTbody = document.getElementById("live-metrics-tbody");
    const failTbody = document.getElementById("live-failures-tbody");

    if (subtitle) subtitle.textContent = `Running scenario: ${jmxName || "JMeter Execution"}`;
    if (badge) badge.classList.remove("hidden");
    if (stopBtn) stopBtn.classList.remove("hidden");
    if (statsTbody) statsTbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Awaiting initial execution metrics from engine...</td></tr>';
    if (failTbody) failTbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No execution errors detected.</td></tr>';

    if (state.activePollingInterval) {
        clearInterval(state.activePollingInterval);
        state.activePollingInterval = null;
    }

    // Cache transaction controller mapping once
    let tcMap = {};
    if (jmxName) {
        try {
            const cfgData = await api.get(`/api/jmx-config?jmx=${encodeURIComponent(jmxName)}`);
            if (cfgData.success && cfgData.config) {
                tcMap = cfgData.config.tc_to_samplers || {};
            }
        } catch (e) { }
    }

    state.activePollingInterval = setInterval(async () => {
        try {
            const data = await api.get("/api/jmeter-progress");

            const timerEl = document.getElementById("live-timer");
            if (timerEl) timerEl.textContent = data.elapsed_str || "00:00";

            const liveStats = data.live_stats || {};
            const keys = Object.keys(liveStats);

            if (keys.length > 0 && statsTbody) {
                statsTbody.innerHTML = "";
                const tcKeys = Object.keys(tcMap);

                if (tcKeys.length > 0) {
                    tcKeys.forEach((tcName) => {
                        const tcStat = liveStats[tcName] || { total: 0, errors: 0, total_rt: 0, min_rt: 0, max_rt: 0 };
                        const avgRt = tcStat.total > 0 ? (tcStat.total_rt / tcStat.total).toFixed(0) : 0;
                        const errPct = tcStat.total > 0 ? ((tcStat.errors / tcStat.total) * 100).toFixed(2) : "0.00";

                        const tr = document.createElement("tr");
                        tr.style.background = "var(--bg-light)";

                        tr.innerHTML = `
                            <td><strong>${tcName}</strong></td>
                            <td><strong>${tcStat.total}</strong></td>
                            <td><strong>${avgRt} ms</strong></td>
                            <td>${tcStat.min_rt} ms</td>
                            <td>${tcStat.max_rt} ms</td>
                            <td>${tcStat.errors}</td>
                            <td style="${tcStat.errors > 0 ? 'color: var(--danger); font-weight: bold;' : ''}">${errPct}%</td>
                        `;
                        statsTbody.appendChild(tr);
                    });
                } else {
                    keys.forEach(lbl => {
                        const st = liveStats[lbl];
                        const avgRt = st.total > 0 ? (st.total_rt / st.total).toFixed(0) : 0;
                        const errPct = st.total > 0 ? ((st.errors / st.total) * 100).toFixed(2) : "0.00";
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td><strong>${lbl}</strong></td>
                            <td>${st.total}</td>
                            <td>${avgRt} ms</td>
                            <td>${st.min_rt} ms</td>
                            <td>${st.max_rt} ms</td>
                            <td>${st.errors}</td>
                            <td style="${st.errors > 0 ? 'color: var(--danger); font-weight: bold;' : ''}">${errPct}%</td>
                        `;
                        statsTbody.appendChild(tr);
                    });
                }
            }

            const errBadge = document.getElementById("error-indicator-badge");
            const failedReqs = data.failed_requests || {};
            const failKeys = Object.keys(failedReqs);

            let totalFailures = 0;
            if (failKeys.length > 0 && failTbody) {
                failTbody.innerHTML = "";
                failKeys.forEach(lbl => {
                    const f = failedReqs[lbl];
                    totalFailures += f.count;
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${lbl}</strong></td>
                        <td><span class="badge badge-failed">${f.status_code}</span></td>
                        <td><strong>${f.count}</strong></td>
                        <td><code>${f.sample_error}</code></td>
                    `;
                    failTbody.appendChild(tr);
                });

                if (errBadge) {
                    errBadge.textContent = totalFailures;
                    errBadge.classList.remove("hidden");
                }
            } else if (errBadge) {
                errBadge.classList.add("hidden");
            }

            const isDone = data.done || (!data.active && !data.running && data.status !== "running");
            if (isDone) {
                clearInterval(state.activePollingInterval);
                state.activePollingInterval = null;
                if (badge) badge.classList.add("hidden");
                if (stopBtn) stopBtn.classList.add("hidden");
                if (subtitle) subtitle.textContent = `Test completed for ${jmxName || data.run_id}. View generated HTML report in History.`;
                loadRuns();
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 2000);
}

export async function checkAndResumeLivePolling() {
    try {
        const data = await api.get("/api/jmeter-progress");
        if (data.active || data.running || data.status === "running") {
            startLivePolling(data.jmx_name || data.run_id || "Running Test");
        }
    } catch (e) {}
}

export async function handleStopTest() {
    if (!confirm("Are you sure you want to terminate the running JMeter process?")) return;

    try {
        const data = await api.post("/api/stop-test", {});
        alert(data.message);
    } catch (err) {
        alert("Failed to stop test: " + err);
    }
}

export async function loadSlaOptions() {
    try {
        const slaSelect = document.getElementById("raw-sla-select");
        if (!slaSelect) return;
        const res = await api.get("/api/ingest/sla-options");
        if (res && res.sla_files) {
            slaSelect.innerHTML = '<option value="">Auto-detect (Paired scenario SLA or config/sla_targets.csv)</option>';
            res.sla_files.forEach(f => {
                const opt = document.createElement("option");
                opt.value = f.path;
                opt.textContent = f.name;
                slaSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.warn("Could not load SLA options:", e);
    }
}

window.handleRunTest = handleRunTest;
window.startLivePolling = startLivePolling;
window.checkAndResumeLivePolling = checkAndResumeLivePolling;
window.handleStopTest = handleStopTest;
window.loadSlaOptions = loadSlaOptions;
window.openPipelineModal = openPipelineModal;
window.closePipelineModal = closePipelineModal;
window.togglePipelineLogs = togglePipelineLogs;
window.updatePipelineModal = updatePipelineModal;
window.startPipelineTracking = startPipelineTracking;

// Load SLA options on startup
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadSlaOptions);
} else {
    loadSlaOptions();
}
