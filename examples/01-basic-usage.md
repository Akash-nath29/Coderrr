# Basic Usage Examples

## Example 1: Create a Simple Script

**Scenario**: You want to create a Node.js script that prints "Hello, World!".

**Request**:
```bash
coderrr exec "Create a simple Node.js script that prints Hello World"
```

**Expected Result**:

Coderrr will create `hello.js`:
```javascript
console.log('Hello, World!');
```

**Tips**:
- Be specific about the filename if you have preferences
- Specify the language/framework if ambiguous

---

## Example 2: Create a Configuration File

**Scenario**: You need a `.eslintrc.json` for your JavaScript project.

**Request**:
```bash
coderrr exec "Create an ESLint configuration file with recommended rules for Node.js"
```

**Expected Result**:

Creates `.eslintrc.json`:
```json
{
  "env": {
    "node": true,
    "es2021": true
  },
  "extends": "eslint:recommended",
  "parserOptions": {
    "ecmaVersion": 12
  },
  "rules": {
    "indent": ["error", 2],
    "quotes": ["error", "single"],
    "semi": ["error", "always"]
  }
}
```

**Tips**:
- Specify the style (e.g., "with semicolons", "using single quotes")
- Mention any specific rules you want

---

## Example 3: Create Multiple Related Files

**Scenario**: You need a package.json and a .gitignore for a new project.

**Request**:
```bash
coderrr exec "Initialize a Node.js project with package.json and .gitignore"
```

**Expected Result**:

Creates `package.json`:
```json
{
  "name": "my-project",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "ISC"
}
```

And `.gitignore`:
```
node_modules/
.env
.DS_Store
*.log
```

**Tips**:
- Group related files in a single request
- Specify project name/details if you want them customized

---

## Example 4: Read and Explain Code

**Scenario**: You have a file and want to understand what it does.

**Request**:
```bash
coderrr exec "Read server.js and explain what it does"
```

**Expected Result**:

Coderrr will read the file and provide an explanation:
```
Explanation: This file creates an Express.js server that:
1. Listens on port 3000
2. Serves static files from the 'public' directory
3. Has a /api/users endpoint that returns JSON data
4. Includes error handling middleware
...
```

**Tips**:
- Ask specific questions: "explain the authentication logic in server.js"
- Request summaries: "summarize what auth.js does"

---

## Example 5: Fix a Simple Bug

**Scenario**: Your script has a typo or small error.

**Request**:
```bash
coderrr exec "Fix the syntax error in calculator.js"
```

**Expected Result**:

Coderrr will:
1. Read `calculator.js`
2. Identify the error (e.g., missing semicolon, typo)
3. Patch the file with the fix
4. Show you what was changed

**Tips**:
- Be specific about the error if you know it
- Coderrr automatically detects common issues

---

## Example 6: Add a Simple Feature

**Scenario**: You want to add logging to an existing script.

**Request**:
```bash
coderrr exec "Add console logging to track function calls in utils.js"
```

**Expected Result**:

Coderrr will update `utils.js` to add `console.log()` statements:
```javascript
function calculateTotal(items) {
  console.log('calculateTotal called with:', items);
  // ... existing code ...
  console.log('calculateTotal returning:', total);
  return total;
}
```

**Tips**:
- Specify what to log: "log input and output", "log errors only"
- Mention logging library if preferred: "add Winston logging"

---

## Example 7: Generate Documentation

**Scenario**: You need a README for your project.

**Request**:
```bash
coderrr exec "Create a README.md for this project with installation and usage instructions"
```

**Expected Result**:

Creates `README.md`:
```markdown
# My Project

## Installation

\`\`\`bash
npm install
\`\`\`

## Usage

\`\`\`javascript
const app = require('./index');
app.start();
\`\`\`

## Features

- Feature 1
- Feature 2
...
```

**Tips**:
- Coderrr scans your codebase to generate relevant docs
- Specify sections you want: "include API reference"

---

## Example 8: Run Commands

**Scenario**: You want to install dependencies or run tests.

**Request**:
```bash
coderrr exec "Install axios and express packages"
```

**Expected Result**:

Coderrr will:
1. Show you the command: `npm install axios express`
2. Ask for permission to run it
3. Execute the command
4. Show the output

**Tips**:
- All commands require your permission
- You can decline and run manually if preferred

---

## Common Patterns

### 1. Chain Multiple Actions

```bash
coderrr exec "Create index.js with a basic Express server, add a .env file with PORT=3000, and create a start script in package.json"
```

### 2. Context-Aware Requests

```bash
# Coderrr knows about your existing files
coderrr exec "Add error handling to the existing routes in server.js"
```

### 3. Interactive Mode for Iteration

```bash
coderrr  # Start interactive mode

? What would you like me to do? Create a calculator app
[... Coderrr creates files ...]

? What would you like me to do? Add a square root function
[... Coderrr adds the feature ...]

? What would you like me to do? Add tests
[... Coderrr creates tests ...]
```

---

## Next Steps

- See [File Operations](./02-file-operations.md) for advanced file manipulation
- See [Web Development](./03-web-development.md) for building web apps
- See [Programmatic Usage](./07-programmatic.md) for using Coderrr in your own scripts
