#!/usr/bin/env python3
"""
Parse and format API responses.

This tool takes JSON response data and can extract specific fields
or format the output as JSON, table, or CSV.

Usage:
    python parse_response.py --data '{"user": {"name": "John"}}'
    echo '{"data": [...]}' | python parse_response.py --extract "data"
    python parse_response.py --data '[...]' --format table

Exit Codes:
    0 - Success
    1 - Invalid arguments
    4 - JSON parsing error
"""

import argparse
import sys
import json
import re
from typing import Any, List


def parse_path(path: str) -> List[Any]:
    """Parse a path expression into components."""
    components = []
    pattern = r'\.?([^\.\[\]]+)|\[(\d+|\*)\]'
    
    for match in re.finditer(pattern, path):
        if match.group(1):
            components.append(match.group(1))
        elif match.group(2):
            idx = match.group(2)
            if idx == '*':
                components.append('*')
            else:
                components.append(int(idx))
    
    return components


def extract_value(data: Any, path: str) -> Any:
    """Extract a value from data using a path expression."""
    if not path:
        return data
    
    components = parse_path(path)
    current = data
    
    for component in components:
        if component == '*':
            if isinstance(current, list):
                return current
            raise TypeError("Can't use [*] on non-array")
        elif isinstance(component, int):
            if not isinstance(current, list):
                raise TypeError(f"Can't use [{component}] on non-array")
            current = current[component]
        else:
            if not isinstance(current, dict):
                raise TypeError(f"Can't access '{component}' on non-object")
            current = current.get(component)
            if current is None:
                raise KeyError(f"Key '{component}' not found")
    
    return current


def format_as_table(data: Any) -> str:
    """Format data as an ASCII table."""
    if isinstance(data, dict):
        data = [data]
    
    if not isinstance(data, list) or not data:
        return json.dumps(data, indent=2)
    
    if not isinstance(data[0], dict):
        return json.dumps(data, indent=2)
    
    # Get all keys
    keys = []
    for item in data:
        for key in item.keys():
            if key not in keys:
                keys.append(key)
    
    # Calculate column widths
    widths = {key: len(str(key)) for key in keys}
    for item in data:
        for key in keys:
            val = str(item.get(key, ''))
            widths[key] = max(widths[key], len(val))
    
    # Build table
    lines = []
    
    # Header
    header = '| ' + ' | '.join(str(k).ljust(widths[k]) for k in keys) + ' |'
    separator = '|-' + '-|-'.join('-' * widths[k] for k in keys) + '-|'
    
    lines.append(header)
    lines.append(separator)
    
    # Rows
    for item in data:
        row = '| ' + ' | '.join(str(item.get(k, '')).ljust(widths[k]) for k in keys) + ' |'
        lines.append(row)
    
    return '\n'.join(lines)


def format_as_csv(data: Any) -> str:
    """Format data as CSV."""
    if isinstance(data, dict):
        data = [data]
    
    if not isinstance(data, list) or not data:
        return ''
    
    if not isinstance(data[0], dict):
        # Simple array of values
        return '\n'.join(str(item) for item in data)
    
    # Get all keys
    keys = []
    for item in data:
        for key in item.keys():
            if key not in keys:
                keys.append(key)
    
    lines = []
    
    # Header
    lines.append(','.join(keys))
    
    # Rows
    for item in data:
        values = []
        for key in keys:
            val = str(item.get(key, ''))
            # Escape commas and quotes
            if ',' in val or '"' in val or '\n' in val:
                val = '"' + val.replace('"', '""') + '"'
            values.append(val)
        lines.append(','.join(values))
    
    return '\n'.join(lines)


def parse_response(data_str: str, extract: str = None, output_format: str = 'json') -> str:
    """
    Parse and format response data.
    
    Args:
        data_str: JSON string to parse
        extract: Optional path to extract
        output_format: Output format (json, table, csv)
        
    Returns:
        Formatted output string
    """
    data = json.loads(data_str)
    
    # Extract if path provided
    if extract:
        data = extract_value(data, extract)
    
    # Format output
    if output_format == 'table':
        return format_as_table(data)
    elif output_format == 'csv':
        return format_as_csv(data)
    else:
        return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='Parse and format API responses',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python parse_response.py --data '{"user": {"name": "John"}}' --extract "user.name"
    echo '{"items": [...]}' | python parse_response.py --extract "items" --format table
    python parse_response.py --data '[{"id":1},{"id":2}]' --format csv
        '''
    )
    parser.add_argument(
        '--data',
        help='JSON response data (if not provided, reads from stdin)'
    )
    parser.add_argument(
        '--extract',
        help='Path to extract specific field (e.g., "data.users[0].name")'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'table', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    
    args = parser.parse_args()
    
    # Get data from argument or stdin
    if args.data:
        data_str = args.data
    else:
        if sys.stdin.isatty():
            print("Error: No data provided. Use --data or pipe JSON to stdin.", file=sys.stderr)
            sys.exit(1)
        data_str = sys.stdin.read()
    
    if not data_str.strip():
        print("Error: Empty input", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = parse_response(data_str, args.extract, args.format)
        print(result)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(4)
    except (KeyError, TypeError, IndexError) as e:
        print(f"Error extracting path: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
