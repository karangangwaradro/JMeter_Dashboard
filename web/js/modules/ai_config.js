// modules/ai_config.js — AI Provider Switching & LLM Keys
import { api } from '../core/api.js';
import { loadStatus } from './status.js';

export async function loadAiConfig() {
    try {
        const data = await api.get("/api/ai-config");

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

        const currentModel = data.model || "gemini-2.5-flash";
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

        if (badgeOpenRouter) {
            if (data.openrouter_configured) {
                badgeOpenRouter.textContent = `Configured (${data.openrouter_key_masked})`;
                badgeOpenRouter.style.color = "var(--green, #10b981)";
            } else {
                badgeOpenRouter.textContent = "Not Set";
                badgeOpenRouter.style.color = "var(--text-muted)";
            }
        }
        if (badgeGemini) {
            if (data.gemini_configured) {
                badgeGemini.textContent = `Configured (${data.gemini_key_masked})`;
                badgeGemini.style.color = "var(--green, #10b981)";
            } else {
                badgeGemini.textContent = "Not Set";
                badgeGemini.style.color = "var(--text-muted)";
            }
        }
        if (badgeGithub) {
            if (data.github_configured) {
                badgeGithub.textContent = `Configured (${data.github_token_masked})`;
                badgeGithub.style.color = "var(--green, #10b981)";
            } else {
                badgeGithub.textContent = "Not Set";
                badgeGithub.style.color = "var(--text-muted)";
            }
        }

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

export function handleAiProviderChange(val) {
    const modelSelect = document.getElementById("ai-model-select");
    const customInput = document.getElementById("ai-model-custom-input");
    if (!modelSelect) return;
    if (val === "openrouter") {
        modelSelect.value = "openrouter/free";
        if (customInput) customInput.classList.add("hidden");
    } else if (val === "gemini") {
        modelSelect.value = "gemini-2.5-flash";
        if (customInput) customInput.classList.add("hidden");
    } else if (val === "github") {
        modelSelect.value = "gpt-4o-mini";
        if (customInput) customInput.classList.add("hidden");
    }
}

export function handleAiModelPresetChange(val) {
    const customInput = document.getElementById("ai-model-custom-input");
    if (!customInput) return;
    if (val === "custom") {
        customInput.classList.remove("hidden");
        customInput.focus();
    } else {
        customInput.classList.add("hidden");
    }
}

export async function handleSaveAiConfig() {
    const provider = document.getElementById("ai-provider-select")?.value || "gemini";
    const modelSelect = document.getElementById("ai-model-select")?.value || "gemini-2.5-flash";
    const customModel = document.getElementById("ai-model-custom-input")?.value?.trim() || "";
    const activeModel = (modelSelect === "custom" && customModel) ? customModel : modelSelect;

    const openrouterKey = document.getElementById("openrouter-key-input")?.value?.trim() || "";
    const geminiKey = document.getElementById("gemini-key-input")?.value?.trim() || "";
    const githubToken = document.getElementById("github-token-input")?.value?.trim() || "";

    try {
        const data = await api.post("/api/ai-config", {
            provider: provider,
            model: activeModel,
            openrouter_key: openrouterKey,
            gemini_key: geminiKey,
            github_token: githubToken
        });
        if (data.success) {
            alert("✅ " + data.message);
            if (openrouterKey && document.getElementById("openrouter-key-input")) document.getElementById("openrouter-key-input").value = "";
            if (geminiKey && document.getElementById("gemini-key-input")) document.getElementById("gemini-key-input").value = "";
            if (githubToken && document.getElementById("github-token-input")) document.getElementById("github-token-input").value = "";
            loadAiConfig();
            loadStatus();
        } else {
            alert("❌ Failed: " + data.message);
        }
    } catch (err) {
        alert("Failed to save AI config: " + err);
    }
}

window.loadAiConfig = loadAiConfig;
window.handleAiProviderChange = handleAiProviderChange;
window.handleAiModelPresetChange = handleAiModelPresetChange;
window.handleSaveAiConfig = handleSaveAiConfig;
