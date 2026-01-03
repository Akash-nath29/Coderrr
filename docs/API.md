# API Reference

## Backend API

### Base URL

Default: `http://localhost:8000`

Configurable via `CODERRR_BACKEND` environment variable.

### Authentication

The backend API requires authentication via GitHub Models or Mistral AI:

**GitHub Models** (default):
```env
GITHUB_TOKEN=your_github_personal_access_token
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411
```

**Mistral AI**:
```env
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_ENDPOINT=https://api.mistral.ai
MISTRAL_MODEL=mistral-large-latest
```

### Endpoints

#### `GET /`

Health check endpoint.

**Response**:
```json
{
  "message": "Coderrr backend is running 🚀",
  "version": "1.0.0",
  "status": "healthy"
}
```

**Status Codes**:
- `200 OK` - Backend is running

---

#### `POST /chat`

Send a chat request to the AI backend.

**Request Body**:
```json
{
  "prompt": "string",          // Required: User's request
  "temperature": 0.2,          // Optional: Response randomness (0.0-1.0)
  "max_tokens": 2000,          // Optional: Maximum response length
  "top_p": 1.0                 // Optional: Nucleus sampling (0.0-1.0)
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a simple Node.js HTTP server",
    "temperature": 0.2,
    "max_tokens": 2000
  }'
```

**Response**:
```json
{
  "response": "{\"explanation\": \"Creating a basic HTTP server...\", \"plan\": [...]}"
}
```

**Error Response**:
```json
{
  "error": "string",           // Error type
  "details": "string"          // Detailed error message
}
```

**Status Codes**:
- `200 OK` - Request successful
- `400 Bad Request` - Invalid request body
- `401 Unauthorized` - Missing or invalid API key
- `500 Internal Server Error` - Backend error

**Expected JSON Response Schema**:

The AI must return this structure:
```json
{
  "explanation": "Brief summary of the plan",
  "plan": [
    {
      "action": "create_file|update_file|patch_file|delete_file|read_file|run_command",
      "path": "relative/path/to/file.js",
      "content": "full file content (for file actions)",
      "command": "shell command (for run_command)",
      "summary": "one-line description of this step"
    }
  ]
}
```

**Supported Actions**:
- `create_file` - Create new file (requires `path`, `content`)
- `update_file` - Replace entire file (requires `path`, `content`)
- `patch_file` - Modify specific parts (requires `path`, `content`)
- `delete_file` - Remove file (requires `path`)
- `read_file` - Read file (requires `path`)
- `run_command` - Execute command (requires `command`)

---

## Frontend API (Node.js)

### Agent Class

Main orchestrator for AI interactions.

#### Constructor

```javascript
const Agent = require('./src/agent');

const agent = new Agent({
  workingDir: '/path/to/project',  // Optional: defaults to process.cwd()
  backendUrl: 'http://localhost:8000'  // Optional: defaults to CODERRR_BACKEND env var
});
```

#### Methods

##### `async process(userInput)`

Process a user request and execute the resulting plan.

**Parameters**:
- `userInput` (string) - User's natural language request

**Returns**: `Promise<void>`

**Example**:
```javascript
await agent.process('Create a TODO app with React');
```

**Behavior**:
1. Scans codebase (if first request)
2. Enhances prompt with project context
3. Sends request to backend
4. Parses JSON response
5. Displays TODO list
6. Executes plan
7. Runs tests (if applicable)

---

##### `async chat(prompt)`

Send a raw chat request to the backend.

**Parameters**:
- `prompt` (string) - Prompt text (can include codebase context)

**Returns**: `Promise<string>` - Raw AI response

**Example**:
```javascript
const response = await agent.chat('Explain this code: ...');
console.log(response);
```

---

##### `async executePlan(plan)`

Execute a parsed plan.

**Parameters**:
- `plan` (array) - Array of operation objects

**Returns**: `Promise<void>`

**Example**:
```javascript
const plan = [
  { action: 'create_file', path: 'test.js', content: 'console.log("hi");' }
];
await agent.executePlan(plan);
```

---

##### `async runTests()`

Auto-detect and run tests for the project.

**Returns**: `Promise<void>`

**Example**:
```javascript
await agent.runTests();
```

**Detection Logic**:
- `package.json` → `npm test`
- `pytest.ini` or `tests/` → `pytest`
- `go.mod` → `go test ./...`
- `Cargo.toml` → `cargo test`

---

##### `async refreshCodebase()`

Force refresh the codebase scan cache.

**Returns**: `Promise<void>`

**Example**:
```javascript
await agent.refreshCodebase();
```

---

##### `findFiles(searchTerm)`

Search for files matching a pattern.

**Parameters**:
- `searchTerm` (string) - Search pattern (case-insensitive)

