# Coderrr AI Agent Instructions

## Architecture Overview

**Coderrr** is a dual-architecture AI coding agent with a Python FastAPI backend and Node.js CLI frontend.

### System Components

1. **Backend** (`main.py`): FastAPI server that interfaces with Mistral AI/GitHub Models
   - Runs on port **5000** (not 8000)
   - Returns structured JSON plans with `explanation` and `plan[]` array
   - System prompt in `SYSTEM_INSTRUCTIONS` enforces strict JSON response schema

2. **CLI Frontend** (Node.js):
   - **New CLI** (`bin/coderrr.js`): Modern commander-based interface with inquirer prompts
   - **Legacy TUI** (`bin/coderrr-cli.js`): Blessed-based terminal UI (kept for compatibility)
   - Default backend: reads from `CODERRR_BACKEND` env variable

3. **Core Modules** (`src/`):
   - `agent.js`: Orchestrates backend communication, plan execution, and auto-testing
   - `fileOps.js`: CRUD operations with automatic directory creation
   - `executor.js`: Command execution with **mandatory user permission prompts**
   - `todoManager.js`: Parses plans into visual TODO lists with progress tracking
   - `ui.js`: Chalk/Ora-based interface (spinners, colors, prompts)
   - `codebaseScanner.js`: **NEW** - Scans project structure to prevent filename mismatches

### Critical Data Flow

```
User Input → Agent.process() → [CodebaseScanner.scan() on first request]
→ Backend /chat (with codebase context) → AI Model → JSON Response
→ parseJsonResponse() → TodoManager.parseTodos() → executePlan()
→ [FileOps.execute() | Executor.execute() with permission] → Auto-test detection
```

## Development Workflow

### Starting the System

**Backend (Terminal 1):**
```powershell
.\env\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 5000
```
Or use: `.\start-backend.ps1`

**CLI (Terminal 2):**
```bash
npm link              # One-time global install
coderrr               # Interactive mode
coderrr exec "task"   # Single command mode
```

### Backend Port Mismatch Fix

The backend runs on **5000**, not 8000. Backend URL is configured via `CODERRR_BACKEND` environment variable:
- `.env`: `CODERRR_BACKEND=http://localhost:8000`
- All code reads from `process.env.CODERRR_BACKEND`

### Python Virtual Environment

The backend has a **clever fallback** in `_import_mistralai_with_fallback()`:
- Tries importing `mistralai` from system
- If that fails, dynamically adds `env/Lib/site-packages` to `sys.path`
- Enables running without activating venv (not recommended for production)

## Key Conventions

### JSON Response Schema (Backend)

The AI **must** return this exact structure (enforced by `SYSTEM_INSTRUCTIONS`):

```json
{
  "explanation": "Brief summary of what will be done",
  "plan": [
    {
      "action": "create_file|update_file|patch_file|delete_file|read_file|run_command",
      "path": "relative/path/file.py",
      "content": "full file content",
      "command": "shell command",
      "summary": "one-line description"
    }
  ]
}
```

**Critical:** Plans are parsed by `Agent.parseJsonResponse()` which handles:
1. Direct JSON parse
2. Markdown code blocks: `` ```json ... ``` ``
3. Fallback: Extracts first `{...}` object

### File Operations

**All paths are relative** to `workingDir` (default: `process.cwd()`):
- `fileOps.resolvePath()` converts relative → absolute
- `createFile()` auto-creates parent directories via `ensureDir()`
- `patchFile()` uses simple string replacement (not diff-based)

