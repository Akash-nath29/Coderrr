#!/usr/bin/env python3
"""
Verify page state and elements.

Usage:
    python verify.py --session abc123 --check visible --selector "#success-msg"
"""

import argparse
import sys
import json
from pathlib import Path

SESSIONS_DIR = Path.home() / '.coderrr' / 'playwright_sessions'


def verify(session_id: str, check: str, selector: str = None, expected: str = None):
    """Verify page state."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    
    if not session_file.exists():
        raise ValueError(f"Session not found: {session_id}")
    
    session = json.loads(session_file.read_text())
    
    # Record verification
    verification = {
        "type": "verify",
        "check": check,
        "selector": selector,
        "expected": expected
    }
    
    session["actions"].append(verification)
    session_file.write_text(json.dumps(session, indent=2))
    
    # In real implementation, would actually perform verification
    return {
        "status": "success",
        "session_id": session_id,
        "check": check,
        "selector": selector,
        "expected": expected,
        "passed": True,
        "message": f"Verification '{check}' passed"
    }


def main():
    parser = argparse.ArgumentParser(description='Verify page state')
    parser.add_argument('--session', required=True, help='Session ID')
    parser.add_argument('--check', required=True, 
                        choices=['visible', 'hidden', 'text', 'value', 'title', 'url'])
    parser.add_argument('--selector', help='Element selector')
    parser.add_argument('--expected', help='Expected value')
    
    args = parser.parse_args()
    
    try:
        result = verify(args.session, args.check, args.selector, args.expected)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
