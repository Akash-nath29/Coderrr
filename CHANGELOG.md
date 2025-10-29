# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Codebase scanner for intelligent file editing
- Auto-scan on first request with 1-minute caching
- File search by pattern functionality
- Comprehensive test suite for scanner
- Environment-based backend URL configuration
- Organized project structure with proper test folder

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
