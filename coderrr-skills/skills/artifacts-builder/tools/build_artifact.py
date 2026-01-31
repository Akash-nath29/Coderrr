#!/usr/bin/env python3
"""
Build artifact into single HTML file.

Usage:
    python build_artifact.py --artifact-dir ./my-artifact --output ./output.html
"""

import argparse
import sys
import json
from pathlib import Path
import re


def build_artifact(artifact_dir: str, output: str, minify: bool = False):
    """Build artifact into single HTML file."""
    artifact_path = Path(artifact_dir)
    
    if not artifact_path.exists():
        raise ValueError(f"Artifact directory not found: {artifact_dir}")
    
    index_file = artifact_path / 'index.html'
    if not index_file.exists():
        raise ValueError("index.html not found in artifact directory")
    
    html = index_file.read_text()
    
    # Collect component code
    components_dir = artifact_path / 'components'
    if components_dir.exists():
        component_code = []
        for comp_file in components_dir.glob('*.jsx'):
            component_code.append(comp_file.read_text())
        
        if component_code:
            # Inject components before main React code
            combined = '\n'.join(component_code)
            html = html.replace(
                '<script type="text/babel">',
                f'<script type="text/babel">\n{combined}\n'
            )
    
    # Minify if requested
    if minify:
        # Basic minification - remove extra whitespace
        html = re.sub(r'\s+', ' ', html)
        html = re.sub(r'>\s+<', '><', html)
    
    # Write output
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    
    return {
        "status": "success",
        "output": str(output_path),
        "size": len(html),
        "size_human": f"{len(html) / 1024:.1f} KB"
    }


def main():
    parser = argparse.ArgumentParser(description='Build artifact')
    parser.add_argument('--artifact-dir', required=True, help='Artifact directory')
    parser.add_argument('--output', required=True, help='Output HTML file')
    parser.add_argument('--minify', action='store_true', help='Minify output')
    
    args = parser.parse_args()
    
    try:
        result = build_artifact(args.artifact_dir, args.output, args.minify)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
