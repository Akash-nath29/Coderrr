---
name: artifacts-builder
description: Build complex HTML artifacts using React, Tailwind CSS, and shadcn/ui components. Use this skill when the user wants to create polished UI components, interactive web widgets, dashboards, landing pages, or sophisticated HTML artifacts with modern styling and interactivity.
---

This skill guides creation of production-quality HTML artifacts using modern frontend technologies. It helps scaffold React components with Tailwind CSS styling and shadcn/ui components for professional, consistent design.

The user wants to create an HTML artifact. They may specify the type (component, page, widget, dashboard), design requirements, and interactivity needs.

## Approach

When building artifacts:
1. **Analyze requirements**: Understand the UI/UX goals
2. **Choose architecture**: Single HTML vs multi-file component
3. **Select components**: Pick appropriate shadcn/ui components
4. **Build progressively**: Start with structure, add styling, then interactivity

## Tools

### scaffold_artifact

Creates the initial artifact structure with appropriate boilerplate.

```bash
python tools/scaffold_artifact.py --name <name> --type <type> --output-dir <path> [--features <list>]
```

**Arguments:**
- `--name` (required): Artifact name (used for file naming)
- `--type` (required): Artifact type - `component`, `page`, `widget`, `dashboard`
- `--output-dir` (required): Output directory
- `--features` (optional): Comma-separated features - `dark-mode`, `animations`, `responsive`

**Types:**
- `component` - Reusable React component
- `page` - Full page layout
- `widget` - Self-contained interactive widget
- `dashboard` - Data dashboard with charts/tables

**When to use:**
- Starting a new artifact
- Getting proper boilerplate
- Setting up the file structure

---

### add_component

Adds pre-built component templates to an artifact.

```bash
python tools/add_component.py --artifact-dir <path> --component <name> [--variant <variant>]
```

**Arguments:**
- `--artifact-dir` (required): Path to artifact directory
- `--component` (required): Component to add (see list below)
- `--variant` (optional): Component variant/style

**Available Components:**
- `button` - Interactive buttons (variants: primary, secondary, outline, ghost)
- `card` - Content card with header/body/footer
- `dialog` - Modal dialog
- `dropdown` - Dropdown menu
- `form` - Form with validation
- `table` - Data table with sorting
- `tabs` - Tabbed interface
- `navbar` - Navigation bar
- `sidebar` - Side navigation
- `chart` - Data visualization (variants: line, bar, pie)

**When to use:**
- Adding UI components
- Building layouts
- Including interactive elements

---

### build_artifact

Compiles the artifact into a single, deliverable HTML file.

```bash
python tools/build_artifact.py --artifact-dir <path> --output <path> [--minify]
```

**Arguments:**
- `--artifact-dir` (required): Path to artifact directory
- `--output` (required): Output HTML file path
- `--minify` (optional): Minify the output

**When to use:**
- Creating final deliverable
- Bundling for distribution
- Generating standalone HTML

---

### preview_artifact

Generates a preview of the artifact.

```bash
python tools/preview_artifact.py --artifact-dir <path> [--port <port>]
```

**Arguments:**
- `--artifact-dir` (required): Path to artifact directory
- `--port` (optional): Preview server port (default: 3000)

**When to use:**
- Testing the artifact
- Visual verification
- Development iteration

## Design Guidelines

### Visual Excellence
- Use rich color palettes, not generic defaults
- Implement smooth animations and transitions
- Apply generous whitespace for breathing room
- Choose distinctive typography

### Modern Aesthetics
- Glassmorphism effects for depth
- Gradient backgrounds and accents
- Subtle shadows and blur effects
- Micro-interactions on hover/focus

### Responsive Design
- Mobile-first approach
- Flexible grids and layouts
- Appropriate breakpoints
- Touch-friendly interactions

## Common Patterns

### Create Landing Page
```bash
python tools/scaffold_artifact.py --name landing --type page --output-dir ./artifacts --features responsive,animations
python tools/add_component.py --artifact-dir ./artifacts/landing --component navbar
python tools/add_component.py --artifact-dir ./artifacts/landing --component button --variant primary
python tools/build_artifact.py --artifact-dir ./artifacts/landing --output ./landing.html
```

### Create Dashboard Widget
```bash
python tools/scaffold_artifact.py --name metrics --type widget --output-dir ./artifacts
python tools/add_component.py --artifact-dir ./artifacts/metrics --component card
python tools/add_component.py --artifact-dir ./artifacts/metrics --component chart --variant line
python tools/build_artifact.py --artifact-dir ./artifacts/metrics --output ./widget.html
```

## Best Practices

1. **Start with scaffold** - Get proper boilerplate and structure
2. **Use components** - Don't build from scratch when components exist
3. **Test responsiveness** - Check at multiple breakpoints
4. **Preview before build** - Catch issues early
5. **Minify for production** - Smaller file size for delivery

## Color Palette Suggestions

Avoid generic colors. Use these curated palettes:

**Professional Dark:**
- Background: `#0f172a`
- Surface: `#1e293b`
- Primary: `#3b82f6`
- Accent: `#f472b6`

**Warm Light:**
- Background: `#fef7ee`
- Surface: `#ffffff`
- Primary: `#ea580c`
- Accent: `#0ea5e9`

**Modern Neutral:**
- Background: `#18181b`
- Surface: `#27272a`
- Primary: `#a78bfa`
- Accent: `#34d399`

## Dependencies

Generates self-contained HTML with embedded:
- React 18 (via CDN)
- Tailwind CSS (via CDN)
- shadcn/ui component styles
