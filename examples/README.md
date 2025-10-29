# Coderrr Examples

This directory contains practical examples of using Coderrr for various tasks.

## Examples

1. [Basic Usage](./01-basic-usage.md) - Getting started with simple requests
2. [File Operations](./02-file-operations.md) - Creating, updating, and managing files
3. [Web Development](./03-web-development.md) - Building web applications
4. [API Development](./04-api-development.md) - Creating REST APIs
5. [Testing](./05-testing.md) - Adding tests to your projects
6. [Refactoring](./06-refactoring.md) - Improving existing code
7. [Programmatic Usage](./07-programmatic.md) - Using Coderrr as a library
8. [Advanced](./08-advanced.md) - Complex multi-step projects

## Quick Start

Each example includes:
- **Scenario**: What you're trying to accomplish
- **Request**: The natural language prompt to use
- **Expected Result**: What Coderrr will create/modify
- **Tips**: Best practices and gotchas

## Running Examples

### CLI Mode

```bash
# Single command
coderrr exec "your request here"

# Interactive mode
coderrr
? What would you like me to do? your request here
```

### Programmatic Mode

```javascript
const Agent = require('./src/agent');
const agent = new Agent();
await agent.process('your request here');
```

## Contributing Examples

Have a great example? Add it to this directory! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
