// modules/execution.js — Test Execution & Real-Time Polling Loop
import { api } from '../core/api.js';
import { state } from '../core/state.js';
import { switchTab } from '../core/router.js';
import { loadRuns, loadReports } from './reports.js';
import { collectThreadGroupConfigs } from './dashboard.js';

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
        const formData = new FormData();
        formData.append("file", file);
        formData.append("tool", tool);
        if (scenarioName) formData.append("test_name", scenarioName);

        try {
            const btn = document.getElementById("btn-launch-test");
            if (btn) btn.textContent = "Ingesting & Normalizing...";
            const data = await api.upload("/api/ingest/upload", formData);
            if (data.success) {
                alert(`Successfully processed ${file.name}! Report generated: ${data.report_url}`);
                window.open(data.report_url, "_blank");
                loadRuns();
                loadReports();
            } else {
                alert("Upload failed: " + (data.message || JSON.stringify(data)));
            }
        } catch (err) {
            alert("Upload ingestion error: " + err);
        } finally {
            const btn = document.getElementById("btn-launch-test");
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

        try {
            const endpoint = method === "mcp" ? "/api/ingest/mcp" : "/api/ingest/api";
            const data = await api.post(endpoint, {
                tool: tool,
                identifier: testId,
                users: users
            });
            if (data.success) {
                alert(`Successfully ingested ${tool} test ${testId}!`);
                if (data.report_url) window.open(data.report_url, "_blank");
                loadRuns();
                loadReports();
            } else {
                alert("Ingestion error: " + (data.message || JSON.stringify(data)));
            }
        } catch (err) {
            alert("Ingestion request failed: " + err);
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

window.handleRunTest = handleRunTest;
window.startLivePolling = startLivePolling;
window.checkAndResumeLivePolling = checkAndResumeLivePolling;
window.handleStopTest = handleStopTest;
