#!/usr/bin/env python3
"""Chart containers, legends, canvas styling."""

def get_chart_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""/* Charts */
        .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
        @media (max-width: 900px) { .chart-grid { grid-template-columns: 1fr; } }

        /* AI Insights & Recs */
        .insight-card { background: var(--surface2); border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; border-left: 4px solid var(--accent); }
        .insight-card h4 { font-size: 0.9rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--accent); }
        .insight-card p { font-size: 0.88rem; line-height: 1.7; }
        .rec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
        @media (max-width: 900px) { .rec-grid { grid-template-columns: 1fr; } }
        .rec-card { border-radius: 10px; padding: 1.25rem; border: 1px solid var(--border); background: var(--surface2); }
        .rec-card.critical { border-left: 4px solid var(--red); }
        .rec-card.warning { border-left: 4px solid var(--yellow); }
        .rec-card.info { border-left: 4px solid var(--blue); }
        .rec-header { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
        .rec-priority { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; padding: 0.2rem 0.6rem; border-radius: 6px; }
        .rec-card.critical .rec-priority { background: var(--red); color: #fff; }
        .rec-card.warning .rec-priority { background: var(--yellow); color: #000; }
        .rec-card.info .rec-priority { background: var(--blue); color: #fff; }
        .rec-category { font-size: 0.72rem; color: var(--muted); padding: 0.2rem 0.6rem; border: 1px solid var(--border); border-radius: 6px; }
        .rec-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; }
        .rec-desc { font-size: 0.85rem; color: var(--muted); line-height: 1.6; }
        .rec-impact { font-size: 0.78rem; color: var(--green); margin-top: 0.75rem; font-weight: 600; }

        /* Capacity */
        .capacity-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-bottom: 1.25rem; }
        .cap-card { background: var(--surface2); border-radius: 10px; padding: 1.25rem; text-align: center; border: 1px solid var(--border); }
        .cap-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; font-weight: 600; }
        .cap-value { font-size: 1.75rem; font-weight: 800; color: var(--accent); }
        .cap-analysis { font-size: 0.85rem; color: var(--muted); }

        /* Editable */
        [contenteditable="true"] { outline: 2px dashed rgba(56, 189, 248, 0.4); outline-offset: 3px; border-radius: 4px; transition: outline-color 0.2s; }
        [contenteditable="true"]:hover { outline-color: var(--accent); }
        [contenteditable="true"]:focus { outline: 2px solid var(--accent); background: var(--surface2); }
        .published-mode [contenteditable="true"] { outline: none !important; background: transparent !important; }

        /* AI Observation Panels — inline below charts */
        .ai-observation-panel { background: var(--surface2); border-radius: 10px; padding: 1rem 1.25rem; margin-top: 1rem; border: 1px solid var(--border); border-left: 4px solid var(--accent); }
        .ai-observation-panel h4 { font-size: 0.88rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--accent); }
        .ai-interpretation { font-size: 0.82rem; color: var(--muted); border-left: 3px solid var(--accent); padding: 0.4rem 0.8rem; margin: 0.5rem 0 0 0; background: rgba(56, 189, 248, 0.04); border-radius: 0 6px 6px 0; font-style: italic; }
        .evidence-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: var(--text); }
        .evidence-chip { background: var(--surface); border: 1px solid var(--border); padding: 0.2rem 0.5rem; border-radius: 5px; font-weight: 600; font-size: 0.78rem; }

        /* Finding Badges */
        .finding-badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.72rem; font-weight: 700; border: 1.5px solid; background: transparent; white-space: nowrap; }
        .finding-badge-inline { display: inline-flex; align-items: center; gap: 0.2rem; padding: 0.15rem 0.45rem; border-radius: 5px; font-size: 0.7rem; font-weight: 700; background: var(--surface); border: 1px solid var(--border); color: var(--accent); }

        /* Finding Detail Cards */
        .finding-detail { background: var(--surface2); border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; border: 1px solid var(--border); border-left: 4px solid var(--accent); scroll-margin-top: 2rem; }

        /* Evidence Source References */
        .evidence-ref { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 5px; font-size: 0.72rem; font-weight: 600; background: var(--surface); border: 1px solid var(--border); color: var(--accent); margin: 0.1rem 0; }

        /* Confidence Badges */
        .confidence-badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 5px; font-size: 0.7rem; font-weight: 600; margin-right: 0.4rem; }
        .confidence-badge.confidence-high { background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
        .confidence-badge.confidence-medium { background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
        .confidence-badge.confidence-low { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }

        .report-footer { text-align: center; color: var(--muted); font-size: 0.82rem; padding: 2.5rem 0; font-weight: 500; }

        /* ── """
