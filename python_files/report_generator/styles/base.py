#!/usr/bin/env python3
"""Base CSS variables, typography, and theme tokens."""

def get_base_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r""":root {
            --bg: #0f172a;
            --surface: #1e293b;
            --surface2: #334155;
            --surface3: #1e293b;
            --surface-solid: #1e293b;
            --surface-dropdown: rgba(30, 41, 59, 0.98);
            --border: #475569;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent2: #0284c7;
            --accent-bg: rgba(56, 189, 248, 0.1);
            --green: #10b981;
            --green-bg: rgba(16, 185, 129, 0.1);
            --yellow: #f59e0b;
            --yellow-bg: rgba(245, 158, 11, 0.1);
            --red: #ef4444;
            --red-bg: rgba(239, 68, 68, 0.1);
            --blue: #38bdf8;
            --blue-bg: rgba(56, 189, 248, 0.1);
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            --shadow-sm: 0 4px 16px rgba(0, 0, 0, 0.2);
            --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .light-mode, html.light-mode {
            --bg: #f8fafc;
            --surface: #ffffff;
            --surface2: #f1f5f9;
            --surface3: #e2e8f0;
            --surface-solid: #ffffff;
            --surface-dropdown: rgba(255, 255, 255, 0.98);
            --border: #cbd5e1;
            --text: #0f172a;
            --muted: #64748b;
            --accent: #0284c7;
            --accent2: #0369a1;
            --accent-bg: rgba(2, 132, 199, 0.1);
            --green: #059669;
            --green-bg: rgba(5, 150, 105, 0.1);
            --yellow: #d97706;
            --yellow-bg: rgba(217, 119, 6, 0.1);
            --red: #dc2626;
            --red-bg: rgba(220, 38, 38, 0.1);
            --blue: #0284c7;
            --blue-bg: rgba(2, 132, 199, 0.1);
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
            --shadow-sm: 0 4px 16px rgba(0, 0, 0, 0.04);
            --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.06);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 1.5rem;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .container, .report-container { max-width: 1400px; margin: 0 auto; }

        """
