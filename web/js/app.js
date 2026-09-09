// js/app.js — PerfPilot Application Master Bootstrap & Module Orchestrator
import { initRouter, switchTab } from './core/router.js';
import { loadStatus } from './modules/status.js';
import { loadAiConfig, handleAiProviderChange, handleAiModelPresetChange, handleSaveAiConfig } from './modules/ai_config.js';
import { loadTests, handleJmxSelection, toggleTgCard, handleSaveJmxConfig, handleToolChange, handleIngestChange, handleSaveAzureConfig } from './modules/dashboard.js';
import { handleRunTest, startLivePolling, handleStopTest } from './modules/execution.js';
import { setupDragAndDrop, handleFileSelect, uploadFile } from './modules/upload.js';
import { loadRuns, loadReports, filterReportsUI, renderRunsTable, loadPublishedReports, recompileLatestReportUI, recompileSingleRunUI, openRecompileModal, closeRecompileModal, toggleRecompileAiOption, executeRecompile, deleteRunUI } from './modules/reports.js';
import { loadSlaScenariosFilter, handleSlaTestPlanChange, loadSlaTargetsForSelectedJmx, filterSlaRowsUI, renderSlaTable, deleteSlaRowUI, openAddScenarioModalUI, closeAddScenarioModalUI, applyScenarioPresetUI, confirmAddScenarioUI, deleteSlaScenarioUI, openAddCustomTransactionModalUI, closeAddTransactionModalUI, confirmAddTransactionUI, snapshotSlaTableState, saveSlaTargetsFromUI } from './modules/sla.js';

// Auto-import sidecars
import './modules/trend.js';
import './modules/ai_studio.js';

export function initApp() {
    initRouter();
    loadStatus();
    loadAiConfig();
    loadTests();
    loadReports();
    loadRuns();
    setupDragAndDrop();
    console.log("🚀 PerfPilot Modular Frontend initialized successfully.");
}

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});
