#!/usr/bin/env python3
"""
Interact with page elements.

Usage:
    python interact.py --session abc123 --action click --selector "#submit-btn"
"""

import argparse
import sys
import json
from pathlib import Path

SESSIONS_DIR = Path.home() / '.coderrr' / 'playwright_sessions'


def interact(session_id: str, action: str, selector: str, value: str = None):
    """Perform interaction on element."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    
    if not session_file.exists():
        raise ValueError(f"Session not found: {session_id}")
    
    session = json.loads(session_file.read_text())
    
    # Record interaction
    interaction = {
        "type": "interact",
        "action": action,
        "selector": selector
    }
    if value:
        interaction["value"] = value
    
    session["actions"].append(interaction)
    session_file.write_text(json.dumps(session, indent=2))
    
    return {
        "status": "success",
        "session_id": session_id,
        "action": action,
        "selector": selector,
        "value": value
    }


def main():
    parser = argparse.ArgumentParser(description='Interact with elements')
    parser.add_argument('--session', required=True, help='Session ID')
    parser.add_argument('--action', required=True, 
                        choices=['click', 'type', 'fill', 'hover', 'scroll', 'select'])
    parser.add_argument('--selector', required=True, help='Element selector')
    parser.add_argument('--value', help='Value for type/fill/select')
    
    args = parser.parse_args()
    
    try:
        result = interact(args.session, args.action, args.selector, args.value)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
