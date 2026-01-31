#!/usr/bin/env python3
"""
Read and extract content from Word documents.

Usage:
    python read_docx.py --file document.docx --format text
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from docx import Document
except ImportError:
    print("Error: 'python-docx' package is required. Install with: pip install python-docx", file=sys.stderr)
    sys.exit(1)


def extract_tables(doc):
    """Extract all tables from document."""
    tables = []
    for table in doc.tables:
        table_data = []
        for row in table.rows:
            row_data = [cell.text for cell in row.cells]
            table_data.append(row_data)
        tables.append(table_data)
    return tables


def read_docx_text(file_path: str, include_tables: bool = False) -> str:
    """Extract text content from Word document."""
    doc = Document(file_path)
    
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    text = '\n\n'.join(paragraphs)
    
    if include_tables:
        tables = extract_tables(doc)
        for i, table in enumerate(tables):
            text += f"\n\n[Table {i + 1}]\n"
            for row in table:
                text += ' | '.join(row) + '\n'
    
    return text


def read_docx_json(file_path: str, include_tables: bool = False) -> dict:
    """Extract structured content from Word document."""
    doc = Document(file_path)
    
    result = {
        "paragraphs": [],
        "headings": [],
        "tables": []
    }
    
    for para in doc.paragraphs:
        if para.text.strip():
            style_name = para.style.name if para.style else "Normal"
            if 'Heading' in style_name:
                result["headings"].append({
                    "text": para.text,
                    "level": style_name
                })
            result["paragraphs"].append({
                "text": para.text,
                "style": style_name
            })
    
    if include_tables:
        result["tables"] = extract_tables(doc)
    
    return result


def read_docx_markdown(file_path: str, include_tables: bool = False) -> str:
    """Convert Word document to Markdown."""
    doc = Document(file_path)
    
    md_lines = []
    
    for para in doc.paragraphs:
        if not para.text.strip():
            continue
        
        style_name = para.style.name if para.style else "Normal"
        
        if 'Heading 1' in style_name:
            md_lines.append(f"# {para.text}")
        elif 'Heading 2' in style_name:
            md_lines.append(f"## {para.text}")
        elif 'Heading 3' in style_name:
            md_lines.append(f"### {para.text}")
        elif 'List' in style_name:
            md_lines.append(f"- {para.text}")
        else:
            md_lines.append(para.text)
        
        md_lines.append("")
    
    if include_tables:
        tables = extract_tables(doc)
        for table in tables:
            if table:
                # Header row
                md_lines.append("| " + " | ".join(table[0]) + " |")
                md_lines.append("| " + " | ".join(["---"] * len(table[0])) + " |")
                # Data rows
                for row in table[1:]:
                    md_lines.append("| " + " | ".join(row) + " |")
                md_lines.append("")
    
    return '\n'.join(md_lines)


def main():
    parser = argparse.ArgumentParser(description='Read Word documents')
    parser.add_argument('--file', required=True, help='Path to Word document')
    parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--include-tables', action='store_true', help='Include table data')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.format == 'text':
            result = read_docx_text(args.file, args.include_tables)
            print(result)
        elif args.format == 'json':
            result = read_docx_json(args.file, args.include_tables)
            print(json.dumps(result, indent=2))
        elif args.format == 'markdown':
            result = read_docx_markdown(args.file, args.include_tables)
            print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
