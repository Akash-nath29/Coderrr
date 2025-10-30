# Self-Healing Feature Documentation

## Overview

Coderrr now includes an **intelligent self-healing mechanism** that automatically retries failed steps with AI-generated fixes. When a command fails or a file operation encounters an error, the agent:

1. ✅ Captures the error message
2. 🔧 Sends error context to the AI backend
3. 💡 Receives a corrected version of the failed step
4. 🔄 Retries the step with the fix
5. 📊 Reports success or escalates to user after max retries

---

## How It Works

### Before (Without Self-Healing):

```
Step 1: Create file ✓
Step 2: Run tests ✗ ERROR: file not found
Step 3: Install deps (SKIPPED)
```

User has to manually fix and rerun.

### After (With Self-Healing):

```
Step 1: Create file ✓
Step 2: Run tests ✗ ERROR: file not found
  → Analyzing error...
  → Fix: Creating missing test file first
  → Retry 1: Create test file ✓
  → Retry 1: Run tests ✓
Step 3: Install deps ✓
```

Agent automatically fixes the issue and continues!

---

## Usage

### Default Behavior (Self-Healing Enabled)

```bash
coderrr
# Automatically retries failed steps up to 2 times
```

### Disable Self-Healing

```bash
coderrr --no-auto-retry
# Stops on first error, no automatic fixes
```

### Custom Retry Count

```bash
coderrr --max-retries 5
# Attempts each failed step up to 5 times
```

### Programmatic Usage

```javascript
const Agent = require('coderrr-cli/src/agent');

const agent = new Agent({
  autoRetry: true,    // Enable self-healing
  maxRetries: 3       // Try up to 3 times per step
});

await agent.process('Create a web server');
```

---

## Examples

### Example 1: Missing Test File

**User Request:** "Add tests for calculator"

**Initial Plan:**
1. Create calculator.js ✓
2. Run tests with `npm test` ✗

**Error:** `Missing script: "test"`

**Self-Healing:**
- AI detects missing test script in package.json
- Generates fix: Add test script to package.json
- Retries with corrected package.json
- Tests now run successfully ✓

### Example 2: Wrong File Path

**User Request:** "Update the authentication module"

**Initial Plan:**
1. Read auth.js ✗

**Error:** `File not found: auth.js`

**Self-Healing:**
- AI scans codebase context
- Detects correct path: `src/auth/authentication.js`
- Retries with correct path
- File updated successfully ✓

### Example 3: Missing Dependencies

**User Request:** "Create Express server"

**Initial Plan:**
1. Create server.js ✓
2. Run server with `node server.js` ✗

**Error:** `Cannot find module 'express'`

**Self-Healing:**
- AI detects missing dependency
- Generates fix: Run `npm install express` first
- Inserts installation step
- Server starts successfully ✓

---

## Configuration

### Agent Constructor Options

```javascript
new Agent({
  autoRetry: boolean,     // Enable/disable self-healing (default: true)
  maxRetries: number,     // Max attempts per step (default: 2)
  autoTest: boolean,      // Auto-run tests (default: true)
  // ... other options
})
```

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--no-auto-retry` | Disable self-healing | Enabled |
| `--max-retries <n>` | Max retry attempts | 2 |
| `--no-auto-test` | Disable auto-testing | Enabled |

---

## How Self-Healing Works Internally

### 1. Error Detection

```javascript
// Command fails
const result = await executor.execute(step.command);
if (!result.success) {
  // Trigger self-healing
}
```

### 2. Error Analysis

Agent sends context to AI:
```json
{
  "failed_step": {
    "action": "run_command",
    "command": "npm test",
    "summary": "Run tests"
  },
  "error": "Missing script: \"test\"",
  "context": {
    "working_directory": "/path/to/project",
    "attempt_number": 1,
    "available_files": ["package.json", "src/index.js", ...]
  }
}
```

### 3. Fix Generation

AI analyzes error and returns:
```json
{
  "explanation": "Missing test script in package.json. Adding it now.",
  "fixed_step": {
    "action": "update_file",
    "path": "package.json",
    "content": "{ ... \"test\": \"jest\" ... }",
    "summary": "Add test script to package.json"
  }
}
```

### 4. Retry with Fix

Agent applies the fix and retries the original step.

### 5. Success or Escalation

- **Success:** Marks step as complete, continues to next step
- **Failure:** Tries up to `maxRetries` times
- **Max Retries Exceeded:** Asks user whether to continue with remaining steps

---

## Best Practices

### ✅ DO:

- **Use default settings** for most cases (2 retries)
- **Enable self-healing** for long-running tasks
- **Monitor fixes** to learn common error patterns
- **Adjust maxRetries** based on task complexity

### ❌ DON'T:

- **Set maxRetries too high** (wastes time/API calls)
- **Disable for critical production** tasks without supervision
- **Rely solely on self-healing** for badly structured requests

---

## Error Types That Self-Healing Can Fix

### ✅ Automatically Fixable:

- Missing files or incorrect paths
- Missing dependencies
- Missing configuration (package.json scripts, etc.)
- Wrong command syntax
- File permission issues (sometimes)
- Missing directories

### ❌ Cannot Fix Automatically:

- Network/API failures (external services down)
- Authentication errors (invalid credentials)
- System-level permissions (sudo required)
- Hardware issues (out of disk space)
- Logic errors in user's code

---

## Performance Considerations

- **API Calls:** Each retry makes 1 additional API call to backend
- **Time:** ~2-5 seconds per retry attempt
- **Cost:** Self-healing uses same backend as normal requests

**Recommendation:** Use default 2 retries for good balance of reliability vs. speed.

---

## Monitoring Self-Healing

### Success Metrics

The agent logs all retry attempts:
```
ℹ Step 2/5: Run tests
✗ Command failed (attempt 1/3)
🔧 Analyzing error and generating fix...
💡 Fix: Missing test script in package.json
✓ Retry successful!
```

### Summary Report

After execution:
```
▶ Execution Summary
✓ Completed: 5/5 tasks
🔧 Self-healed: 2 steps (40% success rate)
```

---

## Future Enhancements

Planned improvements:
- [ ] Learn from previous fixes (caching)
- [ ] Suggest preventive fixes before errors occur
- [ ] Multi-step healing (fix dependencies recursively)
- [ ] User feedback on fix quality
- [ ] Healing statistics dashboard

---

## Troubleshooting

### Self-Healing Not Working?

1. **Check backend connectivity:**
   ```bash
   curl https://coderrr-backend.vercel.app
   ```

2. **Verify autoRetry is enabled:**
   ```bash
   coderrr --max-retries 2  # Should work
   coderrr --no-auto-retry  # Disables self-healing
   ```

3. **Check error logs:**
   - Look for "🔧 Analyzing error..." messages
   - If missing, self-healing isn't triggering

### Too Many Retries?

```bash
# Reduce retry count
coderrr --max-retries 1
```

### Want to See What's Being Fixed?

Enable verbose mode (coming soon):
```bash
coderrr --verbose
```

---

## Contributing

Want to improve self-healing? See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Adding new error patterns
- Improving fix generation prompts
- Testing self-healing scenarios

---

**Self-healing makes Coderrr truly autonomous!** 🤖✨
