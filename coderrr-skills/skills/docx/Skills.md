---
name: docx
description: Create, edit, and analyze Word documents with professional formatting. Use this skill when the user asks to create Word documents, add content to DOCX files, extract text from Word files, work with tables, headers, footers, or analyze document structure. Supports tracked changes, comments, and advanced formatting.
---

This skill provides comprehensive Word document manipulation using python-docx. It handles document creation, content extraction, formatting, and structural analysis.

The user provides document requirements or existing files to process. They may want to create new documents, modify existing ones, or extract information from Word files.

## Approach

Before invoking tools, understand the document operation:
- **Create new**: Use `create_docx` with content structure
- **Extract content**: Use `read_docx` to get text, tables, or metadata
- **Modify existing**: Use `edit_docx` to add or update content
- **Analyze structure**: Use `analyze_docx` for document breakdown

## Tools

### create_docx

Creates a new Word document with specified content and formatting.

```bash
python tools/create_docx.py --output <path> --title <title> [--content <json>] [--template <path>]
```

**Arguments:**
- `--output` (required): Output file path (.docx)
- `--title` (required): Document title
- `--content` (optional): JSON structure defining document content
- `--template` (optional): Path to template document

**Content JSON Structure:**
```json
{
  "sections": [
    {"type": "heading", "level": 1, "text": "Main Title"},
    {"type": "paragraph", "text": "Body text here..."},
    {"type": "heading", "level": 2, "text": "Subsection"},
    {"type": "list", "items": ["Item 1", "Item 2", "Item 3"], "ordered": false},
    {"type": "table", "headers": ["Col1", "Col2"], "rows": [["A", "B"], ["C", "D"]]}
  ]
}
```

**When to use:**
- Generating reports
- Creating structured documents
- Building documents from templates
- Automating document workflows

---

### read_docx

Extracts content from existing Word documents.

```bash
python tools/read_docx.py --file <path> [--format <text|json|markdown>] [--include-tables]
```

**Arguments:**
- `--file` (required): Path to Word document
- `--format` (optional): Output format - `text`, `json`, or `markdown` (default: text)
- `--include-tables` (optional): Include table data in output

**Output:** Document content in specified format.

**When to use:**
- Extracting text for analysis
- Converting Word to other formats
- Reading document structure
- Processing uploaded documents

---

### edit_docx

Modifies an existing Word document.

```bash
python tools/edit_docx.py --file <path> --output <path> --operations <json>
```

**Arguments:**
- `--file` (required): Input Word document
- `--output` (required): Output file path
- `--operations` (required): JSON array of edit operations

**Operations JSON:**
```json
[
  {"action": "append_paragraph", "text": "New paragraph"},
  {"action": "replace_text", "find": "old text", "replace": "new text"},
  {"action": "add_heading", "text": "New Section", "level": 2},
  {"action": "insert_table", "headers": ["A", "B"], "rows": [["1", "2"]]}
]
```

**When to use:**
- Adding content to existing documents
- Find and replace operations
- Appending sections
- Batch document updates

---

### analyze_docx

Analyzes document structure and provides detailed metadata.

```bash
python tools/analyze_docx.py --file <path>
```

**Arguments:**
- `--file` (required): Path to Word document

**Output:** JSON with word count, paragraph count, heading structure, table count, styles used, and more.

**When to use:**
- Auditing document structure
- Checking document properties
- Understanding document composition
- Quality assurance checks

## Common Patterns

### Create a Simple Report
```bash
python tools/create_docx.py --output report.docx --title "Monthly Report" --content '{"sections": [{"type": "heading", "level": 1, "text": "Summary"}, {"type": "paragraph", "text": "This month we achieved..."}]}'
```

### Extract All Text
```bash
python tools/read_docx.py --file document.docx --format text
```

### Add Section to Existing Document
```bash
python tools/edit_docx.py --file original.docx --output updated.docx --operations '[{"action": "append_paragraph", "text": "Additional content here"}]'
```

### Get Document Statistics
```bash
python tools/analyze_docx.py --file document.docx
```

## Best Practices

1. **Use templates** - Start from well-formatted templates for consistent styling
2. **Structure content as JSON** - Makes complex documents reproducible
3. **Preserve originals** - Always output to new file when editing
4. **Check analysis first** - Understand document structure before modifying
5. **Use markdown format** - Great for further processing or display

## Dependencies

Requires `python-docx>=0.8.11`. Automatically installed with the skill.
