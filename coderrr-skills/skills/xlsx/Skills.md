---
name: xlsx
description: Create and manipulate Excel spreadsheets with formulas and formatting. Use this skill when the user asks to create Excel files, read spreadsheet data, update cells, add formulas, format worksheets, or analyze Excel structure. Supports multiple sheets, cell formatting, and Excel formulas.
---

This skill provides comprehensive Excel manipulation using openpyxl. It handles spreadsheet creation, data reading/writing, formula insertion, and formatting.

The user provides spreadsheet requirements or existing files to process. They may want to create reports, read data, update values, or apply formatting.

## Approach

Before invoking tools, understand the spreadsheet task:
- **Create new**: Use `create_xlsx` with data and structure
- **Read data**: Use `read_xlsx` to extract cell values
- **Modify cells**: Use `edit_xlsx` to update content
- **Analyze structure**: Use `analyze_xlsx` for workbook overview

## Tools

### create_xlsx

Creates Excel workbooks with data, formulas, and formatting.

```bash
python tools/create_xlsx.py --output <path> --sheets <json>
```

**Arguments:**
- `--output` (required): Output file path (.xlsx)
- `--sheets` (required): JSON specification of sheets and data

**Sheets JSON Structure:**
```json
[
  {
    "name": "Sheet1",
    "headers": ["Name", "Value", "Total"],
    "data": [
      ["Item A", 100, "=B2*1.1"],
      ["Item B", 200, "=B3*1.1"]
    ],
    "column_widths": {"A": 20, "B": 15, "C": 15}
  }
]
```

**Formula Support:**
- Start cell values with `=` for formulas
- Standard Excel formulas: `=SUM(A1:A10)`, `=AVERAGE(B:B)`, `=IF(A1>0,"Yes","No")`

**When to use:**
- Generating data reports
- Creating templates
- Building formatted spreadsheets
- Automating Excel file creation

---

### read_xlsx

Reads data from Excel files.

```bash
python tools/read_xlsx.py --file <path> [--sheet <name>] [--range <A1:Z100>] [--format <json|csv|text>]
```

**Arguments:**
- `--file` (required): Path to Excel file
- `--sheet` (optional): Sheet name (default: active sheet)
- `--range` (optional): Cell range to read (e.g., "A1:D10")
- `--format` (optional): Output format (default: json)

**When to use:**
- Extracting spreadsheet data
- Reading specific ranges
- Converting Excel to other formats
- Processing uploaded files

---

### edit_xlsx

Modifies existing Excel files.

```bash
python tools/edit_xlsx.py --file <path> --output <path> --operations <json>
```

**Arguments:**
- `--file` (required): Input Excel file
- `--output` (required): Output file path
- `--operations` (required): JSON array of operations

**Operations:**
```json
[
  {"action": "set_cell", "sheet": "Sheet1", "cell": "A1", "value": "Updated"},
  {"action": "set_range", "sheet": "Sheet1", "start": "A2", "data": [["Row1"], ["Row2"]]},
  {"action": "add_formula", "sheet": "Sheet1", "cell": "C10", "formula": "=SUM(C1:C9)"},
  {"action": "add_sheet", "name": "NewSheet"},
  {"action": "format_cell", "sheet": "Sheet1", "cell": "A1", "bold": true, "bg_color": "FFFF00"}
]
```

**When to use:**
- Updating cell values
- Adding formulas
- Applying formatting
- Modifying structure

---

### analyze_xlsx

Analyzes workbook structure and statistics.

```bash
python tools/analyze_xlsx.py --file <path>
```

**Output:** JSON with sheet names, dimensions, cell counts, and formula locations.

**When to use:**
- Understanding workbook structure
- Getting sheet dimensions
- Finding formulas
- Auditing spreadsheets

## Common Patterns

### Create Simple Spreadsheet
```bash
python tools/create_xlsx.py --output data.xlsx --sheets '[{"name": "Data", "headers": ["ID", "Name", "Value"], "data": [[1, "Item A", 100], [2, "Item B", 200]]}]'
```

### Read Entire Sheet
```bash
python tools/read_xlsx.py --file data.xlsx --format json
```

### Read Specific Range
```bash
python tools/read_xlsx.py --file data.xlsx --sheet "Sheet1" --range "A1:C10" --format csv
```

### Update Cells
```bash
python tools/edit_xlsx.py --file data.xlsx --output updated.xlsx --operations '[{"action": "set_cell", "sheet": "Sheet1", "cell": "B2", "value": 150}]'
```

### Add Summary Formula
```bash
python tools/edit_xlsx.py --file data.xlsx --output updated.xlsx --operations '[{"action": "add_formula", "sheet": "Sheet1", "cell": "B10", "formula": "=SUM(B2:B9)"}]'
```

## Formula Examples

| Formula | Description |
|---------|-------------|
| `=SUM(A1:A10)` | Sum of range |
| `=AVERAGE(B:B)` | Average of column |
| `=IF(A1>0,"Yes","No")` | Conditional |
| `=VLOOKUP(A1,Sheet2!A:B,2,FALSE)` | Lookup |
| `=CONCATENATE(A1," ",B1)` | Text join |
| `=TODAY()` | Current date |

## Dependencies

Requires `openpyxl>=3.1.0`. Automatically installed with the skill.
