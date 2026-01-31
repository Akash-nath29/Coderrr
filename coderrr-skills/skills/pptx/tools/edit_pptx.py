#!/usr/bin/env python3
"""
Edit PowerPoint presentations.

Usage:
    python edit_pptx.py --file input.pptx --output output.pptx --operations '[...]'
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from pptx import Presentation
except ImportError:
    print("Error: 'python-pptx' package is required. Install with: pip install python-pptx", file=sys.stderr)
    sys.exit(1)


def apply_operation(prs, operation):
    """Apply a single edit operation."""
    action = operation.get('action')
    
    if action == 'add_slide':
        layout_map = {'title': 0, 'content': 1, 'section': 2, 'two_content': 3, 'blank': 6}
        layout_idx = layout_map.get(operation.get('layout', 'content'), 1)
        layout = prs.slide_layouts[layout_idx]
        slide = prs.slides.add_slide(layout)
        
        if hasattr(slide.shapes, 'title') and slide.shapes.title:
            slide.shapes.title.text = operation.get('title', '')
        
        content = operation.get('content', [])
        if content and len(slide.placeholders) > 1:
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.text = content[0]
            for item in content[1:]:
                p = tf.add_paragraph()
                p.text = item
    
    elif action == 'update_slide':
        idx = operation.get('index', 1) - 1
        if 0 <= idx < len(prs.slides):
            slide = prs.slides[idx]
            if 'title' in operation and hasattr(slide.shapes, 'title'):
                slide.shapes.title.text = operation['title']
    
    elif action == 'add_notes':
        idx = operation.get('index', 1) - 1
        if 0 <= idx < len(prs.slides):
            slide = prs.slides[idx]
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = operation.get('notes', '')
    
    elif action == 'delete_slide':
        idx = operation.get('index', 1) - 1
        if 0 <= idx < len(prs.slides):
            rId = prs.slides._sldIdLst[idx].rId
            prs.part.drop_rel(rId)
            del prs.slides._sldIdLst[idx]


def edit_pptx(input_path: str, output_path: str, operations: list):
    """Edit a PowerPoint presentation."""
    prs = Presentation(input_path)
    
    for operation in operations:
        apply_operation(prs, operation)
    
    prs.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Edit PowerPoint presentations')
    parser.add_argument('--file', required=True, help='Input PowerPoint file')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--operations', required=True, help='JSON array of operations')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        operations = json.loads(args.operations)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid operations JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = edit_pptx(args.file, args.output, operations)
        print(json.dumps({"status": "success", "file": result}))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
