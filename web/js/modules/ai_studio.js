// ai_studio.js — Interactive AI Insights Studio & Refinement Playground

let currentStudioRunId = null;
let currentStudioRunData = null;
let currentStudioInsights = null;

export function initAiStudio() {
    loadStudioRuns();

    const runSelect = document.getElementById("studio-run-select");
    if (runSelect && !runSelect.dataset.listenerBound) {
        runSelect.dataset.listenerBound = "true";
        runSelect.addEventListener("change", (e) => {
            const selected = e.target.value;
            if (selected) {
                loadRunPromptPreview(selected);
            }
        });
    }

    const generateBtn = document.getElementById("studio-generate-btn");
    if (generateBtn && !generateBtn.dataset.listenerBound) {
        generateBtn.dataset.listenerBound = "true";
        generateBtn.addEventListener("click", () => {
            generateStudioInsights();
        });
    }

    const saveBtn = document.getElementById("studio-save-btn");
    if (saveBtn && !saveBtn.dataset.listenerBound) {
        saveBtn.dataset.listenerBound = "true";
        saveBtn.addEventListener("click", () => {
            saveStudioInsights();
        });
    }

    const resetPromptBtn = document.getElementById("studio-reset-prompt-btn");
    if (resetPromptBtn && !resetPromptBtn.dataset.listenerBound) {
        resetPromptBtn.dataset.listenerBound = "true";
        resetPromptBtn.addEventListener("click", () => {
            if (currentStudioRunId) {
                loadRunPromptPreview(currentStudioRunId);
            }
        });
    }

    const copyPromptBtn = document.getElementById("studio-copy-prompt-btn");
    if (copyPromptBtn && !copyPromptBtn.dataset.listenerBound) {
        copyPromptBtn.dataset.listenerBound = "true";
        copyPromptBtn.addEventListener("click", () => {
            const promptText = document.getElementById("studio-prompt-input")?.value || "";
            navigator.clipboard.writeText(promptText);
            showStudioToast("Prompt copied to clipboard!");
        });
    }

    const copyJsonBtn = document.getElementById("studio-copy-json-btn");
    if (copyJsonBtn && !copyJsonBtn.dataset.listenerBound) {
        copyJsonBtn.dataset.listenerBound = "true";
        copyJsonBtn.addEventListener("click", () => {
            if (currentStudioInsights) {
                navigator.clipboard.writeText(JSON.stringify(currentStudioInsights, null, 2));
                showStudioToast("Insights JSON copied to clipboard!");
            }
        });
    }
}

// ── Load available runs into dropdown ──────────────────────────────────────────
export async function loadStudioRuns() {
    const runSelect = document.getElementById("studio-run-select");
    if (!runSelect) return;

    try {
        const resp = await fetch("/api/ai-studio/runs");
        const data = await resp.json();
        if (data.success && data.runs && data.runs.length > 0) {
            runSelect.innerHTML = '<option value="">-- Select a Test Execution Run --</option>';
            data.runs.forEach(r => {
                const opt = document.createElement("option");
                opt.value = r.id;
                const aiBadge = r.has_ai ? `[AI: ${r.ai_grade || 'Ready'}]` : "[No AI]";
                const s = r.summary || {};
                const total = s.total ?? s.total_requests ?? 0;
                const avgRt = s.avg_rt ?? s.avg_response_time ?? 0;
                const formattedAvgRt = typeof avgRt === "number" ? avgRt.toFixed(0) : avgRt;
                opt.textContent = `${r.id} · ${r.jmx_name || 'Scenario'} (${total} reqs, ${formattedAvgRt}ms) ${aiBadge}`;
                runSelect.appendChild(opt);
            });

            // Preserve current selection if present, else auto-select the latest run
            if (currentStudioRunId && Array.from(runSelect.options).some(o => o.value === currentStudioRunId)) {
                runSelect.value = currentStudioRunId;
            } else {
                runSelect.selectedIndex = 1;
                loadRunPromptPreview(data.runs[0].id);
            }
        } else {
            runSelect.innerHTML = '<option value="">No past test runs found</option>';
        }
    } catch (err) {
        console.error("Error loading studio runs:", err);
        runSelect.innerHTML = '<option value="">Failed to load runs</option>';
    }
}

