# Recipe System

Recipes are pre-defined sets of tasks that Coderrr can execute.

## Usage
List available recipes:
`coderrr recipe --list`

Run a recipe:
`coderrr recipe <name>`

## Creating your own
Save a `.json` file in `~/.coderrr/recipes/`:
```json
{
  "name": "Quick Express",
  "tasks": ["Initialize npm", "Install express", "Create app.js"]
}