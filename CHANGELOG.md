# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-07-30

Complete rewrite. Coderrr is now a single Python CLI distributed on PyPI as
`coderrr`. The npm package `coderrr-cli` and the hosted backend are retired.
See [docs/V2-MIGRATION.md](docs/V2-MIGRATION.md).

### Added

- **Spec-driven development.** Every request produces `requirements.md`,
  `design.md` and `tasks.md` in `.coderrr/specs/NNN-slug/`. The plan is shown and
  approved before anything is modified. Specs double as cross-session memory and
  are meant to be committed.
- **Two-mode agent.** Write tools are absent from the model's tool list during
  planning and unlocked only by approval — enforced structurally, not by prompt.
- **Real agent loop.** The model reads, acts, observes tool results, and
  iterates, replacing v1's blind up-front plan generation.
- **Five providers over plain HTTP** — Ollama (default), Anthropic, OpenAI,
  Google, OpenRouter. No provider SDKs required.
- **Sandboxed execution.** `run_in_sandbox` replaces `run_command`: a scratch
  copy of the project by default, a container when Docker is available. The
  active tier is always reported.
- **Deterministic workspace containment** (`policy/paths.py`), with symlink
  resolution and property-based test coverage.
- **LLM write verification**, configurable via `[verify]` — including
  `[verify].temperature`, which defaults to `0.3` rather than `0.0` so that a
  weak verifier's false rejection is not reproduced identically on every retry.
- **Ephemeral skills** — markdown guidance fetched on demand, integrity-checked,
  deleted after use.
- **Offline test suite.** A scripted fake provider drives the agent loop; adapters
  are tested against recorded SSE fixtures.

### Changed

- API keys stay on your machine and go straight to your provider. Nothing is
  proxied through a server.
- Credentials resolve from environment → OS keyring → `~/.coderrr/config.toml`,
  written mode `0600` (was `0644`).
- `edit_file` requires an exact, unique match. The three fuzzy-matching fallbacks
  are gone — with a real loop the model reads before editing.
- `.coderrr/` now separates committed `specs/` from gitignored `cache/` and
  `session/`.
- CI quality gates are blocking. v1 marked every lint and security check
  `continue-on-error`.

### Removed

- Node.js CLI, `bin/`, and all `src/*.js` modules
- Hosted FastAPI backend (`backend/`) and its Vercel deployment
- `run_command` — arbitrary shell against the working tree
- Auto-commit and `git add .` behaviour; version control is yours
- Recipes and insights subsystems
- v1 skills that shipped executable Python tools

### Fixed

- Windows consoles that cannot encode the status glyphs no longer take the CLI
  down. cp1252 and cp437 reject most of the icon set, which made every command
  raise `UnicodeEncodeError`; icons now fall back to ASCII, and unencodable
  model output — an arrow in a spec, an em dash in a summary — prints as `?`
  rather than aborting the command partway through.
- Provider errors that stringify to nothing now name the exception class instead
  of reporting an empty `request failed:`. Read and connect timeouts were the
  common case.
- Sandbox timeouts clean up the subprocess tree on Windows.

Issues found in the v1 audit that this rewrite closes: unconfirmed file writes,
absent path containment, shell injection in the skill runner and git commit
messages, backend SSRF and open-proxy abuse, API keys transiting a third party,
command steps reporting success before completion, predictable temp-file paths,
and PID-based termination of unrelated processes.

---

## [1.1.1] and earlier

### Added
- Codebase scanner for intelligent file editing
- Auto-scan on first request with 1-minute caching
- File search by pattern functionality
- Comprehensive test suite for scanner
- Environment-based backend URL configuration
- Organized project structure with proper test folder
- Git integration with auto-commit safety net
- `--auto-commit` flag for automatic git checkpoints and commits
- `coderrr rollback` command for reverting Coderrr changes
- Safety checkpoint system before AI operations

### Changed
- Backend URL now centralized in `.env` as `CODERRR_BACKEND`
- Removed hardcoded URLs from all source files
- Cleaned up documentation files
- Improved error messages for backend connection

### Fixed
- Backend port mismatch (8000 vs 5000)
- Filename mismatch issues with AI agent
- Missing dotenv configuration in test files

## [1.0.0] - 2025-10-30

### Added
- Initial release
- AI-powered coding agent with task analysis
- File operations (create, update, patch, delete, read)
- Command execution with user permission prompts
- Auto-testing support (npm, pytest, go, rust, java)
- Beautiful CLI with progress indicators
- Interactive and single-command modes
- TODO list generation and tracking
- Dual CLI implementations (commander and blessed TUI)
- FastAPI backend with Mistral AI integration
- GitHub Models support
- Comprehensive documentation

### Features
- 🎯 Task breakdown into actionable TODO items
- 📝 Smart file operations with automatic directory creation
- 💻 Safe command execution (like GitHub Copilot)
- 🧪 Automatic test detection and execution
- 🎨 Colorful CLI with spinners and status indicators
- 🔄 Continuous conversation mode

### Technical
- Node.js 16+ frontend
- Python 3.8+ FastAPI backend
- Mistral AI / GitHub Models integration
- JSON-based plan execution
- Modular architecture
- Permission-based safety model
