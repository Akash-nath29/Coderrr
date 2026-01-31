#!/usr/bin/env python3
"""
Start a browser testing session.

Usage:
    python start_browser.py --browser chromium --headless
"""

import argparse
import sys
import json
import uuid
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: 'playwright' package is required. Install with: pip install playwright && playwright install", file=sys.stderr)
    sys.exit(1)


# Session storage (in real implementation, use proper session management)
SESSIONS_DIR = Path.home() / '.coderrr' / 'playwright_sessions'


def start_browser(browser: str = 'chromium', headless: bool = False, viewport: str = None):
    """Start browser session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    session_id = str(uuid.uuid4())[:8]
    
    # Parse viewport
    width, height = 1280, 720
    if viewport:
        parts = viewport.lower().split('x')
        if len(parts) == 2:
            width, height = int(parts[0]), int(parts[1])
    
    # Store session config (actual browser managed separately)
    session_config = {
        "id": session_id,
        "browser": browser,
        "headless": headless,
        "viewport": {"width": width, "height": height},
        "status": "ready",
        "actions": []
    }
    
    session_file = SESSIONS_DIR / f"{session_id}.json"
    session_file.write_text(json.dumps(session_config, indent=2))
    
    return {
        "status": "success",
        "session_id": session_id,
        "browser": browser,
        "headless": headless,
        "viewport": f"{width}x{height}"
    }


def main():
    parser = argparse.ArgumentParser(description='Start browser session')
    parser.add_argument('--browser', default='chromium', choices=['chromium', 'firefox', 'webkit'])
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--viewport', help='Viewport size (e.g., 1920x1080)')
    
    args = parser.parse_args()
    
    try:
        result = start_browser(args.browser, args.headless, args.viewport)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
