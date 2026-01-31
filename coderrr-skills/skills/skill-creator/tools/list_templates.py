#!/usr/bin/env python3
"""
List available tool templates.

Usage:
    python list_templates.py --category file
"""

import argparse
import sys
import json


TEMPLATES = {
    "file": [
        {
            "name": "file_reader",
            "description": "Read and parse various file formats",
            "args": ["--file", "--format"]
        },
        {
            "name": "file_writer",
            "description": "Write content to files with formatting",
            "args": ["--output", "--content", "--format"]
        },
        {
            "name": "file_converter",
            "description": "Convert between file formats",
            "args": ["--input", "--output", "--from-format", "--to-format"]
        }
    ],
    "web": [
        {
            "name": "http_client",
            "description": "Make HTTP requests with custom headers",
            "args": ["--url", "--method", "--headers", "--data"]
        },
        {
            "name": "html_parser",
            "description": "Parse and extract from HTML",
            "args": ["--html", "--selector", "--format"]
        },
        {
            "name": "url_validator",
            "description": "Validate and analyze URLs",
            "args": ["--url", "--check-accessibility"]
        }
    ],
    "data": [
        {
            "name": "json_processor",
            "description": "Process and transform JSON data",
            "args": ["--input", "--query", "--transform"]
        },
        {
            "name": "csv_handler",
            "description": "Read, write, and transform CSV",
            "args": ["--file", "--columns", "--filter"]
        },
        {
            "name": "data_validator",
            "description": "Validate data against schemas",
            "args": ["--data", "--schema", "--format"]
        }
    ],
    "cli": [
        {
            "name": "command_runner",
            "description": "Execute shell commands safely",
            "args": ["--command", "--timeout", "--capture"]
        },
        {
            "name": "interactive_prompt",
            "description": "Interactive user prompts",
            "args": ["--prompt", "--type", "--default"]
        }
    ]
}


def list_templates(category: str = None):
    """List available templates."""
    if category:
        if category not in TEMPLATES:
            return {
                "error": f"Unknown category: {category}",
                "available": list(TEMPLATES.keys())
            }
        return {
            "category": category,
            "templates": TEMPLATES[category]
        }
    else:
        return {
            "categories": list(TEMPLATES.keys()),
            "total_templates": sum(len(t) for t in TEMPLATES.values()),
            "templates": TEMPLATES
        }


def main():
    parser = argparse.ArgumentParser(description='List tool templates')
    parser.add_argument('--category', choices=['file', 'web', 'data', 'cli'],
                        help='Filter by category')
    
    args = parser.parse_args()
    
    result = list_templates(args.category)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
