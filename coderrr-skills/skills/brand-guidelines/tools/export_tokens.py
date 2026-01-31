#!/usr/bin/env python3
"""
Export design tokens.

Usage:
    python export_tokens.py --brand myproject --format css --output variables.css
"""

import argparse
import sys
import json
from pathlib import Path


BRANDS_DIR = Path.home() / '.coderrr' / 'brands'


def export_css(brand: dict) -> str:
    """Export as CSS variables."""
    lines = [":root {"]
    
    # Colors
    palette = brand.get("palette", {}).get("colors", {})
    for color_name, shades in palette.items():
        if isinstance(shades, dict):
            for shade, value in shades.items():
                lines.append(f"  --color-{color_name}-{shade}: {value};")
        else:
            lines.append(f"  --color-{color_name}: {shades};")
    
    # Fonts
    fonts = brand.get("fonts", {})
    for font_type, font_name in fonts.items():
        lines.append(f"  --font-{font_type}: '{font_name}', sans-serif;")
    
    lines.append("}")
    return '\n'.join(lines)


def export_scss(brand: dict) -> str:
    """Export as SCSS variables."""
    lines = []
    
    palette = brand.get("palette", {}).get("colors", {})
    for color_name, shades in palette.items():
        if isinstance(shades, dict):
            for shade, value in shades.items():
                lines.append(f"${color_name}-{shade}: {value};")
        else:
            lines.append(f"${color_name}: {shades};")
    
    fonts = brand.get("fonts", {})
    for font_type, font_name in fonts.items():
        lines.append(f"$font-{font_type}: '{font_name}', sans-serif;")
    
    return '\n'.join(lines)


def export_tailwind(brand: dict) -> str:
    """Export as Tailwind config."""
    config = {
        "theme": {
            "extend": {
                "colors": {},
                "fontFamily": {}
            }
        }
    }
    
    palette = brand.get("palette", {}).get("colors", {})
    for color_name, shades in palette.items():
        config["theme"]["extend"]["colors"][color_name] = shades
    
    fonts = brand.get("fonts", {})
    for font_type, font_name in fonts.items():
        config["theme"]["extend"]["fontFamily"][font_type] = [font_name, "sans-serif"]
    
    return f"module.exports = {json.dumps(config, indent=2)}"


def export_tokens(brand_name: str, format_type: str, output: str):
    """Export design tokens."""
    brand_file = BRANDS_DIR / f"{brand_name}.json"
    
    if not brand_file.exists():
        raise ValueError(f"Brand not found: {brand_name}")
    
    brand = json.loads(brand_file.read_text())
    
    exporters = {
        'css': export_css,
        'scss': export_scss,
        'tailwind': export_tailwind,
        'json': lambda b: json.dumps(b, indent=2)
    }
    
    if format_type not in exporters:
        raise ValueError(f"Unknown format: {format_type}")
    
    content = exporters[format_type](brand)
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    
    return {
        "status": "success",
        "brand": brand_name,
        "format": format_type,
        "output": str(output_path)
    }


def main():
    parser = argparse.ArgumentParser(description='Export design tokens')
    parser.add_argument('--brand', required=True, help='Brand name')
    parser.add_argument('--format', required=True, choices=['css', 'scss', 'json', 'tailwind'])
    parser.add_argument('--output', required=True, help='Output file path')
    
    args = parser.parse_args()
    
    try:
        result = export_tokens(args.brand, args.format, args.output)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
