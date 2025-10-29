# 🤖 Coderrr - AI Coding Agent CLI

**Coderrr** is an AI-powered coding agent that works like Claude Code but runs on your system! It analyzes tasks, creates TODO lists, performs file operations, and executes commands with your permission.

## ✨ Features

- 🎯 **Task Analysis** - Breaks down requests into actionable TODO items
- 📝 **File Operations** - Create, update, patch, delete, and read files
- 💻 **Command Execution** - Runs shell commands with permission prompts (like GitHub Copilot)
- 🧪 **Auto Testing** - Automatically detects and runs tests after completing tasks
- 🔍 **Codebase Scanner** - Automatically scans and understands your project structure for accurate file editing
- 🎨 **Beautiful CLI** - Clean, colorful interface with progress indicators
- 🔄 **Interactive Mode** - Continuous conversation loop for iterative development

## 🚀 Installation

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
pip install -r requirements.txt
```

3. Create `.env` file with your API keys:
```env
GITHUB_TOKEN=your_github_token_here
# OR
MISTRAL_API_KEY=your_mistral_key_here

# Optional: customize backend
MISTRAL_ENDPOINT=https://models.github.ai/inference
MISTRAL_MODEL=mistral-ai/Mistral-Large-2411
CODERRR_BACKEND=http://localhost:5000
```

4. Start the backend server:
```bash
python -m uvicorn main:app --reload --port 8000
```

Or use npm script:
```bash
npm run start:backend
```

## 📖 Usage

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

## 🎯 Example Commands

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
coderrr start --backend http://my-backend:8000

# Different working directory
coderrr start --dir /path/to/project
```

## 🏗️ How It Works

1. **User Input** - You provide a coding task or request
2. **AI Analysis** - The backend LLM analyzes and creates a structured plan
3. **TODO Generation** - Tasks are broken down into actionable steps
4. **Execution** - The agent executes each step:
   - File operations (create, update, patch, delete)
   - Command execution (with permission prompts)
5. **Testing** - Automatically runs tests if a test framework is detected
6. **Completion** - Shows summary and stats

## 🛠️ Architecture

```
Coderrr/
├── bin/
│   └── coderrr.js           # CLI entry point
├── src/
│   ├── agent.js             # Core agent logic
│   ├── fileOps.js           # File operations
│   ├── executor.js          # Command executor
│   ├── todoManager.js       # TODO tracking
│   └── ui.js                # UI utilities
├── main.py                  # FastAPI backend
├── package.json
└── requirements.txt
```

## � Codebase Awareness

Coderrr includes an intelligent **Codebase Scanner** that:

- **Automatically scans** your project on first request
- **Remembers** all existing files and their locations
- **Prevents** filename mismatches when editing existing code
- **Caches** results for fast subsequent requests
- **Ignores** common folders like `node_modules`, `env`, `__pycache__`

This means when you ask to "edit the agent file", it knows you mean `src/agent.js` not `agent.py` or `agentController.js`.

[Read more about Codebase Scanner](./CODEBASE_SCANNER.md)

## �🔒 Safety Features

- **Permission Prompts** - All commands require user confirmation before execution
- **Diff Preview** - See changes before files are modified
- **Step-by-step** - Each action is executed individually with feedback
- **Error Handling** - Graceful error handling with options to continue or stop

## 🧪 Supported Test Frameworks

Coderrr automatically detects and runs tests for:

- **JavaScript/TypeScript** - npm test
- **Python** - pytest
- **Go** - go test
- **Rust** - cargo test
- **Java** - Maven (mvn test) or Gradle (gradle test)

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

Inspired by:
- Claude Code (Anthropic)
- GitHub Copilot CLI
- Cursor AI

---

**Made with ❤️ by developers, for developers**
