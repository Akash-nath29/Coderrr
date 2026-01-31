#!/usr/bin/env python3
"""
Analyze PowerPoint presentation structure.

Usage:
    python analyze_pptx.py --file presentation.pptx
"""

import argparse
import sys
import json
from pathlib import Path
from collections import Counter

try:
    from pptx import Presentation
except ImportError:
    print("Error: 'python-pptx' package is required. Install with: pip install python-pptx", file=sys.stderr)
    sys.exit(1)


def analyze_pptx(file_path: str) -> dict:
    """Analyze presentation structure."""
    prs = Presentation(file_path)
    
    word_count = 0
    layouts_used = Counter()
    slides_with_notes = 0
    
    for slide in prs.slides:
        layouts_used[slide.slide_layout.name] += 1
        
        for shape in slide.shapes:
            if hasattr(shape, 'text'):
                word_count += len(shape.text.split())
        
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text
            if notes.strip():
                slides_with_notes += 1
    
    return {
        "file": str(file_path),
        "statistics": {
            "slide_count": len(prs.slides),
            "word_count": word_count,
            "slides_with_notes": slides_with_notes
        },
        "layouts_used": dict(layouts_used.most_common()),
        "dimensions": {
            "width": prs.slide_width.inches,
            "height": prs.slide_height.inches
        }
    }


def main():
    parser = argparse.ArgumentParser(description='Analyze PowerPoint presentations')
    parser.add_argument('--file', required=True, help='Path to PowerPoint file')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = analyze_pptx(args.file)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
