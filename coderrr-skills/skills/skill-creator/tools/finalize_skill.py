#!/usr/bin/env python3
"""
Validate and finalize a skill for publishing.

Usage:
    python finalize_skill.py --skill-dir ./my-skill
"""

import argparse
import sys
import json
import ast
from pathlib import Path
import re


def validate_skill(skill_dir: str) -> dict:
    """Validate skill structure and files."""
    skill_path = Path(skill_dir)
    issues = []
    warnings = []
    
    # Check Skills.md exists
    skills_md = skill_path / 'Skills.md'
    if not skills_md.exists():
        issues.append("Skills.md not found")
    else:
        content = skills_md.read_text()
        
        # Check frontmatter
        if not content.startswith('---'):
            issues.append("Skills.md missing YAML frontmatter")
        else:
            # Extract frontmatter
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                if 'name:' not in frontmatter:
                    issues.append("Skills.md missing 'name' in frontmatter")
                if 'description:' not in frontmatter:
                    issues.append("Skills.md missing 'description' in frontmatter")
    
    # Check requirements.txt exists
    if not (skill_path / 'requirements.txt').exists():
        warnings.append("requirements.txt not found (optional but recommended)")
    
    # Check tools directory
    tools_dir = skill_path / 'tools'
    if not tools_dir.exists():
        issues.append("tools/ directory not found")
    else:
        tool_files = list(tools_dir.glob('*.py'))
        if not tool_files:
            warnings.append("No Python tool files found in tools/")
        
        # Validate each tool
        for tool_file in tool_files:
            try:
                source = tool_file.read_text()
                ast.parse(source)
                
                # Check for argparse
                if 'argparse' not in source:
                    warnings.append(f"{tool_file.name}: No argparse import found")
                
                # Check for docstring
                if '"""' not in source and "'''" not in source:
                    warnings.append(f"{tool_file.name}: No docstring found")
                    
            except SyntaxError as e:
                issues.append(f"{tool_file.name}: Syntax error at line {e.lineno}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "tool_count": len(list((skill_path / 'tools').glob('*.py'))) if (skill_path / 'tools').exists() else 0
    }


def main():
    parser = argparse.ArgumentParser(description='Validate and finalize a skill')
    parser.add_argument('--skill-dir', required=True, help='Skill directory')
    parser.add_argument('--validate-only', action='store_true', help='Only validate')
    
    args = parser.parse_args()
    
    if not Path(args.skill_dir).exists():
        print(f"Error: Directory not found: {args.skill_dir}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = validate_skill(args.skill_dir)
        result["skill_dir"] = args.skill_dir
        
        if result["valid"]:
            result["message"] = "Skill is valid and ready for publishing"
        else:
            result["message"] = "Skill has issues that must be fixed"
        
        print(json.dumps(result, indent=2))
        
        if not result["valid"]:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