**Returns**: `Array<{path, name, size}>` - Matching files

**Example**:
```javascript
const jsFiles = agent.findFiles('.js');
console.log(jsFiles);
// [{ path: 'src/agent.js', name: 'agent.js', size: 31234 }, ...]
```

---

##### `getCodebaseSummary()`

Get summary of the scanned codebase.

**Returns**: `string` - Formatted codebase summary

**Example**:
```javascript
const summary = agent.getCodebaseSummary();
console.log(summary);
// Working Directory: /path/to/project
// Total Files: 25
// Total Directories: 4
// ...
```

---

### FileOperations Class

Handle file operations.

#### Constructor

```javascript
const FileOperations = require('./src/fileOps');

const fileOps = new FileOperations('/path/to/project');
```

#### Methods

##### `async createFile(path, content)`

Create a new file.

**Parameters**:
- `path` (string) - Relative file path
- `content` (string) - File content

**Returns**: `Promise<void>`

**Example**:
```javascript
await fileOps.createFile('src/utils.js', 'module.exports = {};');
```

---

##### `async readFile(path)`

Read a file.

**Parameters**:
- `path` (string) - Relative file path

**Returns**: `Promise<string>` - File content

**Example**:
```javascript
const content = await fileOps.readFile('package.json');
console.log(content);
```

---

##### `async updateFile(path, content)`

Replace entire file content.

**Parameters**:
- `path` (string) - Relative file path
- `content` (string) - New file content

**Returns**: `Promise<void>`

**Example**:
```javascript
await fileOps.updateFile('README.md', '# New Title\n\n...');
```

---

##### `async patchFile(path, content)`

Modify parts of a file (simple string replacement).

**Parameters**:
- `path` (string) - Relative file path
- `content` (string) - New content to replace old

**Returns**: `Promise<void>`

**Example**:
```javascript
await fileOps.patchFile('config.js', 'port: 5000');
```

---

##### `async deleteFile(path)`

Delete a file.

**Parameters**:
- `path` (string) - Relative file path

**Returns**: `Promise<void>`

**Example**:
```javascript
await fileOps.deleteFile('old-file.js');
```

---

##### `async execute(operation)`

Execute a file operation from a plan step.

**Parameters**:
- `operation` (object) - Operation object with `action`, `path`, `content`

**Returns**: `Promise<void>`

**Example**:
```javascript
await fileOps.execute({
  action: 'create_file',
  path: 'test.js',
  content: 'console.log("test");'
});
```

---

### Executor Class

Execute shell commands safely.

#### Constructor

```javascript
const Executor = require('./src/executor');

const executor = new Executor('/path/to/project');
```

#### Methods

##### `async execute(command, options)`

Execute a shell command.

**Parameters**:
- `command` (string) - Shell command to execute
- `options` (object) - Execution options
  - `requirePermission` (boolean) - Prompt user for permission (default: true)
  - `cwd` (string) - Working directory (default: workingDir)
  - `shell` (string) - Shell to use (default: 'powershell.exe' on Windows)

**Returns**: `Promise<{stdout, stderr, code}>` - Execution result

**Example**:
```javascript
const result = await executor.execute('npm install', {
  requirePermission: true,
  cwd: '/path/to/project'
});

console.log(result.stdout);
```

---

### CodebaseScanner Class

Scan project structure.

#### Constructor

```javascript
const CodebaseScanner = require('./src/codebaseScanner');

const scanner = new CodebaseScanner('/path/to/project');
```

#### Methods

##### `async scan(forceRefresh)`

Scan the codebase.

**Parameters**:
- `forceRefresh` (boolean) - Bypass cache (default: false)

**Returns**: `Promise<{structure, files, summary}>` - Scan results

**Example**:
```javascript
const results = await scanner.scan();
console.log(results.summary);
// { totalFiles: 25, totalDirectories: 4, totalSize: 512000 }
```

---

##### `getSummaryForAI()`

Get formatted summary for AI context.

**Returns**: `string` - Formatted summary

**Example**:
```javascript
const summary = scanner.getSummaryForAI();
// Includes file list, directory structure, working dir
```

---

##### `findFiles(searchTerm)`

Search for files.

**Parameters**:
- `searchTerm` (string) - Search pattern (case-insensitive)

**Returns**: `Array<{path, name, size}>` - Matching files

**Example**:
```javascript
const tests = scanner.findFiles('test');
console.log(tests);
```

---

##### `clearCache()`

Clear the scan cache.

**Returns**: `void`

**Example**:
```javascript
scanner.clearCache();
```

---

### UI Module

User interface utilities.

#### Functions

##### `section(title)`

Display a section header.

**Parameters**:
- `title` (string) - Section title

**Example**:
```javascript
ui.section('Starting Build');
```

---

##### `success(message)`

