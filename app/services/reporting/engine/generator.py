#!/usr/bin/env python3
"""
generator.py — Core orchestrator for the PerfPilot Report Generator.

Assembles the final standalone HTML report by:
1. Computing all metrics via data_processor
2. Building CSS via styles module
3. Building HTML body via components module
4. Building JavaScript via scripts module
5. Writing the single self-contained HTML file
"""

from pathlib import Path

from app.services.reporting.engine.data_processor import prepare_report_data
from app.services.reporting.engine.styles import build_all_css
from app.services.reporting.engine.components import render_body
from app.services.reporting.engine.scripts import build_all_js


def generate_report(parsed: dict, azure_data: dict, ai_insights: dict,
                    report_path: Path, jmx_name: str, users: int):
    """Generate a standalone HTML performance report.
    
    This is the main entry point. It orchestrates the modular report
    generation pipeline:
    
    1. Data Processing  → Computes all metrics, SLA evaluation, chart data
    2. CSS Assembly      → Builds the complete stylesheet
    3. HTML Components   → Renders header, tabs, footer, modals
    4. JS Assembly       → Builds all client-side interactivity
    5. Document Assembly → Combines into final HTML document
    6. File Output       → Writes the standalone HTML file
    
    Args:
        parsed: Parsed JTL test results
        azure_data: Azure Monitor infrastructure metrics
        ai_insights: AI-generated performance analysis
        report_path: Output file path for the HTML report
        jmx_name: Name of the JMeter test script
        users: Number of virtual users
    
    Returns:
        Path: The report_path after writing
    """
    report_path = Path(report_path)
    # Step 1: Prepare all data
    ctx = prepare_report_data(parsed, azure_data, ai_insights, jmx_name, users)
    
    # Step 2: Build CSS
    css = build_all_css(ctx)
    
    # Step 3: Build HTML body components
    body_html = render_body(ctx)
    
    # Step 4: Build JavaScript
    js = build_all_js(ctx)
    
    # Step 5: Assemble the complete HTML document
    html = _assemble_document(ctx, css, body_html, js)
    
    # Step 6: Write to file
    report_path.write_text(html, encoding="utf-8")
    return report_path


def _assemble_document(ctx: dict, css: str, body_html: str, js: str) -> str:
    """Assemble the complete HTML document from its parts."""
    jmx_name = ctx["jmx_name"]
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{jmx_name} — Performance Report | PerfPilot</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Crect%20width%3D%2264%22%20height%3D%2264%22%20rx%3D%2216%22%20fill%3D%22%230f172a%22%20stroke%3D%22%2338bdf8%22%20stroke-width%3D%221.5%22%2F%3E%3Cpolyline%20points%3D%2210%2C32%2020%2C32%2026%2C48%2035%2C16%2042%2C40%2048%2C32%2054%2C32%22%20fill%3D%22none%22%20stroke%3D%22%2338bdf8%22%20stroke-width%3D%224.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3Ccircle%20cx%3D%2235%22%20cy%3D%2216%22%20r%3D%223.5%22%20fill%3D%22%2338bdf8%22%2F%3E%3C%2Fsvg%3E">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        if (typeof Chart === 'undefined') {{
            document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"><\\/script>');
        }}
    </script>
    <script>
        if (typeof Chart === 'undefined') {{
            document.write('<script src="https://unpkg.com/chart.js@4.4.1/dist/chart.umd.js"><\\/script>');
        }}
    </script>
    <style>
{css}
    </style>
</head>
{body_html}
<script>
{js}
</script>
</body>
</html>"""
