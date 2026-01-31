#!/usr/bin/env python3
"""
Configure core brand values.

Usage:
    python set_brand.py --name myproject --primary "#3b82f6" --secondary "#64748b"
"""

import argparse
import sys
import json
from pathlib import Path


BRANDS_DIR = Path.home() / '.coderrr' / 'brands'


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def set_brand(name: str, primary: str, secondary: str, accent: str = None, fonts: dict = None):
    """Set brand configuration."""
    BRANDS_DIR.mkdir(parents=True, exist_ok=True)
    
    brand = {
        "name": name,
        "colors": {
            "primary": primary,
            "secondary": secondary
        },
        "fonts": fonts or {
            "heading": "Inter",
            "body": "Inter",
            "mono": "JetBrains Mono"
        }
    }
    
    if accent:
        brand["colors"]["accent"] = accent
    
    # Save brand config
    brand_file = BRANDS_DIR / f"{name}.json"
    brand_file.write_text(json.dumps(brand, indent=2))
    
    return {
        "status": "success",
        "brand": name,
        "file": str(brand_file),
        "colors": brand["colors"],
        "fonts": brand["fonts"]
    }


def main():
    parser = argparse.ArgumentParser(description='Set brand configuration')
    parser.add_argument('--name', required=True, help='Brand name')
    parser.add_argument('--primary', required=True, help='Primary color (hex)')
    parser.add_argument('--secondary', required=True, help='Secondary color (hex)')
    parser.add_argument('--accent', help='Accent color (hex)')
    parser.add_argument('--fonts', help='Font configuration JSON')
    
    args = parser.parse_args()
    
    fonts = None
    if args.fonts:
        try:
            fonts = json.loads(args.fonts)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid fonts JSON - {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        result = set_brand(args.name, args.primary, args.secondary, args.accent, fonts)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
