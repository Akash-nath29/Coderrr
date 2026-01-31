---
name: brand-guidelines
description: Apply official brand colors, typography, and design tokens to projects. Use this skill when the user wants to set up brand colors, configure typography, generate color palettes, create design tokens, or ensure brand consistency across a project.
---

This skill helps maintain brand consistency by managing colors, typography, and design tokens. It generates CSS variables, config files, and documentation for brand implementation.

The user wants to apply brand styling to a project. They may provide brand colors, font choices, or want to generate a cohesive palette.

## Approach

When setting up brand guidelines:
1. **Define**: Use `set_brand` to configure core brand values
2. **Generate**: Use `generate_palette` for extended colors
3. **Export**: Use `export_tokens` for CSS/SCSS/JSON/Tailwind
4. **Document**: Use `create_styleguide` for team reference

## Tools

### set_brand

Configures core brand values.

```bash
python tools/set_brand.py --name <brand> --primary <color> --secondary <color> [--accent <color>] [--fonts <json>]
```

**Arguments:**
- `--name` (required): Brand/project name
- `--primary` (required): Primary brand color (hex)
- `--secondary` (required): Secondary color (hex)
- `--accent` (optional): Accent color (hex)
- `--fonts` (optional): Font configuration JSON

**Fonts JSON:**
```json
{
  "heading": "Outfit",
  "body": "Inter",
  "mono": "JetBrains Mono"
}
```

**When to use:**
- Starting a new project
- Updating brand colors
- Setting typography

---

### generate_palette

Generates extended color palette from brand colors.

```bash
python tools/generate_palette.py --brand <name> [--include <shades|semantic|both>]
```

**Arguments:**
- `--brand` (required): Brand name (from set_brand)
- `--include` (optional): What to generate (default: both)

**Generates:**
- **Shades**: 50-950 scale for each color
- **Semantic**: success, warning, error, info colors

**When to use:**
- Creating full color system
- Generating consistent shades
- Adding semantic colors

---

### export_tokens

Exports design tokens in various formats.

```bash
python tools/export_tokens.py --brand <name> --format <format> --output <path>
```

**Arguments:**
- `--brand` (required): Brand name
- `--format` (required): Output format - `css`, `scss`, `json`, `tailwind`, `figma`
- `--output` (required): Output file path

**CSS Output Example:**
```css
:root {
  --color-primary: #3b82f6;
  --color-primary-50: #eff6ff;
  --color-primary-500: #3b82f6;
  --font-heading: 'Outfit', sans-serif;
}
```

**When to use:**
- Integrating with existing projects
- Setting up Tailwind config
- Sharing with design tools

---

### create_styleguide

Generates brand documentation.

```bash
python tools/create_styleguide.py --brand <name> --output <path> [--format <html|markdown>]
```

**Arguments:**
- `--brand` (required): Brand name
- `--output` (required): Output file/directory
- `--format` (optional): Guide format (default: html)

**When to use:**
- Documenting brand for team
- Creating design reference
- Onboarding designers

## Common Patterns

### Complete Brand Setup
```bash
# Define brand
python tools/set_brand.py --name myproject --primary "#6366f1" --secondary "#64748b" --accent "#f43f5e" --fonts '{"heading": "Outfit", "body": "Inter"}'

# Generate extended palette
python tools/generate_palette.py --brand myproject --include both

# Export for Tailwind
python tools/export_tokens.py --brand myproject --format tailwind --output tailwind.config.js

# Create documentation
python tools/create_styleguide.py --brand myproject --output ./docs/brand
```

### Quick CSS Variables
```bash
python tools/set_brand.py --name quick --primary "#0ea5e9" --secondary "#1e293b"
python tools/export_tokens.py --brand quick --format css --output variables.css
```

## Color Guidelines

**Primary**: Main brand color, buttons, links, key UI elements
**Secondary**: Supporting color, backgrounds, borders
**Accent**: Call-to-action, highlights, notifications

**Shade Scale:**
- 50: Lightest (backgrounds)
- 100-200: Light variants
- 300-400: Muted variants
- 500: Base color
- 600-700: Darker variants
- 800-900: Darkest (text on light)
- 950: Near-black variant

## Typography Guidelines

**Heading fonts**: Display, expressive
- Outfit, Space Grotesk, Clash Display, Satoshi

**Body fonts**: Readable, neutral
- Inter, Source Sans, Nunito Sans, DM Sans

**Mono fonts**: Code, technical
- JetBrains Mono, Fira Code, IBM Plex Mono

## Dependencies

Uses Python standard library with optional `colormath` for advanced color operations.
