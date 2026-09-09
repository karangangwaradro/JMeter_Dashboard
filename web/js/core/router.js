// core/router.js — Tab Switching & Navigation Router
import { loadStatus } from '../modules/status.js';
import { loadTests } from '../modules/dashboard.js';
import { loadSlaScenariosFilter } from '../modules/sla.js';
import { loadRuns, loadReports } from '../modules/reports.js';

export function initRouter() {
    const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
    const sidebar = document.getElementById("app-sidebar");
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    const globalSearch = document.getElementById("global-search");
    document.addEventListener("keydown", (e) => {
        if (e.key === "/" && document.activeElement !== globalSearch && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
            e.preventDefault();
            globalSearch?.focus();
        }
    });

    window.addEventListener("hashchange", () => {
        const hash = window.location.hash.replace("#", "");
        if (hash && document.getElementById(hash)) {
            switchTab(hash, false);
        }
    });

    const initialHash = window.location.hash.replace("#", "");
    if (initialHash && document.getElementById(initialHash)) {
        switchTab(initialHash, false);
    }
}

export function switchTab(tabId, updateHash = true) {
    if (updateHash) {
        window.location.hash = tabId;
    }

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
    } else if (tabId === "tab-live") {
        if (typeof window.checkAndResumeLivePolling === "function") {
            window.checkAndResumeLivePolling();
        }
    } else if (tabId === "tab-sla") {
        const jmxSelect = document.getElementById("jmx-select");
        const preferredJmx = jmxSelect && jmxSelect.value ? jmxSelect.value : "";
        loadSlaScenariosFilter(preferredJmx);
    } else if (tabId === "tab-reports") {
        loadRuns();
        loadReports();
    } else if (tabId === "tab-trend") {
        if (typeof window.fetchAndRenderTrend === "function") {
            window.fetchAndRenderTrend();
        }
    } else if (tabId === "tab-ai-studio") {
        if (typeof window.loadStudioRuns === "function") {
            window.loadStudioRuns();
        }
    }
}

window.switchTab = switchTab;
