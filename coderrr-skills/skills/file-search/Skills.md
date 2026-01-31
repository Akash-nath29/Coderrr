---
name: file-search
description: Find files and search content within your filesystem. Use this skill when the user asks to find files by name or pattern, search for text within files (grep-like operations), get directory statistics, count files, or analyze folder structure. Handles glob patterns, regex search, and comprehensive file system analysis.
---

This skill provides powerful filesystem search and analysis capabilities using only Python's standard library. It handles file discovery, content searching, and statistical analysis of directories.

The user provides a search query, file pattern, or directory path. They may want to find specific files, search for text patterns, or understand the structure of a codebase.

## Approach

Before invoking tools, understand the search intent:
- **Find files by name/pattern**: Use `find_files` with glob patterns
- **Search within file contents**: Use `search_content` with text or regex queries
- **Analyze directory structure**: Use `file_stats` for size, counts, and composition
- **Combined operations**: Chain tools for complex queries (e.g., find Python files, then search within them)

## Tools

### find_files

Recursively finds files and directories matching glob patterns.

```bash
python tools/find_files.py --pattern <glob> --path <directory> [--type <file|dir|all>]
```

**Arguments:**
- `--pattern` (required): Glob pattern to match (e.g., `*.py`, `**/*.json`, `test_*`)
- `--path` (required): Directory to search in
- `--type` (optional): Filter by type - `file`, `dir`, or `all` (default: all)

**Output:** JSON array of matching paths.

**When to use:**
- Finding all files of a certain type
- Locating configuration files
- Discovering test files or specific modules
- Listing directories matching a pattern

**Glob Pattern Guide:**
- `*` matches any characters in a single path segment
- `**` matches any characters across path segments (recursive)
- `?` matches a single character
- `[abc]` matches any character in brackets

---

### search_content

Searches for text patterns within files. Similar to grep but outputs structured JSON.

```bash
python tools/search_content.py --query <text> --path <file_or_dir> [--regex]
```

**Arguments:**
- `--query` (required): Text or regex pattern to search for
- `--path` (required): File or directory to search in
- `--regex` (optional): Treat query as a regular expression

**Output:** JSON array of matches with file, line number, and content.

**When to use:**
- Finding where a function or variable is used
- Locating TODO comments or specific strings
- Searching for import statements
- Finding configuration values

**Supported file types:** Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, Ruby, PHP, HTML, CSS, JSON, YAML, Markdown, and more.

---

### file_stats

Analyzes files and directories, providing comprehensive statistics.

```bash
python tools/file_stats.py --path <file_or_dir>
```

**Arguments:**
- `--path` (required): File or directory to analyze

**Output:** JSON with file counts, sizes, type breakdown, and largest files.

**When to use:**
- Understanding codebase composition
- Finding the largest files in a project
- Counting files by type
- Auditing directory structure

## Common Patterns

### Find All Python Files in Project
```bash
python tools/find_files.py --pattern "**/*.py" --path ./src --type file
```

### Search for Function Usage
```bash
python tools/search_content.py --query "def process_data" --path ./src
```

### Find Imports with Regex
```bash
python tools/search_content.py --query "^import\s+\w+" --path ./src --regex
```

### Get Project Statistics
```bash
python tools/file_stats.py --path ./my-project
```

### Find Only Directories
```bash
python tools/find_files.py --pattern "*test*" --path . --type dir
```

## Best Practices

1. **Use specific paths** - Narrow the search scope for faster results
2. **Leverage glob patterns** - `**/*.py` is more efficient than searching everything
3. **Use regex for complex patterns** - When simple text matching isn't enough
4. **Check file_stats first** - Understand the codebase before deep searching
5. **Combine tools** - Find files first, then search within specific ones

## Error Handling

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | - |
| 1 | Invalid path or pattern | Verify path exists and pattern syntax |
| 2 | Permission denied | Check file permissions |

## Dependencies

None - uses Python's standard library only (pathlib, os, re, json).