// ── Fetch prompt preview & telemetry for chosen run ───────────────────────────
export async function loadRunPromptPreview(runId) {
    if (!runId) return;
    currentStudioRunId = runId;
    const promptInput = document.getElementById("studio-prompt-input");
    const statusChip = document.getElementById("studio-status-indicator");
    
    if (statusChip) statusChip.textContent = "Loading run telemetry...";

    try {
        const resp = await fetch(`/api/ai-studio/prompt-preview?run_id=${encodeURIComponent(runId)}`);
        const data = await resp.json();
        if (data.success) {
            currentStudioRunData = data;
            if (promptInput) {
                promptInput.value = data.prompt || "";
            }
            updateStudioTelemetryDisplay(data);

            if (data.existing_insights && data.existing_insights.source && data.existing_insights.source !== "none") {
                currentStudioInsights = data.existing_insights;
                renderStudioInsights(data.existing_insights, 0, data.existing_insights.model || "Existing Insights");
                if (statusChip) statusChip.innerHTML = `Loaded existing insights (${data.existing_insights.source})`;
            } else {
                currentStudioInsights = null;
                renderStudioEmptyPlaceholder("Click '⚡ Generate Insights' to run AI analysis with the current prompt.");
                if (statusChip) statusChip.innerHTML = "Telemetry ready. Prompt loaded.";
            }
        } else {
            showStudioToast("Failed to load prompt preview: " + data.message, true);
        }
    } catch (err) {
        console.error("Error loading prompt preview:", err);
        showStudioToast("Error loading run data: " + err.message, true);
    }
}

// ── Update KPI & Telemetry Strip ──────────────────────────────────────────────
export function updateStudioTelemetryDisplay(data) {
    const s = data.summary || {};
    const inf = data.infra || {};

    const elTotal = document.getElementById("kpi-studio-total");
    const elAvg = document.getElementById("kpi-studio-avgrt");
    const elP95 = document.getElementById("kpi-studio-p95");
    const elErr = document.getElementById("kpi-studio-err");
    const elCpu = document.getElementById("kpi-studio-cpu");

    const total = s.total ?? s.total_requests ?? 0;
    const avgRt = s.avg_rt ?? s.avg_response_time ?? 0;
    const p95 = s.p95 ?? s.p95_response_time ?? 0;
    const errRate = s.error_rate ?? s.err_pct ?? 0;

    if (elTotal) elTotal.textContent = typeof total === "number" ? total.toLocaleString() : total;
    if (elAvg) elAvg.textContent = typeof avgRt === "number" ? `${avgRt.toFixed(0)} ms` : `${avgRt} ms`;
    if (elP95) elP95.textContent = typeof p95 === "number" ? `${p95.toFixed(0)} ms` : `${p95} ms`;
    if (elErr) elErr.textContent = typeof errRate === "number" ? `${errRate.toFixed(2)}%` : `${errRate}%`;
    if (elCpu) elCpu.textContent = (inf.max_cpu !== undefined && inf.max_cpu !== null) ? `${Number(inf.max_cpu).toFixed(1)}%` : "N/A";
}

// ── Quick Prompt Rule Inserters ───────────────────────────────────────────────
export function appendStudioPromptRule(ruleText) {
    const promptInput = document.getElementById("studio-prompt-input");
    if (!promptInput) return;
    promptInput.value = promptInput.value.trim() + "\n\nADDITIONAL USER INSTRUCTION:\n" + ruleText;
    showStudioToast("Injected custom rule into prompt!");
    promptInput.scrollTop = promptInput.scrollHeight;
}

