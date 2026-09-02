// app.js — Frontend Application Logic for PerfPilot SPA

// ── Utility: HTML Escaping ──────────────────────────────────────────────────
function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

let activePollingInterval = null;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    loadStatus();
    loadAiConfig();
    loadTests();
    loadReports();
    loadRuns();
    setupDragAndDrop();

    // Sidebar Toggle Handler
    const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
    const sidebar = document.getElementById("app-sidebar");
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    // '/' Global Search Shortcut
    const globalSearch = document.getElementById("global-search");
    document.addEventListener("keydown", (e) => {
        if (e.key === "/" && document.activeElement !== globalSearch && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
            e.preventDefault();
            globalSearch?.focus();
        }
    });

    // Check hash URL
    const hash = window.location.hash.replace("#", "");
    if (hash && document.getElementById(hash)) {
        switchTab(hash);
    }
}

// ── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tabId) {
    window.location.hash = tabId;

    document.querySelectorAll(".tab-content").forEach(pane => {
        pane.classList.add("hidden");
    });
    const targetPane = document.getElementById(tabId);
    if (targetPane) {
        targetPane.classList.remove("hidden");
    }

    document.querySelectorAll(".nav-links a").forEach(link => {
        if (link.getAttribute("data-tab") === tabId) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    if (tabId === "tab-dashboard") {
        loadStatus();
        loadTests();
    } else if (tabId === "tab-sla") {
        const jmxSelect = document.getElementById("jmx-select");
        const preferredJmx = jmxSelect && jmxSelect.value ? jmxSelect.value : "";
        loadSlaScenariosFilter(preferredJmx);
    } else if (tabId === "tab-reports") {
        loadRuns();
        loadReports();
    } else if (tabId === "tab-compare") {
        if (typeof fetchAndRenderRunComparison === "function") {
            fetchAndRenderRunComparison();
        }
    } else if (tabId === "tab-trend") {
        if (typeof fetchAndRenderTrend === "function") {
            fetchAndRenderTrend();
        }
    } else if (tabId === "tab-ai-studio") {
        if (typeof loadStudioRuns === "function") {
            loadStudioRuns();
        }
    }
}

// ── API Fetch Helpers ────────────────────────────────────────────────────────
async function loadStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();

        // JMeter Card
        const indJmeter = document.getElementById("ind-jmeter");
        const valJmeter = document.getElementById("val-jmeter");
        if (data.jmeter && data.jmeter.available) {
            indJmeter.className = "indicator online";
            valJmeter.textContent = data.jmeter.version || "Apache JMeter Ready";
        } else {
            indJmeter.className = "indicator offline";
            valJmeter.textContent = "Not Found (Set JMETER_HOME)";
        }

        // Azure Card
        const indAzure = document.getElementById("ind-azure");
        const valAzure = document.getElementById("val-azure");
        if (data.azure_configured) {
            indAzure.className = "indicator online";
            valAzure.textContent = "Configured & Active";
        } else {
            indAzure.className = "indicator";
            valAzure.textContent = "Not Configured (Optional)";
        }

        // AI Card
        const indAi = document.getElementById("ind-ai");
        const valAi = document.getElementById("val-ai");
        if (data.ai_configured) {
            indAi.className = "indicator online";
            valAi.textContent = data.ai_mode || "AI Insights Ready";
        } else {
            indAi.className = "indicator";
            valAi.textContent = "Rule-based Fallback Mode";
        }
    } catch (err) {
        console.error("Failed to load status:", err);
    }
}

window.availableJmxFiles = [];
window.selectedJmxConfig = null;

async function loadTests() {
    try {
        const res = await fetch("/api/tests");
        const data = await res.json();

        window.availableJmxFiles = [];
        const jmxSelect = document.getElementById("jmx-select");
        if (!jmxSelect) return;

        const currentVal = jmxSelect.value;
        jmxSelect.innerHTML = '<option value="">Select test plan...</option>';

        if (data.tests && data.tests.length > 0) {
            data.tests.forEach(t => {
                if (t.endsWith(".jmx")) {
                    window.availableJmxFiles.push(t);
                    const opt = document.createElement("option");
                    opt.value = t;
                    opt.textContent = t;
                    jmxSelect.appendChild(opt);
                }
            });
        }

        // Restore selection if still valid
        if (currentVal && window.availableJmxFiles.includes(currentVal)) {
            jmxSelect.value = currentVal;
        } else if (window.availableJmxFiles.length > 0) {
            jmxSelect.value = window.availableJmxFiles[0];
            handleJmxSelection(window.availableJmxFiles[0]);
        }
    } catch (err) {
        console.error("Failed to load tests:", err);
    }
}

