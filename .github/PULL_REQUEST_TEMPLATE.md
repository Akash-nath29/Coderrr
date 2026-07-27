# Pull Request

## Description

Brief description of what this PR does.

Fixes #(issue number)

## Type of Change

Please check the relevant options:

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test improvements

## Changes Made

Detailed list of changes:

- Change 1
- Change 2
- Change 3

## Motivation and Context

Why is this change required? What problem does it solve?

## Testing

How has this been tested? Please describe your testing process:

**Test Configuration**:
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.12.0]

**Test Cases**:
1. Test case 1 - Expected result
2. Test case 2 - Expected result

**The four gates** (all blocking in CI):
```bash
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```

## Screenshots (if applicable)

Add screenshots to demonstrate the changes.

## Checklist

### Code Quality

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `mypy` passes in strict mode
- [ ] I have removed any debugging code or stray prints

### Testing

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] `pytest` passes locally
- [ ] My tests do not touch the real `~/.coderrr` (everything roots in `tmp_path`)
- [ ] I have tested the changes manually

### Design invariants

- [ ] Write tools remain absent from the model's tool list in Planning mode
- [ ] Path containment stays deterministic code, not a model judgement
- [ ] No new tool runs commands against the user's working tree
- [ ] Tool failures return `ToolResult.error(...)` rather than raising

*If this PR intentionally changes any of the above, explain why below.*

### Documentation

- [ ] I have updated the documentation accordingly
- [ ] I have updated the CHANGELOG.md
- [ ] I have added docstrings for new modules and public functions
- [ ] I have updated the README.md if the changes affect user-facing features

### Dependencies

- [ ] I have not added any unnecessary dependencies
- [ ] If I added dependencies, I updated `pyproject.toml` (and the right extra)

## Breaking Changes

If this PR introduces breaking changes, describe them here and explain the migration path for users:

- Breaking change 1 - How to migrate
- Breaking change 2 - How to migrate

## Additional Notes

Any additional information that reviewers should know.

## Related Issues

List any related issues or PRs:

- Related to #(issue)
- Depends on #(PR)
