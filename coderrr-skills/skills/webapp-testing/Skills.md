---
name: webapp-testing
description: Test local web applications using Playwright browser automation. Use this skill when the user wants to test web applications, automate browser interactions, take screenshots, verify UI elements, or run end-to-end tests on web pages.
---

This skill provides browser automation and testing capabilities using Playwright. It handles page navigation, element interaction, screenshot capture, and test verification.

The user wants to test a web application. They may want to verify UI elements, test user flows, check responsiveness, or capture screenshots.

## Approach

When testing web applications:
1. **Start**: Use `start_browser` to launch browser session
2. **Navigate**: Use `navigate` to open pages
3. **Interact**: Use `interact` to click, type, or scroll
4. **Verify**: Use `verify` to check elements and content
5. **Capture**: Use `screenshot` to save visual state
6. **Report**: Use `generate_report` to summarize results

## Tools

### start_browser

Launches a browser session for testing.

```bash
python tools/start_browser.py [--browser <chromium|firefox|webkit>] [--headless] [--viewport <WxH>]
```

**Arguments:**
- `--browser` (optional): Browser engine (default: chromium)
- `--headless` (optional): Run without visible window
- `--viewport` (optional): Viewport size (e.g., "1920x1080")

**Output:** Session ID for subsequent commands.

**When to use:**
- Starting a test session
- Configuring browser options
- Setting viewport for responsive testing

---

### navigate

Navigates to a URL.

```bash
python tools/navigate.py --session <id> --url <url> [--wait-until <event>]
```

**Arguments:**
- `--session` (required): Session ID from start_browser
- `--url` (required): URL to navigate to
- `--wait-until` (optional): Wait condition - `load`, `domcontentloaded`, `networkidle`

**When to use:**
- Opening test pages
- Navigating between routes
- Starting user flows

---

### interact

Interacts with page elements.

```bash
python tools/interact.py --session <id> --action <action> --selector <selector> [--value <value>]
```

**Arguments:**
- `--session` (required): Session ID
- `--action` (required): Action - `click`, `type`, `fill`, `hover`, `scroll`, `select`
- `--selector` (required): CSS selector or text selector
- `--value` (optional): Value for type/fill/select actions

**Selector formats:**
- CSS: `#id`, `.class`, `button[type="submit"]`
- Text: `text=Login`, `text="Sign Up"`
- Role: `role=button[name="Submit"]`

**When to use:**
- Clicking buttons
- Filling forms
- Hovering for tooltips
- Scrolling pages

---

### verify

Verifies page state and elements.

```bash
python tools/verify.py --session <id> --check <type> [--selector <selector>] [--expected <value>]
```

**Arguments:**
- `--session` (required): Session ID
- `--check` (required): Check type - `visible`, `hidden`, `text`, `value`, `title`, `url`
- `--selector` (optional): Element selector (for element checks)
- `--expected` (optional): Expected value for comparison

**When to use:**
- Verifying element visibility
- Checking text content
- Validating form values
- Confirming navigation

---

### screenshot

Captures page screenshot.

```bash
python tools/screenshot.py --session <id> --output <path> [--selector <selector>] [--full-page]
```

**Arguments:**
- `--session` (required): Session ID
- `--output` (required): Output file path
- `--selector` (optional): Capture specific element only
- `--full-page` (optional): Capture entire scrollable page

**When to use:**
- Visual regression testing
- Documenting test results
- Bug reporting
- Before/after comparisons

---

### generate_report

Generates test report from session.

```bash
python tools/generate_report.py --session <id> --output <path> [--format <html|json|markdown>]
```

**Arguments:**
- `--session` (required): Session ID
- `--output` (required): Report output path
- `--format` (optional): Report format (default: html)

**When to use:**
- Summarizing test results
- Creating documentation
- Sharing results

## Common Patterns

### Test Login Flow
```bash
# Start browser
python tools/start_browser.py --headless
# Navigate to login page
python tools/navigate.py --session $SESSION --url http://localhost:3000/login
# Fill credentials
python tools/interact.py --session $SESSION --action fill --selector "#email" --value "test@example.com"
python tools/interact.py --session $SESSION --action fill --selector "#password" --value "password123"
# Click login
python tools/interact.py --session $SESSION --action click --selector "button[type=submit]"
# Verify success
python tools/verify.py --session $SESSION --check url --expected "/dashboard"
```

### Responsive Testing
```bash
# Mobile viewport
python tools/start_browser.py --viewport 375x667
python tools/navigate.py --session $SESSION --url http://localhost:3000
python tools/screenshot.py --session $SESSION --output mobile.png

# Desktop viewport
python tools/start_browser.py --viewport 1920x1080
python tools/navigate.py --session $SESSION --url http://localhost:3000
python tools/screenshot.py --session $SESSION --output desktop.png
```

### Visual Regression
```bash
python tools/start_browser.py --headless
python tools/navigate.py --session $SESSION --url http://localhost:3000
python tools/screenshot.py --session $SESSION --output current.png --full-page
```

## Best Practices

1. **Use headless for CI** - No display needed in pipelines
2. **Wait for network idle** - Ensure page fully loaded
3. **Prefer role selectors** - More resilient than CSS
4. **Take screenshots on failure** - Helps debugging
5. **Clean up sessions** - Don't leave browsers running

## Viewport Presets

| Device | Viewport |
|--------|----------|
| Mobile S | 320x568 |
| Mobile M | 375x667 |
| Mobile L | 425x812 |
| Tablet | 768x1024 |
| Laptop | 1366x768 |
| Desktop | 1920x1080 |

## Dependencies

Requires `playwright>=1.40.0`. Run `playwright install` after pip install.
