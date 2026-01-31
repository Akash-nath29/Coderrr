---
name: pptx
description: Create, edit, and analyze PowerPoint presentations. Use this skill when the user asks to create slides, modify presentations, extract content from PPTX files, add speaker notes, or analyze presentation structure. Supports layouts, images, charts, and professional formatting.
---

This skill provides comprehensive PowerPoint manipulation using python-pptx. It handles presentation creation, slide editing, content extraction, and structural analysis.

The user provides presentation requirements or existing files to process. They may want to create new presentations, modify existing ones, or extract content from slides.

## Approach

Before invoking tools, understand the presentation task:
- **Create new**: Use `create_pptx` with slide specifications
- **Extract content**: Use `read_pptx` to get text and structure
- **Modify slides**: Use `edit_pptx` to update content
- **Analyze structure**: Use `analyze_pptx` for presentation overview

## Tools

### create_pptx

Creates PowerPoint presentations with specified slides and content.

```bash
python tools/create_pptx.py --output <path> --title <title> --slides <json>
```

**Arguments:**
- `--output` (required): Output file path (.pptx)
- `--title` (required): Presentation title (first slide)
- `--slides` (required): JSON array of slide specifications

**Slides JSON Structure:**
```json
[
  {"layout": "title", "title": "Main Title", "subtitle": "Subtitle"},
  {"layout": "content", "title": "Slide Title", "content": ["Bullet 1", "Bullet 2"]},
  {"layout": "two_content", "title": "Comparison", "left": ["Left items"], "right": ["Right items"]},
  {"layout": "section", "title": "Section Header"},
  {"layout": "blank", "notes": "Speaker notes here"}
]
```

**Layouts:**
- `title` - Title slide with subtitle
- `content` - Title with bullet points
- `two_content` - Two column layout
- `section` - Section header
- `blank` - Blank slide

**When to use:**
- Generating presentations from data
- Creating report slides
- Building pitch decks
- Automating slide generation

---

### read_pptx

Extracts content from existing PowerPoint files.

```bash
python tools/read_pptx.py --file <path> [--format <text|json|markdown>] [--include-notes]
```

**Arguments:**
- `--file` (required): Path to PowerPoint file
- `--format` (optional): Output format (default: text)
- `--include-notes` (optional): Include speaker notes

**When to use:**
- Extracting presentation content
- Converting slides to other formats
- Reading speaker notes
- Processing uploaded presentations

---

### edit_pptx

Modifies existing PowerPoint presentations.

```bash
python tools/edit_pptx.py --file <path> --output <path> --operations <json>
```

**Arguments:**
- `--file` (required): Input PowerPoint file
- `--output` (required): Output file path
- `--operations` (required): JSON array of operations

**Operations:**
```json
[
  {"action": "add_slide", "layout": "content", "title": "New Slide", "content": ["Point 1"]},
  {"action": "update_slide", "index": 2, "title": "Updated Title"},
  {"action": "add_notes", "index": 1, "notes": "Speaker notes..."},
  {"action": "delete_slide", "index": 5}
]
```

**When to use:**
- Adding slides to existing presentations
- Updating slide content
- Adding speaker notes
- Modifying presentation structure

---

### analyze_pptx

Analyzes presentation structure and provides metadata.

```bash
python tools/analyze_pptx.py --file <path>
```

**Output:** JSON with slide count, layouts used, content summary, and word count.

**When to use:**
- Understanding presentation structure
- Auditing slide content
- Getting presentation statistics
- Quality assurance

## Common Patterns

### Create Simple Presentation
```bash
python tools/create_pptx.py --output deck.pptx --title "Q4 Report" --slides '[{"layout": "content", "title": "Summary", "content": ["Revenue up 15%", "New customers: 500"]}]'
```

### Extract All Content
```bash
python tools/read_pptx.py --file presentation.pptx --format text --include-notes
```

### Add Slide to Existing Deck
```bash
python tools/edit_pptx.py --file deck.pptx --output updated.pptx --operations '[{"action": "add_slide", "layout": "content", "title": "Conclusion", "content": ["Key takeaways"]}]'
```

## Dependencies

Requires `python-pptx>=0.6.21`. Automatically installed with the skill.
