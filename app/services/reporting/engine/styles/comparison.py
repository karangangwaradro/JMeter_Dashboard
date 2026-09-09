#!/usr/bin/env python3
"""Benchmark and run comparison styles."""

def get_comparison_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""/* ── Benchmark & Run Comparison Styles ── */
        .comp-kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .comp-kpi-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.2rem;
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            position: relative;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .comp-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        .comp-kpi-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .comp-kpi-split {
            display: flex;
            align-items: baseline;
            gap: 0.4rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.2rem;
            color: var(--text);
            flex-wrap: wrap;
        }
        .comp-kpi-prev {
            font-size: 0.9rem;
            color: var(--muted);
            text-decoration: line-through;
            opacity: 0.8;
        }
        .comp-kpi-arrow {
            font-size: 0.85rem;
            color: var(--muted);
        }
        .comp-delta-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
            width: fit-content;
        }
        .comp-delta-badge.improved { background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); }
        .comp-delta-badge.degraded { background: rgba(239, 68, 68, 0.15); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); }
        .comp-delta-badge.neutral { background: var(--surface3); color: var(--muted); border: 1px solid var(--border); }
        
        /* Full Width Modular Chart Panels */
        .comp-chart-fullwidth {
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.25rem 1.4rem;
            margin-bottom: 1.5rem;
            position: relative;
            box-sizing: border-box;
        }
        .comp-chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.85rem;
        }
        .comp-chart-title-group {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .comp-chart-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .comp-chart-sub {
            font-size: 0.8rem;
            color: var(--muted);
            margin-top: 0.2rem;
        }
        
        /* Interactive Controls Toolbar */
        .comp-controls-toolbar {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            flex-wrap: wrap;
        }
        .comp-ctrl-item {
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }
        .comp-ctrl-label {
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .comp-select {
            padding: 0.38rem 0.75rem;
            font-size: 0.8rem;
            font-weight: 600;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--surface2);
            color: var(--text);
            font-family: inherit;
            outline: none;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .comp-select:hover, .comp-select:focus {
            border-color: var(--accent);
        }
        
        /* Segmented Button Groups */
        .comp-btn-group {
            display: inline-flex;
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px;
            gap: 2px;
        }
        .comp-btn-group-btn {
            border: none;
            background: transparent;
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.3rem 0.65rem;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: all 0.15s ease;
            font-family: inherit;
        }
        .comp-btn-group-btn:hover {
            color: var(--text);
            background: rgba(255, 255, 255, 0.05);
        }
        .comp-btn-group-btn.active {
            background: var(--surface);
            color: var(--accent);
            font-weight: 700;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .comp-search-input {
            padding: 0.38rem 0.75rem;
            font-size: 0.8rem;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--surface2);
            color: var(--text);
            font-family: inherit;
            outline: none;
            min-width: 160px;
            transition: border-color 0.2s;
        }
        .comp-search-input:focus {
            border-color: var(--accent);
        }
        
        /* Chart Canvas Wrappers */
        .comp-canvas-container {
            width: 100%;
            position: relative;
        }
        
        /* 4-Quadrant SLA Matrix */
        .comp-matrix-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .comp-matrix-box {
            border-radius: 8px;
            padding: 1.1rem;
            border: 1px solid var(--border);
            background: var(--surface2);
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
            position: relative;
        }
        .comp-matrix-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
        }
        .comp-matrix-box.active-filter {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px var(--accent);
        }
        .comp-matrix-box.pass-pass { border-left: 4px solid var(--green); }
        .comp-matrix-box.pass-fail { border-left: 4px solid var(--red); background: rgba(239, 68, 68, 0.05); }
        .comp-matrix-box.fail-pass { border-left: 4px solid var(--green); background: rgba(16, 185, 129, 0.05); }
        .comp-matrix-box.fail-fail { border-left: 4px solid var(--yellow); }

        /* Quick Filter Chips */
        .comp-filter-chips-bar {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .comp-filter-chip {
            padding: 0.25rem 0.65rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--surface2);
            color: var(--muted);
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .comp-filter-chip:hover {
            color: var(--text);
            border-color: var(--accent);
        }
        .comp-filter-chip.active {
            background: var(--accent);
            color: #0f172a;
            border-color: var(--accent);
            font-weight: 700;
        }

        /* Hide in published mode */
        .published-mode #compare-selector-bar,
        .published-mode #compare-empty-state,
        .published-mode .ai-chat-fab,
        .published-mode .ai-chat-drawer {
            display: none !important;
        }

        /* --- Edit Mode Styles --- */
        [contenteditable="true"] { outline: none !important; background: transparent !important; border: none !important; transition: all 0.2s; }
        body.edit-mode-active [contenteditable="true"] { outline: 1px dashed var(--accent) !important; background: rgba(56, 189, 248, 0.08) !important; cursor: text; }
        .delete-rec-btn { display: none; position: absolute; right: 0.5rem; top: 0.5rem; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; color: #ef4444; padding: 0.2rem 0.5rem; font-size: 0.75rem; cursor: pointer; font-weight: 700; transition: all 0.2s; z-index: 10; }
        .delete-rec-btn:hover { background: #ef4444; color: #fff; }
        body.edit-mode-active .delete-rec-btn { display: block !important; }
"""
