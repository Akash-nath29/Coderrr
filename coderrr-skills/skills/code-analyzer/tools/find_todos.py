#!/usr/bin/env python3
"""
Find TODO, FIXME, HACK, and XXX comments in code.

This tool searches for common task markers in code comments
and outputs their locations.

Usage:
    python find_todos.py --path ./src
    python find_todos.py --path ./src --types FIXME,TODO

Exit Codes:
    0 - Success
    1 - Invalid path
"""

import argparse
import sys
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List


# Default markers to search for
DEFAULT_MARKERS = ['TODO', 'FIXME', 'HACK', 'XXX', 'BUG', 'NOTE']

# File extensions to search
SEARCHABLE_EXTENSIONS = {
    '.py', '.pyw', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cc', '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
    '.sql', '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
    '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte',
    '.md', '.txt', '.rst', '.yaml', '.yml', '.toml', '.xml'
}


def find_todos_in_file(file_path: Path, markers: List[str]) -> List[Dict[str, Any]]:
    """Find TODO-like comments in a single file."""
    todos = []
    
    # Build pattern for markers
    pattern = r'\b(' + '|'.join(re.escape(m) for m in markers) + r')[\s:]*(.*)$'
    regex = re.compile(pattern, re.IGNORECASE)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                match = regex.search(line)
                if match:
                    marker_type = match.group(1).upper()
                    text = match.group(2).strip()
                    
                    # Clean up the text (remove trailing comment markers)
                    text = re.sub(r'[\*/]+\s*$', '', text).strip()
                    
                    todos.append({
                        'file': str(file_path),
                        'line': line_num,
                        'type': marker_type,
                        'text': text if text else '(no description)'
                    })
    except (IOError, OSError):
        pass
    
    return todos


def find_todos(path_str: str, marker_types: List[str] = None) -> Dict[str, Any]:
    """
    Find TODO-like comments in files.
    
    Args:
        path_str: Path to file or directory
        marker_types: List of marker types to search for
        
    Returns:
        Dictionary with found items
        
    Raises:
        ValueError: If path doesn't exist
    """
    path = Path(path_str)
    
    if not path.exists():
        raise ValueError(f"Path does not exist: {path_str}")
    
    markers = marker_types if marker_types else DEFAULT_MARKERS
    all_todos = []
    
    if path.is_file():
        all_todos.extend(find_todos_in_file(path, markers))
    else:
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in SEARCHABLE_EXTENSIONS:
                    all_todos.extend(find_todos_in_file(file_path, markers))
    
    # Sort by file and line number
    all_todos.sort(key=lambda x: (x['file'], x['line']))
    
    # Group by type for summary
    by_type: Dict[str, int] = {}
    for todo in all_todos:
        by_type[todo['type']] = by_type.get(todo['type'], 0) + 1
    
    return {
        'count': len(all_todos),
        'by_type': by_type,
        'items': all_todos
    }


def main():
    parser = argparse.ArgumentParser(
        description='Find TODO, FIXME, HACK, and XXX comments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python find_todos.py --path ./src
    python find_todos.py --path ./src --types FIXME,TODO
    python find_todos.py --path ./main.py
        '''
    )
    parser.add_argument(
        '--path',
        required=True,
        help='File or directory to search'
    )
    parser.add_argument(
        '--types',
        help='Comma-separated list of marker types (default: TODO,FIXME,HACK,XXX,BUG,NOTE)'
    )
    
    args = parser.parse_args()
    
    marker_types = None
    if args.types:
        marker_types = [t.strip().upper() for t in args.types.split(',')]
    
    try:
        result = find_todos(args.path, marker_types)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