Display success message.

**Parameters**:
- `message` (string) - Success message

**Example**:
```javascript
ui.success('Build complete!');
```

---

##### `error(message)`

Display error message.

**Parameters**:
- `message` (string) - Error message

**Example**:
```javascript
ui.error('Failed to connect');
```

---

##### `warning(message)`

Display warning message.

**Parameters**:
- `message` (string) - Warning message

**Example**:
```javascript
ui.warning('Deprecated API usage');
```

---

##### `info(message)`

Display info message.

**Parameters**:
- `message` (string) - Info message

**Example**:
```javascript
ui.info('Scanning codebase...');
```

---

##### `async confirm(message, defaultValue)`

Prompt for confirmation.

**Parameters**:
- `message` (string) - Prompt message
- `defaultValue` (boolean) - Default answer (default: true)

**Returns**: `Promise<boolean>` - User's answer

**Example**:
```javascript
const proceed = await ui.confirm('Continue?', true);
if (proceed) {
  // Do something
}
```

---

##### `spinner(message)`

Create a spinner.

**Parameters**:
- `message` (string) - Spinner message

**Returns**: `Ora` - Spinner instance

**Example**:
```javascript
const spin = ui.spinner('Loading...');
spin.start();
// ... do work ...
spin.succeed('Done!');
```

---

##### `displayFileOp(action, path, status)`

Display file operation.

**Parameters**:
- `action` (string) - Operation type
- `path` (string) - File path
- `status` (string) - Status (optional: 'success', 'error')

**Example**:
```javascript
ui.displayFileOp('create_file', 'src/test.js', 'success');
// Output: ✓ create_file: src/test.js
```

---

##### `displayCommand(command)`

Display command before execution.

**Parameters**:
- `command` (string) - Command to display

**Example**:
```javascript
ui.displayCommand('npm install');
// Output: $ npm install
```

---

## CLI Commands

### `coderrr`

Interactive mode - starts a REPL session.

**Usage**:
```bash
coderrr
```

**Example**:
```bash
$ coderrr
? What would you like me to do? Create a REST API with Express
[Agent processes request...]
```

---

### `coderrr exec <request>`

Execute a single request.

**Usage**:
```bash
coderrr exec "<natural language request>"
```

**Example**:
```bash
$ coderrr exec "Add error handling to server.js"
[Agent processes request...]
```

---

### `coderrr start`

Start the backend server.

**Usage**:
```bash
coderrr start
```

**Behavior**:
- Starts FastAPI backend on port 5000
- Enables auto-reload in development
- Logs to stdout

---

## Error Codes

### Backend Errors

| Code | Meaning | Resolution |
|------|---------|-----------|
| `ECONNREFUSED` | Cannot connect to backend | Start backend with `uvicorn main:app --reload --port 5000` |
| `AUTH_ERROR` | Invalid API key | Check `GITHUB_TOKEN` or `MISTRAL_API_KEY` |
| `JSON_PARSE_ERROR` | Invalid AI response | Check backend logs for raw response |
| `TIMEOUT` | Request timeout | Increase `TIMEOUT_MS` in `.env` |

### Frontend Errors

| Code | Meaning | Resolution |
|------|---------|-----------|
| `FILE_NOT_FOUND` | File doesn't exist | Check file path |
| `PERMISSION_DENIED` | No write permissions | Check directory permissions |
| `INVALID_ACTION` | Unknown operation | Check plan action type |
| `USER_CANCELLED` | User declined permission | Expected behavior |

---

## Rate Limits

### GitHub Models

- **Rate Limit**: 15 requests/minute (free tier)
- **Token Limit**: 128,000 tokens/request
- **Retry**: Exponential backoff recommended

### Mistral AI

- **Rate Limit**: Varies by plan
- **Token Limit**: Varies by model
- **Retry**: Check `Retry-After` header

---

## Best Practices

1. **Always check backend health** before requests:
   ```bash
   curl http://localhost:8000
   ```

2. **Use appropriate temperature**:
   - `0.0-0.3` for code generation (deterministic)
   - `0.5-0.7` for creative tasks
   - `0.8-1.0` for brainstorming

3. **Set max_tokens wisely**:
   - Small changes: 1000 tokens
   - Medium projects: 2000 tokens
   - Large projects: 4000 tokens

4. **Handle errors gracefully**:
   ```javascript
   try {
     await agent.process(request);
   } catch (error) {
     if (error.code === 'ECONNREFUSED') {
       // Handle connection error
     } else {
       // Generic error handling
     }
   }
   ```

5. **Clear cache when needed**:
   ```javascript
   // After major file changes
   await agent.refreshCodebase();
   ```

---

For more details, see [ARCHITECTURE.md](ARCHITECTURE.md) and [examples/](../examples/)