// ── Execute AI Insights Generation ───────────────────────────────────────────
export async function generateStudioInsights() {
    const promptInput = document.getElementById("studio-prompt-input");
    const modelSelect = document.getElementById("studio-model-select");
    const tempInput = document.getElementById("studio-temp-input");
    const generateBtn = document.getElementById("studio-generate-btn");
    const statusChip = document.getElementById("studio-status-indicator");

    const promptText = promptInput?.value || "";
    const model = modelSelect?.value || "gemini-2.5-flash";
    const temperature = parseFloat(tempInput?.value || 0.2);

    if (!promptText.trim()) {
        showStudioToast("Prompt cannot be empty!", true);
        return;
    }

    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="pulse-loader"></span> Analyzing...';
    }
    if (statusChip) statusChip.innerHTML = `Running inference with <strong>${model}</strong>...`;

    try {
        const payload = {
            run_id: currentStudioRunId,
            prompt: promptText,
            model: model,
            provider: (model.includes("/") || model.toLowerCase().includes("nemotron")) ? "openrouter" : (model.toLowerCase().includes("gemini") ? "gemini" : "github"),
            temperature: temperature,
            summary: currentStudioRunData?.summary,
            labels: currentStudioRunData?.labels,
            infra: currentStudioRunData?.infra
        };

        const startTime = Date.now();
        const resp = await fetch("/api/ai-studio/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (data.success && data.insights) {
            currentStudioInsights = data.insights;
            const elapsed = data.elapsed_ms || (Date.now() - startTime);
            renderStudioInsights(data.insights, elapsed, model);
            if (statusChip) statusChip.innerHTML = `✅ Generated in <strong>${(elapsed/1000).toFixed(2)}s</strong> (${model})`;
            showStudioToast("Insights generated successfully!");
        } else {
            showStudioToast(data.message || "AI Generation Failed", true);
            if (statusChip) statusChip.innerHTML = `❌ Failed: ${data.message || "Unknown error"}`;
        }
    } catch (err) {
        console.error("AI Generation error:", err);
        showStudioToast("Generation error: " + err.message, true);
        if (statusChip) statusChip.innerHTML = `❌ Error: ${err.message}`;
    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '⚡ Generate &amp; Refine Insights';
        }
    }
}

// ── Save Refined Insights to Run JSON ─────────────────────────────────────────
export async function saveStudioInsights() {
    if (!currentStudioRunId || !currentStudioInsights) {
        showStudioToast("No insights to save! Generate or load insights first.", true);
        return;
    }

    const saveBtn = document.getElementById("studio-save-btn");
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving & Recompiling...";
    }

    try {
        const resp = await fetch("/api/ai-studio/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                run_id: currentStudioRunId,
                insights: currentStudioInsights
            })
        });
        const data = await resp.json();
        if (data.success) {
            showStudioToast("Saved! Report recompiled with refined AI insights.");
        } else {
            showStudioToast("Save failed: " + data.message, true);
        }
    } catch (err) {
        showStudioToast("Error saving insights: " + err.message, true);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = "💾 Save Refined Insights to Run";
        }
    }
}

// ── Render Generated Insights into Output Panel ───────────────────────────────
export function renderStudioInsights(insights, elapsedMs, modelName) {
    if (typeof insights === "string") {
        try {
            insights = JSON.parse(insights);
        } catch {
            insights = { executive_summary: insights, performance_score: "--", performance_grade: "--" };
        }
    }
    if (!insights || typeof insights !== "object") {
        insights = {};
    }

    const scoreBadge = document.getElementById("studio-score-badge");
    const execTextEl = document.getElementById("studio-exec-summary-text");
    const jsonEl = document.getElementById("studio-raw-json");

    if (scoreBadge) {
        const score = insights.performance_score ?? "--";
        const grade = insights.performance_grade ?? "--";
        scoreBadge.innerHTML = `Score: <strong>${score}/100</strong> (Grade ${grade})`;
    }

    if (execTextEl) {
        execTextEl.textContent = insights.executive_summary || "No executive assessment generated.";
    }

    if (jsonEl) {
        jsonEl.textContent = JSON.stringify(insights, null, 2);
    }

    // Render Sub-Views
    renderStudioFindingsView(insights);
    renderStudioRecommendationsView(insights);
    renderStudioTabIntelView(insights);
}

