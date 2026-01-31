#!/usr/bin/env python3
"""
Get statistics about files and directories.

This tool analyzes a file or directory and provides statistics including
file count, total size, file type breakdown, and largest files.

Usage:
    python file_stats.py --path ./src
    python file_stats.py --path ./main.py

Exit Codes:
    0 - Success
    1 - Invalid path
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_file_stats(file_path: Path) -> Dict[str, Any]:
    """Get statistics for a single file."""
    stat = file_path.stat()
    return {
        'path': str(file_path),
        'type': 'file',
        'size': stat.st_size,
        'size_human': format_size(stat.st_size),
        'extension': file_path.suffix or '(no extension)',
        'modified': stat.st_mtime
    }


def get_directory_stats(dir_path: Path, top_n: int = 10) -> Dict[str, Any]:
    """Get statistics for a directory."""
    file_count = 0
    dir_count = 0
    total_size = 0
    file_types: Dict[str, int] = defaultdict(int)
    files_with_sizes: List[Dict[str, Any]] = []
    
    try:
        for root, dirs, files in os.walk(dir_path):
            dir_count += len(dirs)
            
            for filename in files:
                file_path = Path(root) / filename
                file_count += 1
                
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    
                    ext = file_path.suffix.lower() if file_path.suffix else '(no extension)'
                    file_types[ext] += 1
                    
                    files_with_sizes.append({
                        'path': str(file_path),
                        'size': size
                    })
                except (OSError, IOError):
                    pass  # Skip files we can't access
    except PermissionError:
        pass
    
    # Sort by size and take top N
    files_with_sizes.sort(key=lambda x: x['size'], reverse=True)
    largest_files = files_with_sizes[:top_n]
    
    # Sort file types by count
    sorted_types = dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True))
    
    return {
        'path': str(dir_path),
        'type': 'directory',
        'file_count': file_count,
        'dir_count': dir_count,
        'total_size': total_size,
        'total_size_human': format_size(total_size),
        'file_types': sorted_types,
        'largest_files': largest_files
    }


def file_stats(path_str: str) -> Dict[str, Any]:
    """
    Get statistics about a file or directory.
    
    Args:
        path_str: Path to analyze
        
    Returns:
        Dictionary with statistics
        
    Raises:
        ValueError: If path doesn't exist
    """
    path = Path(path_str)
    
    if not path.exists():
        raise ValueError(f"Path does not exist: {path_str}")
    
    if path.is_file():
        return get_file_stats(path)
    else:
        return get_directory_stats(path)


def main():
    parser = argparse.ArgumentParser(
        description='Get statistics about files and directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python file_stats.py --path ./src
    python file_stats.py --path ./main.py
        '''
    )
    parser.add_argument(
        '--path',
        required=True,
        help='File or directory to analyze'
    )
    
    args = parser.parse_args()
    
    try:
        stats = file_stats(args.path)
        print(json.dumps(stats, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
