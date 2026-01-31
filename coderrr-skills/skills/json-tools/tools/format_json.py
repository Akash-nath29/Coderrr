#!/usr/bin/env python3
"""
Format and pretty print JSON data.

This tool reads JSON from a file or stdin and outputs it formatted
with configurable indentation, or minified.

Usage:
    python format_json.py --file data.json
    echo '{"a":1}' | python format_json.py
    python format_json.py --file data.json --minify

Exit Codes:
    0 - Success
    1 - Invalid file path
    2 - JSON parsing error
"""

import argparse
import sys
import json
from pathlib import Path


def format_json(data: str, indent: int = 2, minify: bool = False) -> str:
    """
    Format JSON data.
    
    Args:
        data: JSON string to format
        indent: Indentation level (ignored if minify is True)
        minify: If True, compress to single line
        
    Returns:
        Formatted JSON string
        
    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    parsed = json.loads(data)
    
    if minify:
        return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
    else:
        return json.dumps(parsed, indent=indent, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='Format and pretty print JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python format_json.py --file data.json
    python format_json.py --file data.json --indent 4
    python format_json.py --file data.json --minify
    echo '{"name":"John"}' | python format_json.py
        '''
    )
    parser.add_argument(
        '--file',
        help='Path to JSON file (reads from stdin if not provided)'
    )
    parser.add_argument(
        '--indent',
        type=int,
        default=2,
        help='Indentation level (default: 2)'
    )
    parser.add_argument(
        '--minify',
        action='store_true',
        help='Compress JSON to single line'
    )
    
    args = parser.parse_args()
    
    # Read JSON data
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("Error: No input. Provide --file or pipe JSON to stdin.", file=sys.stderr)
            sys.exit(1)
        data = sys.stdin.read()
    
    # Format and output
    try:
        formatted = format_json(data, args.indent, args.minify)
        print(formatted)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e.msg} at line {e.lineno}, column {e.colno}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
