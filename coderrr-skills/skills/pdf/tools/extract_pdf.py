#!/usr/bin/env python3
"""
Extract text and tables from PDF documents.

Usage:
    python extract_pdf.py --file document.pdf --format text
    python extract_pdf.py --file data.pdf --tables --format json
"""

import argparse
import sys
import json
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Error: 'pdfplumber' package is required. Install with: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


def parse_page_range(page_spec: str, total_pages: int) -> list:
    """Parse page specification into list of page numbers (0-indexed)."""
    if not page_spec or page_spec.lower() == 'all':
        return list(range(total_pages))
    
    pages = []
    for part in page_spec.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            start = int(start) - 1
            end = min(int(end), total_pages)
            pages.extend(range(start, end))
        else:
            pages.append(int(part) - 1)
    
    return [p for p in pages if 0 <= p < total_pages]


def extract_pdf(file_path: str, pages: str = None, extract_tables: bool = False, output_format: str = 'text'):
    """Extract content from PDF."""
    with pdfplumber.open(file_path) as pdf:
        page_nums = parse_page_range(pages, len(pdf.pages))
        
        if output_format == 'json':
            result = {
                "file": str(file_path),
                "total_pages": len(pdf.pages),
                "extracted_pages": len(page_nums),
                "content": []
            }
            
            for page_num in page_nums:
                page = pdf.pages[page_num]
                page_data = {
                    "page": page_num + 1,
                    "text": page.extract_text() or ""
                }
                
                if extract_tables:
                    tables = page.extract_tables()
                    page_data["tables"] = tables if tables else []
                
                result["content"].append(page_data)
            
            return json.dumps(result, indent=2)
        
        else:  # text format
            text_parts = []
            for page_num in page_nums:
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                
                if extract_tables:
                    tables = page.extract_tables()
                    for i, table in enumerate(tables):
                        text_parts.append(f"\n[Table {i + 1}]")
                        for row in table:
                            text_parts.append(" | ".join(str(cell) if cell else "" for cell in row))
            
            return '\n\n'.join(text_parts)


def main():
    parser = argparse.ArgumentParser(description='Extract text and tables from PDFs')
    parser.add_argument('--file', required=True, help='Path to PDF file')
    parser.add_argument('--pages', help='Page range (e.g., "1-5", "1,3,5", "all")')
    parser.add_argument('--tables', action='store_true', help='Extract tables')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = extract_pdf(args.file, args.pages, args.tables, args.format)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
