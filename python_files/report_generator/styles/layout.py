#!/usr/bin/env python3
"""Page layout, header bar, navigation pills, and KPI grids."""

def get_layout_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""/* Header Bar */
        .report-header, .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--surface);
            padding: 1.25rem 1.75rem;
            border-radius: 16px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            margin-bottom: 1.5rem;
        }
        .header-left { display: flex; align-items: center; gap: 1.25rem; }
        .header-title h1, .report-title h1 { font-size: 1.4rem; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 0.6rem; }
        .header-title p, .report-title p { font-size: 0.8rem; color: var(--muted); margin-top: 0.2rem; }
        .header-actions, .header-right { display: flex; gap: 0.75rem; align-items: center; }
        .engine-badge { background: var(--surface2); border: 1px solid var(--border); padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; letter-spacing: 0; }
        .score-circle { width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; font-weight: 800; border: 2px solid {score_color}; color: {score_color}; background: var(--surface2); }
        .status-pill { padding: 0.35rem 0.85rem; border-radius: 12px; font-size: 0.78rem; font-weight: 700; color: #fff; background: {status_color}; text-shadow: 0 1px 2px rgba(0,0,0,0.1); }

        /* Buttons */
        .btn, .theme-toggle {
            background: var(--surface2);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.5rem 0.9rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.2s ease;
            user-select: none;
        }
        .btn:hover, .theme-toggle:hover { background: var(--accent); color: #ffffff; border-color: var(--accent); }

        /* Tab Navigation Bar */
        .report-nav, .tab-nav {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            background: var(--surface);
            padding: 0.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow-x: auto;
        }
        .nav-btn {
            background: transparent;
            color: var(--muted);
            border: none;
            padding: 0.65rem 1.1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
        }
        .nav-btn:hover { color: var(--text); background: var(--surface2); }
        .nav-btn.active {
            color: #ffffff;
            background: var(--accent);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
            font-weight: 700;
        }

        /* Tab Panes & Hidden Elements */
        .tab-pane { display: block; animation: fadeIn 0.3s ease-in-out; }
        .tab-pane.hidden, .hidden { display: none !important; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* KPI Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }
        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        .kpi-card:hover {
            border-color: var(--accent);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }
        .kpi-label { font-size: 0.75rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
        .kpi-value { font-size: 1.8rem; font-weight: 800; margin: 0.3rem 0; color: var(--text); }
        .kpi-sub { font-size: 0.75rem; color: var(--muted); }
        .pass { color: var(--green); } .warn { color: var(--yellow); } .fail { color: var(--red); }

        /* Glass Panel / Section */
        .glass-panel, .section, .chart-box {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow);
        }
        .glass-panel h2, .glass-panel h3, .section h2, .chart-box h3 {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--text);
        }

        /* Human Validation Checkbox Styles */
        .human-val-label {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--muted);
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 0.25rem 0.75rem;
            border-radius: 14px;
            user-select: none;
            transition: all 0.2s ease;
        }
        .human-val-label:hover {
            border-color: var(--accent);
            color: var(--text);
            background: var(--surface2);
        }
        .human-val-checkbox {
            cursor: pointer;
            accent-color: #10b981;
            width: 14px;
            height: 14px;
            margin: 0;
        }
        .human-val-label.validated {
            background: rgba(16, 185, 129, 0.12);
            border-color: rgba(16, 185, 129, 0.4);
            color: #10b981;
        }
        .human-val-label.validated .human-val-text {
            color: #10b981;
            font-weight: 700;
        }
        .ai-augmented-section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.5rem 1.75rem;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow);
        }
        .ai-sub-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
        }
        .ai-sub-card:last-child {
            margin-bottom: 0;
        }
        .ai-sub-card.card-validated {
            border-color: rgba(16, 185, 129, 0.5) !important;
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.12);
        }

        """
