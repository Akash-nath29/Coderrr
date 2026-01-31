#!/usr/bin/env python3
"""
Validate MCP server implementation.

Usage:
    python validate_mcp.py --server-dir ./my-server
"""

import argparse
import sys
import json
from pathlib import Path
import ast


def validate_mcp(server_dir: str) -> dict:
    """Validate MCP server."""
    server_path = Path(server_dir)
    issues = []
    warnings = []
    
    # Check directory exists
    if not server_path.exists():
        return {"valid": False, "issues": ["Server directory not found"]}
    
    # Check mcp.json
    config_file = server_path / 'mcp.json'
    if not config_file.exists():
        issues.append("mcp.json configuration file not found")
    else:
        try:
            config = json.loads(config_file.read_text())
            
            if not config.get("name"):
                warnings.append("Server name not specified in mcp.json")
            
            tools = config.get("tools", [])
            for tool in tools:
                if not tool.get("name"):
                    issues.append("Tool missing name")
                if not tool.get("description"):
                    warnings.append(f"Tool '{tool.get('name', 'unknown')}' missing description")
                if not tool.get("parameters"):
                    warnings.append(f"Tool '{tool.get('name', 'unknown')}' missing parameters schema")
                    
        except json.JSONDecodeError:
            issues.append("mcp.json is not valid JSON")
    
    # Check server implementation
    server_file = server_path / 'src' / 'server.py'
    if not server_file.exists():
        server_file = server_path / 'src' / 'index.ts'
    
    if not server_file.exists():
        issues.append("Server implementation not found (src/server.py or src/index.ts)")
    else:
        # Validate Python syntax
        if server_file.suffix == '.py':
            try:
                ast.parse(server_file.read_text())
            except SyntaxError as e:
                issues.append(f"Syntax error in server.py: line {e.lineno}")
    
    # Check for README
    if not (server_path / 'README.md').exists():
        warnings.append("README.md not found")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "tools_count": len(config.get("tools", [])) if config_file.exists() else 0,
        "resources_count": len(config.get("resources", [])) if config_file.exists() else 0
    }


def main():
    parser = argparse.ArgumentParser(description='Validate MCP server')
    parser.add_argument('--server-dir', required=True, help='Server directory')
    
    args = parser.parse_args()
    
    try:
        result = validate_mcp(args.server_dir)
        result["server_dir"] = args.server_dir
        print(json.dumps(result, indent=2))
        
        if not result["valid"]:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