export function renderStudioFindingsView(insights) {
    const findingsContainer = document.getElementById("studio-view-findings");
    if (!findingsContainer) return;

    let html = "";

    // Data Quality
    const dqList = Array.isArray(insights?.data_quality_findings) ? insights.data_quality_findings : [];
    if (dqList.length > 0) {
        html += '<div style="margin-bottom:1rem;"><h4 style="color:#f59e0b; margin:0 0 0.5rem 0; font-size:0.88rem;">⚠️ Data Quality Warnings</h4>';
        dqList.forEach(dq => {
            html += `
            <div style="background:rgba(245,158,11,0.08); border-left:3px solid #f59e0b; padding:0.6rem 0.85rem; border-radius:6px; margin-bottom:0.5rem; font-size:0.8rem;">
                <div style="font-weight:700; color:#fbbf24;">${dq.issue || 'Data Discrepancy'}</div>
                <div style="color:var(--text); margin-top:0.2rem;"><strong>Evidence:</strong> ${dq.evidence || ''}</div>
                <div style="color:var(--muted); margin-top:0.2rem;"><strong>Action:</strong> ${dq.action || ''}</div>
            </div>`;
        });
        html += '</div>';
    }

    // Root Cause Assessments
    const rcList = insights?.root_cause_assessment || [];
    html += '<h4 style="color:#60a5fa; margin:0 0 0.5rem 0; font-size:0.88rem;">🔍 Root-Cause Assessments &amp; Outliers</h4>';
    if (Array.isArray(rcList) && rcList.length > 0) {
        rcList.forEach(rc => {
            const conf = rc.confidence || "Medium";
            const confColor = conf === "Confirmed" || conf === "High" ? "#34d399" : conf === "Medium" ? "#fbbf24" : "#94a3b8";
            html += `
            <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.6rem; font-size:0.82rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                    <strong style="color:var(--text); font-size:0.88rem;">${rc.finding || 'Assessment'}</strong>
                    <span style="font-size:0.7rem; font-weight:700; color:${confColor}; border:1px solid ${confColor}; padding:0.1rem 0.4rem; border-radius:4px;">Confidence: ${conf}</span>
                </div>
                <div style="color:var(--text); margin-bottom:0.3rem;">${rc.likely_cause || ''}</div>
                ${rc.evidence ? `<div style="color:var(--muted); font-size:0.78rem;"><strong>Evidence:</strong> ${rc.evidence}</div>` : ''}
                ${rc.recommended_investigation ? `<div style="color:#93c5fd; font-size:0.78rem; margin-top:0.3rem;"><strong>Investigation:</strong> ${rc.recommended_investigation}</div>` : ''}
            </div>`;
        });
    } else if (typeof rcList === "object" && rcList !== null && rcList.assessment) {
        html += `
        <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.8rem 1rem; font-size:0.82rem;">
            <div style="font-weight:700; color:var(--text);">${rcList.primary_bottleneck || 'Primary Bottleneck'}</div>
            <div style="color:var(--text); margin-top:0.3rem;">${rcList.assessment}</div>
        </div>`;
    } else {
        html += '<p style="color:var(--muted); font-size:0.82rem;">No specific root-cause anomalies detected.</p>';
    }

    findingsContainer.innerHTML = html;
}

export function renderStudioRecommendationsView(insights) {
    const recsContainer = document.getElementById("studio-view-recs");
    if (!recsContainer) return;

    const recs = Array.isArray(insights?.recommendations) ? insights.recommendations : [];
    if (recs.length === 0) {
        recsContainer.innerHTML = '<p style="color:var(--muted); font-size:0.84rem;">No recommendations generated for this run.</p>';
        return;
    }

    let html = "";
    recs.forEach(r => {
        const pri = r.priority || "Medium";
        const priClass = String(pri).toLowerCase();
        const actions = Array.isArray(r.action) ? r.action : (r.action ? [r.action] : []);
        const actionHtml = actions.length > 0
            ? `<div style="margin-top:0.4rem; font-size:0.8rem;"><strong>Action Plan:</strong><ul style="margin:0.2rem 0 0 1.1rem; padding:0;">${actions.map(a => `<li style="margin-bottom:0.25rem;">${a}</li>`).join('')}</ul></div>`
            : '';

        html += `
        <div class="ai-rec-card ${priClass}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                <span class="ai-rec-badge ${priClass}">${pri}</span>
                <span style="font-size:0.75rem; color:var(--muted); font-weight:600;">${r.category || 'General'}</span>
            </div>
            <div style="font-size:0.92rem; font-weight:700; color:var(--text); margin-bottom:0.3rem;">${r.title || 'Recommendation'}</div>
            <div style="font-size:0.82rem; color:var(--text); line-height:1.5;">${r.why || ''}</div>
            ${actionHtml}
            ${r.expected_impact ? `<div style="font-size:0.78rem; color:#34d399; margin-top:0.4rem;"><strong>Expected Impact:</strong> ${r.expected_impact}</div>` : ''}
            ${r.validation ? `<div style="font-size:0.78rem; color:var(--muted); margin-top:0.2rem;"><strong>Validation:</strong> ${r.validation}</div>` : ''}
        </div>`;
    });

    recsContainer.innerHTML = html;
}

