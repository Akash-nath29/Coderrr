#!/usr/bin/env python3
"""
Generate internal newsletters.

Usage:
    python newsletter.py --title "Weekly Update" --sections '[...]'
"""

import argparse
import sys
import json
from datetime import datetime


def generate_newsletter_md(title: str, sections: list) -> str:
    """Generate markdown newsletter."""
    lines = [
        f"# 📰 {title}",
        f"*{datetime.now().strftime('%B %d, %Y')}*",
        "",
        "---",
        ""
    ]
    
    for section in sections:
        section_type = section.get("type", "content")
        
        if section_type == "intro":
            lines.append(section.get("content", ""))
            lines.append("")
        
        elif section_type == "highlight":
            lines.append(f"## 🌟 {section.get('title', 'Highlight')}")
            lines.append(section.get("content", ""))
            lines.append("")
        
        elif section_type == "updates":
            lines.append("## 📋 Updates")
            for item in section.get("items", []):
                lines.append(f"- {item}")
            lines.append("")
        
        elif section_type == "spotlight":
            lines.append(f"## 👤 Team Spotlight: {section.get('name', 'Team Member')}")
            if section.get("role"):
                lines.append(f"*{section['role']}*")
            lines.append("")
            lines.append(section.get("content", ""))
            lines.append("")
        
        elif section_type == "upcoming":
            lines.append("## 📅 Upcoming Events")
            for event in section.get("events", []):
                lines.append(f"- **{event.get('date', '')}**: {event.get('title', '')}")
            lines.append("")
        
        elif section_type == "content":
            if section.get("title"):
                lines.append(f"## {section['title']}")
            lines.append(section.get("content", ""))
            lines.append("")
    
    lines.append("---")
    lines.append("*Questions? Reply to this newsletter or reach out to the team.*")
    
    return '\n'.join(lines)


def generate_newsletter_html(title: str, sections: list) -> str:
    """Generate HTML newsletter."""
    md = generate_newsletter_md(title, sections)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f8fafc; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1 {{ color: #1e40af; }}
        h2 {{ color: #334155; margin-top: 24px; }}
    </style>
</head>
<body>
<div class="container">
<pre style="white-space: pre-wrap; font-family: inherit;">{md}</pre>
</div>
</body>
</html>"""


def newsletter(title: str, sections: list, format_type: str = 'markdown'):
    """Generate newsletter."""
    if format_type == 'html':
        return generate_newsletter_html(title, sections)
    return generate_newsletter_md(title, sections)


def main():
    parser = argparse.ArgumentParser(description='Generate newsletter')
    parser.add_argument('--title', required=True, help='Newsletter title')
    parser.add_argument('--sections', required=True, help='Sections JSON')
    parser.add_argument('--format', default='markdown', choices=['markdown', 'html'])
    
    args = parser.parse_args()
    
    try:
        sections = json.loads(args.sections)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid sections JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = newsletter(args.title, sections, args.format)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
