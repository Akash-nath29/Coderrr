---
name: skill-creator
description: Interactive tool for building new custom skills for Coderrr. Use this skill when the user wants to create a new skill, scaffold a skill structure, generate tool templates, or set up skill documentation. Guides through the complete skill creation process.
---

This skill helps create new skills for the Coderrr marketplace. It scaffolds the required file structure, generates tool templates, and creates proper documentation.

The user wants to create a new skill. They may provide a name, description, and list of tools they want to include.

## Approach

When creating a new skill:
1. **Initialize**: Use `init_skill` to scaffold the structure
2. **Add tools**: Use `add_tool` for each tool in the skill
3. **Finalize**: Use `finalize_skill` to validate and complete

## Tools

### init_skill

Scaffolds a new skill directory structure.

```bash
python tools/init_skill.py --name <skill-name> --description <desc> --output-dir <path> [--author <name>]
```

**Arguments:**
- `--name` (required): Skill name (lowercase, hyphens for spaces)
- `--description` (required): One-line description of the skill
- `--output-dir` (required): Directory to create skill in
- `--author` (optional): Skill author name

**Creates:**
```
skill-name/
├── Skills.md          # Documentation template
├── requirements.txt   # Empty dependencies file
└── tools/             # Empty tools directory
```

**When to use:**
- Starting a new skill project
- Setting up skill structure
- Creating skill scaffolding

---

### add_tool

Generates a tool template with proper structure.

```bash
python tools/add_tool.py --skill-dir <path> --tool-name <name> --description <desc> [--args <json>]
```

**Arguments:**
- `--skill-dir` (required): Path to skill directory
- `--tool-name` (required): Tool name (lowercase, underscores)
- `--description` (required): What the tool does
- `--args` (optional): JSON array of argument definitions

**Args JSON:**
```json
[
  {"name": "input", "type": "string", "required": true, "help": "Input file path"},
  {"name": "output", "type": "string", "required": false, "help": "Output file path"},
  {"name": "verbose", "type": "flag", "help": "Enable verbose output"}
]
```

**When to use:**
- Adding tools to a skill
- Generating tool boilerplate
- Setting up argument parsing

---

### finalize_skill

Validates and finalizes a skill for publishing.

```bash
python tools/finalize_skill.py --skill-dir <path> [--validate-only]
```

**Arguments:**
- `--skill-dir` (required): Path to skill directory
- `--validate-only` (optional): Only validate, don't modify

**Validates:**
- Skills.md has required fields
- All tools have valid Python syntax
- requirements.txt is present
- Tools have docstrings and argparse

**When to use:**
- Before publishing a skill
- Checking skill structure
- Validating tool implementations

---

### list_templates

Lists available tool templates for common patterns.

```bash
python tools/list_templates.py [--category <category>]
```

**Categories:**
- `file` - File processing tools
- `web` - Web/HTTP tools
- `data` - Data manipulation tools
- `cli` - CLI interaction tools

**When to use:**
- Finding template inspiration
- Exploring common patterns
- Starting with working examples

## Skill Creation Workflow

### Step 1: Initialize
```bash
python tools/init_skill.py --name my-skill --description "Description here" --output-dir ./skills
```

### Step 2: Add Tools
```bash
python tools/add_tool.py --skill-dir ./skills/my-skill --tool-name process_data --description "Process data files" --args '[{"name": "input", "type": "string", "required": true, "help": "Input file"}]'
```

### Step 3: Implement Tool Logic
Edit the generated tool file to add your implementation.

### Step 4: Validate
```bash
python tools/finalize_skill.py --skill-dir ./skills/my-skill --validate-only
```

### Step 5: Finalize
```bash
python tools/finalize_skill.py --skill-dir ./skills/my-skill
```

## Best Practices

1. **Use descriptive names** - Both skill and tool names should be clear
2. **Write detailed descriptions** - Help users understand when to use the skill
3. **Include examples** - Show real usage in Skills.md
4. **Handle errors gracefully** - Use proper exit codes and stderr
5. **Output JSON** - Structured output is easier to parse
6. **Document arguments** - Help text for every argument

## Dependencies

None - uses Python's standard library only.
