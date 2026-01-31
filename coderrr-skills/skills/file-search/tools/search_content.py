#!/usr/bin/env python3
"""
Search for text within files (grep-like functionality).

This tool searches for text patterns within files and returns matches
with line numbers.

Usage:
    python search_content.py --query "TODO" --path ./src
    python search_content.py --query "def \\w+\\(" --path ./src --regex

Exit Codes:
    0 - Success
    1 - Invalid path or pattern
"""

import argparse
import sys
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any


# File extensions to search (text files only)
SEARCHABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
    '.sql', '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
    '.html', '.css', '.scss', '.sass', '.less', '.xml', '.json', '.yaml', '.yml',
    '.md', '.txt', '.rst', '.ini', '.cfg', '.conf', '.env', '.toml',
    '.gitignore', '.dockerignore', 'Dockerfile', 'Makefile', '.editorconfig'
}


def is_searchable(file_path: Path) -> bool:
    """Check if a file should be searched based on extension."""
    if file_path.suffix.lower() in SEARCHABLE_EXTENSIONS:
        return True
    if file_path.name in SEARCHABLE_EXTENSIONS:
        return True
    return False


def search_file(file_path: Path, query: str, is_regex: bool = False) -> List[Dict[str, Any]]:
    """
    Search for matches in a single file.
    
    Args:
        file_path: Path to the file to search
        query: Text or regex pattern to search for
        is_regex: Whether to treat query as regex
        
    Returns:
        List of match objects with file, line, and content
    """
    matches = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if is_regex:
                    if re.search(query, line):
                        matches.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.rstrip()
                        })
                else:
                    if query.lower() in line.lower():
                        matches.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.rstrip()
                        })
    except (IOError, OSError):
        pass  # Skip files that can't be read
    
    return matches


def search_content(query: str, search_path: str, is_regex: bool = False) -> List[Dict[str, Any]]:
    """
    Search for text within files.
    
    Args:
        query: Text or pattern to search for
        search_path: File or directory to search in
        is_regex: Whether to treat query as regex
        
    Returns:
        List of match objects
        
    Raises:
        ValueError: If path doesn't exist or regex is invalid
    """
    path = Path(search_path)
    
    if not path.exists():
        raise ValueError(f"Path does not exist: {search_path}")
    
    # Validate regex if needed
    if is_regex:
        try:
            re.compile(query)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    all_matches = []
    
    if path.is_file():
        all_matches.extend(search_file(path, query, is_regex))
    else:
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                if is_searchable(file_path):
                    all_matches.extend(search_file(file_path, query, is_regex))
    
    return all_matches


def main():
    parser = argparse.ArgumentParser(
        description='Search for text within files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python search_content.py --query "TODO" --path ./src
    python search_content.py --query "def \\w+\\(" --path ./src --regex
    python search_content.py --query "import" --path ./main.py
        '''
    )
    parser.add_argument(
        '--query',
        required=True,
        help='Text or pattern to search for'
    )
    parser.add_argument(
        '--path',
        required=True,
        help='File or directory to search in'
    )
    parser.add_argument(
        '--regex',
        action='store_true',
        help='Treat query as a regular expression'
    )
    
    args = parser.parse_args()
    
    try:
        matches = search_content(args.query, args.path, args.regex)
        print(json.dumps(matches, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
