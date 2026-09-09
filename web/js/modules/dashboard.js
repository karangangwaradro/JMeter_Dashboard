// modules/dashboard.js — Multi-Tool Selection & JMX Parameter Editor
import { api } from '../core/api.js';
import { state } from '../core/state.js';
import { loadStatus } from './status.js';

window.availableJmxFiles = [];
window.selectedJmxConfig = null;

export async function loadTests() {
    try {
        const data = await api.get("/api/tests");
        window.availableJmxFiles = [];
        state.availableJmxFiles = [];

        const jmxSelect = document.getElementById("jmx-select");
        if (!jmxSelect) return;

        const currentVal = jmxSelect.value;
        jmxSelect.innerHTML = '<option value="">Select test plan...</option>';

        if (data.tests && data.tests.length > 0) {
            data.tests.forEach(t => {
                const name = typeof t === "string" ? t : (t.name || "");
                if (name && name.endsWith(".jmx")) {
                    window.availableJmxFiles.push(name);
                    state.availableJmxFiles.push(name);
                    const opt = document.createElement("option");
                    opt.value = name;
                    opt.textContent = name;
                    jmxSelect.appendChild(opt);
                }
            });
        }

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

export async function handleJmxSelection(jmxName) {
    const container = document.getElementById("thread-groups-container");
    const csvBox = document.getElementById("csv-warnings-box");
    const launchBtn = document.getElementById("btn-launch-test");
    const saveBtn = document.getElementById("btn-save-config");

    if (!jmxName) {
        if (container) container.innerHTML = '<div class="info-box">Select a JMX file above to view and configure its user journeys.</div>';
        if (launchBtn) launchBtn.disabled = true;
        if (saveBtn) saveBtn.disabled = true;
        if (csvBox) csvBox.classList.add("hidden");
        window.selectedJmxConfig = null;
        state.selectedJmxConfig = null;
        return;
    }

    if (container) container.innerHTML = '<div class="info-box" style="text-align:center;">⏳ Loading user journeys...</div>';

    try {
        const data = await api.get(`/api/jmx-config?jmx=${encodeURIComponent(jmxName)}`);

        if (!data.success || !data.config) {
            if (container) container.innerHTML = '<div class="info-box" style="color: var(--danger);">Failed to read JMX configuration.</div>';
            if (launchBtn) launchBtn.disabled = true;
            if (saveBtn) saveBtn.disabled = true;
            return;
        }

        window.selectedJmxConfig = data.config;
        state.selectedJmxConfig = data.config;
        const tgs = data.config.thread_groups || [];

        const missingCsvs = (data.config.csv_files || []).filter(c => !c.exists);
        if (missingCsvs.length > 0 && csvBox) {
            csvBox.classList.remove("hidden");
            csvBox.innerHTML = `<div class="info-box" style="border-color: var(--danger); background: rgba(239,68,68,0.08);">
                <strong>⚠️ Missing CSV Files:</strong> ${missingCsvs.map(c => `<code>${c.filename}</code>`).join(", ")}
                <br><small>Upload them in the Upload Test Assets section before running.</small>
            </div>`;
        } else if (csvBox) {
            csvBox.classList.add("hidden");
            csvBox.innerHTML = "";
        }

        if (tgs.length === 0 && container) {
            container.innerHTML = '<div class="info-box" style="color: var(--danger);">No User Journeys found in this JMX file.</div>';
            if (launchBtn) launchBtn.disabled = true;
            if (saveBtn) saveBtn.disabled = true;
            return;
        }

        if (container) {
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
        }

        if (launchBtn) launchBtn.disabled = false;
        if (saveBtn) saveBtn.disabled = false;

    } catch (err) {
        console.error("Failed to load JMX config:", err);
        if (container) container.innerHTML = '<div class="info-box" style="color: var(--danger);">Error loading user journey configuration.</div>';
        if (launchBtn) launchBtn.disabled = true;
        if (saveBtn) saveBtn.disabled = true;
    }
}

export function toggleTgCard(checkbox) {
    const card = checkbox.closest('.tg-config-card');
    if (!card) return;
    const fields = card.querySelector('.tg-fields');
    const label = checkbox.closest('.tg-toggle');
    if (checkbox.checked) {
        card.style.opacity = '1';
        if (fields) {
            fields.style.opacity = '1';
            fields.style.pointerEvents = 'auto';
        }
        if (label) label.title = 'Enabled — click to disable';
    } else {
        card.style.opacity = '0.5';
        if (fields) {
            fields.style.opacity = '0.4';
            fields.style.pointerEvents = 'none';
        }
        if (label) label.title = 'Disabled — click to enable';
    }
}

export function collectThreadGroupConfigs() {
    const jmxName = document.getElementById("jmx-select")?.value;
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

export async function handleSaveJmxConfig() {
    const payload = collectThreadGroupConfigs();
    if (!payload || payload.thread_groups.length === 0) {
        alert("Please select a JMX file and configure user journeys first.");
        return;
    }

    try {
        const data = await api.post("/api/save-config", payload);
        alert(data.message);
    } catch (err) {
        alert("Failed to save configuration: " + err);
    }
}

export function handleToolChange(tool) {
    const ingestSelect = document.getElementById("ingest-select");
    const cloudLbl = document.getElementById("lbl-cloud-test-id");
    if (cloudLbl) {
        if (tool === "blazemeter") {
            cloudLbl.textContent = "BlazeMeter Test ID / Master ID";
        } else if (tool === "neoload") {
            cloudLbl.textContent = "NeoLoad Test ID / Result ID";
        } else {
            cloudLbl.textContent = "Cloud Test ID";
        }
    }
    handleIngestChange(ingestSelect ? ingestSelect.value : "local");
}

export function handleIngestChange(method) {
    const tool = document.getElementById("tool-select") ? document.getElementById("tool-select").value : "jmeter";
    const grpJmeter = document.getElementById("group-jmeter-local");
    const grpCloud = document.getElementById("group-cloud-id");
    const grpUpload = document.getElementById("group-upload-raw");
    const btnSaveCfg = document.getElementById("btn-save-config");
    const btnLaunch = document.getElementById("btn-launch-test");

    if (grpJmeter) grpJmeter.classList.add("hidden");
    if (grpCloud) grpCloud.classList.add("hidden");
    if (grpUpload) grpUpload.classList.add("hidden");

    if (method === "file_upload") {
        if (grpUpload) grpUpload.classList.remove("hidden");
        if (btnSaveCfg) btnSaveCfg.style.display = "none";
        if (btnLaunch) btnLaunch.textContent = "Upload & Generate Report";
    } else if (method === "direct_api" || method === "mcp") {
        if (grpCloud) grpCloud.classList.remove("hidden");
        if (btnSaveCfg) btnSaveCfg.style.display = "none";
        if (btnLaunch) btnLaunch.textContent = `Fetch & Ingest via ${method === "mcp" ? "MCP" : "API"}`;
    } else {
        if (grpJmeter) grpJmeter.classList.remove("hidden");
        if (btnSaveCfg) btnSaveCfg.style.display = "block";
        if (btnLaunch) btnLaunch.textContent = "Execute Performance Test";
    }
}

export async function handleSaveAzureConfig() {
    const input = document.getElementById("azure-resources-input")?.value || "";
    try {
        const data = await api.post("/api/azure-config", { resource_ids: input });
        alert(data.message);
        loadStatus();
    } catch (err) {
        alert("Failed to save Azure config: " + err);
    }
}

window.loadTests = loadTests;
window.handleJmxSelection = handleJmxSelection;
window.toggleTgCard = toggleTgCard;
window.handleSaveJmxConfig = handleSaveJmxConfig;
window.handleToolChange = handleToolChange;
window.handleIngestChange = handleIngestChange;
window.handleSaveAzureConfig = handleSaveAzureConfig;
