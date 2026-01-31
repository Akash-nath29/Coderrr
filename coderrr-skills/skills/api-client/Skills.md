---
name: api-client
description: Make HTTP requests and work with API responses. Use this skill when the user asks to call APIs, make HTTP GET/POST requests, test endpoints, fetch data from REST APIs, or parse and format API responses. Supports custom headers, JSON payloads, and multiple output formats.
---

This skill provides HTTP client functionality for interacting with REST APIs. It handles authentication headers, JSON request bodies, error responses, and output formatting in JSON, table, or CSV formats.

The user provides an API endpoint to call or response data to process. They may need to test APIs, fetch data, or parse responses into usable formats.

## Approach

Before invoking tools, understand the API interaction:
- **Fetch data**: Use `http_get` for reading resources
- **Send data**: Use `http_post` for creating/updating resources
- **Process results**: Use `parse_response` to extract or reformat data
- **Full workflow**: Chain all three for complete API interactions

Consider authentication, headers, and expected response formats.

## Tools

### http_get

Makes HTTP GET requests with optional custom headers.

```bash
python tools/http_get.py --url <url> [--headers <json>] [--timeout <seconds>]
```

**Arguments:**
- `--url` (required): Complete URL including protocol (https://...)
- `--headers` (optional): JSON string of headers (e.g., `'{"Authorization": "Bearer token"}'`)
- `--timeout` (optional): Request timeout in seconds (default: 30)

**Output:** Response body. JSON responses are automatically pretty-printed.

**Default headers included:**
- `User-Agent: Coderrr-API-Client/1.0`
- `Accept: application/json`

**When to use:**
- Fetching resources from APIs
- Testing API endpoints
- Downloading JSON data
- Checking API availability

---

### http_post

Makes HTTP POST requests with JSON body.

```bash
python tools/http_post.py --url <url> --data <json> [--headers <json>] [--timeout <seconds>]
```

**Arguments:**
- `--url` (required): Complete URL including protocol
- `--data` (required): JSON string of request body
- `--headers` (optional): JSON string of additional headers
- `--timeout` (optional): Request timeout in seconds (default: 30)

**Output:** Response body. JSON responses are automatically pretty-printed.

**Default headers included:**
- `Content-Type: application/json`
- `Accept: application/json`

**When to use:**
- Creating new resources
- Submitting form data
- Authenticating with APIs
- Triggering actions

---

### parse_response

Parses JSON responses and formats or extracts data.

```bash
python tools/parse_response.py [--data <json>] [--extract <path>] [--format <type>]
```

**Arguments:**
- `--data` (optional): JSON string to parse. If omitted, reads from stdin
- `--extract` (optional): Path expression to extract (e.g., `data.users[0].name`)
- `--format` (optional): Output format - `json`, `table`, or `csv` (default: json)

**Output:** Formatted data according to specified format.

**When to use:**
- Extracting specific fields from responses
- Converting JSON to readable tables
- Exporting data to CSV
- Processing piped API output

## Common Patterns

### Simple GET Request
```bash
python tools/http_get.py --url https://api.github.com/users/octocat
```

### Authenticated Request
```bash
python tools/http_get.py --url https://api.example.com/me --headers '{"Authorization": "Bearer YOUR_TOKEN"}'
```

### POST with JSON Data
```bash
python tools/http_post.py --url https://api.example.com/users --data '{"name": "John", "email": "john@example.com"}'
```

### Chained API Call with Extraction
```bash
python tools/http_get.py --url https://api.example.com/users | python tools/parse_response.py --extract "data[*].email"
```

### Format as Table
```bash
python tools/http_get.py --url https://api.example.com/users | python tools/parse_response.py --format table
```

### Export to CSV
```bash
python tools/http_get.py --url https://api.example.com/users | python tools/parse_response.py --format csv > users.csv
```

## Authentication Patterns

### Bearer Token
```bash
--headers '{"Authorization": "Bearer YOUR_ACCESS_TOKEN"}'
```

### API Key (Header)
```bash
--headers '{"X-API-Key": "YOUR_API_KEY"}'
```

### Basic Auth (Base64)
```bash
--headers '{"Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="}'
```

### Multiple Headers
```bash
--headers '{"Authorization": "Bearer token", "X-Request-ID": "123", "Accept-Language": "en-US"}'
```

## Response Format Examples

### JSON (default)
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Table
```
| id | name     | email            |
|----|----------|------------------|
| 1  | John Doe | john@example.com |
| 2  | Jane Doe | jane@example.com |
```

### CSV
```csv
id,name,email
1,John Doe,john@example.com
2,Jane Doe,jane@example.com
```

## Best Practices

1. **Always use HTTPS** - Never send credentials over HTTP
2. **Handle errors** - Check exit codes and stderr for failures
3. **Set appropriate timeouts** - Long for slow APIs, short for health checks
4. **Use extraction** - Don't process entire responses when you need one field
5. **Chain tools** - Pipe http_get to parse_response for clean workflows
6. **Escape JSON carefully** - Use single quotes around JSON strings in bash

## Error Handling

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | - |
| 1 | Invalid arguments or URL | Check URL format, header syntax |
| 2 | Network/connection error | Verify network, check timeout |
| 3 | HTTP error (4xx, 5xx) | Check authentication, request format |
| 4 | JSON parsing error | Verify response is valid JSON |

**HTTP Error Details:** When HTTP 4xx/5xx occurs, the response body is still printed to stderr for debugging.

## Dependencies

Requires `requests>=2.28.0`. Automatically installed with the skill.
