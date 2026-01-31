#!/usr/bin/env python3
"""
Get PDF metadata and information.

Usage:
    python pdf_info.py --file document.pdf
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Error: 'PyPDF2' package is required. Install with: pip install PyPDF2", file=sys.stderr)
    sys.exit(1)


def get_pdf_info(file_path: str) -> dict:
    """Get PDF metadata and structure information."""
    path = Path(file_path)
    reader = PdfReader(file_path)
    
    # Get file size
    file_size = path.stat().st_size
    
    # Get metadata
    metadata = reader.metadata
    meta_dict = {}
    if metadata:
        for key in ['/Title', '/Author', '/Subject', '/Creator', '/Producer', '/CreationDate', '/ModDate']:
            if key in metadata:
                meta_dict[key.lstrip('/')] = str(metadata[key])
    
    # Page info
    pages_info = []
    for i, page in enumerate(reader.pages[:10]):  # First 10 pages
        mediabox = page.mediabox
        pages_info.append({
            "page": i + 1,
            "width": float(mediabox.width),
            "height": float(mediabox.height)
        })
    
    return {
        "file": str(path.absolute()),
        "file_size": file_size,
        "file_size_human": f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.2f} MB",
        "page_count": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "metadata": meta_dict,
        "pages": pages_info
    }


def main():
    parser = argparse.ArgumentParser(description='Get PDF information')
    parser.add_argument('--file', required=True, help='PDF file to analyze')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = get_pdf_info(args.file)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
