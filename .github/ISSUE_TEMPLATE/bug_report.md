---
name: Bug Report
about: Create a report to help us improve Coderrr
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

A clear and concise description of what the bug is.

## To Reproduce

Steps to reproduce the behavior:

1. Run command '...'
2. Enter request '...'
3. See error

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

What actually happened instead.

## Screenshots/Logs

If applicable, add screenshots or log output to help explain your problem.

```
Paste logs here
```

## Environment

Run `coderrr doctor` and paste the output — it covers most of the below.

```
paste `coderrr doctor` output here
```

**System Information:**
- OS: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- Shell: [e.g., PowerShell 5.1, bash 5.0]
- Python Version: [e.g., 3.12.0]
- Coderrr Version: [e.g., 2.0.0]

**Configuration:**
- Provider: [ollama / anthropic / openai / google / openrouter]
- Model: [e.g., gemma4:31b-cloud]
- Sandbox tier: [scratch / docker]

**MCP servers** (only if the issue involves one — `coderrr mcp list` shows this):
- Server URL or command: [e.g., https://mcp.linear.app/mcp]
- Transport: [http / stdio]
- Auth: [signed in / not signed in / static header / none]

**Which phase did it happen in?**
- [ ] Planning (before the plan was approved)
- [ ] Approval prompt
- [ ] Execution (after approval)
- [ ] Connecting or signing in to an MCP server

## Additional Context

Anything else that helps — whether it only happens with certain requests, when
it started, and so on. If a spec was created, attaching `tasks.md` often helps.

## Checklist

- [ ] I have searched for similar issues
- [ ] I have included all requested information above
- [ ] I am on Coderrr v2 (v1 / the npm package is no longer supported)
- [ ] I have tested with the latest version of Coderrr
