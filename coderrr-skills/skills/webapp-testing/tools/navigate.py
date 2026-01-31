#!/usr/bin/env python3
"""
Navigate to a URL in browser session.

Usage:
    python navigate.py --session abc123 --url http://localhost:3000
"""

import argparse
import sys
import json
from pathlib import Path

SESSIONS_DIR = Path.home() / '.coderrr' / 'playwright_sessions'


def navigate(session_id: str, url: str, wait_until: str = 'load'):
    """Navigate to URL."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    
    if not session_file.exists():
        raise ValueError(f"Session not found: {session_id}")
    
    session = json.loads(session_file.read_text())
    
    # Record navigation action
    session["actions"].append({
        "type": "navigate",
        "url": url,
        "wait_until": wait_until
    })
    session["current_url"] = url
    
    session_file.write_text(json.dumps(session, indent=2))
    
    return {
        "status": "success",
        "session_id": session_id,
        "url": url,
        "wait_until": wait_until
    }


def main():
    parser = argparse.ArgumentParser(description='Navigate to URL')
    parser.add_argument('--session', required=True, help='Session ID')
    parser.add_argument('--url', required=True, help='URL to navigate to')
    parser.add_argument('--wait-until', default='load', 
                        choices=['load', 'domcontentloaded', 'networkidle'])
    
    args = parser.parse_args()
    
    try:
        result = navigate(args.session, args.url, args.wait_until)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
