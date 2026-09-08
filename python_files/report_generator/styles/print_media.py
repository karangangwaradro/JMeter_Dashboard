#!/usr/bin/env python3
"""Print media query styles and PDF export formatting."""

def get_print_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""@media print {
            body { background: #ffffff !important; color: #000000 !important; padding: 0 !important; font-size: 10pt !important; }
            * { overflow: visible !important; }
            .report-container, .container { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
            .glass-panel, .section, .chart-box, .kpi-card { background: #ffffff !important; box-shadow: none !important; border: 1px solid #ddd !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; border-radius: 6px !important; padding: 1rem !important; margin-bottom: 1.5rem !important; }
            .report-nav, .theme-toggle, #publishBtn, #pdfBtn, #editModeBadge, .delete-rec-btn, .btn { display: none !important; }
            .tab-pane, .tab-pane.hidden { display: block !important; opacity: 1 !important; visibility: visible !important; height: auto !important; position: static !important; margin-bottom: 1rem !important; animation: none !important; }
            .chart-box, .section, .kpi-card, .rec-card, table, tr, img { page-break-inside: avoid !important; }
            .report-header, .header { border: none !important; box-shadow: none !important; padding: 0 0 1rem 0 !important; margin-bottom: 1.5rem !important; border-bottom: 2px solid #e1e4e8 !important; border-radius: 0 !important; }
            
            /* Fixes for specific elements to fit PDF A4 perfectly */
            .chart-box { width: 100% !important; padding: 0.5rem !important; page-break-inside: avoid !important; }
            table { width: 100% !important; border-collapse: collapse !important; font-size: 9pt !important; page-break-inside: auto !important; }
            tr { page-break-inside: avoid !important; page-break-after: auto !important; }
            th, td { border: 1px solid #e1e4e8 !important; padding: 0.4rem !important; background: none !important; }
            
            /* Typography scaling for print */
            h1 { font-size: 16pt !important; }
            h2 { font-size: 13pt !important; margin-bottom: 0.75rem !important; margin-top: 0 !important; }
            h3 { font-size: 11pt !important; margin-bottom: 0.5rem !important; }
            p, span, div { font-size: 9.5pt !important; line-height: 1.4 !important; }
            .kpi-value { font-size: 18pt !important; }
            .kpi-label { font-size: 8pt !important; }
            .kpi-card { padding: 0.75rem !important; }
            .rec-card { padding: 0.75rem !important; border-width: 1px !important; border-left-width: 4px !important; margin-bottom: 0.5rem !important; }
            .rec-desc { font-size: 9pt !important; }
            .insight-card p { font-size: 9.5pt !important; }
            .insight-card { border-width: 1px !important; border-left-width: 4px !important; padding: 1rem !important; }
        }
            table { width: 100% !important; border-collapse: collapse !important; font-size: 9pt !important; page-break-inside: auto !important; }
            tr { page-break-inside: avoid !important; page-break-after: auto !important; }
            th, td { border: 1px solid #e1e4e8 !important; padding: 0.4rem !important; background: none !important; }
            
            /* Typography scaling for print */
            h1 { font-size: 16pt !important; }
            h2 { font-size: 13pt !important; margin-bottom: 0.75rem !important; margin-top: 0 !important; }
            h3 { font-size: 11pt !important; margin-bottom: 0.5rem !important; }
            p, span, div { font-size: 9.5pt !important; line-height: 1.4 !important; }
            .kpi-value { font-size: 18pt !important; }
            .kpi-label { font-size: 8pt !important; }
            .kpi-card { padding: 0.75rem !important; }
            .rec-card { padding: 0.75rem !important; border-width: 1px !important; border-left-width: 4px !important; margin-bottom: 0.5rem !important; }
            .rec-desc { font-size: 9pt !important; }
            .insight-card p {  font-size: 9.5pt !important; }
            .insight-card { border-width: 1px !important; border-left-width: 4px !important; padding: 1rem !important; }
        }

        /* --- Drawer Overlay & Panel --- */
        #findingDrawerOverlay {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 9998; backdrop-filter: blur(2px);
        }
        #findingDrawer {
            display: none; position: fixed; top: 0; right: -450px; width: 450px; height: 100%; background: var(--surface); box-shadow: -4px 0 15px rgba(0,0,0,0.15); z-index: 9999; border-left: 1px solid var(--border); overflow-y: auto; transition: right 0.3s ease; padding: 1.5rem;
        }
        #findingDrawer.open { right: 0; }
        .drawer-close { font-size: 1.5rem; cursor: pointer; color: var(--muted); background: transparent; border: none; outline: none; }
        .drawer-section { margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }
        .drawer-section:last-child { border-bottom: none; }
        .drawer-h { font-size: 0.85rem; font-weight: 700; color: var(--accent); margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.5px; }

        /* --- Graph Info Button & Modal --- */
        .chart-info-btn {
            position: absolute;
            top: 1rem;
            right: 1.1rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--surface2);
            border: 1.5px solid var(--border);
            color: var(--accent);
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            flex-shrink: 0;
            user-select: none;
            z-index: 15;
        }
        .chart-info-btn:hover {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
            transform: translateY(-2px) scale(1.1);
            box-shadow: 0 4px 14px rgba(99,102,241,0.35);
        }
        #graphModalOverlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 10000;
            opacity: 0;
            align-items: center;
            justify-content: center;
            transition: opacity 0.2s ease;
        }
        #graphModalOverlay.open {
            opacity: 1;
        }
        #graphInfoModal {
            background: var(--surface-dropdown, #ffffff);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 20px 35px -5px rgba(0, 0, 0, 0.35), 0 10px 15px -5px rgba(0, 0, 0, 0.15);
            width: 90%;
            max-width: 540px;
            max-height: 85vh;
            overflow-y: auto;
            padding: 1.5rem;
            margin: auto;
            transform: scale(0.95);
            opacity: 0;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
            z-index: 10001;
        }
        html.dark #graphInfoModal {
            background: rgba(15, 23, 42, 0.98);
            border-color: rgba(255, 255, 255, 0.14);
        }
        #graphModalOverlay.open #graphInfoModal {
            transform: scale(1);
            opacity: 1;
        }
        .graph-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.8rem;
            margin-bottom: 1rem;
        }
        .graph-modal-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .graph-modal-close {
            font-size: 1.5rem;
            line-height: 1;
            color: var(--muted);
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 0 0.3rem;
            border-radius: 4px;
            transition: color 0.15s;
        }
        .graph-modal-close:hover {
            color: var(--text);
        }
        .graph-modal-section {
            margin-bottom: 1rem;
        }
        .graph-modal-section:last-child {
            margin-bottom: 0;
        }
        .graph-modal-section-title {
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--accent);
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }
        .graph-modal-text {
            font-size: 0.86rem;
            color: var(--text);
            line-height: 1.5;
            margin: 0;
        }
        .graph-modal-list {
            margin: 0.3rem 0 0 1.2rem;
            padding: 0;
            font-size: 0.86rem;
            color: var(--text);
            line-height: 1.5;
        }
        .graph-modal-list li {
            margin-bottom: 0.3rem;
        }

        /* --- Chart Multi-Select Dropdown Component --- */
        .chart-ms-wrap {
            position: relative;
            display: inline-block;
            text-align: left;
        }
        .chart-ms-btn {
            display: inline-flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.4rem;
            background: var(--surface2);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.35rem 0.65rem;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            min-width: 170px;
            max-width: 280px;
            box-sizing: border-box;
            outline: none;
            transition: all 0.15s ease;
            user-select: none;
        }
        .chart-ms-btn:hover, .chart-ms-btn:focus {
            border-color: var(--accent);
            background: var(--surface);
        }
        .chart-ms-btn-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }
        .chart-ms-badge {
            background: var(--accent);
            color: #ffffff;
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.1rem 0.4rem;
            border-radius: 10px;
            flex-shrink: 0;
        }
        .chart-ms-dropdown {
            display: none;
            position: absolute;
            top: calc(100% + 6px);
            right: 0;
            width: 320px;
            max-height: 380px;
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.28), 0 4px 14px rgba(0, 0, 0, 0.12);
            z-index: 1000;
            padding: 0.65rem;
            flex-direction: column;
            gap: 0.55rem;
            box-sizing: border-box;
            opacity: 1;
        }
        html.dark .chart-ms-dropdown {
            background: #0f172a;
            border-color: rgba(255, 255, 255, 0.16);
            box-shadow: 0 22px 50px rgba(0, 0, 0, 0.8), 0 4px 16px rgba(0, 0, 0, 0.4);
        }
        .chart-ms-dropdown.open {
            display: flex;
        }
        .chart-ms-search {
            width: 100%;
            box-sizing: border-box;
            background: #f8fafc;
            color: var(--text);
            border: 1px solid #cbd5e1;
            border-radius: 5px;
            padding: 0.4rem 0.6rem;
            font-size: 0.75rem;
            outline: none;
            transition: border-color 0.15s, box-shadow 0.15s;
        }
        .chart-ms-search:focus {
            border-color: var(--accent);
            background: #ffffff;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
        }
        html.dark .chart-ms-search {
            background: #1e293b;
            color: #f1f5f9;
            border-color: rgba(255, 255, 255, 0.12);
        }
        html.dark .chart-ms-search:focus {
            background: #0f172a;
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
        }
        .chart-ms-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.3rem;
            padding-bottom: 0.45rem;
            border-bottom: 1px solid #e2e8f0;
        }
        html.dark .chart-ms-actions {
            border-bottom-color: rgba(255, 255, 255, 0.1);
        }
        .chart-ms-action-btn {
            background: #f1f5f9;
            color: var(--text);
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.22rem 0.48rem;
            cursor: pointer;
            transition: all 0.12s;
        }
        html.dark .chart-ms-action-btn {
            background: #1e293b;
            border-color: rgba(255, 255, 255, 0.12);
        }
        .chart-ms-action-btn:hover {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
        }
        .chart-ms-list {
            overflow-y: auto;
            max-height: 230px;
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }
        .chart-ms-item {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.45rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
            color: var(--text);
            user-select: none;
            transition: background 0.12s;
        }
        .chart-ms-item:hover {
            background: #f1f5f9;
        }
        html.dark .chart-ms-item:hover {
            background: #1e293b;
        }
        .chart-ms-item input[type="checkbox"] {
            accent-color: var(--accent);
            cursor: pointer;
            width: 14px;
            height: 14px;
            margin: 0;
            flex-shrink: 0;
        }
        .chart-ms-item-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }
        .chart-ms-color-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }
    """
