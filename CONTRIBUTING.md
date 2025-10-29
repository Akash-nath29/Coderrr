# Contributing to Coderrr

First off, thank you for considering contributing to Coderrr! 🎉

## Code of Conduct

This project and everyone participating in it is governed by our commitment to providing a welcoming and inspiring community for all.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots if possible**
* **Include your environment details** (OS, Node.js version, Python version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and explain the behavior you expected to see**
* **Explain why this enhancement would be useful**

### Pull Requests

The project follows a strict branching workflow to maintain code quality:

**Branch Structure:**
- `main` - Production-ready code (protected)
- `dev` - Development branch for integration
- `feature/*` - Feature branches for new work

**Workflow:**
1. Feature branches merge to `dev`
2. `dev` merges to `main` after testing
3. **Direct feature → main PRs are blocked by CI**

**Creating a Pull Request:**

1. **Create a feature branch from `dev`:**
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

3. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create PR to `dev` branch** (NOT to `main`)
   - Go to GitHub and create a Pull Request
   - **Base branch: `dev`**
   - **Compare branch: `feature/your-feature-name`**

5. **Wait for CI tests to pass:**
   - All tests run automatically on PR
   - Tests run in development environment
   - Fix any failures before requesting review

6. **After merge to `dev`:**
   - Maintainers will create `dev` → `main` PR
   - Production tests run before merge to `main`

**PR Requirements:**
* Fill in the required template
* Follow the JavaScript and Python style guides
* Include thoughtful tests
* Update documentation as needed
* End all files with a newline
* All CI checks must pass

## Development Setup

### Prerequisites

* Node.js 16+ and npm
* Python 3.8+
* Git

### Setup Instructions

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/coderrr.git
   cd coderrr
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Set up Python virtual environment**
   ```bash
   python -m venv env
   # On Windows:
   .\env\Scripts\Activate.ps1
   # On Linux/Mac:
   source env/bin/activate
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Create your `.env` file**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Link the CLI for local development**
   ```bash
   npm link
   ```

7. **Create your feature branch from `dev`**
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

### Running Tests

```bash
# Run all tests
npm test

# Run specific test
node test/test-scanner.js
node test/test-agent-scanner.js
```

### Code Structure

```
coderrr/
├── src/              # Core Node.js modules
├── bin/              # CLI entry points
├── backend/          # Python FastAPI backend
│   ├── main.py      # Backend server
│   └── requirements.txt
├── test/             # Test files
├── docs/             # Documentation
├── examples/         # Usage examples
└── .github/          # GitHub workflows and templates
```

## Style Guides

### JavaScript Style Guide

* Use 2 spaces for indentation
* Use semicolons
* Use single quotes for strings
* Use meaningful variable names
* Add JSDoc comments for functions
* Follow existing code patterns

### Python Style Guide

* Follow PEP 8
* Use 4 spaces for indentation
* Use type hints where appropriate
* Add docstrings to functions and classes

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Use conventional commit format (feat, fix, docs, style, refactor, test, chore)

**Commit Prefixes:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, semicolons, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add codebase scanner feature

- Implement automatic project scanning
- Cache results for performance
- Add tests for scanner functionality

Closes #42
```

## Project Architecture

### Backend (Python/FastAPI)

The backend (`backend/main.py`) handles:
- AI model communication (Mistral/GitHub Models)
- Request/response processing
- JSON schema enforcement

### Frontend (Node.js)

The CLI (`src/`) handles:
- User interaction
- File operations
- Command execution with permission
- TODO list management
- Auto-testing

### Key Design Decisions

1. **Separation of Concerns**: Backend handles AI, frontend handles file system
2. **Permission-Based Execution**: All commands require user approval
3. **Codebase Awareness**: Scanner provides project context to AI
4. **Modular Architecture**: Each feature is a separate module
5. **Strict Branching Model**: `feature` → `dev` → `main` workflow enforced by CI

## Testing Guidelines

* Write tests for new features
* Ensure existing tests pass
* Test both success and failure cases
* Include integration tests for major features

## Documentation

* Update README.md for user-facing changes
* Update .github/copilot-instructions.md for architecture changes
* Add JSDoc comments to new functions
* Create examples for new features

## Review Process

1. **Create a feature branch from `dev`:**
   ```bash
   git checkout dev
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following style guides
   - Add/update tests
   - Update documentation

3. **Test locally:**
   ```bash
   npm test
   node test/test-scanner.js
   ```

4. **Commit with conventional format:**
   ```bash
   git commit -m "feat: your feature description"
   ```

5. **Push and create PR to `dev`:**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Create PR on GitHub: `feature/your-feature-name` → `dev`

6. **CI/CD Automated Checks:**
   - Branch workflow validation (blocks feature → main)
   - Node.js tests (3 OS × 3 versions = 9 jobs)
   - Python tests (3 OS × 4 versions = 12 jobs)
   - Integration tests
   - Linting & security audits
   - Environment: Development

7. **Code Review:**
   - Respond to review feedback
   - Make requested changes
   - Re-push to update PR

8. **After approval and merge to `dev`:**
   - Maintainers will handle `dev` → `main` PR
   - Production environment tests run
   - Deployment to production

9. **Celebrate when merged!** 🎉

## Recognition

Contributors will be added to:
- README.md Contributors section
- GitHub contributors page
- Release notes

## Questions?

Feel free to:
- Open an issue with the "question" label
- Start a discussion in GitHub Discussions
- Reach out to maintainers

Thank you for contributing! 🚀
