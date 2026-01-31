#!/usr/bin/env python3
"""
Create Word documents with structured content.

Usage:
    python create_docx.py --output report.docx --title "Report" --content '{"sections": [...]}'
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    print("Error: 'python-docx' package is required. Install with: pip install python-docx", file=sys.stderr)
    sys.exit(1)


def add_content_section(doc, section):
    """Add a content section to the document."""
    section_type = section.get('type', 'paragraph')
    
    if section_type == 'heading':
        level = section.get('level', 1)
        doc.add_heading(section.get('text', ''), level=level)
    
    elif section_type == 'paragraph':
        para = doc.add_paragraph(section.get('text', ''))
        if section.get('bold'):
            for run in para.runs:
                run.bold = True
        if section.get('italic'):
            for run in para.runs:
                run.italic = True
    
    elif section_type == 'list':
        items = section.get('items', [])
        ordered = section.get('ordered', False)
        style = 'List Number' if ordered else 'List Bullet'
        for item in items:
            doc.add_paragraph(item, style=style)
    
    elif section_type == 'table':
        headers = section.get('headers', [])
        rows = section.get('rows', [])
        
        if headers:
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = 'Table Grid'
            
            # Add headers
            header_cells = table.rows[0].cells
            for i, header in enumerate(headers):
                header_cells[i].text = str(header)
            
            # Add data rows
            for row_data in rows:
                row_cells = table.add_row().cells
                for i, cell_data in enumerate(row_data):
                    if i < len(row_cells):
                        row_cells[i].text = str(cell_data)
    
    elif section_type == 'page_break':
        doc.add_page_break()


def create_docx(output_path: str, title: str, content: dict = None, template_path: str = None):
    """Create a Word document."""
    if template_path and Path(template_path).exists():
        doc = Document(template_path)
    else:
        doc = Document()
    
    # Add title
    doc.add_heading(title, level=0)
    
    # Add content sections
    if content and 'sections' in content:
        for section in content['sections']:
            add_content_section(doc, section)
    
    # Save document
    doc.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create Word documents')
    parser.add_argument('--output', required=True, help='Output file path (.docx)')
    parser.add_argument('--title', required=True, help='Document title')
    parser.add_argument('--content', help='JSON structure defining document content')
    parser.add_argument('--template', help='Path to template document')
    
    args = parser.parse_args()
    
    content = None
    if args.content:
        try:
            content = json.loads(args.content)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid content JSON - {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        result = create_docx(args.output, args.title, content, args.template)
        print(json.dumps({"status": "success", "file": result}))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
