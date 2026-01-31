#!/usr/bin/env python3
"""
Query JSON data using path expressions.

This tool allows querying nested JSON data using a simple path syntax
similar to JSONPath.

Usage:
    python query_json.py --file data.json --path "users[0].name"
    python query_json.py --file data.json --path "items[*].id"

Exit Codes:
    0 - Success
    1 - Invalid file path
    2 - JSON parsing error
    3 - Invalid path expression
"""

import argparse
import sys
import json
import re
from pathlib import Path
from typing import Any, List


def parse_path(path: str) -> List[Any]:
    """
    Parse a path expression into components.
    
    Supports:
        - .key or key - object property
        - [0] - array index
        - [*] - all array elements
    
    Args:
        path: Path expression string
        
    Returns:
        List of path components
    """
    components = []
    
    # Split on dots and brackets
    pattern = r'\.?([^\.\[\]]+)|\[(\d+|\*)\]'
    
    for match in re.finditer(pattern, path):
        if match.group(1):
            # Property name
            components.append(match.group(1))
        elif match.group(2):
            # Array index or wildcard
            idx = match.group(2)
            if idx == '*':
                components.append('*')
            else:
                components.append(int(idx))
    
    return components


def query_value(data: Any, components: List[Any]) -> Any:
    """
    Query a value from data using path components.
    
    Args:
        data: The JSON data to query
        components: List of path components
        
    Returns:
        The matched value(s)
        
    Raises:
        KeyError: If a key doesn't exist
        IndexError: If an index is out of range
        TypeError: If the path is invalid for the data type
    """
    if not components:
        return data
    
    current = data
    result_is_array = False
    results = []
    
    for i, component in enumerate(components):
        remaining = components[i + 1:]
        
        if component == '*':
            # Wildcard - apply remaining path to all elements
            if not isinstance(current, list):
                raise TypeError(f"Can't use [*] on non-array value")
            
            for item in current:
                try:
                    result = query_value(item, remaining)
                    if isinstance(result, list) and remaining and remaining[-1] == '*':
                        results.extend(result)
                    else:
                        results.append(result)
                except (KeyError, IndexError, TypeError):
                    pass
            
            return results
        
        elif isinstance(component, int):
            # Array index
            if not isinstance(current, list):
                raise TypeError(f"Can't use [{component}] on non-array value")
            current = current[component]
        
        else:
            # Object property
            if not isinstance(current, dict):
                raise TypeError(f"Can't access '{component}' on non-object value")
            if component not in current:
                raise KeyError(f"Key '{component}' not found")
            current = current[component]
    
    return current


def query_json(file_path: str, path: str) -> Any:
    """
    Query JSON file with a path expression.
    
    Args:
        file_path: Path to JSON file
        path: Path expression
        
    Returns:
        The matched value
    """
    path_obj = Path(file_path)
    
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(path_obj, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    components = parse_path(path)
    
    if not components:
        return data
    
    return query_value(data, components)


def main():
    parser = argparse.ArgumentParser(
        description='Query JSON data using path expressions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Path Syntax:
    .key or key  - Access object property
    [0]          - Access array element by index
    [*]          - Access all array elements

Examples:
    python query_json.py --file data.json --path "user.name"
    python query_json.py --file data.json --path "users[0]"
    python query_json.py --file data.json --path "items[*].id"
    python query_json.py --file config.json --path "database.host"
        '''
    )
    parser.add_argument(
        '--file',
        required=True,
        help='Path to JSON file'
    )
    parser.add_argument(
        '--path',
        required=True,
        help='Path expression (e.g., "users[0].name")'
    )
    
    args = parser.parse_args()
    
    try:
        result = query_json(args.file, args.path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e.msg} at line {e.lineno}", file=sys.stderr)
        sys.exit(2)
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
