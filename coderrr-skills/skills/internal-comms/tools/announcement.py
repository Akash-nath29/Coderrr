#!/usr/bin/env python3
"""
Generate announcements.

Usage:
    python announcement.py --type general --subject "Title" --content '{...}'
"""

import argparse
import sys
import json
from datetime import datetime


URGENCY_ICONS = {
    "normal": "📢",
    "important": "⚠️",
    "urgent": "🚨"
}

TYPE_TITLES = {
    "general": "Announcement",
    "policy": "Policy Update",
    "event": "Event Announcement",
    "change": "Change Notice",
    "launch": "Launch Announcement"
}


def generate_announcement(ann_type: str, subject: str, content: dict, urgency: str = 'normal') -> str:
    """Generate announcement."""
    icon = URGENCY_ICONS.get(urgency, "📢")
    type_title = TYPE_TITLES.get(ann_type, "Announcement")
    
    lines = [
        f"# {icon} {type_title}: {subject}",
        "",
        f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
    ]
    
    if content.get("effective_date"):
        lines.append(f"**Effective:** {content['effective_date']}")
    
    if urgency != "normal":
        lines.append(f"**Priority:** {urgency.upper()}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary
    if content.get("summary"):
        lines.append(f"**TL;DR:** {content['summary']}")
        lines.append("")
    
    # Details
    if content.get("details"):
        lines.append("## Details")
        lines.append(content["details"])
        lines.append("")
    
    # Action Items
    if content.get("action_items"):
        lines.append("## Action Required")
        for item in content["action_items"]:
            lines.append(f"- [ ] {item}")
        lines.append("")
    
    # Contact
    if content.get("contact"):
        lines.append("---")
        lines.append(f"*Questions? Contact: {content['contact']}*")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate announcement')
    parser.add_argument('--type', required=True, 
                        choices=['general', 'policy', 'event', 'change', 'launch'])
    parser.add_argument('--subject', required=True, help='Announcement subject')
    parser.add_argument('--content', required=True, help='Content JSON')
    parser.add_argument('--urgency', default='normal', choices=['normal', 'important', 'urgent'])
    
    args = parser.parse_args()
    
    try:
        content = json.loads(args.content)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid content JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = generate_announcement(args.type, args.subject, content, args.urgency)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
