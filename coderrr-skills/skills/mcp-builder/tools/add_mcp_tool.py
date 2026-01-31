#!/usr/bin/env python3
"""
Add a tool to MCP server.

Usage:
    python add_mcp_tool.py --server-dir ./my-server --name search --description "Search documents" --parameters '{...}'
"""

import argparse
import sys
import json
from pathlib import Path


def add_mcp_tool(server_dir: str, name: str, description: str, parameters: dict):
    """Add tool to MCP server."""
    server_path = Path(server_dir)
    
    if not server_path.exists():
        raise ValueError(f"Server directory not found: {server_dir}")
    
    # Update config
    config_file = server_path / 'mcp.json'
    if config_file.exists():
        config = json.loads(config_file.read_text())
    else:
        config = {"tools": [], "resources": []}
    
    tool_def = {
        "name": name,
        "description": description,
        "parameters": parameters
    }
    
    # Check for duplicate
    if any(t["name"] == name for t in config.get("tools", [])):
        raise ValueError(f"Tool '{name}' already exists")
    
    config["tools"].append(tool_def)
    config_file.write_text(json.dumps(config, indent=2))
    
    # Generate handler stub
    handler_code = f'''
# Tool: {name}
# {description}
async def handle_{name.replace('-', '_')}({', '.join(parameters.get('properties', {}).keys())}):
    """
    {description}
    """
    # TODO: Implement tool logic
    return {{"result": "Not implemented"}}
'''
    
    handlers_file = server_path / 'src' / 'handlers.py'
    if handlers_file.exists():
        existing = handlers_file.read_text()
        handlers_file.write_text(existing + handler_code)
    else:
        handlers_file.write_text(f'# Tool handlers\n{handler_code}')
    
    return {
        "status": "success",
        "tool": name,
        "handler": str(handlers_file)
    }


def main():
    parser = argparse.ArgumentParser(description='Add MCP tool')
    parser.add_argument('--server-dir', required=True, help='Server directory')
    parser.add_argument('--name', required=True, help='Tool name')
    parser.add_argument('--description', required=True, help='Tool description')
    parser.add_argument('--parameters', required=True, help='Parameters JSON schema')
    
    args = parser.parse_args()
    
    try:
        parameters = json.loads(args.parameters)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid parameters JSON - {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = add_mcp_tool(args.server_dir, args.name, args.description, parameters)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
