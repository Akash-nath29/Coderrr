#!/usr/bin/env python3
"""
Create PDF documents from content specification.

Usage:
    python create_pdf.py --output report.pdf --content '{"elements": [...]}'
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
except ImportError:
    print("Error: 'reportlab' package is required. Install with: pip install reportlab", file=sys.stderr)
    sys.exit(1)


def create_pdf(output_path: str, content: dict, title: str = None):
    """Create a PDF document from content specification."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Add title if provided
    if title:
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 0.5 * inch))
    
    # Process elements
    for element in content.get('elements', []):
        elem_type = element.get('type', 'paragraph')
        
        if elem_type == 'heading':
            size = element.get('size', 18)
            style = ParagraphStyle('CustomHeading', parent=styles['Heading1'], fontSize=size)
            story.append(Paragraph(element.get('text', ''), style))
            story.append(Spacer(1, 0.2 * inch))
        
        elif elem_type == 'paragraph':
            story.append(Paragraph(element.get('text', ''), styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
        
        elif elem_type == 'list':
            items = element.get('items', [])
            for item in items:
                bullet = "• " if not element.get('ordered') else f"{items.index(item) + 1}. "
                story.append(Paragraph(f"{bullet}{item}", styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
        
        elif elem_type == 'table':
            headers = element.get('headers', [])
            rows = element.get('rows', [])
            data = [headers] + rows if headers else rows
            
            if data:
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 0.2 * inch))
        
        elif elem_type == 'page_break':
            story.append(PageBreak())
        
        elif elem_type == 'spacer':
            height = element.get('height', 0.5)
            story.append(Spacer(1, height * inch))
    
    doc.build(story)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create PDF documents')
    parser.add_argument('--output', required=True, help='Output PDF file path')
    parser.add_argument('--content', required=True, help='JSON content specification')
    parser.add_argument('--title', help='Document title')
    
    args = parser.parse_args()
    
    try:
        content = json.loads(args.content)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid content JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = create_pdf(args.output, content, args.title)
        print(json.dumps({"status": "success", "file": result}))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
