#!/usr/bin/env python3
"""
Read and extract content from PowerPoint files.

Usage:
    python read_pptx.py --file presentation.pptx --format text
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


def extract_slide_text(slide):
    """Extract all text from a slide."""
    texts = []
    for shape in slide.shapes:
        if hasattr(shape, 'text') and shape.text:
            texts.append(shape.text)
    return texts


def read_pptx(file_path: str, output_format: str = 'text', include_notes: bool = False):
    """Read PowerPoint content."""
    prs = Presentation(file_path)
    
    if output_format == 'json':
        result = {
            "file": str(file_path),
            "slide_count": len(prs.slides),
            "slides": []
        }
        
        for i, slide in enumerate(prs.slides):
            slide_data = {
                "number": i + 1,
                "layout": slide.slide_layout.name,
                "content": extract_slide_text(slide)
            }
            
            if include_notes and slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
                slide_data["notes"] = notes
            
            result["slides"].append(slide_data)
        
        return json.dumps(result, indent=2)
    
    elif output_format == 'markdown':
        lines = []
        for i, slide in enumerate(prs.slides):
            lines.append(f"## Slide {i + 1}")
            lines.append("")
            for text in extract_slide_text(slide):
                lines.append(f"- {text}")
            
            if include_notes and slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
                if notes.strip():
                    lines.append("")
                    lines.append(f"*Notes: {notes}*")
            
            lines.append("")
        
        return '\n'.join(lines)
    
    else:  # text
        lines = []
        for i, slide in enumerate(prs.slides):
            lines.append(f"=== Slide {i + 1} ===")
            for text in extract_slide_text(slide):
                lines.append(text)
            
            if include_notes and slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
                if notes.strip():
                    lines.append(f"[Notes: {notes}]")
            
            lines.append("")
        
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Read PowerPoint files')
    parser.add_argument('--file', required=True, help='Path to PowerPoint file')
    parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text')
    parser.add_argument('--include-notes', action='store_true', help='Include speaker notes')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = read_pptx(args.file, args.format, args.include_notes)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
