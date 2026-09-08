#!/usr/bin/env python3
"""Tables, tree tables, badges, and filters."""

def get_table_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""/* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            text-align: left;
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
        }
        th, td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }
        th {
            background: var(--surface2);
            color: var(--muted);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.05em;
        }
        td { color: var(--text); }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }
        .light-mode tr:hover td { background: rgba(0, 0, 0, 0.02); }
        tr:last-child td { border-bottom: none; }

        /* Tree Table Specifics */
        .tg-header-row td { border-bottom: 1px solid var(--accent) !important; }
        .tree-toggle-btn {
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--accent);
            font-size: 0.72rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 0.5rem;
            transition: all 0.15s ease;
        }
        .tree-toggle-btn:hover {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
        }
        .tree-toggle-spacer { display: inline-block; width: 0.95rem; margin-right: 0.25rem; }
        .tree-row.depth-0 { background: var(--surface); font-weight: 600; }
        .tree-row.depth-1 { background: rgba(0, 0, 0, 0.15); font-size: 0.82rem; }
        .tree-row.depth-2 { background: rgba(0, 0, 0, 0.25); font-size: 0.8rem; color: var(--muted); }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge.pass { background: var(--green-bg); color: var(--green); }
        .badge.warn { background: var(--yellow-bg); color: var(--yellow); }
        .badge.breach, .badge.fail { background: var(--red-bg); color: var(--red); }

        /* Search & Filter inputs */
        .search-input, select, input[type="text"] {
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.45rem 0.8rem;
            border-radius: 6px;
            font-size: 0.8rem;
            outline: none;
            transition: border-color 0.15s, box-shadow 0.15s;
        }
        .search-input:focus, select:focus, input[type="text"]:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-bg);
        }
        .userpath-hidden { display: none !important; }

        /* Error Distribution & Analysis Styles */
        .error-analysis-grid {
            display: grid;
            grid-template-columns: 290px 1fr;
            gap: 1.5rem;
            align-items: stretch;
        }
        @media (max-width: 900px) {
            .error-analysis-grid { grid-template-columns: 1fr; }
        }
        .doughnut-container {
            position: relative;
            width: 200px;
            height: 200px;
            margin: 0 auto;
        }
        .doughnut-center-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            pointer-events: none;
            width: 100%;
        }
        .doughnut-center-num {
            font-size: 2.1rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1;
            margin-bottom: 0.2rem;
        }
        .doughnut-center-label {
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--muted);
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .error-cat-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: center;
            margin-top: 1.25rem;
            width: 100%;
        }
        .error-cat-pill {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 0.35rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            user-select: none;
            color: var(--text);
        }
        .error-cat-pill:hover, .error-cat-pill.active {
            background: var(--surface2);
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .error-detail-panel {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            min-height: 280px;
            transition: all 0.25s ease;
        }
        .flash-panel {
            animation: flashHighlight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        @keyframes flashHighlight {
            0% { opacity: 0.4; transform: scale(0.99); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Line Chart Multi-Select Filters & Snapshots */
        .metric-toggle-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--muted);
            transition: all 0.2s ease;
            user-select: none;
        }
        .metric-toggle-pill.active {
            background: var(--surface2);
            color: var(--text);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            border-color: var(--accent);
        }
        .tx-multiselect-box {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            max-height: 140px;
            overflow-y: auto;
            padding: 0.5rem;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 0.35rem;
        }
        .tx-check-item {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.8rem;
            color: var(--text);
            cursor: pointer;
            padding: 0.25rem 0.4rem;
            border-radius: 4px;
            transition: background 0.15s ease;
        }
        .tx-check-item:hover {
            background: var(--surface2);
        }
        .snapshot-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            position: relative;
            animation: fadeIn 0.3s ease-in-out;
        }

        /* Card Info Button & Drawer Styles */
        .card-info-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--accent);
            font-size: 0.72rem;
            font-weight: 800;
            font-style: normal;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            line-height: 1;
            user-select: none;
            flex-shrink: 0;
        }
        .card-info-btn:hover {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
            transform: scale(1.12);
            box-shadow: 0 2px 10px rgba(56, 189, 248, 0.35);
        }
        .card-info-btn.active {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-bg);
        }
        .card-info-drawer {
            display: none;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.07) 0%, rgba(30, 41, 59, 0.95) 100%);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-left: 4px solid var(--accent);
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 1.25rem;
            font-size: 0.82rem;
            color: var(--text);
            line-height: 1.55;
            animation: slideDownInfo 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        }
        .card-info-drawer.open {
            display: block;
        }
        .light-mode .card-info-drawer {
            background: linear-gradient(135deg, rgba(2, 132, 199, 0.05) 0%, rgba(248, 250, 252, 0.98) 100%);
            border-color: rgba(2, 132, 199, 0.25);
            border-left-color: var(--accent);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }
        .card-info-drawer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.6rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid rgba(56, 189, 248, 0.15);
        }
        .light-mode .card-info-drawer-header {
            border-bottom-color: rgba(2, 132, 199, 0.15);
        }
        .card-info-drawer-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }
        .card-info-close-btn {
            background: transparent;
            border: none;
            color: var(--muted);
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            padding: 0 4px;
            line-height: 1;
            transition: color 0.15s ease;
        }
        .card-info-close-btn:hover {
            color: var(--red);
        }
        .card-info-section-title {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text);
            margin-top: 0.6rem;
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }
        .card-info-drawer p {
            color: var(--muted);
            margin-bottom: 0.4rem;
        }
        .card-info-drawer ul {
            margin-left: 1.25rem;
            margin-bottom: 0.5rem;
        }
        .card-info-drawer li {
            margin-bottom: 0.25rem;
            color: var(--muted);
        }
        .card-info-drawer li strong {
            color: var(--text);
        }

        """
