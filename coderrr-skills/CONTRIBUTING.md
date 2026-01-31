# Contributing to Coderrr Skills

Thank you for your interest in contributing to the Coderrr skills marketplace! This guide will help you create and submit your own skills.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Skill Requirements](#skill-requirements)
- [Creating a New Skill](#creating-a-new-skill)
- [Testing Your Skill](#testing-your-skill)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code of Conduct](#code-of-conduct)

## Getting Started

1. **Fork** this repository
2. **Clone** your fork locally
3. Create a new **branch** for your skill: `git checkout -b skill/your-skill-name`

## Skill Requirements

Every skill must meet these requirements:

### Required Files

```
skills/your-skill-name/
├── Skills.md           # Required: Skill documentation
├── requirements.txt    # Optional: Python dependencies
└── tools/
    └── your_tool.py    # Required: At least one tool
```

### Skills.md Format

Your `Skills.md` must include:

```markdown
---
name: your-skill-name
displayName: Your Skill Name
description: Brief description of what your skill does
version: 1.0.0
author: Your Name
tags:
  - tag1
  - tag2
---

# Your Skill Name

Detailed description of your skill.

## Tools

### tool_name

Description of what this tool does.

**Arguments:**
- `--arg1` (required): Description
- `--arg2` (optional): Description

**Example:**
\`\`\`bash
python tools/tool_name.py --arg1 value
\`\`\`

**Output:**
Description of output format
```

### Tool Requirements

Each Python tool must:

1. **Use argparse** for command-line arguments
2. **Include docstrings** explaining functionality
3. **Handle errors gracefully** with informative messages
4. **Output to stdout** for easy piping
5. **Return exit code 0** on success, non-zero on failure

### Example Tool Structure

```python
#!/usr/bin/env python3
"""
Brief description of what this tool does.
"""

import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser(
        description='What this tool does'
    )
    parser.add_argument('--input', required=True, help='Input description')
    parser.add_argument('--format', default='json', help='Output format')
    
    args = parser.parse_args()
    
    try:
        # Your tool logic here
        result = process(args.input)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

## Testing Your Skill

Before submitting, test your skill locally:

1. **Install Coderrr CLI** (if not already installed):
   ```bash
   npm install -g coderrr-cli
   ```

2. **Install your skill locally**:
   ```bash
   coderrr install ./skills/your-skill-name
   ```

3. **Test each tool**:
   ```bash
   python ~/.coderrr/skills/your-skill-name/tools/your_tool.py --help
   ```

4. **Verify with the agent**:
   ```bash
   coderrr
   > Use the your_tool to do something
   ```

## Submitting a Pull Request

1. **Update registry.json** with your skill metadata:
   ```json
   {
     "your-skill-name": {
       "name": "your-skill-name",
       "displayName": "Your Skill Name",
       "description": "What your skill does",
       "version": "1.0.0",
       "author": "Your Name",
       "repository": "https://github.com/your-username/your-repo",
       "download_url": "https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/skills/your-skill-name",
       "tools": ["tool1", "tool2"],
       "tags": ["tag1", "tag2"]
     }
   }
   ```

2. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add your-skill-name skill"
   ```

3. **Push to your fork**:
   ```bash
   git push origin skill/your-skill-name
   ```

4. **Open a Pull Request** with:
   - Clear title: `Add [skill-name] skill`
   - Description of what your skill does
   - List of tools included
   - Any external dependencies

### PR Checklist

- [ ] Skills.md is complete with all required sections
- [ ] All tools have proper docstrings
- [ ] All tools handle errors gracefully
- [ ] requirements.txt lists all dependencies (if any)
- [ ] registry.json is updated with correct metadata
- [ ] Tools tested locally and working

## Code of Conduct

- **Be respectful** in all interactions
- **Write clean, readable code** with comments
- **Document thoroughly** for other users
- **Test before submitting** to avoid broken skills
- **No malicious code** - skills that harm users will be removed

## Questions?

If you have questions, feel free to:

- Open an [issue](https://github.com/Akash-nath29/coderrr-skills/issues)
- Check existing skills for examples
- Read the [Coderrr CLI documentation](https://github.com/Akash-nath29/Coderrr)

Thank you for contributing! 🚀
