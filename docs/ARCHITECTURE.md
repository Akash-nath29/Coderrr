# Coderrr Architecture

## Overview

Coderrr is a dual-architecture AI coding agent built with a Python FastAPI backend and Node.js CLI frontend. This document explains the system design, data flow, and key architectural decisions.

## System Components

### 1. Backend (Python/FastAPI)

**File**: `main.py`

**Responsibilities**:
- Interface with AI models (Mistral AI / GitHub Models)
- Enforce JSON response schema
- Handle API authentication
- Process chat requests
- Return structured plans

**Key Features**:
- FastAPI for high-performance async API
- Dynamic mistralai import with fallback
- Environment-based configuration
- CORS enabled for local development

**Endpoint**:
```
POST /chat
{
  "prompt": "user request",
  "temperature": 0.2,
  "max_tokens": 2000,
  "top_p": 1.0
}

Response:
{
  "response": "JSON-formatted plan"
}
```

### 2. Frontend (Node.js)

**Entry Points**:
- `bin/coderrr.js` - Modern commander-based CLI
- `bin/coderrr-cli.js` - Blessed-based TUI (legacy)

**Core Modules** (`src/`):

#### `agent.js` - Core Orchestrator
- Backend communication
- Plan parsing and execution
- Codebase scanning integration
- Auto-testing coordination

#### `fileOps.js` - File Operations
- Create, read, update, patch, delete files
- Automatic directory creation
- Path resolution (relative → absolute)

#### `executor.js` - Command Execution
- Safe command execution
- User permission prompts
- Live stdout/stderr streaming
- Shell configuration (PowerShell on Windows)

#### `todoManager.js` - TODO Management
- Parse plans into visual TODO lists
- Track progress (pending → in-progress → completed)
- Visual indicators (○ ⋯ ✓)

#### `codebaseScanner.js` - Project Intelligence
- Recursive file discovery
- Smart filtering (ignore node_modules, etc.)
- Caching (1-minute TTL)
- File search by pattern

#### `gitOps.js` - Git Integration
- Git repository detection
- Automatic checkpoint commits before operations
- Auto-commit successful changes
- Interactive rollback menu
- Uncommitted changes detection

#### `ui.js` - User Interface
- Chalk-based colored output
- Ora spinners
- Inquirer prompts
- Status indicators

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        User Input                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Agent.process(request)   │
        │  - Load codebase context    │
        │  - Prepare enhanced prompt  │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Backend POST /chat         │
        │  - Call Mistral AI          │
        │  - Enforce JSON schema      │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Agent.parseJsonResponse()  │
        │  - Extract JSON from text   │
        │  - Handle markdown blocks   │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  TodoManager.parseTodos()   │
        │  - Create visual TODO list  │
        │  - Display to user          │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   Agent.executePlan()       │
        │   For each action:          │
        │   ├─ File op → FileOps      │
        │   └─ Command → Executor     │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │     Agent.runTests()        │
        │  - Detect test framework    │
        │  - Execute tests            │
        └─────────────┬───────────────┘
                      │
                      ▼
                ┌─────────┐
                │  Done!  │
                └─────────┘
