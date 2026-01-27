# Coderrr - AI Coding Agent CLI

[![npm version](https://badge.fury.io/js/coderrr-cli.svg)](https://www.npmjs.com/package/coderrr-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D16.0.0-brightgreen)](https://nodejs.org/)
[![GitHub issues](https://img.shields.io/github/issues/Akash-nath29/Coderrr)](https://github.com/Akash-nath29/Coderrr/issues)
[![GitHub stars](https://img.shields.io/github/stars/Akash-nath29/Coderrr)](https://github.com/Akash-nath29/Coderrr/stargazers)

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

## Table of Contents

- [See Coderrr in Action](#see-coderrr-in-action)
- [Features](#features)
  - [Core Capabilities](#core-capabilities)
  - [Advanced Features](#advanced-features)
- [Installation](#installation)
  - [Quick Start](#quick-start-zero-config)
  - [Advanced Configuration](#advanced-configuration-optional)
  - [Self-Hosting Backend](#self-hosting-backend-advanced)
- [Usage Examples](#usage-examples)
  - [Interactive Mode](#interactive-mode-default)
  - [Single Command Mode](#single-command-mode)
  - [Options](#options)
  - [Example Commands](#example-commands)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Codebase Intelligence](#codebase-intelligence)
- [Safety Features](#safety-features)
- [Supported Test Frameworks](#supported-test-frameworks)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

---

## See Coderrr in Action
![coderrr_output](https://github.com/user-attachments/assets/e3172bc8-6b42-42b9-aef1-39ebdd42153f)

---

## Features

### Core Capabilities

- **Task Analysis** - Breaks down complex requests into structured, actionable TODO items
- **File Operations** - Create, update, patch, delete, and read files with automatic directory creation
- **Command Execution** - Runs shell commands with mandatory permission prompts (GitHub Copilot-style)
- **Self-Healing** - Automatically retries failed steps with AI-generated fixes
- **Auto Testing** - Automatically detects and runs tests after completing tasks
- **Codebase Intelligence** - Scans and understands project structure for accurate file editing
- **Git Integration** - Automatic checkpoints and commits with easy rollback capability
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

## Minimal Quick Start (For First-Time Users)

If you just want to try Coderrr quickly without any configuration, follow these steps:

```bash
npm install -g coderrr-cli
cd C:\Coder\Coderrr
coderrr
### Quick Start (Zero Config!)

```bash
npm install -g coderrr-cli
```

That's it! The CLI comes pre-configured with a hosted backend.

## Prerequisites

To run Coderrr locally from source or contribute to the project, ensure you have:

- Node.js >= 16.x
- npm (comes with Node.js)
- Python >= 3.8
- pip
- Git

### Usage

Navigate to any folder and start coding:

```bash
cd my-project
coderrr
```

---

## Advanced Configuration (Optional)

By default, Coderrr uses our hosted backend at `https://coderrr-backend.vercel.app`.

If you want to use a custom backend (self-hosted or different provider), you have several options:

### Option 1: User Config File (Recommended)

Create `~/.coderrr/.env`:

**Windows:**
```powershell
mkdir $HOME\.coderrr
echo CODERRR_BACKEND=http://localhost:8000 > $HOME\.coderrr\.env
```

**Linux/Mac:**
```bash
mkdir -p ~/.coderrr
echo "CODERRR_BACKEND=http://localhost:8000" > ~/.coderrr/.env
```

### Option 2: System Environment Variable

**Windows:**
```powershell
setx CODERRR_BACKEND "http://localhost:8000"
```

**Linux/Mac:**
```bash
export CODERRR_BACKEND="http://localhost:8000"
# Add to ~/.bashrc or ~/.zshrc for persistence
```

### Option 3: Command Line Flag

```bash
coderrr --backend http://localhost:8000
```

---

## Self-Hosting Backend (Advanced)

Most users won't need this! But if you want to run your own backend for privacy or customization, see our [Self-Hosting Guide](./docs/SELF_HOSTING.md).

---

## Usage Examples

### Interactive Mode (Default)

Navigate to your project and start the agent:

```bash
cd my-project
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

- `-b, --backend <url>` - Override the default backend URL
- `-d, --dir <path>` - Working directory (default: current directory)
- `--no-auto-test` - Disable automatic test running
- `--no-auto-retry` - Disable automatic retry/self-healing on errors
- `--max-retries <number>` - Maximum retry attempts per failed step (default: 2)
- `--auto-commit` - Enable git checkpoints and auto-commit (opt-in)

**Default Backend:** Uses hosted backend at `https://coderrr-backend.vercel.app`

**Self-Healing:** When a step fails, Coderrr automatically analyzes the error and attempts to fix it up to 2 times before giving up.

**Git Integration:** With `--auto-commit` flag, Coderrr creates safety checkpoints before operations and auto-commits successful changes. Use `coderrr rollback` to undo changes.

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

# With git safety (auto-commit enabled)
coderrr --auto-commit exec "Create user authentication system"

# Rollback changes
coderrr rollback

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

## 📁 Project Structure

The Coderrr repository follows a clean and modular structure to improve
maintainability, scalability, and contributor onboarding.

```text
Coderrr/
├── bin/            # CLI entry points (modern CLI & legacy TUI)
├── src/            # Core agent logic, file operations, execution & UI
├── backend/        # FastAPI backend for AI processing
├── docs/           # Detailed documentation (architecture, API, guides)
├── examples/       # Example usage and demo projects
├── test/           # General test files
├── tests/unit/     # Unit tests for core components
├── .github/        # GitHub Actions, CI/CD workflows, templates
├── package.json    # Node.js dependencies and CLI metadata
├── README.md       # Project overview and usage guide
└── LICENSE         # MIT license

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

### Backend (FastAPI)

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
## Local Development Setup (For Contributors)

This section explains how to run Coderrr locally from source for development or contributions.

### 1. Clone the Repository

```bash
git clone https://github.com/Akash-nath29/Coderrr.git
cd Coderrr
```
### 2. Backend Setup
You can run the backend using Docker (recommended) or set it up manually.

#### Option A: Docker (Recommended)

```bash
docker compose up --build
```
The backend will be started at `http://localhost:5000` with hot-reloading enabled.

#### Option B: Manual Setup (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Run the backend server:
```bash
uvicorn main:app --reload --port 5000
```
Backend will be available at:
```bash
http://localhost:5000
```
### 3. CLI Setup (Node.js)
From the project root:
```bash
npm install
npm link
```
This allows you to run the local CLI using:
```bash
coderrr
```
### 4. Configure CLI to Use Local Backend
Create a user config file:
```bash
mkdir -p ~/.coderrr
echo "CODERRR_BACKEND=http://localhost:5000" > ~/.coderrr/.env
```
Or run directly:
```bash
coderrr --backend http://localhost:5000
```
### 5. Verify Local Setup
```bash
cd any-project
coderrr
```

---
## Troubleshooting

### Backend not reachable
- Ensure FastAPI is running on port 5000
- Check `CODERRR_BACKEND` value

### `coderrr` command not found
- Run `npm link` again
- Restart terminal

### Python dependency errors
- Ensure virtual environment is activated
- Re-run `pip install -r requirements.txt`   

---

## Contributing

Before contributing, please review the **Project Structure** section above to understand where new code, tests, or documentation should be added.


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
