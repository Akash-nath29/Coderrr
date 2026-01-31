---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers. Use this skill when the user wants to build an MCP server, create MCP tools, implement MCP resources, or integrate with MCP-compatible clients. Provides scaffolding, templates, and validation.
---

This skill helps build MCP (Model Context Protocol) servers for extending AI agent capabilities. It provides scaffolding, templates, and best practices for creating production-quality MCP implementations.

The user wants to create an MCP server. They may specify the type of tools, resources, or prompts they want to expose.

## Approach

When building MCP servers:
1. **Initialize**: Use `init_mcp` to scaffold server structure
2. **Add tools**: Use `add_mcp_tool` for each tool
3. **Add resources**: Use `add_mcp_resource` for data sources
4. **Validate**: Use `validate_mcp` to check compliance
5. **Test**: Use `test_mcp` to verify functionality

## Tools

### init_mcp

Scaffolds a new MCP server project.

```bash
python tools/init_mcp.py --name <name> --language <py|ts> --output-dir <path> [--transport <stdio|sse>]
```

**Arguments:**
- `--name` (required): Server name
- `--language` (required): Implementation language - `py` or `ts`
- `--output-dir` (required): Output directory
- `--transport` (optional): Transport type (default: stdio)

**Creates:**
```
my-mcp-server/
├── src/
│   └── server.py (or index.ts)
├── pyproject.toml (or package.json)
├── README.md
└── tests/
```

**When to use:**
- Starting a new MCP server
- Getting proper project structure
- Setting up dependencies

---

### add_mcp_tool

Adds a tool definition to the MCP server.

```bash
python tools/add_mcp_tool.py --server-dir <path> --name <name> --description <desc> --parameters <json>
```

**Arguments:**
- `--server-dir` (required): MCP server directory
- `--name` (required): Tool name
- `--description` (required): Tool description
- `--parameters` (required): JSON schema for parameters

**Parameters JSON:**
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "description": "Search query"},
    "limit": {"type": "integer", "default": 10}
  },
  "required": ["query"]
}
```

**When to use:**
- Adding server capabilities
- Exposing functions to AI agents
- Implementing tool handlers

---

### add_mcp_resource

Adds a resource definition to the MCP server.

```bash
python tools/add_mcp_resource.py --server-dir <path> --uri <uri> --name <name> --description <desc> [--mime-type <type>]
```

**Arguments:**
- `--server-dir` (required): MCP server directory
- `--uri` (required): Resource URI pattern (e.g., `file:///{path}`)
- `--name` (required): Resource name
- `--description` (required): Resource description
- `--mime-type` (optional): Content type (default: text/plain)

**When to use:**
- Exposing data sources
- Providing file access
- Sharing dynamic content

---

### validate_mcp

Validates MCP server implementation.

```bash
python tools/validate_mcp.py --server-dir <path>
```

**Output:** Validation report with compliance status and issues.

**Checks:**
- Valid manifest structure
- Tool definitions follow schema
- Resource URIs are valid
- Handler implementations exist

**When to use:**
- Before publishing
- CI/CD validation
- Debugging issues

---

### test_mcp

Tests MCP server functionality.

```bash
python tools/test_mcp.py --server-dir <path> [--tool <name>] [--input <json>]
```

**Arguments:**
- `--server-dir` (required): MCP server directory
- `--tool` (optional): Specific tool to test
- `--input` (optional): Test input JSON

**When to use:**
- Verifying tool behavior
- Testing handlers
- Debugging responses

## MCP Concepts

### Tools
Functions the AI can invoke:
```python
@server.tool("search")
async def search(query: str, limit: int = 10):
    """Search for documents."""
    return {"results": [...]}
```

### Resources
Data the AI can read:
```python
@server.resource("file:///{path}")
async def read_file(path: str):
    """Read file contents."""
    return {"content": ...}
```

### Prompts
Pre-defined prompt templates:
```python
@server.prompt("summarize")
def summarize_prompt(content: str):
    """Create summary prompt."""
    return f"Summarize: {content}"
```

## Common Patterns

### Create Python MCP Server
```bash
python tools/init_mcp.py --name my-server --language py --output-dir ./servers
python tools/add_mcp_tool.py --server-dir ./servers/my-server --name search --description "Search documents" --parameters '{"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'
python tools/validate_mcp.py --server-dir ./servers/my-server
```

### Add File Resource
```bash
python tools/add_mcp_resource.py --server-dir ./my-server --uri "file:///{path}" --name "files" --description "Access local files" --mime-type text/plain
```

## Best Practices

1. **Clear descriptions** - Help AI understand when to use tools
2. **Typed parameters** - Use JSON Schema for validation
3. **Error handling** - Return meaningful error messages
4. **Async handlers** - Use async for I/O operations
5. **Test thoroughly** - Verify with various inputs

## Dependencies

For Python servers:
- `mcp>=1.0.0`
- `httpx>=0.25.0` (for SSE transport)
