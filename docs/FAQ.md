# Frequently Asked Questions (FAQ)

## General Questions

### What is Coderrr?

Coderrr is an AI-powered coding agent that understands natural language requests and autonomously creates, modifies, and manages code. Think of it like having an AI pair programmer that can handle everything from simple file creation to complex multi-file refactoring.

### How is Coderrr different from GitHub Copilot?

| Feature | Coderrr | GitHub Copilot |
|---------|---------|----------------|
| **Scope** | Full file operations, multi-file changes | Inline code suggestions |
| **Autonomy** | Autonomous plan execution | Requires manual acceptance |
| **Interface** | CLI + Programmatic API | IDE extension |
| **File Awareness** | Full codebase scanning | Current file context |
| **Commands** | Can execute shell commands | Code suggestions only |

### What AI models does Coderrr support?

Coderrr supports:
- **GitHub Models** (default): Mistral Large via Azure
- **Mistral AI**: Direct Mistral API access

You can configure this via environment variables in `.env`.

### Is Coderrr free?

Coderrr itself is free and open-source (MIT License). However, you need:
- A GitHub account (for GitHub Models) - **Free tier available**
- Or a Mistral AI API key (paid service)

### Can I use Coderrr offline?

No, Coderrr requires an internet connection to communicate with AI models. However, once you have the generated code, you can work offline.

---

## Installation & Setup

### What are the system requirements?

**Required**:
- Node.js 16+ (for CLI)
- Python 3.8+ (for backend)
- Windows, macOS, or Linux

**Recommended**:
- Node.js 18+ for best compatibility
- Python 3.11 for optimal performance
- PowerShell 5.1+ on Windows

### How do I install Coderrr?

```bash
# Clone the repository
git clone https://github.com/yourusername/coderrr.git
cd coderrr

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Link CLI globally
npm link
```

See [README.md](../README.md) for detailed instructions.

### Why do I need both Node.js and Python?

Coderrr uses a **dual architecture**:
- **Backend (Python/FastAPI)**: Handles AI model communication
- **Frontend (Node.js)**: CLI interface and file operations

This separation allows for flexibility and easier maintenance.

### How do I get a GitHub Token?