**Codebase Scanner Integration:**
- `codebaseScanner.js` automatically scans project on first request
- Provides AI with list of all existing files and directories
- Prevents filename mismatches (e.g., looking for "chatbot.py" when it's "chat.py")
- Caches results for 1 minute to avoid re-scanning
- Agent includes codebase context in prompts sent to backend

**Example:**
```javascript
// Input: "src/models/user.py"
// Resolves to: "E:/Projects/Coderrr/src/models/user.py"
// Creates: "E:/Projects/Coderrr/src/models/" if needed
```

### Command Execution Safety

**ALL commands require user permission** (like GitHub Copilot):

```javascript
executor.execute(command, { 
  requirePermission: true,  // Always true by default
  cwd: workingDir,
  shell: 'powershell.exe'   // Windows default
})
```

Flow: `ui.displayCommand()` → `ui.confirm()` → Execute → Live stdout/stderr

### Auto-Testing

After successful plan execution, `Agent.runTests()` auto-detects:
- `package.json` → `npm test`
- `pytest.ini` or `tests/` → `pytest`
- `go.mod` → `go test ./...`
- `Cargo.toml` → `cargo test`

Detection happens in `runTests()` by checking file existence.

### Codebase Scanner

**Purpose:** Give AI awareness of project structure to prevent filename mismatches

**How it works:**
1. On first `Agent.process()` call, `scanner.scan()` runs automatically
2. Scans all source files (ignoring `node_modules`, `env`, `__pycache__`, etc.)
3. Builds structure: `{ directories: [...], files: [{path, name, size}], summary: {...} }`
4. Caches for 1 minute (60000ms)
5. Context appended to AI prompt before backend request

**Key methods:**
- `scanner.scan(forceRefresh)` - Scan codebase (uses cache unless forced)
- `scanner.getSummaryForAI()` - Get concise summary for AI context
- `scanner.findFiles(searchTerm)` - Search for files by name
- `scanner.clearCache()` - Clear cached scan results
- `agent.refreshCodebase()` - Manually rescan with UI feedback

**Ignored patterns:**
- Dirs: `node_modules`, `env`, `venv`, `__pycache__`, `.git`, `dist`, `build`, `coverage`
- Files: `.DS_Store`, `package-lock.json`, `yarn.lock`, `.env`, `.gitignore`
- Extensions: Includes `.js`, `.py`, `.ts`, `.go`, `.rs`, `.java`, `.md`, `.json`, etc.
- Size limit: 500KB max per file

**AI Context Enhancement:**
Agent.chat() now sends:
```
{prompt}

EXISTING PROJECT STRUCTURE:
Working Directory: E:/Projects/Coderrr
Total Files: 25
Total Directories: 4

DIRECTORIES:
src
bin
test
...

EXISTING FILES:
- src/agent.js (31KB)
- src/fileOps.js (8KB)
...

When editing existing files, use EXACT filenames from the list above.
```

## Project-Specific Patterns

### Error Handling Pattern

```javascript
try {
  // Operation
} catch (error) {
  if (error.code === 'ECONNREFUSED') {
    // Specific handling with helpful message
  } else {
    ui.error(`Generic error: ${error.message}`);
  }
  throw error;  // Always re-throw for upper handlers
}
```

### TODO State Transitions

TodoManager uses visual indicators:
- `○` pending (not started)
- `⋯` in-progress (currently executing)
- `✓` completed

State flow: `setInProgress(index)` → Execute → `complete(index)`

### UI Conventions

- Use `ui.section()` for major phase headers
- Use `ui.spinner()` for long operations (stop before next output)
- Use `ui.displayFileOp(action, path, status)` for file operations
- Use `ui.displayCommand(cmd)` before permission prompts

## Integration Points

### Backend API Contract

**Endpoint:** `POST /chat`
**Request:**
```json
{
  "prompt": "user request",
  "temperature": 0.2,
  "max_tokens": 2000,
  "top_p": 1.0
}
```

**Response:**
```json
{
  "response": "raw AI text (may contain JSON)"
}
```

**Error Response:**
```json
{
  "error": "error type",
  "details": "error details"
}
```

### Environment Variables

Critical vars (`.env`):
- `GITHUB_TOKEN` or `MISTRAL_API_KEY`: API authentication
- `MISTRAL_ENDPOINT`: API endpoint (default: GitHub Models)
- `MISTRAL_MODEL`: Model name
- `CODERRR_BACKEND`: CLI → Backend connection URL

## Testing & Debugging

### Quick Connection Test
```bash
node test-connection.js  # Tests backend connectivity
```

### Manual Backend Test
```bash
curl http://localhost:8000
# Should return: {"message":"Coderrr backend is running 🚀",...}
```

### Common Issues

1. **ECONNREFUSED**: Backend not running or wrong port in CODERRR_BACKEND
   - Check: `ps aux | grep uvicorn` (or Task Manager on Windows)
   - Fix: Set CODERRR_BACKEND=http://localhost:8000 in .env

2. **JSON Parse Errors**: AI didn't return proper JSON
   - Backend logs show raw AI response
   - Check `SYSTEM_INSTRUCTIONS` prompt

3. **Import Errors** (`mistralai` not found):
   - Activate venv: `.\env\Scripts\Activate.ps1`
   - Or rely on fallback (adds `env/Lib/site-packages` to path)

## When Modifying Code

- **Backend URL changes**: Update `CODERRR_BACKEND` in `.env` and `.env.example`
- **New file operations**: Add to `FileOperations.execute()` switch statement
- **New test frameworks**: Add detection in `Agent.runTests()` testCommands array
- **UI changes**: Modify `src/ui.js`, never inline UI logic in other modules
- **Permission bypass**: Only for trusted operations, set `requirePermission: false`

## Architecture Decisions

**Why Two CLIs?**
- `coderrr-cli.js`: Original blessed TUI (rich terminal UI)
- `coderrr.js`: New commander CLI (simpler, better for scripting)
- Both use same backend and executor modules

**Why Separate Backend?**
- Decouples AI logic from CLI
- Enables multiple frontends (CLI, web, API)
- Easier to swap AI providers (just change backend)

**Why Permission Prompts?**
- Safety: Prevents accidental destructive operations
- Transparency: User sees exact commands before execution
- Trust: Like GitHub Copilot's model
