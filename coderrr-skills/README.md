# Coderrr Skills Marketplace

[![Skills](https://img.shields.io/badge/skills-15-blue)](https://github.com/Akash-nath29/coderrr-skills)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)

A marketplace of installable skills for [Coderrr CLI](https://github.com/Akash-nath29/coderrr) - the AI-powered coding assistant.

## 🚀 Quick Start

Install skills directly from Coderrr CLI:

```bash
# Install a skill
coderrr install web-scraper

# List installed skills
coderrr skills

# Search for skills
coderrr search pdf
```

## 📦 Available Skills

| Skill | Description | Tools |
|-------|-------------|-------|
| **web-scraper** | Fetch, parse, and extract content from web pages | `fetch_page`, `extract_text` |
| **file-search** | Find files and search content within your filesystem | `find_files`, `search_content`, `file_stats` |
| **code-analyzer** | Analyze code quality, structure, and maintainability | `lint_python`, `count_lines`, `find_todos` |
| **json-tools** | Format, query, and validate JSON data | `format_json`, `query_json`, `validate_json` |
| **api-client** | Make HTTP requests and work with API responses | `http_get`, `http_post`, `parse_response` |
| **docx** | Create, edit, and analyze Word documents | `create_docx`, `read_docx`, `edit_docx`, `analyze_docx` |
| **pdf** | Comprehensive PDF toolkit for document manipulation | `extract_pdf`, `create_pdf`, `merge_pdf`, `split_pdf`, `pdf_info` |
| **pptx** | Create, edit, and analyze PowerPoint presentations | `create_pptx`, `read_pptx`, `edit_pptx`, `analyze_pptx` |
| **xlsx** | Create and manipulate Excel spreadsheets with formulas | `create_xlsx`, `read_xlsx`, `edit_xlsx`, `analyze_xlsx` |
| **skill-creator** | Interactive tool for building new custom skills | `init_skill`, `add_tool`, `finalize_skill`, `list_templates` |
| **artifacts-builder** | Build complex HTML artifacts using React and Tailwind | `scaffold_artifact`, `add_component`, `build_artifact`, `preview_artifact` |
| **mcp-builder** | Guide for creating high-quality MCP servers | `init_mcp`, `add_mcp_tool`, `validate_mcp` |
| **webapp-testing** | Test web applications using Playwright automation | `start_browser`, `navigate`, `interact`, `verify`, `screenshot` |
| **brand-guidelines** | Apply brand colors, typography, and design tokens | `set_brand`, `generate_palette`, `export_tokens` |
| **internal-comms** | Write status reports, newsletters, and announcements | `status_report`, `newsletter`, `announcement`, `meeting_summary` |

## 🎯 Skills by Category

### 📄 Document Processing
- **docx** - Word document handling
- **pdf** - PDF manipulation
- **pptx** - PowerPoint presentations
- **xlsx** - Excel spreadsheets

### 🌐 Web & API
- **web-scraper** - Web page scraping
- **api-client** - HTTP requests
- **webapp-testing** - Browser automation

### 💻 Development
- **code-analyzer** - Code quality analysis
- **json-tools** - JSON manipulation
- **file-search** - File system operations
- **skill-creator** - Skill development
- **mcp-builder** - MCP server creation

### 🎨 Design & Communication
- **artifacts-builder** - HTML/React components
- **brand-guidelines** - Design tokens
- **internal-comms** - Team communications

## 📁 Repository Structure

```
coderrr-skills/
├── registry.json          # Central skill registry
├── README.md              # This file
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # MIT License
└── skills/
    ├── web-scraper/
    │   ├── Skills.md      # Skill documentation
    │   ├── requirements.txt
    │   └── tools/
    │       ├── fetch_page.py
    │       └── extract_text.py
    ├── docx/
    │   ├── Skills.md
    │   ├── requirements.txt
    │   └── tools/
    │       ├── create_docx.py
    │       ├── read_docx.py
    │       ├── edit_docx.py
    │       └── analyze_docx.py
    └── ... (other skills)
```

## 🛠️ Creating New Skills

1. Fork this repository
2. Create a new skill directory under `skills/`
3. Add required files:
   - `Skills.md` - Documentation with YAML frontmatter
   - `tools/` - Python tool scripts
   - `requirements.txt` - Dependencies (if any)
4. Update `registry.json`
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Skill Structure

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

Detailed documentation for the AI agent...
```

## 📖 Skills.md Format

Each skill's `Skills.md` follows this structure:

1. **YAML Frontmatter** - `name` and `description`
2. **Approach** - When to use which tool
3. **Tools** - Detailed documentation for each tool
4. **Common Patterns** - Usage examples
5. **Best Practices** - Guidelines for effective use
6. **Dependencies** - Required packages

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting.

### Ideas for New Skills
- Database connectors
- Cloud service integrations
- Image manipulation
- Markdown processing
- Git automation

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Coderrr CLI](https://github.com/Akash-nath29/coderrr)
- [Documentation](https://github.com/Akash-nath29/coderrr#readme)
- [Issue Tracker](https://github.com/Akash-nath29/coderrr-skills/issues)
