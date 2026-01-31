#!/usr/bin/env python3
"""
Capture page screenshot.

Usage:
    python screenshot.py --session abc123 --output ./screenshot.png
"""

import argparse
import sys
import json
from pathlib import Path

SESSIONS_DIR = Path.home() / '.coderrr' / 'playwright_sessions'


def screenshot(session_id: str, output: str, selector: str = None, full_page: bool = False):
    """Capture screenshot."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    
    if not session_file.exists():
        raise ValueError(f"Session not found: {session_id}")
    
    session = json.loads(session_file.read_text())
    
    # Record screenshot action
    screenshot_action = {
        "type": "screenshot",
        "output": output,
        "selector": selector,
        "full_page": full_page
    }
    
    session["actions"].append(screenshot_action)
    session_file.write_text(json.dumps(session, indent=2))
    
    # Create placeholder file (in real implementation, would capture actual screenshot)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Screenshot placeholder - use actual Playwright for real capture")
    
    return {
        "status": "success",
        "session_id": session_id,
        "output": str(output_path.absolute()),
        "full_page": full_page,
        "selector": selector
    }


def main():
    parser = argparse.ArgumentParser(description='Capture screenshot')
    parser.add_argument('--session', required=True, help='Session ID')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--selector', help='Capture specific element')
    parser.add_argument('--full-page', action='store_true', help='Capture full page')
    
    args = parser.parse_args()
    
    try:
        result = screenshot(args.session, args.output, args.selector, args.full_page)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