```

## JSON Plan Schema

The AI returns plans in this strict format:

```json
{
  "explanation": "Brief summary of the plan",
  "plan": [
    {
      "action": "create_file|update_file|patch_file|delete_file|read_file|run_command",
      "path": "relative/path/to/file.js",
      "content": "full file content",
      "command": "shell command",
      "summary": "one-line description"
    }
  ]
}
```

**Supported Actions**:
- `create_file` - Create new file with content
- `update_file` - Replace entire file
- `patch_file` - Modify specific parts
- `delete_file` - Remove file
- `read_file` - Read and display file
- `run_command` - Execute shell command

## Codebase Scanner Architecture

### Purpose
Give AI full awareness of project structure to prevent filename mismatches.

### How It Works

1. **Scan Phase**
   ```javascript
   // On first Agent.process() call
   scanner.scan() → {
     structure: [...],  // All files/dirs
     files: {...},      // File metadata
     summary: {...}     // Stats
   }
   ```

2. **Cache Phase**
   - Results cached for 60 seconds
   - Subsequent requests use cache
   - Manual refresh available

3. **Context Enhancement**
   ```javascript
   enhancedPrompt = `${userPrompt}

   EXISTING PROJECT STRUCTURE:
   - src/agent.js (31KB)
   - src/fileOps.js (8KB)
   ...

   Use EXACT filenames from above.`
   ```

### Ignored Patterns

**Directories**:
- `node_modules`, `env`, `.venv`, `__pycache__`
- `.git`, `dist`, `build`, `coverage`
- `vendor`, `.next`, `.nuxt`

**Files**:
- `.DS_Store`, `Thumbs.db`
- `package-lock.json`, `yarn.lock`
- `.env`, `.gitignore`

**Size Limit**: 500KB per file

## Security Model

### Permission-Based Execution

All commands require user approval:

```javascript
executor.execute(command, {
  requirePermission: true  // Always enforced
})
```

**Flow**:
1. Display command to user
2. Prompt for confirmation (Y/n)
3. Execute if approved
4. Show live output

### Environment Isolation

- All secrets in `.env`
- No hardcoded credentials
- Backend URL configurable
- API keys never logged

### File Operations

- Paths resolved to absolute
- Parent directories auto-created
- Operations logged
- User can review changes

## Configuration

### Environment Variables

**Required**:
```env
GITHUB_TOKEN=xxx              # GitHub Models API key
# OR
MISTRAL_API_KEY=xxx           # Mistral AI API key
```

**Optional**:
```env
MISTRAL_ENDPOINT=https://...  # API endpoint
MISTRAL_MODEL=mistral-large   # Model name
CODERRR_BACKEND=http://...    # Backend URL
TIMEOUT_MS=120000             # Request timeout
```

### Backend Configuration

**Port**: 5000 (default)
**Host**: localhost (secure)
**Reload**: Enabled in development

**Command**:
```bash
uvicorn main:app --reload --port 5000
```

## Auto-Testing

Automatic test detection after successful plan execution:

| Framework | Detection | Command |
|-----------|-----------|---------|
| JavaScript | `package.json` | `npm test` |
| Python | `pytest.ini` or `tests/` | `pytest` |
| Go | `go.mod` | `go test ./...` |
| Rust | `Cargo.toml` | `cargo test` |
| Java | `pom.xml` or `build.gradle` | `mvn test` / `gradle test` |

## Error Handling

### Connection Errors

```javascript
if (error.code === 'ECONNREFUSED') {
  ui.error('Cannot connect to backend')
  ui.warning('Start backend: uvicorn main:app --reload --port 5000')
}
```

### JSON Parse Errors

Three-tier parsing strategy:
1. Direct `JSON.parse()`
2. Extract from markdown code blocks
3. Find first `{...}` object

### File Operation Errors

- Graceful fallback
- Clear error messages
- Continue with next operation option

## Performance Considerations

### Caching

- **Codebase scan**: 60-second TTL
- **Typical scan time**: <10ms for 25 files
- **Memory**: ~200KB cached data

### Backend

- **Async FastAPI**: Non-blocking I/O
- **Streaming**: Response streaming planned
- **Timeout**: 120s default

### Frontend

- **Lazy loading**: Modules loaded on demand
- **Spinners**: Async UI updates
- **Parallel ops**: File operations can run in parallel

## Extension Points

### Adding File Operations

```javascript
// In src/fileOps.js
class FileOperations {
  async newOperation(params) {
    // Implementation
  }
  
  async execute(operation) {
    case 'new_operation':
      return await this.newOperation(operation);
  }
}
```

### Adding Test Frameworks

```javascript
// In src/agent.js
async runTests() {
  const testCommands = [
    // Add new detection
    { file: 'newtest.config', command: 'newtest run' }
  ];
}
```

### Custom Backends

Change `CODERRR_BACKEND`:
```env
CODERRR_BACKEND=https://my-custom-backend.com
```

Backend must implement `/chat` endpoint with same schema.

## Monitoring & Debugging

### Logs

- Backend: `uvicorn` logs to stdout
- Frontend: UI messages via `ui.js`
- Errors: Caught and displayed with context

### Debug Mode

```bash
# Enable verbose logging
DEBUG=* coderrr exec "task"
```

### Testing

```bash
# Run all tests
npm test

# Specific tests
node test/test-scanner.js
node test/test-agent-scanner.js
node test/test-connection.js
```

## Best Practices

1. **Always use environment variables** for configuration
2. **Never bypass permission prompts** for safety
3. **Keep scanner cache** to 1 minute for balance
4. **Review AI-generated code** before committing
5. **Run tests** after making changes
6. **Update documentation** when adding features
7. **Follow existing patterns** for consistency

## Future Architecture

Planned improvements:

- [ ] WebSocket streaming for real-time responses
- [ ] Plugin system for custom operations
- [ ] Multi-backend support (OpenAI, Claude)
- [ ] Semantic code search
- [ ] Dependency analysis
- [ ] Incremental scanning
- [ ] Undo/redo operations

---

For implementation details, see [.github/copilot-instructions.md](../.github/copilot-instructions.md)