export function renderStudioTabIntelView(insights) {
    const tabContainer = document.getElementById("studio-view-tabs");
    if (!tabContainer) return;

    const pi = insights?.performance_intelligence || {};
    const tabs = [
        { key: "tab_tx_stats", name: "Transaction Performance", icon: "⚡" },
        { key: "tab_rt_stats", name: "Response Times & SLA", icon: "⏱️" },
        { key: "tab_error_stats", name: "Reliability & Errors", icon: "🛡️" },
        { key: "tab_infra_stats", name: "Host Infrastructure", icon: "🖥️" }
    ];

    let html = "";
    tabs.forEach(t => {
        const item = pi[t.key] || {};
        const obs = Array.isArray(item.observations) ? item.observations : [];
        const recs = Array.isArray(item.recommendations) ? item.recommendations : [];
        html += `
        <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
            <div style="font-size:0.88rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">${t.icon} ${t.name}</div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.75rem; font-size:0.8rem;">
                <div>
                    <strong style="color:#60a5fa; text-transform:uppercase; font-size:0.72rem;">Observations:</strong>
                    <ul style="margin:0.2rem 0 0 1rem; padding:0; line-height:1.5; color:var(--text);">
                        ${obs.map(o => `<li style="margin-bottom:0.25rem;">${o}</li>`).join('') || '<li style="color:var(--muted);">None</li>'}
                    </ul>
                </div>
                <div>
                    <strong style="color:#34d399; text-transform:uppercase; font-size:0.72rem;">Recommendations:</strong>
                    <ul style="margin:0.2rem 0 0 1rem; padding:0; line-height:1.5; color:var(--text);">
                        ${recs.map(r => `<li style="margin-bottom:0.25rem;">${r}</li>`).join('') || '<li style="color:var(--muted);">None</li>'}
                    </ul>
                </div>
            </div>
        </div>`;
    });

    tabContainer.innerHTML = html;
}

export function renderStudioEmptyPlaceholder(msg) {
    const container = document.getElementById("studio-view-findings");
    if (container) container.innerHTML = `<p style="color:var(--muted); font-size:0.85rem; padding:1rem 0;">${msg}</p>`;
    const recs = document.getElementById("studio-view-recs");
    if (recs) recs.innerHTML = `<p style="color:var(--muted); font-size:0.85rem; padding:1rem 0;">No active recommendations to display.</p>`;
    const tabs = document.getElementById("studio-view-tabs");
    if (tabs) tabs.innerHTML = `<p style="color:var(--muted); font-size:0.85rem; padding:1rem 0;">No tab observations to display.</p>`;
}

// ── Switch Studio Output Sub-tabs ─────────────────────────────────────────────
export function switchStudioOutputTab(tabName) {
    document.querySelectorAll(".ai-output-tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-out-tab") === tabName);
    });

    ["findings", "recs", "tabs", "json"].forEach(name => {
        const pane = document.getElementById(`studio-view-${name}`);
        if (pane) {
            pane.style.display = (name === tabName) ? "block" : "none";
        }
    });
}

// ── Toast Notification Helper ─────────────────────────────────────────────────
export function showStudioToast(msg, isError = false) {
    let toast = document.getElementById("studio-toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "studio-toast";
        toast.style.position = "fixed";
        toast.style.bottom = "24px";
        toast.style.right = "24px";
        toast.style.padding = "0.75rem 1.25rem";
        toast.style.borderRadius = "8px";
        toast.style.fontWeight = "600";
        toast.style.fontSize = "0.85rem";
        toast.style.zIndex = "99999";
        toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.4)";
        toast.style.transition = "all 0.3s ease";
        document.body.appendChild(toast);
    }
    toast.style.background = isError ? "#ef4444" : "#10b981";
    toast.style.color = "#ffffff";
    toast.textContent = msg;
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
    }, 3500);
}

// ── Global Window Bindings for Inline Event Handlers & Core Router ───────────
window.initAiStudio = initAiStudio;
window.loadStudioRuns = loadStudioRuns;
window.loadRunPromptPreview = loadRunPromptPreview;
window.updateStudioTelemetryDisplay = updateStudioTelemetryDisplay;
window.appendStudioPromptRule = appendStudioPromptRule;
window.generateStudioInsights = generateStudioInsights;
window.saveStudioInsights = saveStudioInsights;
window.renderStudioInsights = renderStudioInsights;
window.renderStudioFindingsView = renderStudioFindingsView;
window.renderStudioRecommendationsView = renderStudioRecommendationsView;
window.renderStudioTabIntelView = renderStudioTabIntelView;
window.switchStudioOutputTab = switchStudioOutputTab;
window.showStudioToast = showStudioToast;

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAiStudio);
} else {
    initAiStudio();
}