1. Go to [GitHub Settings → Developer Settings → Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a name like "Coderrr"
4. Select scopes: No specific scopes needed for GitHub Models
5. Generate and copy the token
6. Add to `.env`: `GITHUB_TOKEN=your_token_here`

---

## Usage Questions

### How do I start using Coderrr?

**Step 1**: Start the backend
```bash
uvicorn main:app --reload --port 5000
```

**Step 2**: Use the CLI
```bash
# Interactive mode
coderrr

# Single command
coderrr exec "your request here"
```

### What kinds of requests can I make?

**File Operations**:
- "Create a Node.js server with Express"
- "Add error handling to server.js"
- "Refactor utils.js to use async/await"
- "Delete old-file.js"

**Code Generation**:
- "Create a REST API for user management"
- "Add JWT authentication"
- "Generate unit tests for calculator.js"

**Project Setup**:
- "Initialize a React project with TypeScript"
- "Set up ESLint and Prettier"
- "Create a .gitignore for Node.js"

**Commands**:
- "Install axios and express"
- "Run tests"
- "Build the project"

### Do I need to approve commands before they run?

**Yes**, by default. Coderrr will:
1. Show you the command
2. Ask for permission (Y/n)
3. Execute if approved
4. Show live output

This is for safety and transparency.

### Can I bypass permission prompts?

Not via CLI for safety reasons. However, in programmatic usage, you can:

```javascript
await executor.execute(command, {
  requirePermission: false  // Use with caution
});
```

### How does Coderrr know about my project structure?

Coderrr has a **Codebase Scanner** that:
1. Automatically scans your project on first request
2. Builds a map of all files and directories
3. Caches results for 1 minute
4. Includes context in AI prompts

This prevents filename mismatches and helps the AI make informed decisions.

### What if the AI makes a mistake?

1. **Use Git**: Always work in a Git repository so you can revert changes
2. **Review changes**: Check what Coderrr created before committing
3. **Iterative fixes**: Ask Coderrr to fix the issue: "Fix the error in server.js"
4. **Manual override**: You can always edit files manually

### Can I undo changes?

Coderrr doesn't have built-in undo. Use Git:

```bash
# Undo uncommitted changes
git checkout -- filename

# Revert a commit
git revert HEAD

# Reset to previous state
git reset --hard HEAD~1
```

**Best practice**: Commit before using Coderrr for major changes.

---

## Backend & Configuration

### Why can't I connect to the backend?

**Check these**:

1. **Is the backend running?**
   ```bash
   curl http://localhost:5000
   # Should return: {"message":"Coderrr backend is running 🚀",...}
   ```

2. **Is the URL correct in .env?**
   ```env
   CODERRR_BACKEND=http://localhost:5000
   ```

3. **Is the port available?**
   - Something else might be using port 5000
   - Try a different port: `uvicorn main:app --reload --port 5001`
   - Update `.env` accordingly

4. **Firewall issues?**
   - Some firewalls block local connections
   - Add an exception for uvicorn/python

### What if I get "mistralai not found" error?

The backend has a fallback mechanism, but for best results:

```bash
# Activate virtual environment (recommended)
# Windows PowerShell:
.\env\Scripts\Activate.ps1

# Windows CMD:
.\env\Scripts\activate.bat

# Linux/Mac:
source env/bin/activate

# Then run backend
uvicorn main:app --reload --port 5000
```

### Can I change the AI model?

Yes, edit `.env`:

```env
# For GitHub Models
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411  # or other models

# For Mistral AI direct
MISTRAL_ENDPOINT=https://api.mistral.ai
MISTRAL_MODEL=mistral-large-latest
MISTRAL_API_KEY=your_mistral_key
```

### How do I increase request timeout?

Edit `.env`:

```env
TIMEOUT_MS=300000  # 5 minutes (default is 120000 = 2 minutes)
```

---

## Troubleshooting

### Coderrr created the wrong files

**Possible causes**:
1. **Ambiguous request**: Be more specific
2. **Cache issue**: Refresh codebase scan:
   ```bash
   coderrr exec "refresh codebase scan and then [your request]"
   ```
3. **Context misunderstanding**: Provide more details

**Solutions**:
- Delete wrong files and try again with clearer instructions
- Use specific filenames: "Create server.js in the src/ directory"
- Mention existing files: "Add a function to the existing utils.js"

### JSON parse errors

**Error**: "Failed to parse JSON response"

**Causes**:
- Backend returned invalid JSON
- AI model didn't follow the expected format
- Network corruption

**Solutions**:
1. Check backend logs for raw response
2. Try again (sometimes AI has a bad output)
3. Reduce request complexity
4. Check `MISTRAL_MODEL` in `.env`

### Tests are failing

**After Coderrr generates code**:

1. **Review the code**: AI-generated code may need tweaking
2. **Install dependencies**: `npm install` or `pip install -r requirements.txt`
3. **Check test configuration**: Ensure test framework is set up correctly
4. **Run manually**: `npm test` or `pytest` to see detailed errors

### Permission denied errors

**On Windows**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**On Linux/Mac**:
```bash
chmod +x bin/coderrr.js
```

### High memory usage

**Codebase scanner caching**:
- Clear cache periodically: Restart CLI or use `refreshCodebase()`
- Ignore large directories: Add to scanner ignore patterns

**Backend**:
- Large responses use more memory
- Reduce `max_tokens` in requests

---

## Advanced Usage

### Can I use Coderrr programmatically?

Yes! See [examples/07-programmatic.md](../examples/07-programmatic.md):

```javascript
const Agent = require('coderrr/src/agent');

const agent = new Agent();
await agent.process('Create a REST API');
```

### Can I integrate Coderrr into my CI/CD?

Yes! See the example in [examples/07-programmatic.md](../examples/07-programmatic.md#example-7-cicd-integration).

You can create automated pipelines that use Coderrr to generate code, run tests, and more.

### How do I add custom file operations?

Edit `src/fileOps.js`:

```javascript
class FileOperations {
  async customOperation(params) {
    // Your implementation
  }
  
  async execute(operation) {
    switch (operation.action) {
      case 'custom_operation':
        return await this.customOperation(operation);
      // ... existing cases
    }
  }
}
```

### Can I use a different backend?

Yes! Coderrr's frontend can connect to any backend that implements the `/chat` endpoint:

```env
CODERRR_BACKEND=https://my-custom-backend.com
```

Your backend must:
- Accept `POST /chat` with `{prompt, temperature, max_tokens, top_p}`
- Return `{response: "JSON-formatted plan"}`

---

## Security & Privacy

### Is my code sent to external servers?

**Yes**, when you make requests:
- Your prompts and codebase context are sent to the AI model
- GitHub Models or Mistral AI process the requests
- Responses are returned to your local machine

**Never sent**:
- `.env` files (ignored by scanner)
- `node_modules/`, `env/` directories
- Large files (>500KB)
- Files in `.gitignore` patterns

### Should I use Coderrr with sensitive code?

**Considerations**:
- Review your organization's policies on using AI tools
- Coderrr sends code context to third-party AI services
- Consider self-hosting if you need full privacy
- Don't include sensitive credentials in code files

**Best practices**:
- Use environment variables for secrets
- Review generated code before committing
- Enable Git pre-commit hooks
- Use in development environments first

### How do I report security vulnerabilities?

See [SECURITY.md](../SECURITY.md) for our security policy.

**Quick summary**:
- Email security issues (don't open public issues)
- Include detailed reproduction steps
- Allow time for fixes before disclosure

---

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.

**Quick ways to contribute**:
- Report bugs
- Suggest features
- Improve documentation
- Submit pull requests
- Share examples

### What should I know before contributing?

1. **Architecture**: Read [docs/ARCHITECTURE.md](ARCHITECTURE.md)
2. **Setup**: Follow development setup in [CONTRIBUTING.md](../CONTRIBUTING.md)
3. **Code style**: Follow existing patterns (JavaScript + Python)
4. **Testing**: Run tests before submitting PRs

### Where do I ask questions?

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For general questions and ideas
- **Documentation**: Check docs/ first

---

## Performance

### How fast is Coderrr?

**Typical timings**:
- Codebase scan: <10ms (cached: instant)
- Simple request: 2-5 seconds
- Complex multi-file request: 10-30 seconds
- Command execution: Depends on the command

**Factors affecting speed**:
- AI model response time
- Network latency
- Request complexity
- Codebase size

### Can I make Coderrr faster?

1. **Reduce context**: Smaller codebases scan faster
2. **Use cache**: Avoid `forceRefresh` unless needed
3. **Lower `max_tokens`**: Faster AI responses
4. **Simpler requests**: Break complex tasks into steps
5. **Local backend**: Run backend on the same machine

### Does Coderrr work with large codebases?

**Yes**, but with considerations:

- Codebase scanner has a **500KB file size limit**
- Scans can take longer (but results are cached)
- AI context window limits may require focused requests

**For very large projects**:
- Use specific directory paths in requests
- Work in focused areas
- Consider clearing cache periodically

---

## Compatibility

### What operating systems are supported?

- ✅ Windows 10/11 (PowerShell)
- ✅ macOS (Catalina and later)
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)

### What shells are supported?

- ✅ PowerShell (Windows default)
- ✅ Bash (Linux/Mac default)
- ✅ Zsh (Mac default)
- ⚠️ CMD (limited support)

### Can I use Coderrr in WSL?

Yes! Coderrr works great in WSL:

```bash
# In WSL terminal
cd /mnt/c/your/project
coderrr
```

### Does Coderrr work with monorepos?

Yes! The codebase scanner handles complex directory structures. For best results:
- Specify which package to work on
- Use relative paths from the root

---

## Licensing & Legal

### What license is Coderrr under?

**MIT License** - see [LICENSE](../LICENSE)

You can:
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Use privately

### Can I use Coderrr in commercial projects?

Yes! The MIT License allows commercial use. However:
- Check the licenses of AI services you use (GitHub Models, Mistral AI)
- Review your organization's policies on AI-generated code

### Do I own the code Coderrr generates?

**Yes**, but:
- AI-generated code may not be copyrightable in all jurisdictions
- You're responsible for ensuring generated code doesn't violate licenses
- Review and modify generated code as needed

---

Still have questions? [Open an issue](https://github.com/yourusername/coderrr/issues) or check the [documentation](../docs/).
