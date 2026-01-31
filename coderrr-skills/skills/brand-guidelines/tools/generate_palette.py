#!/usr/bin/env python3
"""
Generate extended color palette.

Usage:
    python generate_palette.py --brand myproject --include both
"""

import argparse
import sys
import json
from pathlib import Path


BRANDS_DIR = Path.home() / '.coderrr' / 'brands'


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    """Convert RGB to hex."""
    return '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, int(c))) for c in rgb])


def lighten(hex_color: str, amount: float) -> str:
    """Lighten a color."""
    r, g, b = hex_to_rgb(hex_color)
    r = r + (255 - r) * amount
    g = g + (255 - g) * amount
    b = b + (255 - b) * amount
    return rgb_to_hex((r, g, b))


def darken(hex_color: str, amount: float) -> str:
    """Darken a color."""
    r, g, b = hex_to_rgb(hex_color)
    r = r * (1 - amount)
    g = g * (1 - amount)
    b = b * (1 - amount)
    return rgb_to_hex((r, g, b))


def generate_shades(base_color: str) -> dict:
    """Generate 50-950 shade scale."""
    return {
        "50": lighten(base_color, 0.95),
        "100": lighten(base_color, 0.9),
        "200": lighten(base_color, 0.75),
        "300": lighten(base_color, 0.6),
        "400": lighten(base_color, 0.3),
        "500": base_color,
        "600": darken(base_color, 0.1),
        "700": darken(base_color, 0.25),
        "800": darken(base_color, 0.4),
        "900": darken(base_color, 0.55),
        "950": darken(base_color, 0.7)
    }


def generate_palette(brand_name: str, include: str = 'both'):
    """Generate extended color palette."""
    brand_file = BRANDS_DIR / f"{brand_name}.json"
    
    if not brand_file.exists():
        raise ValueError(f"Brand not found: {brand_name}")
    
    brand = json.loads(brand_file.read_text())
    palette = {"colors": {}}
    
    if include in ['shades', 'both']:
        # Generate shades for each brand color
        for name, color in brand.get("colors", {}).items():
            palette["colors"][name] = generate_shades(color)
    
    if include in ['semantic', 'both']:
        # Add semantic colors
        palette["colors"]["success"] = generate_shades("#22c55e")
        palette["colors"]["warning"] = generate_shades("#eab308")
        palette["colors"]["error"] = generate_shades("#ef4444")
        palette["colors"]["info"] = generate_shades("#3b82f6")
    
    # Update brand file with palette
    brand["palette"] = palette
    brand_file.write_text(json.dumps(brand, indent=2))
    
    return {
        "status": "success",
        "brand": brand_name,
        "generated": list(palette["colors"].keys())
    }


def main():
    parser = argparse.ArgumentParser(description='Generate color palette')
    parser.add_argument('--brand', required=True, help='Brand name')
    parser.add_argument('--include', default='both', choices=['shades', 'semantic', 'both'])
    
    args = parser.parse_args()
    
    try:
        result = generate_palette(args.brand, args.include)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
