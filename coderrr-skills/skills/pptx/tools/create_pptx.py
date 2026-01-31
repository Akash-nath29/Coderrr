#!/usr/bin/env python3
"""
Create PowerPoint presentations.

Usage:
    python create_pptx.py --output deck.pptx --title "Title" --slides '[...]'
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    print("Error: 'python-pptx' package is required. Install with: pip install python-pptx", file=sys.stderr)
    sys.exit(1)


def add_slide(prs, slide_spec):
    """Add a slide based on specification."""
    layout_name = slide_spec.get('layout', 'content')
    
    # Map layout names to indices (standard template)
    layout_map = {
        'title': 0,       # Title Slide
        'content': 1,     # Title and Content
        'section': 2,     # Section Header
        'two_content': 3, # Two Content
        'comparison': 4,  # Comparison
        'blank': 6        # Blank
    }
    
    layout_idx = layout_map.get(layout_name, 1)
    layout = prs.slide_layouts[layout_idx]
    slide = prs.slides.add_slide(layout)
    
    # Add title
    if hasattr(slide.shapes, 'title') and slide.shapes.title:
        slide.shapes.title.text = slide_spec.get('title', '')
    
    # Handle different layouts
    if layout_name == 'title':
        # Title slide with subtitle
        if len(slide.placeholders) > 1:
            subtitle = slide.placeholders[1]
            subtitle.text = slide_spec.get('subtitle', '')
    
    elif layout_name == 'content':
        # Content slide with bullets
        content = slide_spec.get('content', [])
        if len(slide.placeholders) > 1:
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.text = content[0] if content else ''
            for item in content[1:]:
                p = tf.add_paragraph()
                p.text = item
                p.level = 0
    
    elif layout_name == 'two_content':
        # Two column layout
        left_content = slide_spec.get('left', [])
        right_content = slide_spec.get('right', [])
        
        placeholders = list(slide.placeholders)
        if len(placeholders) > 1 and left_content:
            tf = placeholders[1].text_frame
            tf.text = left_content[0]
            for item in left_content[1:]:
                p = tf.add_paragraph()
                p.text = item
        
        if len(placeholders) > 2 and right_content:
            tf = placeholders[2].text_frame
            tf.text = right_content[0]
            for item in right_content[1:]:
                p = tf.add_paragraph()
                p.text = item
    
    # Add speaker notes
    if 'notes' in slide_spec:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = slide_spec['notes']
    
    return slide


def create_pptx(output_path: str, title: str, slides_spec: list):
    """Create a PowerPoint presentation."""
    prs = Presentation()
    
    # Add title slide
    title_slide_layout = prs.slide_layouts[0]
    title_slide = prs.slides.add_slide(title_slide_layout)
    title_slide.shapes.title.text = title
    
    # Add content slides
    for slide_spec in slides_spec:
        add_slide(prs, slide_spec)
    
    prs.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create PowerPoint presentations')
    parser.add_argument('--output', required=True, help='Output file path (.pptx)')
    parser.add_argument('--title', required=True, help='Presentation title')
    parser.add_argument('--slides', required=True, help='JSON array of slide specifications')
    
    args = parser.parse_args()
    
    try:
        slides = json.loads(args.slides)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid slides JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = create_pptx(args.output, args.title, slides)
        print(json.dumps({"status": "success", "file": result, "slides": len(slides) + 1}))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
