#!/usr/bin/env python3
"""
Generate meeting summaries.

Usage:
    python meeting_summary.py --title "Team Sync" --date "2024-02-01" --data '{...}'
"""

import argparse
import sys
import json


def generate_meeting_summary(title: str, date: str, data: dict) -> str:
    """Generate meeting summary."""
    lines = [
        f"# 📋 Meeting Summary: {title}",
        "",
        f"**Date:** {date}",
    ]
    
    if data.get("attendees"):
        lines.append(f"**Attendees:** {', '.join(data['attendees'])}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Agenda
    if data.get("agenda"):
        lines.append("## 📌 Agenda")
        for i, item in enumerate(data["agenda"], 1):
            lines.append(f"{i}. {item}")
        lines.append("")
    
    # Discussion
    if data.get("discussion"):
        lines.append("## 💬 Discussion")
        for item in data["discussion"]:
            lines.append(f"### {item.get('topic', 'Topic')}")
            lines.append(item.get("summary", ""))
            lines.append("")
    
    # Decisions
    if data.get("decisions"):
        lines.append("## ✅ Decisions Made")
        for decision in data["decisions"]:
            lines.append(f"- ✓ {decision}")
        lines.append("")
    
    # Action Items
    if data.get("action_items"):
        lines.append("## 📝 Action Items")
        lines.append("")
        lines.append("| Owner | Task | Due Date |")
        lines.append("|-------|------|----------|")
        for item in data["action_items"]:
            owner = item.get("owner", "-")
            task = item.get("task", "-")
            due = item.get("due", "-")
            lines.append(f"| {owner} | {task} | {due} |")
        lines.append("")
    
    # Next Meeting
    if data.get("next_meeting"):
        lines.append("---")
        lines.append(f"**Next Meeting:** {data['next_meeting']}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate meeting summary')
    parser.add_argument('--title', required=True, help='Meeting title')
    parser.add_argument('--date', required=True, help='Meeting date')
    parser.add_argument('--data', required=True, help='Meeting data JSON')
    
    args = parser.parse_args()
    
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid data JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = generate_meeting_summary(args.title, args.date, data)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
