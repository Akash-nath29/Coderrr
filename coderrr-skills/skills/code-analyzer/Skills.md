---
name: code-analyzer
description: Analyze code quality, structure, and maintainability. Use this skill when the user asks to lint code, count lines of code, find TODO/FIXME comments, analyze code structure, check for issues, or audit a codebase. Provides static analysis for Python and line counting for multiple languages.
---

This skill provides code quality analysis without external dependencies. It uses Python's AST module for static analysis and pattern matching for comment detection, supporting multiple programming languages for line counting.

The user provides code files or directories to analyze. They may want quality checks, metrics, or to find action items like TODOs scattered through the codebase.

## Approach

Before invoking tools, understand the analysis goal:
- **Quality check**: Use `lint_python` for syntax and import issues
- **Size metrics**: Use `count_lines` for comprehensive line statistics
- **Action items**: Use `find_todos` to locate TODO, FIXME, HACK markers
- **Full audit**: Run all three tools sequentially for complete picture

## Tools

### lint_python

Performs static analysis on Python files using the AST module. Detects syntax errors, unused imports, and provides code structure metrics.

```bash
python tools/lint_python.py --file <python_file>
```

**Arguments:**
- `--file` (required): Path to Python file to analyze

**Output:** JSON with errors, warnings, and info (function/class/import counts).

**What it detects:**
- Syntax errors (with line numbers)
- Unused imports
- Function and class counts
- Import analysis

**When to use:**
- Quick quality check before committing
- Finding unused imports to clean up
- Getting code structure overview
- Validating Python syntax

**Limitations:** Uses only stdlib AST, so it won't detect runtime errors, type issues, or complex linting rules that tools like flake8/pylint catch.

---

### count_lines

Counts lines of code with detailed breakdown by type (code, comments, blank) and language.

```bash
python tools/count_lines.py --path <file_or_dir>
```

**Arguments:**
- `--path` (required): File or directory to analyze

**Output:** JSON with summary totals and per-language breakdown.

**Supported languages:**
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)
- Go (`.go`)
- Rust (`.rs`)
- Ruby (`.rb`)
- PHP, Swift, Kotlin, Scala, C#

**When to use:**
- Estimating project size
- Comparing code vs comment ratios
- Understanding language distribution
- Tracking codebase growth

---

### find_todos

Finds TODO, FIXME, HACK, XXX, BUG, and NOTE comments throughout codebase.

```bash
python tools/find_todos.py --path <file_or_dir> [--types <comma_separated>]
```

**Arguments:**
- `--path` (required): File or directory to search
- `--types` (optional): Comma-separated marker types (default: `TODO,FIXME,HACK,XXX,BUG,NOTE`)

**Output:** JSON with count, breakdown by type, and list of all items with file/line/text.

**When to use:**
- Reviewing technical debt
- Finding incomplete implementations
- Tracking known issues in code
- Generating action item lists

## Common Patterns

### Quick Python File Check
```bash
python tools/lint_python.py --file ./main.py
```

### Full Directory Analysis
```bash
python tools/count_lines.py --path ./src
```

### Find Only Critical Items
```bash
python tools/find_todos.py --path ./src --types FIXME,BUG
```

### Complete Code Audit
```bash
# Run all three for comprehensive analysis
python tools/lint_python.py --file ./main.py
python tools/count_lines.py --path ./src
python tools/find_todos.py --path ./src
```

## Best Practices

1. **Run lint before commits** - Catch syntax errors and unused imports early
2. **Track line counts over time** - Monitor codebase growth
3. **Review TODOs regularly** - Don't let technical debt accumulate
4. **Focus on high-priority markers** - FIXME and BUG are usually more urgent than TODO
5. **Combine with file-search** - Find specific files first, then analyze them

## Interpreting Results

### lint_python Output
```json
{
  "file": "./main.py",
  "errors": [],                    // Syntax errors - must fix
  "warnings": [                    // Quality issues - should fix
    {"line": 1, "type": "unused_import", "message": "Unused import: os"}
  ],
  "info": {
    "functions": 5,                // Code structure overview
    "classes": 2,
    "imports": 8
  }
}
```

### count_lines Output
```json
{
  "summary": {
    "total_lines": 1500,
    "code_lines": 1100,           // Executable code
    "comment_lines": 200,          // Documentation
    "blank_lines": 200             // Formatting
  }
}
```

A healthy ratio is roughly 70-80% code, 10-20% comments, 10-15% blank lines.

## Error Handling

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | - |
| 1 | Invalid file path | Verify file exists |
| 2 | File parsing error | Check file encoding, syntax |

## Dependencies

None - uses Python's standard library only (ast, os, re, json).