async function handleJmxSelection(jmxName) {
    const container = document.getElementById("thread-groups-container");
    const csvBox = document.getElementById("csv-warnings-box");
    const launchBtn = document.getElementById("btn-launch-test");
    const saveBtn = document.getElementById("btn-save-config");

    if (!jmxName) {
        container.innerHTML = '<div class="info-box">Select a JMX file above to view and configure its user journeys.</div>';
        launchBtn.disabled = true;
        saveBtn.disabled = true;
        csvBox.classList.add("hidden");
        window.selectedJmxConfig = null;
        return;
    }

    container.innerHTML = '<div class="info-box" style="text-align:center;">⏳ Loading user journeys...</div>';

    try {
        const res = await fetch(`/api/jmx-config?jmx=${encodeURIComponent(jmxName)}`);
        const data = await res.json();

        if (!data.success || !data.config) {
            container.innerHTML = '<div class="info-box" style="color: var(--danger);">Failed to read JMX configuration.</div>';
            launchBtn.disabled = true;
            saveBtn.disabled = true;
            return;
        }

        window.selectedJmxConfig = data.config;
        const tgs = data.config.thread_groups || [];

        // Show CSV warnings if any
        const missingCsvs = (data.config.csv_files || []).filter(c => !c.exists);
        if (missingCsvs.length > 0) {
            csvBox.classList.remove("hidden");
            csvBox.innerHTML = `<div class="info-box" style="border-color: var(--danger); background: rgba(239,68,68,0.08);">
                <strong>⚠️ Missing CSV Files:</strong> ${missingCsvs.map(c => `<code>${c.filename}</code>`).join(", ")}
                <br><small>Upload them in the Upload Test Assets section before running.</small>
            </div>`;
        } else {
            csvBox.classList.add("hidden");
            csvBox.innerHTML = "";
        }

        if (tgs.length === 0) {
            container.innerHTML = '<div class="info-box" style="color: var(--danger);">No User Journeys found in this JMX file.</div>';
            launchBtn.disabled = true;
            saveBtn.disabled = true;
            return;
        }

        container.innerHTML = "";

        tgs.forEach((tg, idx) => {
            const card = document.createElement("div");
            card.className = "tg-config-card";
            card.dataset.tgName = tg.name;
            card.dataset.tgIndex = idx;
            card.style = "background: #ffffff; padding: 1rem 1.25rem; border-radius: var(--border-radius-sm); border: 1px solid var(--border-color); transition: opacity 0.2s;";

            const durationVal = tg.duration > 0 ? `${tg.duration}s` : "0";
            const rampupVal = tg.rampup > 0 ? `${tg.rampup}s` : "0";
            const iterationsVal = tg.iterations || tg.loop_count || 1;
            const isEnabled = tg.enabled !== false;

            card.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <strong style="font-size: 0.9rem; font-weight: 600; color: var(--text-primary);">${tg.name}</strong>
                        <span class="badge badge-passed" style="font-size: 0.7rem; padding: 0.15rem 0.5rem; font-weight: 500;">User Journey ${idx + 1}</span>
                    </div>
                    <label class="tg-toggle" title="${isEnabled ? 'Enabled — click to disable' : 'Disabled — click to enable'}">
                        <input type="checkbox" class="tg-enabled-check" ${isEnabled ? 'checked' : ''} onchange="toggleTgCard(this)">
                        <span class="tg-toggle-slider"></span>
                    </label>
                </div>
                <div class="tg-fields" style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 0.75rem;${!isEnabled ? ' opacity: 0.4; pointer-events: none;' : ''}">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label style="font-size: 0.75rem;">Virtual Users</label>
                        <input type="number" class="tg-users" min="1" max="5000" value="${tg.users}" required>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label style="font-size: 0.75rem;">Duration</label>
                        <input type="text" class="tg-duration" value="${durationVal}" placeholder="60s or 5m" required>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label style="font-size: 0.75rem;">Ramp-Up</label>
                        <input type="text" class="tg-rampup" value="${rampupVal}" placeholder="10s" required>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label style="font-size: 0.75rem;">Iterations</label>
                        <input type="number" class="tg-iterations" min="-1" value="${iterationsVal}" title="-1 = infinite (use with duration)" required>
                    </div>
                </div>
            `;

            if (!isEnabled) card.style.opacity = '0.5';
            container.appendChild(card);
        });

        launchBtn.disabled = false;
        saveBtn.disabled = false;

    } catch (err) {
        console.error("Failed to load JMX config:", err);
        container.innerHTML = '<div class="info-box" style="color: var(--danger);">Error loading user journey configuration.</div>';
        launchBtn.disabled = true;
        saveBtn.disabled = true;
    }
}

function toggleTgCard(checkbox) {
    const card = checkbox.closest('.tg-config-card');
    const fields = card.querySelector('.tg-fields');
    const label = checkbox.closest('.tg-toggle');
    if (checkbox.checked) {
        card.style.opacity = '1';
        fields.style.opacity = '1';
        fields.style.pointerEvents = 'auto';
        label.title = 'Enabled — click to disable';
    } else {
        card.style.opacity = '0.5';
        fields.style.opacity = '0.4';
        fields.style.pointerEvents = 'none';
        label.title = 'Disabled — click to enable';
    }
}

function collectThreadGroupConfigs() {
    const jmxName = document.getElementById("jmx-select").value;
    if (!jmxName) return null;

    const cards = document.querySelectorAll(".tg-config-card");
    const thread_groups = [];

    cards.forEach(card => {
        const enabledCheck = card.querySelector(".tg-enabled-check");
        thread_groups.push({
            name: card.dataset.tgName,
            enabled: enabledCheck ? enabledCheck.checked : true,
            users: parseInt(card.querySelector(".tg-users").value) || 1,
            duration: card.querySelector(".tg-duration").value || "0",
            rampup: card.querySelector(".tg-rampup").value || "0",
            iterations: parseInt(card.querySelector(".tg-iterations").value) || 1
        });
    });

    return { jmx: jmxName, thread_groups };
}

// ── Save Config ──────────────────────────────────────────────────────────────
async function handleSaveJmxConfig() {
    const payload = collectThreadGroupConfigs();
    if (!payload || payload.thread_groups.length === 0) {
        alert("Please select a JMX file and configure user journeys first.");
        return;
    }

    try {
        const res = await fetch("/api/save-config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        alert("Failed to save configuration: " + err);
    }
}

// ── Run Test ──────────────────────────────────────────────────────────────────
async function handleRunTest(e) {
    e.preventDefault();

    const payload = collectThreadGroupConfigs();
    if (!payload || payload.thread_groups.length === 0) return;

    try {
        const res = await fetch("/api/run-test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            switchTab("tab-live");
            startLivePolling(payload.jmx);
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) {
        alert("Failed to launch test: " + err);
    }
}

// ── Live Polling ──────────────────────────────────────────────────────────────
function startLivePolling(jmxName) {
    const subtitle = document.getElementById("live-test-subtitle");
    const badge = document.getElementById("live-indicator-badge");
    const stopBtn = document.getElementById("btn-stop-test");

    subtitle.textContent = `Running scenario: ${jmxName}`;
    badge.classList.remove("hidden");
    stopBtn.classList.remove("hidden");

    if (activePollingInterval) clearInterval(activePollingInterval);

    activePollingInterval = setInterval(async () => {
        try {
            const res = await fetch("/api/jmeter-progress");
            const data = await res.json();

            document.getElementById("live-timer").textContent = data.elapsed_str || "00:00";

            // Fetch current JMX TC hierarchy if available
            let tcMap = {};
            if (jmxName) {
                try {
                    const cfgRes = await fetch(`/api/jmx-config?jmx=${encodeURIComponent(jmxName)}`);
                    const cfgData = await cfgRes.json();
                    if (cfgData.success && cfgData.config) {
                        tcMap = cfgData.config.tc_to_samplers || {};
                    }
                } catch (e) { }
            }

            // Update stats table with Transaction Level grouping & Expandable child HTTP requests
            const statsTbody = document.getElementById("live-metrics-tbody");
            const liveStats = data.live_stats || {};
            const keys = Object.keys(liveStats);

            if (keys.length > 0) {
                statsTbody.innerHTML = "";
                const tcKeys = Object.keys(tcMap);

                // Render Transaction Controllers first
                if (tcKeys.length > 0) {
                    tcKeys.forEach((tcName, idx) => {
                        const tcStat = liveStats[tcName] || { total: 0, errors: 0, total_rt: 0, min_rt: 0, max_rt: 0 };
                        const avgRt = tcStat.total > 0 ? (tcStat.total_rt / tcStat.total).toFixed(0) : 0;
                        const errPct = tcStat.total > 0 ? ((tcStat.errors / tcStat.total) * 100).toFixed(2) : "0.00";
                        const children = tcMap[tcName] || [];
                        const trId = `tc-child-row-${idx}`;

                        const tr = document.createElement("tr");
                        tr.style.background = "var(--bg-light)";

                        tr.innerHTML = `
                            <td>
                                <strong>${tcName}</strong>
                            </td>
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
                    // Fallback to top-level keys
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

            // Update Error Breakdown tab & badge counter
            const failTbody = document.getElementById("live-failures-tbody");
            const errBadge = document.getElementById("error-indicator-badge");
            const failedReqs = data.failed_requests || {};
            const failKeys = Object.keys(failedReqs);

            let totalFailures = 0;
            if (failKeys.length > 0) {
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
            } else {
                if (errBadge) {
                    errBadge.classList.add("hidden");
                }
            }

            if (data.done || !data.running) {
                clearInterval(activePollingInterval);
                badge.classList.add("hidden");
                stopBtn.classList.add("hidden");
                subtitle.textContent = `Test completed for ${jmxName}. View generated HTML report in History.`;
                loadRuns();
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 2000);
}

// ── Stop Test ─────────────────────────────────────────────────────────────────
async function handleStopTest() {
    if (!confirm("Are you sure you want to terminate the running JMeter process?")) return;

    try {
        const res = await fetch("/api/stop-test", { method: "POST" });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        alert("Failed to stop test: " + err);
    }
}

// ── History & Reports ─────────────────────────────────────────────────────────
let allRunsData = [];

async function loadRuns() {
    try {
        const res = await fetch("/api/runs");
        const data = await res.json();
        allRunsData = data.runs || [];

        const searchInput = document.getElementById("report-search-input");
        const query = searchInput ? searchInput.value : "";
        filterReportsUI(query);

        loadPublishedReports();
    } catch (err) {
        console.error("Failed to load runs:", err);
    }
}

function filterReportsUI(query) {
    const term = (query || "").toLowerCase().trim();
    const tbody = document.getElementById("runs-tbody");
    if (!tbody) return;

    if (!allRunsData || allRunsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No test execution history recorded yet.</td></tr>';
        return;
    }

    const filtered = allRunsData.filter(run => {
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

function renderRunsTable(runs) {
    const tbody = document.getElementById("runs-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    runs.forEach(run => {
        const tr = document.createElement("tr");
        tr.className = "clickable-row";
        const badgeClass = run.status === "passed" ? "badge-passed" : run.status === "warning" ? "badge-warning" : "badge-failed";

        // Whole row click handler to open HTML report
        tr.onclick = (e) => {
            if (e.target.closest("button") || e.target.closest("a")) return;
            if (run.report_file) {
                window.open(`/Results/${run.report_file}`, "_blank");
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
            <td style="text-align: center;">${run.has_ai_insights ? ' AI' : '📊 Rule'}</td>
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

async function loadPublishedReports() {
    try {
        const res = await fetch("/api/reports");
        const data = await res.json();
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

let currentRecompileTargetRunId = null;

function recompileLatestReportUI() {
    openRecompileModal(null);
}

function recompileSingleRunUI(runId) {
    openRecompileModal(runId);
}

async function openRecompileModal(runId = null) {
    currentRecompileTargetRunId = runId;
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

    // Populate active AI provider & model meta in modal
    try {
        const res = await fetch("/api/ai-config");
        const data = await res.json();
        const provElem = document.getElementById("recompile-active-provider");
        const modelElem = document.getElementById("recompile-active-model");
        if (provElem) provElem.textContent = (data.provider || "openrouter").toUpperCase();
        if (modelElem) modelElem.textContent = data.model || "nvidia/nemotron-3-ultra-550b-a55b:free";
    } catch (e) {
        console.warn("Could not fetch AI meta for modal:", e);
    }

    if (modal) modal.classList.remove("hidden");
}

function closeRecompileModal() {
    const modal = document.getElementById("recompile-modal");
    if (modal) modal.classList.add("hidden");
}

function toggleRecompileAiOption(checked) {
    const meta = document.getElementById("recompile-ai-meta");
    if (meta) {
        meta.style.opacity = checked ? "1" : "0.4";
    }
}

async function executeRecompile() {
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
        const res = await fetch("/api/recompile-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                run_id: currentRecompileTargetRunId || "",
                regenerate_ai: regenAi
            })
        });
        const data = await res.json();
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

async function deleteRunUI(runId) {
    if (!confirm(`Are you sure you want to delete report '${runId}' and ALL associated files (.html, .json, .jtl, azure JSON)?`)) return;

    try {
        const res = await fetch("/api/delete-run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_id: runId })
        });
        const data = await res.json();
        alert(data.message);
        loadRuns();
    } catch (err) {
        alert("Failed to delete report: " + err);
    }
}

async function loadReports() {
    // Supplementary function for report list
}

// ── Azure Config ─────────────────────────────────────────────────────────────
async function handleSaveAzureConfig() {
    const input = document.getElementById("azure-resources-input").value;
    try {
        const res = await fetch("/api/azure-config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resource_ids: input })
        });
        const data = await res.json();
        alert(data.message);
        loadStatus();
    } catch (err) {
        alert("Failed to save Azure config: " + err);
    }
}

// ── AI & LLM Config ─────────────────────────────────────────────────────────
async function loadAiConfig() {
    try {
        const res = await fetch("/api/ai-config");
        if (!res.ok) return;
        const data = await res.json();

        const providerSelect = document.getElementById("ai-provider-select");
        const modelSelect = document.getElementById("ai-model-select");
        const customModelInput = document.getElementById("ai-model-custom-input");

        const badgeOpenRouter = document.getElementById("badge-openrouter-key");
        const badgeGemini = document.getElementById("badge-gemini-key");
        const badgeGithub = document.getElementById("badge-github-key");
        const statusPill = document.getElementById("ai-status-pill");

        if (providerSelect && data.provider) {
            providerSelect.value = data.provider;
        }

        // Set model
        const currentModel = data.model || "nvidia/nemotron-3-ultra-550b-a55b:free";
        if (modelSelect) {
            let found = false;
            for (let opt of modelSelect.options) {
                if (opt.value === currentModel) {
                    modelSelect.value = currentModel;
                    found = true;
                    break;
                }
            }
            if (!found) {
                modelSelect.value = "custom";
                if (customModelInput) {
                    customModelInput.classList.remove("hidden");
                    customModelInput.value = currentModel;
                }
            } else {
                if (customModelInput) customModelInput.classList.add("hidden");
            }
        }

        // Keys & Badges
        if (badgeOpenRouter) {
            if (data.openrouter_configured) {
                badgeOpenRouter.textContent = `Configured (${data.openrouter_key_masked})`;
                badgeOpenRouter.style.color = "var(--green)";
            } else {
                badgeOpenRouter.textContent = "Not Set";
                badgeOpenRouter.style.color = "var(--text-muted)";
            }
        }
        if (badgeGemini) {
            if (data.gemini_configured) {
                badgeGemini.textContent = `Configured (${data.gemini_key_masked})`;
                badgeGemini.style.color = "var(--green)";
            } else {
                badgeGemini.textContent = "Not Set";
                badgeGemini.style.color = "var(--text-muted)";
            }
        }
        if (badgeGithub) {
            if (data.github_configured) {
                badgeGithub.textContent = `Configured (${data.github_token_masked})`;
                badgeGithub.style.color = "var(--green)";
            } else {
                badgeGithub.textContent = "Not Set";
                badgeGithub.style.color = "var(--text-muted)";
            }
        }

        // Status pill
        if (statusPill) {
            const activeProv = data.provider || "openrouter";
            const isConfigured = (activeProv === "openrouter" && data.openrouter_configured) ||
                (activeProv === "gemini" && data.gemini_configured) ||
                (activeProv === "github" && data.github_configured);
            if (isConfigured) {
                statusPill.textContent = `${activeProv.toUpperCase()} Ready`;
                statusPill.style.color = "#10b981";
                statusPill.style.background = "rgba(16, 185, 129, 0.15)";
                statusPill.style.borderColor = "rgba(16, 185, 129, 0.3)";
            } else {
                statusPill.textContent = "Key Required";
                statusPill.style.color = "#f59e0b";
                statusPill.style.background = "rgba(245, 158, 11, 0.15)";
                statusPill.style.borderColor = "rgba(245, 158, 11, 0.3)";
            }
        }
    } catch (err) {
        console.error("Failed to load AI config:", err);
    }
}

function handleAiProviderChange(val) {
    const modelSelect = document.getElementById("ai-model-select");
    const customInput = document.getElementById("ai-model-custom-input");
    if (!modelSelect) return;
    if (val === "openrouter") {
        modelSelect.value = "nvidia/nemotron-3-ultra-550b-a55b:free";
        if (customInput) customInput.classList.add("hidden");
    } else if (val === "gemini") {
        modelSelect.value = "gemini-2.5-flash";
        if (customInput) customInput.classList.add("hidden");
    } else if (val === "github") {
        modelSelect.value = "gpt-4o-mini";
        if (customInput) customInput.classList.add("hidden");
    }
}

function handleAiModelPresetChange(val) {
    const customInput = document.getElementById("ai-model-custom-input");
    if (!customInput) return;
    if (val === "custom") {
        customInput.classList.remove("hidden");
        customInput.focus();
    } else {
        customInput.classList.add("hidden");
    }
}

async function handleSaveAiConfig() {
    const provider = document.getElementById("ai-provider-select")?.value || "openrouter";
    const modelSelect = document.getElementById("ai-model-select")?.value || "nvidia/nemotron-3-ultra-550b-a55b:free";
    const customModel = document.getElementById("ai-model-custom-input")?.value?.trim() || "";
    const activeModel = (modelSelect === "custom" && customModel) ? customModel : modelSelect;

    const openrouterKey = document.getElementById("openrouter-key-input")?.value?.trim() || "";
    const geminiKey = document.getElementById("gemini-key-input")?.value?.trim() || "";
    const githubToken = document.getElementById("github-token-input")?.value?.trim() || "";

    try {
        const res = await fetch("/api/ai-config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                provider: provider,
                model: activeModel,
                openrouter_key: openrouterKey,
                gemini_key: geminiKey,
                github_token: githubToken
            })
        });
        const data = await res.json();
        if (data.success) {
            alert("✅ " + data.message);
            if (openrouterKey) document.getElementById("openrouter-key-input").value = "";
            if (geminiKey) document.getElementById("gemini-key-input").value = "";
            if (githubToken) document.getElementById("github-token-input").value = "";
            loadAiConfig();
            loadStatus();
        } else {
            alert("❌ Failed: " + data.message);
        }
    } catch (err) {
        alert("Failed to save AI config: " + err);
    }
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────
function setupDragAndDrop() {
    const zone = document.getElementById("drop-zone");
    if (!zone) return;

    zone.addEventListener("click", () => document.getElementById("file-input").click());

    ["dragenter", "dragover"].forEach(eventName => {
        zone.addEventListener(eventName, e => {
            e.preventDefault();
            zone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        zone.addEventListener(eventName, e => {
            e.preventDefault();
            zone.classList.remove("dragover");
        });
    });

    zone.addEventListener("drop", e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
        uploadFile(files[0]);
    }
    e.target.value = "";
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload-jmx", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        alert(data.message);
        loadTests();
        const sel = document.getElementById("test-select");
        if (sel && sel.value) {
            handleSelectTestScenario(sel.value);
        }
    } catch (err) {
        alert("Upload failed: " + err);
    }
}

// ── SLA Management ─────────────────────────────────────────────────────────────
let currentSlaScenarios = [];
let currentSlaIdentifications = [];
let currentSlaFilterQuery = "";

async function loadSlaScenariosFilter(preferredJmx = "") {
    try {
        const res = await fetch("/api/tests");
        const data = await res.json();
        const filter = document.getElementById("sla-jmx-filter");
        if (!filter) return;

        const currentVal = preferredJmx || filter.value;
        filter.innerHTML = '<option value="">All Scenarios / Global Fallback (config/sla_targets.csv)</option>';

        let matched = false;
        if (data.tests && data.tests.length > 0) {
            data.tests.forEach(testFile => {
                if (testFile.endsWith(".jmx")) {
                    const opt = document.createElement("option");
                    opt.value = testFile;
                    opt.textContent = `${testFile} (Paired SLA CSV)`;
                    filter.appendChild(opt);
                    if (currentVal && currentVal === testFile) {
                        matched = true;
                    }
                }
            });
        }

        // Set the active value: prefer passed preferredJmx, then previous val if exists, else first jmx if available
        if (matched) {
            filter.value = currentVal;
        } else if (currentVal === "") {
            filter.value = "";
        } else if (filter.options.length > 1) {
            filter.selectedIndex = 1; // pick first actual JMX test plan
        }

        handleSlaTestPlanChange(filter.value);
    } catch (err) {
        console.error("Failed to load SLA scenario filter:", err);
    }
}

function handleSlaTestPlanChange(jmxName = "") {
    const planNameEl = document.getElementById("sla-chip-plan-name");
    const fileChipEl = document.getElementById("sla-chip-file");

    if (planNameEl) {
        planNameEl.textContent = jmxName || "Global Default";
    }
    if (fileChipEl) {
        if (jmxName) {
            const clean = jmxName.replace(/\.jmx$/i, "");
            fileChipEl.textContent = `Tests/${clean}_sla.csv`;
            fileChipEl.title = `Paired SLA CSV file for ${jmxName}`;
        } else {
            fileChipEl.textContent = "config/sla_targets.csv";
            fileChipEl.title = "Global fallback SLA file";
        }
    }

    loadSlaTargetsForSelectedJmx(jmxName);
}

async function loadSlaTargetsForSelectedJmx(jmxName = "") {
    const tbody = document.getElementById("sla-tbody");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding: 2rem;"><span class="spinner-inline" style="margin-right: 8px;"></span> Loading SLA targets for ${escapeHtml(jmxName || "Global Default")}...</td></tr>`;

    try {
        const url = jmxName ? `/api/sla?jmx=${encodeURIComponent(jmxName)}` : "/api/sla";
        const res = await fetch(url);
        const data = await res.json();

        currentSlaScenarios = data.scenarios || [];
        currentSlaIdentifications = data.identifications || [];

        // Update meta count chips
        const txChip = document.getElementById("sla-chip-txs");
        const scChip = document.getElementById("sla-chip-scenarios");
        if (txChip) {
            txChip.textContent = `${currentSlaIdentifications.length} Transactions`;
        }
        if (scChip) {
            scChip.textContent = `${currentSlaScenarios.length} Load Scenarios`;
        }

        renderSlaTable();
    } catch (err) {
        console.error("Failed to load SLA targets:", err);
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger" style="padding: 1.5rem;">Failed to load SLA targets: ${escapeHtml(String(err))}</td></tr>`;
    }
}

function filterSlaRowsUI(query) {
    currentSlaFilterQuery = (query || "").trim().toLowerCase();
    const tbody = document.getElementById("sla-tbody");
    if (!tbody) return;

    const rows = tbody.querySelectorAll("tr[data-label]");
    let visibleCount = 0;
    rows.forEach(tr => {
        const label = (tr.dataset.label || "").toLowerCase();
        if (!currentSlaFilterQuery || label.includes(currentSlaFilterQuery)) {
            tr.style.display = "";
            visibleCount++;
        } else {
            tr.style.display = "none";
        }
    });

    const noMatchesRow = document.getElementById("sla-no-matches-row");
    if (visibleCount === 0 && rows.length > 0) {
        if (!noMatchesRow) {
            const tr = document.createElement("tr");
            tr.id = "sla-no-matches-row";
            const colSpan = 6 + currentSlaScenarios.length;
            tr.innerHTML = `<td colspan="${colSpan}" class="text-center text-muted" style="padding: 1.5rem;">No transactions matching "<strong>${escapeHtml(query)}</strong>"</td>`;
            tbody.appendChild(tr);
        }
    } else if (noMatchesRow) {
        noMatchesRow.remove();
    }
}

function renderSlaTable() {
    const thead = document.getElementById("sla-thead");
    const tbody = document.getElementById("sla-tbody");
    if (!thead || !tbody) return;

    // 1. Build Header Row with Dynamic Scenario Columns
    let thHtml = `
        <tr>
            <th>Transaction / Sampler Label</th>
            <th style="text-align: center; min-width: 90px;">Critical?</th>
            <th style="min-width: 130px;">Base RT (ms)<br><span style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">Default / Fallback</span></th>
            <th style="min-width: 110px;">Base Err (%)<br><span style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">Default</span></th>
    `;

    currentSlaScenarios.forEach(sc => {
        thHtml += `
            <th class="sla-scenario-th" style="text-align: center; min-width: 170px;">
                <div class="sla-sc-th-header">
                    <span class="sla-sc-name">${escapeHtml(sc.name)}</span>
                    <span class="sla-sc-badge">${sc.users} Users</span>
                    <button type="button" class="sla-sc-del-btn" title="Delete scenario column" onclick="deleteSlaScenarioUI('${sc.id}')">✕</button>
                </div>
                <div class="sla-sc-th-sub">Target RT (ms) | Err (%)</div>
            </th>
        `;
    });

    thHtml += `
            <th>Status / Scope</th>
            <th>Actions</th>
        </tr>
    `;
    thead.innerHTML = thHtml;

    // 2. Build Body Rows
    tbody.innerHTML = "";
    if (currentSlaIdentifications.length === 0) {
        const colSpan = 6 + currentSlaScenarios.length;
        tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-muted" style="padding: 2rem;">No SLA targets found for this test plan. Click "➕ Add Row" or "➕ Add Load Scenario" to get started.</td></tr>`;
        return;
    }

    currentSlaIdentifications.forEach(item => {
        const tr = document.createElement("tr");
        const isDefault = item.label === "default";
        const isCrit = item.is_critical === 1 || item.is_critical === "1" || item.is_critical === true || item.is_critical === "true";
        const isCritChecked = isCrit ? "checked" : "";

        let rowHtml = `
            <td>
                <strong>${escapeHtml(item.label)}</strong>
                ${isDefault ? ' <span class="badge badge-passed">GLOBAL DEFAULT</span>' : ''}
            </td>
            <td style="text-align: center;">
                ${isDefault ? '-' : `
                    <label style="
                        position:relative;
                        display:inline-flex;
                        align-items:center;
                        width:42px;
                        height:23px;
                        padding:2px;
                        border-radius:999px;
                        cursor:pointer;
                        box-sizing:border-box;
                        background:${isCrit ? 'rgba(239,68,68,.16)' : 'rgba(148,163,184,.16)'};
                        border:1px solid ${isCrit ? 'rgba(239,68,68,.28)' : 'rgba(148,163,184,.28)'};
                        backdrop-filter:blur(12px);
                        -webkit-backdrop-filter:blur(12px);
                        box-shadow:inset 0 1px 2px rgba(255,255,255,.7), 0 2px 6px rgba(15,23,42,.06);
                        transition:background .25s ease, border-color .25s ease, box-shadow .25s ease;
                    ">
                        <input
                            type="checkbox"
                            class="sla-crit-checkbox"
                            ${isCritChecked}
                            style="position:absolute; opacity:0; width:0; height:0;"
                            onchange="
                                const track=this.parentElement;
                                const knob=track.querySelector('.sla-toggle-knob');
                                track.style.background=this.checked ? 'rgba(239,68,68,.16)' : 'rgba(148,163,184,.16)';
                                track.style.borderColor=this.checked ? 'rgba(239,68,68,.32)' : 'rgba(148,163,184,.28)';
                                knob.style.transform=this.checked ? 'translateX(19px) scaleX(1.12)' : 'translateX(0) scaleX(1)';
                                knob.style.background=this.checked ? '#ef4444' : 'rgba(255,255,255,.92)';
                            "
                        >
                        <span
                            class="sla-toggle-knob"
                            style="
                                display:block;
                                width:17px;
                                height:17px;
                                flex:none;
                                border-radius:50%;
                                background:${isCrit ? '#ef4444' : 'rgba(255,255,255,.92)'};
                                transform:${isCrit ? 'translateX(19px) scaleX(1.12)' : 'translateX(0) scaleX(1)'};
                                box-shadow:${isCrit ? '0 2px 7px rgba(239,68,68,.28), inset 0 1px 1px rgba(255,255,255,.45)' : '0 2px 6px rgba(15,23,42,.12), inset 0 1px 1px rgba(255,255,255,.8)'};
                                transition:transform .38s cubic-bezier(.34,1.56,.64,1), background .22s ease, box-shadow .22s ease;
                            "
                        ></span>
                    </label>
                `}
            </td>
            <td><input type="number" class="sla-rt-input" value="${item.rt}" style="width: 110px;" required></td>
            <td><input type="number" step="0.1" class="sla-err-input" value="${item.err}" style="width: 90px;" required></td>
        `;

        // Scenario Cells
        const itemScenarios = item.scenarios || {};
        currentSlaScenarios.forEach(sc => {
            const scVal = itemScenarios[sc.id] || itemScenarios[sc.name] || { rt: item.rt, err: item.err };
            rowHtml += `
                <td class="sla-sc-td" style="text-align: center;">
                    <div style="display: flex; gap: 6px; justify-content: center; align-items: center;">
                        <input type="number" class="sla-sc-rt-input" data-sc-id="${sc.id}" value="${scVal.rt}" placeholder="RT" title="${escapeHtml(sc.name)} Target RT (ms)" style="width: 76px; text-align: center;" required>
                        <input type="number" step="0.1" class="sla-sc-err-input" data-sc-id="${sc.id}" value="${scVal.err}" placeholder="Err%" title="${escapeHtml(sc.name)} Target Error Rate (%)" style="width: 62px; text-align: center;" required>
                    </div>
                </td>
            `;
        });

        rowHtml += `
            <td><span class="badge ${item.defined ? 'badge-passed' : 'badge-warning'}">${escapeHtml(item.status || 'Defined')}</span></td>
            <td>${!isDefault ? `<button type="button" class="btn btn-danger" onclick="deleteSlaRowUI(this)" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Delete</button>` : '<span class="text-muted" style="font-size:0.75rem;">System Default</span>'}</td>
        `;

        tr.innerHTML = rowHtml;
        tr.dataset.label = item.label;
        tbody.appendChild(tr);
    });

    if (currentSlaFilterQuery) {
        filterSlaRowsUI(currentSlaFilterQuery);
    }
}

function deleteSlaRowUI(button) {
    const tr = button.closest("tr");
    if (!tr) return;
    const label = tr.dataset.label;
    if (confirm(`Remove SLA definition for "${label}"?`)) {
        tr.remove();
        snapshotSlaTableState();
        const txChip = document.getElementById("sla-chip-txs");
        if (txChip) {
            txChip.textContent = `${currentSlaIdentifications.length} Transactions`;
        }
    }
}

function openAddScenarioModalUI() {
    const modal = document.getElementById("add-scenario-modal");
    if (!modal) return;
    const nameInput = document.getElementById("new-scenario-name");
    const usersInput = document.getElementById("new-scenario-users");
    if (nameInput) nameInput.value = "";
    if (usersInput) usersInput.value = "";
    modal.classList.remove("hidden");
    if (nameInput) nameInput.focus();
}

function closeAddScenarioModalUI() {
    const modal = document.getElementById("add-scenario-modal");
    if (modal) modal.classList.add("hidden");
}

function applyScenarioPresetUI(name, users) {
    const nameInput = document.getElementById("new-scenario-name");
    const usersInput = document.getElementById("new-scenario-users");
    if (nameInput) nameInput.value = name;
    if (usersInput) usersInput.value = users;
}

function confirmAddScenarioUI() {
    const nameInput = document.getElementById("new-scenario-name");
    const usersInput = document.getElementById("new-scenario-users");

    const scName = nameInput ? nameInput.value.trim() : "";
    const scUsers = usersInput ? parseInt(usersInput.value, 10) : 0;

    if (!scName) {
        alert("Please enter a Scenario Name (e.g. 'Normal Load', 'Peak Load', 'Spike Load').");
        if (nameInput) nameInput.focus();
        return;
    }
    if (!scUsers || scUsers <= 0) {
        alert("Please enter a valid target user count (e.g. 50, 200, 500).");
        if (usersInput) usersInput.focus();
        return;
    }

    // Check if scenario with same name or same users already exists
    const exists = currentSlaScenarios.some(s => s.name.toLowerCase() === scName.toLowerCase() || s.users === scUsers);
    if (exists) {
        alert(`A scenario with name "${scName}" or user load (${scUsers} Users) already exists.`);
        return;
    }

    // Snapshot current inputs in table before re-rendering
    snapshotSlaTableState();

    const scId = `sc_${scName.toLowerCase().replace(/[^a-z0-9_]/g, '_')}_${scUsers}`;
    currentSlaScenarios.push({
        id: scId,
        name: scName,
        users: scUsers
    });

    // Sort scenarios by user load
    currentSlaScenarios.sort((a, b) => a.users - b.users);

    closeAddScenarioModalUI();

    const scChip = document.getElementById("sla-chip-scenarios");
    if (scChip) {
        scChip.textContent = `${currentSlaScenarios.length} Load Scenarios`;
    }

    renderSlaTable();
}

function deleteSlaScenarioUI(scenarioId) {
    const sc = currentSlaScenarios.find(s => s.id === scenarioId);
    if (!sc) return;

    if (!confirm(`Are you sure you want to delete the "${sc.name} (${sc.users} Users)" load scenario column?`)) {
        return;
    }

    snapshotSlaTableState();
    currentSlaScenarios = currentSlaScenarios.filter(s => s.id !== scenarioId);

    const scChip = document.getElementById("sla-chip-scenarios");
    if (scChip) {
        scChip.textContent = `${currentSlaScenarios.length} Load Scenarios`;
    }

    renderSlaTable();
}

// ── Custom Transaction Row Modal ──
function openAddCustomTransactionModalUI() {
    const modal = document.getElementById("add-transaction-modal");
    if (!modal) return;
    const labelInput = document.getElementById("new-tx-label");
    const rtInput = document.getElementById("new-tx-rt");
    const errInput = document.getElementById("new-tx-err");
    const critInput = document.getElementById("new-tx-critical");

    if (labelInput) labelInput.value = "";
    if (rtInput) rtInput.value = "500";
    if (errInput) errInput.value = "1.0";
    if (critInput) critInput.checked = false;

    modal.classList.remove("hidden");
    if (labelInput) labelInput.focus();
}

function closeAddTransactionModalUI() {
    const modal = document.getElementById("add-transaction-modal");
    if (modal) modal.classList.add("hidden");
}

function confirmAddTransactionUI() {
    const labelInput = document.getElementById("new-tx-label");
    const rtInput = document.getElementById("new-tx-rt");
    const errInput = document.getElementById("new-tx-err");
    const critInput = document.getElementById("new-tx-critical");

    const label = labelInput ? labelInput.value.trim() : "";
    const rt = rtInput ? parseFloat(rtInput.value) || 500 : 500;
    const err = errInput ? parseFloat(errInput.value) || 1.0 : 1.0;
    const isCrit = critInput ? (critInput.checked ? 1 : 0) : 0;

    if (!label) {
        alert("Please enter a Transaction or Sampler label.");
        if (labelInput) labelInput.focus();
        return;
    }

    snapshotSlaTableState();

    const exists = currentSlaIdentifications.some(i => i.label.toLowerCase() === label.toLowerCase());
    if (exists) {
        alert(`A transaction with label "${label}" already exists in the SLA table.`);
        return;
    }

    currentSlaIdentifications.push({
        label: label,
        rt: rt,
        err: err,
        is_critical: isCrit,
        scenarios: {},
        status: "Custom Added",
        defined: true
    });

    closeAddTransactionModalUI();

    const txChip = document.getElementById("sla-chip-txs");
    if (txChip) {
        txChip.textContent = `${currentSlaIdentifications.length} Transactions`;
    }

    renderSlaTable();
}

function snapshotSlaTableState() {
    const tbody = document.getElementById("sla-tbody");
    if (!tbody) return;

    const rows = tbody.querySelectorAll("tr");
    const updatedIdentifications = [];

    rows.forEach(tr => {
        const label = tr.dataset.label;
        if (!label) return;
        const rtInput = tr.querySelector(".sla-rt-input");
        const errInput = tr.querySelector(".sla-err-input");
        const critInput = tr.querySelector(".sla-crit-checkbox");

        const scMap = {};
        currentSlaScenarios.forEach(sc => {
            const scRtInput = tr.querySelector(`.sla-sc-rt-input[data-sc-id="${sc.id}"]`);
            const scErrInput = tr.querySelector(`.sla-sc-err-input[data-sc-id="${sc.id}"]`);
            if (scRtInput && scErrInput) {
                scMap[sc.id] = {
                    rt: parseFloat(scRtInput.value) || (rtInput ? parseFloat(rtInput.value) : 500),
                    err: parseFloat(scErrInput.value) || (errInput ? parseFloat(errInput.value) : 1.0)
                };
                scMap[sc.name] = scMap[sc.id];
            }
        });

        const exItem = currentSlaIdentifications.find(i => i.label === label) || {};
        updatedIdentifications.push({
            label: label,
            rt: rtInput ? parseFloat(rtInput.value) || 500 : (exItem.rt || 500),
            err: errInput ? parseFloat(errInput.value) || 1.0 : (exItem.err || 1.0),
            is_critical: critInput ? (critInput.checked ? 1 : 0) : (exItem.is_critical || 0),
            scenarios: scMap,
            status: exItem.status || "Explicitly Defined",
            defined: exItem.defined !== undefined ? exItem.defined : true
        });
    });

    currentSlaIdentifications = updatedIdentifications;
}

async function saveSlaTargetsFromUI() {
    const filter = document.getElementById("sla-jmx-filter");
    const jmxName = filter ? filter.value : "";
    const saveBtn = document.getElementById("btn-save-sla");
    const origBtnHtml = saveBtn ? saveBtn.innerHTML : "";

    snapshotSlaTableState();

    const slas = currentSlaIdentifications.map(item => ({
        label: item.label,
        rt: item.rt,
        err: item.err,
        is_critical: item.is_critical,
        scenarios: item.scenarios || {}
    }));

    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-inline"></span> Saving...';
    }

    try {
        const res = await fetch("/api/sla", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                slas: slas,
                scenarios: currentSlaScenarios,
                jmx: jmxName
            })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message || "SLA targets saved successfully!");
            loadSlaTargetsForSelectedJmx(jmxName);
        } else {
            alert("Failed to save SLA targets: " + (data.message || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to save SLA targets: " + err);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = origBtnHtml;
        }
    }
}

// Global modal close on Escape key
window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        closeAddScenarioModalUI();
        closeAddTransactionModalUI();
    }
});

