---
name: pdf
description: Comprehensive PDF toolkit for document manipulation. Use this skill when the user asks to extract text from PDFs, create PDF documents, merge or split PDFs, extract tables from PDFs, work with PDF forms, or analyze PDF structure. Handles both text extraction and PDF generation.
---

This skill provides complete PDF manipulation capabilities using PyPDF2 and pdfplumber for reading, and reportlab for creation. It handles text extraction, document merging/splitting, and PDF generation.

The user provides PDF files to process or content to convert to PDF. They may want to extract information, combine documents, or create new PDFs.

## Approach

Before invoking tools, understand the PDF operation:
- **Extract text**: Use `extract_pdf` for text and table extraction
- **Create new PDF**: Use `create_pdf` to generate from content
- **Merge files**: Use `merge_pdf` to combine multiple PDFs
- **Split file**: Use `split_pdf` to separate pages
- **Get info**: Use `pdf_info` for metadata and structure

## Tools

### extract_pdf

Extracts text and optionally tables from PDF documents.

```bash
python tools/extract_pdf.py --file <path> [--pages <range>] [--tables] [--format <text|json>]
```

**Arguments:**
- `--file` (required): Path to PDF file
- `--pages` (optional): Page range (e.g., "1-5", "1,3,5", "all")
- `--tables` (optional): Extract tables as structured data
- `--format` (optional): Output format - `text` or `json` (default: text)

**Output:** Extracted text or JSON with text and tables.

**When to use:**
- Reading PDF content
- Extracting data from reports
- Processing scanned documents (with text layer)
- Getting tabular data from PDFs

---

### create_pdf

Creates PDF documents from content specification.

```bash
python tools/create_pdf.py --output <path> --content <json> [--title <title>]
```

**Arguments:**
- `--output` (required): Output PDF file path
- `--content` (required): JSON content specification
- `--title` (optional): Document title

**Content JSON Structure:**
```json
{
  "elements": [
    {"type": "heading", "text": "Title", "size": 24},
    {"type": "paragraph", "text": "Body text..."},
    {"type": "list", "items": ["Item 1", "Item 2"]},
    {"type": "table", "headers": ["A", "B"], "rows": [["1", "2"]]},
    {"type": "page_break"}
  ]
}
```

**When to use:**
- Generating reports
- Creating invoices
- Building PDF documents programmatically
- Converting structured data to PDF

---

### merge_pdf

Combines multiple PDF files into one.

```bash
python tools/merge_pdf.py --files <path1> <path2> ... --output <path>
```

**Arguments:**
- `--files` (required): List of PDF files to merge
- `--output` (required): Output merged PDF path

**When to use:**
- Combining report sections
- Merging scanned documents
- Creating document packages
- Assembling multi-part documents

---

### split_pdf

Splits a PDF into separate files.

```bash
python tools/split_pdf.py --file <path> --output-dir <dir> [--pages <spec>]
```

**Arguments:**
- `--file` (required): PDF file to split
- `--output-dir` (required): Directory for output files
- `--pages` (optional): Page specification (e.g., "1-3,4-6" or "each" for individual pages)

**When to use:**
- Extracting specific pages
- Breaking up large documents
- Creating individual page files
- Separating document sections

---

### pdf_info

Gets PDF metadata and structure information.

```bash
python tools/pdf_info.py --file <path>
```

**Arguments:**
- `--file` (required): PDF file to analyze

**Output:** JSON with page count, metadata, file size, and structure info.

**When to use:**
- Checking PDF properties
- Getting page counts
- Verifying PDF integrity
- Understanding document structure

## Common Patterns

### Extract All Text
```bash
python tools/extract_pdf.py --file document.pdf --format text
```

### Extract Specific Pages
```bash
python tools/extract_pdf.py --file report.pdf --pages "1-5"
```

### Extract Tables as JSON
```bash
python tools/extract_pdf.py --file data.pdf --tables --format json
```

### Merge Multiple PDFs
```bash
python tools/merge_pdf.py --files part1.pdf part2.pdf part3.pdf --output combined.pdf
```

### Split Into Individual Pages
```bash
python tools/split_pdf.py --file document.pdf --output-dir ./pages --pages each
```

### Create Simple PDF
```bash
python tools/create_pdf.py --output report.pdf --title "Report" --content '{"elements": [{"type": "heading", "text": "Summary"}, {"type": "paragraph", "text": "Content here..."}]}'
```

## Best Practices

1. **Check pdf_info first** - Understand document structure before processing
2. **Use page ranges** - Don't extract everything if you only need specific pages
3. **Handle scanned PDFs** - Some PDFs are images without text layers
4. **Preserve originals** - Merge/split create new files, don't modify originals
5. **Use tables flag** - Better structured output for tabular data

## Dependencies

Requires:
- `PyPDF2>=3.0.0` - PDF reading and manipulation
- `pdfplumber>=0.9.0` - Advanced text and table extraction
- `reportlab>=4.0.0` - PDF creation

Automatically installed with the skill.
