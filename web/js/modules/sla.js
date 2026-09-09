// modules/sla.js — Scenario SLA Targets & Matrix Configuration
import { api } from '../core/api.js';
import { state } from '../core/state.js';
import { escapeHtml } from '../core/utils.js';

export async function loadSlaScenariosFilter(preferredJmx = "") {
    try {
        const data = await api.get("/api/tests");
        const filter = document.getElementById("sla-jmx-filter");
        if (!filter) return;

        const currentVal = preferredJmx || filter.value;
        filter.innerHTML = '<option value="">All Scenarios / Global Fallback (config/sla_targets.csv)</option>';

        let matched = false;
        if (data.tests && data.tests.length > 0) {
            data.tests.forEach(t => {
                const testFile = typeof t === "string" ? t : (t.name || "");
                if (testFile && testFile.endsWith(".jmx")) {
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

        if (matched) {
            filter.value = currentVal;
        } else if (currentVal === "") {
            filter.value = "";
        } else if (filter.options.length > 1) {
            filter.selectedIndex = 1;
        }

        handleSlaTestPlanChange(filter.value);
    } catch (err) {
        console.error("Failed to load SLA scenario filter:", err);
    }
}

export function handleSlaTestPlanChange(jmxName = "") {
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

export async function loadSlaTargetsForSelectedJmx(jmxName = "") {
    const tbody = document.getElementById("sla-tbody");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding: 2rem;"><span class="spinner-inline" style="margin-right: 8px;"></span> Loading SLA targets for ${escapeHtml(jmxName || "Global Default")}...</td></tr>`;

    try {
        const url = jmxName ? `/api/sla?jmx=${encodeURIComponent(jmxName)}` : "/api/sla";
        const data = await api.get(url);

        state.currentSlaScenarios = data.scenarios || [];
        state.currentSlaIdentifications = data.identifications || [];

        const txChip = document.getElementById("sla-chip-txs");
        const scChip = document.getElementById("sla-chip-scenarios");
        if (txChip) {
            txChip.textContent = `${state.currentSlaIdentifications.length} Transactions`;
        }
        if (scChip) {
            scChip.textContent = `${state.currentSlaScenarios.length} Load Scenarios`;
        }

        renderSlaTable();
    } catch (err) {
        console.error("Failed to load SLA targets:", err);
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger" style="padding: 1.5rem;">Failed to load SLA targets: ${escapeHtml(String(err))}</td></tr>`;
    }
}

export function filterSlaRowsUI(query) {
    state.currentSlaFilterQuery = (query || "").trim().toLowerCase();
    const tbody = document.getElementById("sla-tbody");
    if (!tbody) return;

    const rows = tbody.querySelectorAll("tr[data-label]");
    let visibleCount = 0;
    rows.forEach(tr => {
        const label = (tr.dataset.label || "").toLowerCase();
        if (!state.currentSlaFilterQuery || label.includes(state.currentSlaFilterQuery)) {
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
            const colSpan = 6 + state.currentSlaScenarios.length;
            tr.innerHTML = `<td colspan="${colSpan}" class="text-center text-muted" style="padding: 1.5rem;">No transactions matching "<strong>${escapeHtml(query)}</strong>"</td>`;
            tbody.appendChild(tr);
        }
    } else if (noMatchesRow) {
        noMatchesRow.remove();
    }
}

export function renderSlaTable() {
    const thead = document.getElementById("sla-thead");
    const tbody = document.getElementById("sla-tbody");
    if (!thead || !tbody) return;

    let thHtml = `
        <tr>
            <th>Transaction / Sampler Label</th>
            <th style="text-align: center; min-width: 90px;">Critical?</th>
            <th style="min-width: 130px;">Base RT (ms)<br><span style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">Default / Fallback</span></th>
            <th style="min-width: 110px;">Base Err (%)<br><span style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">Default</span></th>
    `;

    state.currentSlaScenarios.forEach(sc => {
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

    tbody.innerHTML = "";
    if (state.currentSlaIdentifications.length === 0) {
        const colSpan = 6 + state.currentSlaScenarios.length;
        tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-muted" style="padding: 2rem;">No SLA targets found for this test plan. Click "➕ Add Row" or "➕ Add Load Scenario" to get started.</td></tr>`;
        return;
    }

    state.currentSlaIdentifications.forEach(item => {
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

        const itemScenarios = item.scenarios || {};
        state.currentSlaScenarios.forEach(sc => {
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

    if (state.currentSlaFilterQuery) {
        filterSlaRowsUI(state.currentSlaFilterQuery);
    }
}

export function deleteSlaRowUI(button) {
    const tr = button.closest("tr");
    if (!tr) return;
    const label = tr.dataset.label;
    if (confirm(`Remove SLA definition for "${label}"?`)) {
        tr.remove();
        snapshotSlaTableState();
        const txChip = document.getElementById("sla-chip-txs");
        if (txChip) {
            txChip.textContent = `${state.currentSlaIdentifications.length} Transactions`;
        }
    }
}

export function openAddScenarioModalUI() {
    const modal = document.getElementById("add-scenario-modal");
    if (!modal) return;
    const nameInput = document.getElementById("new-scenario-name");
    const usersInput = document.getElementById("new-scenario-users");
    if (nameInput) nameInput.value = "";
    if (usersInput) usersInput.value = "";
    modal.classList.remove("hidden");
    if (nameInput) nameInput.focus();
}

export function closeAddScenarioModalUI() {
    const modal = document.getElementById("add-scenario-modal");
    if (modal) modal.classList.add("hidden");
}

export function applyScenarioPresetUI(name, users) {
    const nameInput = document.getElementById("new-scenario-name");
    const usersInput = document.getElementById("new-scenario-users");
    if (nameInput) nameInput.value = name;
    if (usersInput) usersInput.value = users;
}

export function confirmAddScenarioUI() {
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

    const exists = state.currentSlaScenarios.some(s => s.name.toLowerCase() === scName.toLowerCase() || s.users === scUsers);
    if (exists) {
        alert(`A scenario with name "${scName}" or user load (${scUsers} Users) already exists.`);
        return;
    }

    snapshotSlaTableState();

    const scId = `sc_${scName.toLowerCase().replace(/[^a-z0-9_]/g, '_')}_${scUsers}`;
    state.currentSlaScenarios.push({
        id: scId,
        name: scName,
        users: scUsers
    });

    state.currentSlaScenarios.sort((a, b) => a.users - b.users);
    closeAddScenarioModalUI();

    const scChip = document.getElementById("sla-chip-scenarios");
    if (scChip) {
        scChip.textContent = `${state.currentSlaScenarios.length} Load Scenarios`;
    }

    renderSlaTable();
}

export function deleteSlaScenarioUI(scenarioId) {
    const sc = state.currentSlaScenarios.find(s => s.id === scenarioId);
    if (!sc) return;

    if (!confirm(`Are you sure you want to delete the "${sc.name} (${sc.users} Users)" load scenario column?`)) {
        return;
    }

    snapshotSlaTableState();
    state.currentSlaScenarios = state.currentSlaScenarios.filter(s => s.id !== scenarioId);

    const scChip = document.getElementById("sla-chip-scenarios");
    if (scChip) {
        scChip.textContent = `${state.currentSlaScenarios.length} Load Scenarios`;
    }

    renderSlaTable();
}

export function openAddCustomTransactionModalUI() {
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

export function closeAddTransactionModalUI() {
    const modal = document.getElementById("add-transaction-modal");
    if (modal) modal.classList.add("hidden");
}

export function confirmAddTransactionUI() {
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

    const exists = state.currentSlaIdentifications.some(i => i.label.toLowerCase() === label.toLowerCase());
    if (exists) {
        alert(`A transaction with label "${label}" already exists in the SLA table.`);
        return;
    }

    state.currentSlaIdentifications.push({
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
        txChip.textContent = `${state.currentSlaIdentifications.length} Transactions`;
    }

    renderSlaTable();
}

export function snapshotSlaTableState() {
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
        state.currentSlaScenarios.forEach(sc => {
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

        const exItem = state.currentSlaIdentifications.find(i => i.label === label) || {};
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

    state.currentSlaIdentifications = updatedIdentifications;
}

export async function saveSlaTargetsFromUI() {
    const filter = document.getElementById("sla-jmx-filter");
    const jmxName = filter ? filter.value : "";
    const saveBtn = document.getElementById("btn-save-sla");
    const origBtnHtml = saveBtn ? saveBtn.innerHTML : "";

    snapshotSlaTableState();

    const slas = state.currentSlaIdentifications.map(item => ({
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
        const data = await api.post("/api/sla", {
            slas: slas,
            scenarios: state.currentSlaScenarios,
            jmx: jmxName
        });
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

// Window event exports
window.loadSlaScenariosFilter = loadSlaScenariosFilter;
window.handleSlaTestPlanChange = handleSlaTestPlanChange;
window.loadSlaTargetsForSelectedJmx = loadSlaTargetsForSelectedJmx;
window.filterSlaRowsUI = filterSlaRowsUI;
window.renderSlaTable = renderSlaTable;
window.deleteSlaRowUI = deleteSlaRowUI;
window.openAddScenarioModalUI = openAddScenarioModalUI;
window.closeAddScenarioModalUI = closeAddScenarioModalUI;
window.applyScenarioPresetUI = applyScenarioPresetUI;
window.confirmAddScenarioUI = confirmAddScenarioUI;
window.deleteSlaScenarioUI = deleteSlaScenarioUI;
window.openAddCustomTransactionModalUI = openAddCustomTransactionModalUI;
window.closeAddTransactionModalUI = closeAddTransactionModalUI;
window.confirmAddTransactionUI = confirmAddTransactionUI;
window.snapshotSlaTableState = snapshotSlaTableState;
window.saveSlaTargetsFromUI = saveSlaTargetsFromUI;
