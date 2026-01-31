#!/usr/bin/env python3
"""
Generate status reports.

Usage:
    python status_report.py --project "Team Name" --period "Week 5" --data '{...}'
"""

import argparse
import sys
import json
from datetime import datetime


def generate_markdown(project: str, period: str, data: dict) -> str:
    """Generate markdown status report."""
    lines = [
        f"# Status Report: {project}",
        f"**Period:** {period}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        ""
    ]
    
    # Highlights
    if data.get("highlights"):
        lines.append("## 🎯 Highlights")
        for item in data["highlights"]:
            lines.append(f"- {item}")
        lines.append("")
    
    # Progress
    if data.get("progress"):
        lines.append("## 📊 Progress")
        progress = data["progress"]
        if "tasks_completed" in progress:
            total = progress.get("tasks_completed", 0) + progress.get("tasks_remaining", 0)
            pct = (progress["tasks_completed"] / total * 100) if total > 0 else 0
            lines.append(f"- **Completed:** {progress['tasks_completed']} tasks")
            lines.append(f"- **Remaining:** {progress.get('tasks_remaining', 0)} tasks")
            lines.append(f"- **Progress:** {pct:.0f}%")
        lines.append("")
    
    # Metrics
    if data.get("metrics"):
        lines.append("## 📈 Metrics")
        for metric, value in data["metrics"].items():
            lines.append(f"- **{metric.replace('_', ' ').title()}:** {value}")
        lines.append("")
    
    # Blockers
    if data.get("blockers"):
        lines.append("## 🚧 Blockers")
        for item in data["blockers"]:
            lines.append(f"- ⚠️ {item}")
        lines.append("")
    
    # Next Steps
    if data.get("next_steps"):
        lines.append("## ➡️ Next Steps")
        for item in data["next_steps"]:
            lines.append(f"- {item}")
        lines.append("")
    
    return '\n'.join(lines)


def generate_html(project: str, period: str, data: dict) -> str:
    """Generate HTML status report."""
    md = generate_markdown(project, period, data)
    # Simple markdown to HTML conversion
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Status Report: {project}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1e293b; }}
        h2 {{ color: #334155; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 8px 0; }}
    </style>
</head>
<body>
<pre>{md}</pre>
</body>
</html>"""
    return html


def status_report(project: str, period: str, data: dict, format_type: str = 'markdown'):
    """Generate status report."""
    if format_type == 'html':
        return generate_html(project, period, data)
    return generate_markdown(project, period, data)


def main():
    parser = argparse.ArgumentParser(description='Generate status report')
    parser.add_argument('--project', required=True, help='Project/team name')
    parser.add_argument('--period', required=True, help='Reporting period')
    parser.add_argument('--data', required=True, help='Report data JSON')
    parser.add_argument('--format', default='markdown', choices=['markdown', 'html'])
    
    args = parser.parse_args()
    
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid data JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = status_report(args.project, args.period, data, args.format)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
