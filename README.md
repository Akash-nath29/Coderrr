# Coderrr - AI Coding Agent CLI

```
   ██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗ 
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝
  ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗
  ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

**Your friendly neighbourhood Open Source AI-Powered Coding Agent**

Coderrr is an AI-powered coding agent that analyzes tasks, creates actionable plans, performs file operations, and executes commands with user permission. Built for developers who want automated assistance without sacrificing control.

---

## Features

### Core Capabilities

- **Task Analysis** - Breaks down complex requests into structured, actionable TODO items
- **File Operations** - Create, update, patch, delete, and read files with automatic directory creation
- **Command Execution** - Runs shell commands with mandatory permission prompts (GitHub Copilot-style)
- **Auto Testing** - Automatically detects and runs tests after completing tasks
- **Codebase Intelligence** - Scans and understands project structure for accurate file editing
- **Interactive Mode** - Continuous conversation loop for iterative development
- **Beautiful CLI** - Clean interface with progress indicators and status updates

### Advanced Features

- **Codebase Scanner** - Automatic project awareness with 1-minute cache
- **Multi-Framework Support** - Works with Node.js, Python, Go, Rust, Java projects
- **Environment Configuration** - Flexible backend configuration via environment variables
- **Safety First** - Permission prompts for all destructive operations
- **Dual Architecture** - Python backend for AI, Node.js frontend for file operations

---

## Installation

### Prerequisites

- Node.js 16+ and npm
- Python 3.8+ (for the backend)

### Install globally via npm

```bash
npm install -g
```

Or link for development:

```bash
npm install
npm link
```

### Set up the backend

1. Activate Python virtual environment:
```powershell
.\env\Scripts\Activate.ps1
```

2. Install Python dependencies:
```bash
pip install -r backend/requirements.txt
```

3. Create `.env` file with your API keys:
```env
GITHUB_TOKEN=your_github_token_here
# OR
MISTRAL_API_KEY=your_mistral_key_here

# Optional: customize backend
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411
CODERRR_BACKEND=http://localhost:5000
TIMEOUT_MS=120000
```

4. Start the backend server:
```bash
cd backend
uvicorn main:app --reload --port 5000
```

Or from root directory:
```bash
npm run start:backend
```

---

## Usage

### Interactive Mode (Default)

Start the agent and chat with it:

```bash
coderrr
```

Or explicitly:

```bash
coderrr start
```

### Single Command Mode

Execute a single request and exit:

```bash
coderrr exec "Create a FastAPI endpoint for user authentication"
```

### Options

- `-b, --backend <url>` - Backend URL (reads from CODERRR_BACKEND env variable)
- `-d, --dir <path>` - Working directory (default: current directory)
- `--no-auto-test` - Disable automatic test running

---

## Example Commands

```bash
# Interactive mode
coderrr

# Create a new feature
coderrr exec "Add a REST API endpoint for creating blog posts"

# Refactor code
coderrr exec "Refactor the authentication module to use JWT tokens"

# Fix bugs
coderrr exec "Fix the database connection timeout issue"

# Write tests
coderrr exec "Add unit tests for the user service"

# Custom backend
coderrr start --backend http://my-backend:5000

# Different working directory
coderrr start --dir /path/to/project
```

---

## How It Works

1. **User Input** - You provide a coding task or request
2. **AI Analysis** - The backend LLM analyzes and creates a structured plan
3. **TODO Generation** - Tasks are broken down into actionable steps
4. **Execution** - The agent executes each step:
   - File operations (create, update, patch, delete)
   - Command execution (with permission prompts)
5. **Testing** - Automatically runs tests if a test framework is detected
6. **Completion** - Shows summary and execution statistics

---

## Architecture

```
Coderrr/
├── bin/
│   ├── coderrr.js           # Modern CLI (commander-based)
│   └── coderrr-cli.js       # Legacy TUI (blessed-based)
├── src/
│   ├── agent.js             # Core agent logic & orchestration
│   ├── fileOps.js           # File operations handler
│   ├── executor.js          # Command executor with permissions
│   ├── todoManager.js       # TODO tracking & visualization
│   ├── codebaseScanner.js   # Project structure scanner
│   └── ui.js                # UI utilities & components
├── backend/
│   ├── main.py              # FastAPI backend server
│   └── requirements.txt     # Python dependencies
├── test/                    # Test suite
├── docs/                    # Documentation
├── examples/                # Usage examples
├── .github/                 # CI/CD workflows
├── package.json
└── .env                     # Environment configuration
```

### Backend (Python/FastAPI)

Handles AI model communication, request processing, and JSON schema enforcement. Runs on port 5000 by default.

### Frontend (Node.js)

Manages user interaction, file operations, command execution, and project scanning. Provides both CLI and TUI interfaces.

---

## Codebase Intelligence

Coderrr includes an intelligent **Codebase Scanner** that:

- **Automatically scans** your project on first request
- **Remembers** all existing files and their locations
- **Prevents** filename mismatches when editing existing code
- **Caches** results for fast subsequent requests
- **Ignores** common folders like `node_modules`, `env`, `__pycache__`

This means when you ask to "edit the agent file", it knows you mean `src/agent.js` not `agent.py` or `agentController.js`.

**Learn more:** See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed architecture documentation.

---

## Safety Features

- **Permission Prompts** - All commands require user confirmation before execution
- **Diff Preview** - See changes before files are modified
- **Step-by-step Execution** - Each action is executed individually with feedback
- **Error Handling** - Graceful error handling with options to continue or stop
- **Git-Friendly** - Works best in Git repositories for easy rollback

---

## Supported Test Frameworks

Coderrr automatically detects and runs tests for:

- **JavaScript/TypeScript** - npm test
- **Python** - pytest
- **Go** - go test
- **Rust** - cargo test
- **Java** - Maven (mvn test) or Gradle (gradle test)

---

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](./CONTRIBUTING.md) before submitting pull requests.

### Branch Workflow

- `feature/*` → `dev` → `main`
- Direct feature to main PRs are blocked by CI
- All tests run on PRs to dev or main

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed development setup and guidelines.

---

## Documentation

- [Architecture](./docs/ARCHITECTURE.md) - System design and data flow
- [API Reference](./docs/API.md) - Complete API documentation
- [FAQ](./docs/FAQ.md) - Frequently asked questions
- [Deployment](./docs/DEPLOYMENT.md) - Production deployment guide
- [Examples](./examples/) - Usage examples and tutorials

---

## License

MIT License - see [LICENSE](./LICENSE) file for details.

---

## Acknowledgments

Inspired by:
- Claude Code (Anthropic)
- GitHub Copilot CLI
- Cursor AI

---

**Built by developers, for developers**
