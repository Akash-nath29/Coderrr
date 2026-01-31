#!/usr/bin/env python3
"""
Count lines of code with detailed breakdown.

This tool counts total lines, code lines, comment lines, and blank lines
for various programming languages.

Usage:
    python count_lines.py --path ./main.py
    python count_lines.py --path ./src

Exit Codes:
    0 - Success
    1 - Invalid path
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict


# Language definitions: extension -> (name, single_comment, multi_start, multi_end)
LANGUAGES = {
    '.py': ('python', '#', '"""', '"""'),
    '.pyw': ('python', '#', '"""', '"""'),
    '.js': ('javascript', '//', '/*', '*/'),
    '.jsx': ('javascript', '//', '/*', '*/'),
    '.ts': ('typescript', '//', '/*', '*/'),
    '.tsx': ('typescript', '//', '/*', '*/'),
    '.java': ('java', '//', '/*', '*/'),
    '.c': ('c', '//', '/*', '*/'),
    '.h': ('c', '//', '/*', '*/'),
    '.cpp': ('cpp', '//', '/*', '*/'),
    '.hpp': ('cpp', '//', '/*', '*/'),
    '.cc': ('cpp', '//', '/*', '*/'),
    '.go': ('go', '//', '/*', '*/'),
    '.rs': ('rust', '//', '/*', '*/'),
    '.rb': ('ruby', '#', '=begin', '=end'),
    '.php': ('php', '//', '/*', '*/'),
    '.swift': ('swift', '//', '/*', '*/'),
    '.kt': ('kotlin', '//', '/*', '*/'),
    '.scala': ('scala', '//', '/*', '*/'),
    '.cs': ('csharp', '//', '/*', '*/'),
}


def count_file_lines(file_path: Path) -> Dict[str, int]:
    """Count lines in a single file."""
    result = {
        'total_lines': 0,
        'code_lines': 0,
        'comment_lines': 0,
        'blank_lines': 0
    }
    
    ext = file_path.suffix.lower()
    if ext not in LANGUAGES:
        return result
    
    _, single_comment, multi_start, multi_end = LANGUAGES[ext]
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            in_multiline = False
            
            for line in f:
                result['total_lines'] += 1
                stripped = line.strip()
                
                if not stripped:
                    result['blank_lines'] += 1
                    continue
                
                # Handle multiline comments
                if in_multiline:
                    result['comment_lines'] += 1
                    if multi_end in stripped:
                        in_multiline = False
                    continue
                
                # Check for multiline comment start
                if multi_start in stripped:
                    result['comment_lines'] += 1
                    if multi_end not in stripped[stripped.index(multi_start) + len(multi_start):]:
                        in_multiline = True
                    continue
                
                # Check for single-line comment
                if stripped.startswith(single_comment):
                    result['comment_lines'] += 1
                    continue
                
                # It's a code line
                result['code_lines'] += 1
                
    except (IOError, OSError):
        pass
    
    return result


def count_lines(path_str: str) -> Dict[str, Any]:
    """
    Count lines of code in a file or directory.
    
    Args:
        path_str: Path to file or directory
        
    Returns:
        Dictionary with line counts
        
    Raises:
        ValueError: If path doesn't exist
    """
    path = Path(path_str)
    
    if not path.exists():
        raise ValueError(f"Path does not exist: {path_str}")
    
    summary = {
        'total_lines': 0,
        'code_lines': 0,
        'comment_lines': 0,
        'blank_lines': 0
    }
    
    by_language: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {'files': 0, 'total_lines': 0, 'code_lines': 0, 'comment_lines': 0, 'blank_lines': 0}
    )
    
    files_to_process = []
    
    if path.is_file():
        files_to_process.append(path)
    else:
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in LANGUAGES:
                    files_to_process.append(file_path)
    
    for file_path in files_to_process:
        counts = count_file_lines(file_path)
        
        if counts['total_lines'] > 0:
            ext = file_path.suffix.lower()
            lang_name = LANGUAGES.get(ext, ('unknown',))[0]
            
            summary['total_lines'] += counts['total_lines']
            summary['code_lines'] += counts['code_lines']
            summary['comment_lines'] += counts['comment_lines']
            summary['blank_lines'] += counts['blank_lines']
            
            by_language[lang_name]['files'] += 1
            by_language[lang_name]['total_lines'] += counts['total_lines']
            by_language[lang_name]['code_lines'] += counts['code_lines']
            by_language[lang_name]['comment_lines'] += counts['comment_lines']
            by_language[lang_name]['blank_lines'] += counts['blank_lines']
    
    return {
        'path': str(path),
        'summary': summary,
        'by_language': dict(by_language)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Count lines of code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python count_lines.py --path ./main.py
    python count_lines.py --path ./src
        '''
    )
    parser.add_argument(
        '--path',
        required=True,
        help='File or directory to analyze'
    )
    
    args = parser.parse_args()
    
    try:
        result = count_lines(args.path)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
