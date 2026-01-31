#!/usr/bin/env python3
"""
Split PDF into separate files.

Usage:
    python split_pdf.py --file document.pdf --output-dir ./pages --pages each
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    print("Error: 'PyPDF2' package is required. Install with: pip install PyPDF2", file=sys.stderr)
    sys.exit(1)


def split_pdf(file_path: str, output_dir: str, pages_spec: str = 'each'):
    """Split PDF into separate files."""
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(file_path).stem
    output_files = []
    
    if pages_spec == 'each':
        # Split into individual pages
        for i in range(total_pages):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            
            output_file = output_path / f"{base_name}_page_{i + 1}.pdf"
            with open(output_file, 'wb') as f:
                writer.write(f)
            output_files.append(str(output_file))
    
    else:
        # Split by ranges (e.g., "1-3,4-6,7-10")
        ranges = pages_spec.split(',')
        for idx, range_spec in enumerate(ranges):
            range_spec = range_spec.strip()
            if '-' in range_spec:
                start, end = map(int, range_spec.split('-'))
            else:
                start = end = int(range_spec)
            
            writer = PdfWriter()
            for page_num in range(start - 1, min(end, total_pages)):
                writer.add_page(reader.pages[page_num])
            
            output_file = output_path / f"{base_name}_part_{idx + 1}.pdf"
            with open(output_file, 'wb') as f:
                writer.write(f)
            output_files.append(str(output_file))
    
    return output_files


def main():
    parser = argparse.ArgumentParser(description='Split PDF files')
    parser.add_argument('--file', required=True, help='PDF file to split')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--pages', default='each', help='Page spec: "each" or ranges like "1-3,4-6"')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = split_pdf(args.file, args.output_dir, args.pages)
        print(json.dumps({
            "status": "success",
            "files": result,
            "count": len(result)
        }, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
