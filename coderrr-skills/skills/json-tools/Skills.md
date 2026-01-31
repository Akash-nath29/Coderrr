---
name: json-tools
description: Format, query, and validate JSON data. Use this skill when the user asks to pretty-print JSON, extract values from JSON, validate JSON syntax, minify JSON, or work with nested JSON structures. Provides JSONPath-like querying, formatting options, and detailed syntax validation.
---

This skill handles all common JSON operations using only Python's standard library. It provides formatting with configurable indentation, querying with path expressions, and validation with precise error locations.

The user provides JSON data (as files or input) to process. They may want to format it for readability, extract specific values, or validate syntax before use.

## Approach

Before invoking tools, understand the JSON operation:
- **Readability**: Use `format_json` to pretty-print or minify
- **Data extraction**: Use `query_json` with path expressions
- **Syntax check**: Use `validate_json` to verify and locate errors
- **Pipeline**: Chain tools for complex operations (validate → query → format)

## Tools

### format_json

Pretty-prints or minifies JSON data. Reads from file or stdin for easy piping.

```bash
python tools/format_json.py [--file <json_file>] [--indent <n>] [--minify]
```

**Arguments:**
- `--file` (optional): Path to JSON file. If omitted, reads from stdin
- `--indent` (optional): Indentation spaces (default: 2)
- `--minify` (optional): Compress to single line

**Output:** Formatted JSON to stdout.

**When to use:**
- Making JSON human-readable
- Standardizing JSON formatting
- Minimizing JSON file size
- Piping output from API calls

---

### query_json

Extracts values from JSON using path expressions. Supports simple JSONPath-like syntax.

```bash
python tools/query_json.py --file <json_file> --path <expression>
```

**Arguments:**
- `--file` (required): Path to JSON file
- `--path` (required): Path expression (e.g., `user.name`, `items[0]`, `data[*].id`)

**Path Syntax:**
- `key` or `.key` - Access object property
- `[0]` - Access array element by index
- `[*]` - Access ALL array elements (returns array of matched values)

**Output:** The matched value as JSON.

**When to use:**
- Extracting specific values from config files
- Getting nested data from API responses
- Selecting array elements
- Drilling into complex JSON structures

**Examples:**
- `user.email` → Gets user's email
- `users[0]` → Gets first user
- `items[*].name` → Gets all item names as array
- `config.database.host` → Gets nested config value

---

### validate_json

Validates JSON syntax and reports precise error locations.

```bash
python tools/validate_json.py --file <json_file>
```

**Arguments:**
- `--file` (required): Path to JSON file to validate

**Output:** JSON with validation result. If invalid, includes error message, line, and column.

**When to use:**
- Checking JSON before parsing in code
- Debugging JSON syntax errors
- Validating user-provided JSON
- CI/CD pipeline validation

## Common Patterns

### Pretty Print a File
```bash
python tools/format_json.py --file config.json --indent 4
```

### Minify JSON
```bash
python tools/format_json.py --file data.json --minify
```

### Format Piped Input
```bash
echo '{"name":"John","age":30}' | python tools/format_json.py
```

### Extract Nested Value
```bash
python tools/query_json.py --file response.json --path "data.user.profile.email"
```

### Get All IDs from Array
```bash
python tools/query_json.py --file users.json --path "users[*].id"
```

### Validate Before Processing
```bash
python tools/validate_json.py --file input.json
```

## Best Practices

1. **Validate first** - Check syntax before querying or processing
2. **Use precise paths** - `users[0].name` is clearer than complex filtering
3. **Pipe for workflows** - Combine with other tools via stdin/stdout
4. **Consistent formatting** - Use same indent (2 or 4) across project
5. **Minify for production** - Reduce file size for deployment

## Path Expression Examples

Given this JSON:
```json
{
  "users": [
    {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
    {"id": 2, "name": "Bob", "roles": ["user"]}
  ],
  "meta": {"total": 2, "page": 1}
}
```

| Path | Result |
|------|--------|
| `users` | The entire users array |
| `users[0]` | `{"id": 1, "name": "Alice", ...}` |
| `users[0].name` | `"Alice"` |
| `users[*].name` | `["Alice", "Bob"]` |
| `users[0].roles[0]` | `"admin"` |
| `meta.total` | `2` |

## Error Handling

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | - |
| 1 | Invalid file path | Verify file exists |
| 2 | JSON parsing error | Check syntax with validate_json |
| 3 | Invalid path expression | Check path syntax |

## Dependencies

None - uses Python's standard library only (json, re, pathlib).
