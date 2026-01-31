#!/usr/bin/env python3
"""
Add component templates to an artifact.

Usage:
    python add_component.py --artifact-dir ./my-artifact --component button --variant primary
"""

import argparse
import sys
import json
from pathlib import Path


COMPONENTS = {
    "button": {
        "primary": '''
const Button = ({ children, onClick, disabled }) => (
    <button 
        onClick={onClick}
        disabled={disabled}
        className="bg-primary hover:bg-blue-600 disabled:bg-slate-400 text-white px-6 py-2.5 rounded-lg font-medium transition-colors shadow-sm hover:shadow-md"
    >
        {children}
    </button>
);
''',
        "secondary": '''
const Button = ({ children, onClick, disabled }) => (
    <button 
        onClick={onClick}
        disabled={disabled}
        className="bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-900 dark:text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
    >
        {children}
    </button>
);
''',
        "outline": '''
const Button = ({ children, onClick, disabled }) => (
    <button 
        onClick={onClick}
        disabled={disabled}
        className="border-2 border-primary text-primary hover:bg-primary hover:text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
    >
        {children}
    </button>
);
'''
    },
    "card": {
        "default": '''
const Card = ({ title, children, footer }) => (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg overflow-hidden">
        {title && (
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
            </div>
        )}
        <div className="px-6 py-4">{children}</div>
        {footer && (
            <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
                {footer}
            </div>
        )}
    </div>
);
'''
    },
    "navbar": {
        "default": '''
const Navbar = ({ logo, links }) => (
    <nav className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
                <div className="text-xl font-bold text-slate-900 dark:text-white">{logo}</div>
                <div className="hidden md:flex space-x-8">
                    {links?.map((link, i) => (
                        <a key={i} href={link.href} className="text-slate-600 dark:text-slate-300 hover:text-primary transition-colors">
                            {link.label}
                        </a>
                    ))}
                </div>
            </div>
        </div>
    </nav>
);
'''
    },
    "table": {
        "default": '''
const Table = ({ headers, rows }) => (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
            <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                    {headers?.map((header, i) => (
                        <th key={i} className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                            {header}
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody className="bg-white dark:bg-slate-900 divide-y divide-slate-200 dark:divide-slate-700">
                {rows?.map((row, i) => (
                    <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                        {row.map((cell, j) => (
                            <td key={j} className="px-6 py-4 whitespace-nowrap text-slate-900 dark:text-white">
                                {cell}
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);
'''
    }
}


def add_component(artifact_dir: str, component: str, variant: str = None):
    """Add a component to the artifact."""
    artifact_path = Path(artifact_dir)
    
    if not artifact_path.exists():
        raise ValueError(f"Artifact directory not found: {artifact_dir}")
    
    if component not in COMPONENTS:
        return {
            "error": f"Unknown component: {component}",
            "available": list(COMPONENTS.keys())
        }
    
    variants = COMPONENTS[component]
    variant = variant or "default"
    if variant not in variants:
        variant = list(variants.keys())[0]
    
    component_code = variants[variant]
    
    # Update components.json
    config_file = artifact_path / 'components.json'
    if config_file.exists():
        config = json.loads(config_file.read_text())
    else:
        config = {"components": []}
    
    config["components"].append({
        "name": component,
        "variant": variant
    })
    config_file.write_text(json.dumps(config, indent=2))
    
    # Save component code
    components_dir = artifact_path / 'components'
    components_dir.mkdir(exist_ok=True)
    (components_dir / f'{component}.jsx').write_text(component_code)
    
    return {
        "status": "success",
        "component": component,
        "variant": variant,
        "file": str(components_dir / f'{component}.jsx')
    }


def main():
    parser = argparse.ArgumentParser(description='Add component to artifact')
    parser.add_argument('--artifact-dir', required=True, help='Artifact directory')
    parser.add_argument('--component', required=True, help='Component name')
    parser.add_argument('--variant', help='Component variant')
    
    args = parser.parse_args()
    
    try:
        result = add_component(args.artifact_dir, args.component, args.variant)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
