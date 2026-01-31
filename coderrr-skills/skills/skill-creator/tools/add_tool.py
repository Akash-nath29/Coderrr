#!/usr/bin/env python3
"""
Add a tool template to a skill.

Usage:
    python add_tool.py --skill-dir ./my-skill --tool-name process_data --description "Process data"
"""

import argparse
import sys
import json
from pathlib import Path


TOOL_TEMPLATE = '''#!/usr/bin/env python3
"""
{description}

Usage:
    python {tool_name}.py {usage_args}
"""

import argparse
import sys
import json


def {function_name}({function_args}):
    """
    {description}
    
    Args:
{args_docstring}
    
    Returns:
        dict: Result of the operation
    """
    # TODO: Implement tool logic here
    result = {{
        "status": "success"
    }}
    
    return result


def main():
    parser = argparse.ArgumentParser(description='{description}')
{arg_parser_code}
    
    args = parser.parse_args()
    
    try:
        result = {function_name}({function_call_args})
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
'''


def generate_tool(skill_dir: str, tool_name: str, description: str, args_spec: list = None):
    """Generate a tool template."""
    tools_dir = Path(skill_dir) / 'tools'
    tools_dir.mkdir(exist_ok=True)
    
    args_spec = args_spec or []
    
    # Generate code parts
    function_name = tool_name.replace('-', '_')
    function_args = ', '.join(arg['name'] for arg in args_spec) if args_spec else ''
    
    # Usage line args
    usage_parts = []
    for arg in args_spec:
        if arg.get('required'):
            usage_parts.append(f"--{arg['name']} <{arg['name']}>")
        else:
            usage_parts.append(f"[--{arg['name']} <{arg['name']}>]")
    usage_args = ' '.join(usage_parts) if usage_parts else '[options]'
    
    # Args docstring
    if args_spec:
        args_docstring = '\n'.join(f"        {arg['name']}: {arg.get('help', 'No description')}" for arg in args_spec)
    else:
        args_docstring = '        None'
    
    # Argparser code
    arg_parser_lines = []
    for arg in args_spec:
        arg_type = arg.get('type', 'string')
        required = arg.get('required', False)
        help_text = arg.get('help', '')
        
        if arg_type == 'flag':
            arg_parser_lines.append(f"    parser.add_argument('--{arg['name']}', action='store_true', help='{help_text}')")
        else:
            req_str = ', required=True' if required else ''
            arg_parser_lines.append(f"    parser.add_argument('--{arg['name']}'{req_str}, help='{help_text}')")
    
    arg_parser_code = '\n'.join(arg_parser_lines) if arg_parser_lines else "    # No arguments defined"
    
    # Function call args
    function_call_args = ', '.join(f"args.{arg['name']}" for arg in args_spec) if args_spec else ''
    
    # Generate code
    code = TOOL_TEMPLATE.format(
        description=description,
        tool_name=tool_name,
        usage_args=usage_args,
        function_name=function_name,
        function_args=function_args,
        args_docstring=args_docstring,
        arg_parser_code=arg_parser_code,
        function_call_args=function_call_args
    )
    
    # Write file
    tool_file = tools_dir / f'{tool_name}.py'
    tool_file.write_text(code)
    
    return {
        "status": "success",
        "file": str(tool_file),
        "tool_name": tool_name
    }


def main():
    parser = argparse.ArgumentParser(description='Add a tool to a skill')
    parser.add_argument('--skill-dir', required=True, help='Skill directory')
    parser.add_argument('--tool-name', required=True, help='Tool name')
    parser.add_argument('--description', required=True, help='Tool description')
    parser.add_argument('--args', help='JSON array of argument definitions')
    
    args = parser.parse_args()
    
    args_spec = []
    if args.args:
        try:
            args_spec = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid args JSON - {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        result = generate_tool(args.skill_dir, args.tool_name, args.description, args_spec)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
