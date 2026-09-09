// modules/status.js — System Health Cards
import { api } from '../core/api.js';

export async function loadStatus() {
    try {
        const data = await api.get("/api/status");

        // JMeter Card
        const indJmeter = document.getElementById("ind-jmeter");
        const valJmeter = document.getElementById("val-jmeter");
        if (data.jmeter && data.jmeter.available) {
            if (indJmeter) indJmeter.className = "indicator online";
            if (valJmeter) valJmeter.textContent = data.jmeter.version || "Apache JMeter Ready";
        } else {
            if (indJmeter) indJmeter.className = "indicator offline";
            if (valJmeter) valJmeter.textContent = "Not Found (Set JMETER_HOME)";
        }

        // Azure Card
        const indAzure = document.getElementById("ind-azure");
        const valAzure = document.getElementById("val-azure");
        if (data.azure_configured) {
            if (indAzure) indAzure.className = "indicator online";
            if (valAzure) valAzure.textContent = "Configured & Active";
        } else {
            if (indAzure) indAzure.className = "indicator";
            if (valAzure) valAzure.textContent = "Not Configured (Optional)";
        }

        // BlazeMeter Card
        const indBm = document.getElementById("ind-blazemeter");
        const valBm = document.getElementById("val-blazemeter");
        if (indBm && valBm) {
            if (data.blazemeter_configured) {
                indBm.className = "indicator online";
                valBm.textContent = "API Configured & Ready";
            } else {
                indBm.className = "indicator";
                valBm.textContent = "Not Configured (Optional)";
            }
        }

        // NeoLoad Card
        const indNl = document.getElementById("ind-neoload");
        const valNl = document.getElementById("val-neoload");
        if (indNl && valNl) {
            if (data.neoload_configured) {
                indNl.className = "indicator online";
                valNl.textContent = "API Configured & Ready";
            } else {
                indNl.className = "indicator";
                valNl.textContent = "Not Configured (Optional)";
            }
        }

        // AI Card
        const indAi = document.getElementById("ind-ai");
        const valAi = document.getElementById("val-ai");
        if (data.gemini_configured || data.openrouter_configured || data.github_configured) {
            if (indAi) indAi.className = "indicator online";
            if (valAi) valAi.textContent = `${(data.active_provider || "").toUpperCase()} (${data.active_model || ""})`;
        } else {
            if (indAi) indAi.className = "indicator";
            if (valAi) valAi.textContent = "Rule-based Fallback Mode";
        }
    } catch (err) {
        console.error("Failed to load status:", err);
    }
}

window.loadStatus = loadStatus;
