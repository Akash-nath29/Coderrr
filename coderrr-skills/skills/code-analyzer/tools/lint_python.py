#!/usr/bin/env python3
"""
Basic Python linting using the AST module.

This tool performs static analysis on Python files to detect common issues
like syntax errors, unused imports, and provides code statistics.

Usage:
    python lint_python.py --file ./main.py

Exit Codes:
    0 - Success (even if issues found)
    1 - Invalid file path
    2 - Unable to parse file
"""

import argparse
import sys
import json
import ast
from pathlib import Path
from typing import Dict, Any, List, Set


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to collect import information."""
    
    def __init__(self):
        self.imports: Set[str] = set()
        self.from_imports: Dict[str, List[str]] = {}
        self.all_names: Set[str] = set()
    
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.add(name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name == '*':
                continue
            self.imports.add(name)
            if module not in self.from_imports:
                self.from_imports[module] = []
            self.from_imports[module].append(name)
        self.generic_visit(node)


class NameVisitor(ast.NodeVisitor):
    """AST visitor to collect all name usages."""
    
    def __init__(self):
        self.used_names: Set[str] = set()
        self.defined_names: Set[str] = set()
        self.function_count = 0
        self.class_count = 0
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        self.function_count += 1
        self.defined_names.add(node.name)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        self.function_count += 1
        self.defined_names.add(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.class_count += 1
        self.defined_names.add(node.name)
        self.generic_visit(node)


def lint_python(file_path: str) -> Dict[str, Any]:
    """
    Perform basic linting on a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Dictionary with lint results
        
    Raises:
        ValueError: If file doesn't exist or isn't Python
        SyntaxError: If file has syntax errors
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    if path.suffix != '.py':
        raise ValueError(f"Not a Python file: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    result = {
        'file': str(path),
        'errors': [],
        'warnings': [],
        'info': {
            'functions': 0,
            'classes': 0,
            'imports': 0
        }
    }
    
    # Try to parse the file
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        result['errors'].append({
            'line': e.lineno,
            'type': 'syntax_error',
            'message': str(e.msg)
        })
        return result
    
    # Collect imports
    import_visitor = ImportVisitor()
    import_visitor.visit(tree)
    
    # Collect name usages
    name_visitor = NameVisitor()
    name_visitor.visit(tree)
    
    # Check for unused imports
    for imp in import_visitor.imports:
        if imp not in name_visitor.used_names:
            result['warnings'].append({
                'line': 1,  # AST doesn't easily give us the line for this
                'type': 'unused_import',
                'message': f"Unused import: {imp}"
            })
    
    # Update info
    result['info']['functions'] = name_visitor.function_count
    result['info']['classes'] = name_visitor.class_count
    result['info']['imports'] = len(import_visitor.imports)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Basic Python linting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python lint_python.py --file ./main.py
    python lint_python.py --file ./src/utils.py
        '''
    )
    parser.add_argument(
        '--file',
        required=True,
        help='Python file to lint'
    )
    
    args = parser.parse_args()
    
    try:
        result = lint_python(args.file)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
