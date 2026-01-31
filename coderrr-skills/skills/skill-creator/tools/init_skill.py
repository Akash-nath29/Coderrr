#!/usr/bin/env python3
"""
Initialize a new skill directory structure.

Usage:
    python init_skill.py --name my-skill --description "Description" --output-dir ./skills
"""

import argparse
import sys
import json
from pathlib import Path


SKILLS_MD_TEMPLATE = '''---
name: {name}
description: {description}
---

This skill provides [detailed description of what the skill does].

The user provides [what input the user gives]. They may want to [what they want to accomplish].

## Approach

Before invoking tools, understand [how to decide which tool to use]:
- **Scenario 1**: Use `tool_name` for [use case]
- **Scenario 2**: Use `other_tool` for [other use case]

## Tools

[Add tool documentation here]

## Common Patterns

[Add usage examples here]

## Best Practices

1. [Best practice 1]
2. [Best practice 2]

## Dependencies

[List dependencies or "None - uses Python's standard library only."]
'''


def init_skill(name: str, description: str, output_dir: str, author: str = None):
    """Initialize a new skill directory."""
    skill_dir = Path(output_dir) / name
    
    # Create directories
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'tools').mkdir(exist_ok=True)
    
    # Create Skills.md
    skills_md = SKILLS_MD_TEMPLATE.format(name=name, description=description)
    (skill_dir / 'Skills.md').write_text(skills_md)
    
    # Create empty requirements.txt
    (skill_dir / 'requirements.txt').write_text('# Add dependencies here, one per line\n')
    
    return {
        "status": "success",
        "skill_dir": str(skill_dir),
        "files_created": [
            str(skill_dir / 'Skills.md'),
            str(skill_dir / 'requirements.txt'),
            str(skill_dir / 'tools')
        ]
    }


def main():
    parser = argparse.ArgumentParser(description='Initialize a new skill')
    parser.add_argument('--name', required=True, help='Skill name')
    parser.add_argument('--description', required=True, help='Skill description')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--author', help='Skill author')
    
    args = parser.parse_args()
    
    # Validate name
    if not args.name.replace('-', '').replace('_', '').isalnum():
        print("Error: Skill name must be alphanumeric with hyphens/underscores", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = init_skill(args.name, args.description, args.output_dir, args.author)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
