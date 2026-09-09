// core/state.js — Central Reactive Application State Store
export const state = {
    availableJmxFiles: [],
    selectedJmxConfig: null,
    activePollingInterval: null,
    allRunsData: [],
    currentRecompileTargetRunId: null,
    currentSlaScenarios: [],
    currentSlaIdentifications: [],
    currentSlaFilterQuery: "",
    currentTrendData: null,
    trendHierarchy: {},
    currentStudioRunId: null,
    currentStudioRunData: null,
    currentStudioInsights: null
};

window.__PERFPILOT_STATE__ = state;
