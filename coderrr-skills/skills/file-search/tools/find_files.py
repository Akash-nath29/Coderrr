#!/usr/bin/env python3
"""
Find files and directories matching a glob pattern.

This tool searches a directory for files and directories that match
the specified glob pattern.

Usage:
    python find_files.py --pattern "*.py" --path ./src
    python find_files.py --pattern "**/*.json" --path . --type file

Exit Codes:
    0 - Success
    1 - Invalid path or pattern
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import List


def find_files(pattern: str, search_path: str, file_type: str = 'all') -> List[str]:
    """
    Find files and directories matching a glob pattern.
    
    Args:
        pattern: Glob pattern to match
        search_path: Directory to search in
        file_type: Filter by type - 'file', 'dir', or 'all'
        
    Returns:
        List of matching paths as strings
        
    Raises:
        ValueError: If path doesn't exist or is invalid
    """
    path = Path(search_path)
    
    if not path.exists():
        raise ValueError(f"Path does not exist: {search_path}")
    
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {search_path}")
    
    matches = []
    
    try:
        for match in path.glob(pattern):
            if file_type == 'file' and not match.is_file():
                continue
            if file_type == 'dir' and not match.is_dir():
                continue
            
            # Use relative path from search directory
            try:
                relative = match.relative_to(path)
                matches.append(str(Path(search_path) / relative))
            except ValueError:
                matches.append(str(match))
    except Exception as e:
        raise ValueError(f"Invalid pattern: {e}")
    
    return sorted(matches)


def main():
    parser = argparse.ArgumentParser(
        description='Find files and directories matching a glob pattern',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python find_files.py --pattern "*.py" --path ./src
    python find_files.py --pattern "**/*.json" --path . --type file
    python find_files.py --pattern "*" --path ./project --type dir
        '''
    )
    parser.add_argument(
        '--pattern',
        required=True,
        help='Glob pattern to match (e.g., "*.py", "**/*.json")'
    )
    parser.add_argument(
        '--path',
        required=True,
        help='Directory to search in'
    )
    parser.add_argument(
        '--type',
        choices=['file', 'dir', 'all'],
        default='all',
        help='Filter by type (default: all)'
    )
    
    args = parser.parse_args()
    
    try:
        matches = find_files(args.pattern, args.path, args.type)
        print(json.dumps(matches, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
