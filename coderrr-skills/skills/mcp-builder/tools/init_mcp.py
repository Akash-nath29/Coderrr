#!/usr/bin/env python3
"""
Initialize a new MCP server project.

Usage:
    python init_mcp.py --name my-server --language py --output-dir ./servers
"""

import argparse
import sys
import json
from pathlib import Path


PYTHON_SERVER_TEMPLATE = '''#!/usr/bin/env python3
"""
{name} MCP Server

A Model Context Protocol server providing [description].
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Create server instance
server = Server("{name}")


# Tools registry
@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        # Add tools here
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    # Implement tool handlers
    raise ValueError(f"Unknown tool: {{name}}")


# Resources registry
@server.list_resources()
async def list_resources():
    """List available resources."""
    return [
        # Add resources here
    ]


@server.read_resource()
async def read_resource(uri: str):
    """Read resource content."""
    raise ValueError(f"Unknown resource: {{uri}}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
'''


PYPROJECT_TEMPLATE = '''[project]
name = "{name}"
version = "0.1.0"
description = "MCP server for {name}"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
]

[project.scripts]
{name} = "src.server:main"
'''


README_TEMPLATE = '''# {name}

A Model Context Protocol (MCP) server.

## Installation

```bash
pip install -e .
```

## Usage

Run the server:
```bash
python src/server.py
```

## Tools

| Tool | Description |
|------|-------------|
| (Add tools) | (Description) |

## Resources

| URI Pattern | Description |
|-------------|-------------|
| (Add resources) | (Description) |

## License

MIT
'''


def init_mcp(name: str, language: str, output_dir: str, transport: str = 'stdio'):
    """Initialize MCP server project."""
    server_dir = Path(output_dir) / name
    
    # Create directories
    server_dir.mkdir(parents=True, exist_ok=True)
    (server_dir / 'src').mkdir(exist_ok=True)
    (server_dir / 'tests').mkdir(exist_ok=True)
    
    if language == 'py':
        # Python server
        (server_dir / 'src' / 'server.py').write_text(
            PYTHON_SERVER_TEMPLATE.format(name=name)
        )
        (server_dir / 'src' / '__init__.py').write_text('')
        (server_dir / 'pyproject.toml').write_text(
            PYPROJECT_TEMPLATE.format(name=name)
        )
    
    # Common files
    (server_dir / 'README.md').write_text(README_TEMPLATE.format(name=name))
    
    # Server config
    config = {
        "name": name,
        "language": language,
        "transport": transport,
        "tools": [],
        "resources": []
    }
    (server_dir / 'mcp.json').write_text(json.dumps(config, indent=2))
    
    return {
        "status": "success",
        "server_dir": str(server_dir),
        "language": language,
        "transport": transport
    }


def main():
    parser = argparse.ArgumentParser(description='Initialize MCP server')
    parser.add_argument('--name', required=True, help='Server name')
    parser.add_argument('--language', required=True, choices=['py', 'ts'])
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--transport', default='stdio', choices=['stdio', 'sse'])
    
    args = parser.parse_args()
    
    try:
        result = init_mcp(args.name, args.language, args.output_dir, args.transport)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
