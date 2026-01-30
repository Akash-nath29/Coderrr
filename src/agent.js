const axios = require('axios');
const fs = require('fs');
const path = require('path');
const ui = require('./ui');
const FileOperations = require('./fileOps');
const CommandExecutor = require('./executor').CommandExecutor;
const TodoManager = require('./todoManager');
const CodebaseScanner = require('./codebaseScanner');
const GitOperations = require('./gitOps');
const { sanitizeAxiosError, formatUserError, createSafeError, isNetworkError } = require('./errorHandler');
const configManager = require('./configManager');
const { getProvider } = require('./providers');

/**
 * Core AI Agent that communicates with backend and executes plans
 */

class Agent {
  /**
   * Creates a new Agent instance with configurable options
   *
   * @param {Object} options - Configuration options for the agent
   * @param {string} options.backendUrl - URL of the AI backend service (default: hosted backend)
   * @param {string} options.workingDir - Working directory for file operations (default: process.cwd())
   * @param {boolean} options.autoTest - Whether to run tests automatically after successful execution (default: true)
   * @param {boolean} options.autoRetry - Whether to enable self-healing retry mechanism (default: true)
   * @param {number} options.maxRetries - Maximum retry attempts per failed step (default: 2)
   * @param {boolean} options.scanOnFirstRequest - Whether to scan codebase on first request (default: true)
   * @param {boolean} options.gitEnabled - Whether to enable Git integration features (default: false)
   */
  constructor(options = {}) {
    // Default to hosted backend, can be overridden via options or env var
    const DEFAULT_BACKEND = 'https://coderrr-backend.vercel.app';
    this.backendUrl = options.backendUrl || process.env.CODERRR_BACKEND || DEFAULT_BACKEND;

    this.workingDir = options.workingDir || process.cwd();
    this.fileOps = new FileOperations(this.workingDir);
    this.executor = new CommandExecutor();
    this.todoManager = new TodoManager();
    this.scanner = new CodebaseScanner(this.workingDir);
    this.git = new GitOperations(this.workingDir);
    this.autoTest = options.autoTest !== false; // Default to true
    this.autoRetry = options.autoRetry !== false; // Default to true - self-healing on errors
    this.maxRetries = options.maxRetries || 2; // Default 2 retries per step
    this.codebaseContext = null; // Cached codebase structure
    this.scanOnFirstRequest = options.scanOnFirstRequest !== false; // Default to true
    this.gitEnabled = options.gitEnabled || false; // Git auto-commit feature (opt-in)
    this.maxHistoryLength = options.maxHistoryLength || 10; // Max conversation turns to keep
    this.skillsPrompt = null; // Skills prompt from Skills.md (persistent skills)
    this.customPrompt = null; // Custom system prompt from Coderrr.md (task-specific)

    // Initialize project-local storage and load cross-session memory
    configManager.initializeProjectStorage(this.workingDir);
    this.conversationHistory = configManager.loadProjectMemory(this.workingDir);

    // Load user provider configuration
    this.providerConfig = configManager.getConfig();

    // Track running processes spawned in separate terminals
    this.runningProcesses = [];

    // Register cleanup handler for when Coderrr exits
    this.registerExitCleanup();
  }

  /**
   * Register cleanup handler to terminate spawned processes on exit
   */
  registerExitCleanup() {
    const cleanup = async () => {
      if (this.runningProcesses.length > 0) {
        ui.info(`Cleaning up ${this.runningProcesses.length} running process(es)...`);
        for (const proc of this.runningProcesses) {
          if (proc && typeof proc.stop === 'function') {
            try {
              const isRunning = await proc.isRunning();
              if (isRunning) {
                await proc.stop();
              }
              if (proc.stopMonitoring) {
                proc.stopMonitoring();
              }
            } catch (e) {
              // Ignore cleanup errors
            }
          }
        }
      }
    };

    // Handle various exit signals
    process.on('exit', cleanup);
    process.on('SIGINT', async () => {
      await cleanup();
      process.exit(0);
    });
    process.on('SIGTERM', async () => {
      await cleanup();
      process.exit(0);
    });
  }

  /**
   * Add a message to conversation history
   * @param {string} role - 'user' or 'assistant'
   * @param {string} content - Message content
   */
  addToHistory(role, content) {
    this.conversationHistory.push({ role, content });

    // Trim history if it exceeds max length (keep most recent)
    // Each turn = 2 messages (user + assistant), so maxHistoryLength * 2
    const maxMessages = this.maxHistoryLength * 2;
    if (this.conversationHistory.length > maxMessages) {
      this.conversationHistory = this.conversationHistory.slice(-maxMessages);
    }

    // Persist to disk for cross-session memory
    configManager.saveProjectMemory(this.workingDir, this.conversationHistory);
  }

  /**
   * Clear conversation history (useful for starting fresh)
   */
  clearHistory() {
    this.conversationHistory = [];
    configManager.clearProjectMemory(this.workingDir);
    ui.info('Conversation history cleared');
  }

  /**
   * Load skills prompt from Skills.md in project directory
   * Skills are persistent guidance that applies to all tasks (e.g., design guidelines)
   */
  loadSkillsPrompt() {
    try {
      const skillsPath = path.join(this.workingDir, 'Skills.md');
      if (fs.existsSync(skillsPath)) {
        this.skillsPrompt = fs.readFileSync(skillsPath, 'utf8').trim();
        ui.info('Loaded skills from Skills.md');
      }
    } catch (error) {
      ui.warning(`Could not load Skills.md: ${error.message}`);
    }
  }

  /**
   * Load custom system prompt from Coderrr.md in project directory
   * This is task-specific guidance that may change per task
   */
  loadCustomPrompt() {
    try {
      const customPromptPath = path.join(this.workingDir, 'Coderrr.md');
      if (fs.existsSync(customPromptPath)) {
        this.customPrompt = fs.readFileSync(customPromptPath, 'utf8').trim();
        ui.info('Loaded task prompt from Coderrr.md');
      }
    } catch (error) {
      ui.warning(`Could not load Coderrr.md: ${error.message}`);
    }
  }

  /**
   * Get formatted conversation history for the backend
   * Limits to 20 items and 5000 chars per message to match backend validation
   */
  getFormattedHistory() {
    // Backend limits: max_items=20, content max_length=5000
    const MAX_HISTORY_ITEMS = 20;
    const MAX_CONTENT_LENGTH = 5000;

    // Take only the most recent items that fit the limit
    const recentHistory = this.conversationHistory.slice(-MAX_HISTORY_ITEMS);

    return recentHistory.map(msg => ({
      role: msg.role,
      content: msg.content.length > MAX_CONTENT_LENGTH
        ? msg.content.substring(0, MAX_CONTENT_LENGTH)
        : msg.content
    }));
  }

  /**
   * Send a prompt to the AI backend
   */
  async chat(prompt, options = {}) {
    try {
      // Load skills prompt on first request if not already loaded
      if (this.skillsPrompt === null) {
        this.loadSkillsPrompt();
      }

      // Load custom prompt on first request if not already loaded
      if (this.customPrompt === null) {
        this.loadCustomPrompt();
      }

      // Scan codebase on first request if enabled
      if (this.scanOnFirstRequest && !this.codebaseContext) {
        const scanSpinner = ui.spinner('Scanning codebase...');
        scanSpinner.start();
        try {
          const scanResult = this.scanner.scan();
          this.codebaseContext = this.scanner.getSummaryForAI();
          scanSpinner.stop();
          ui.success(`Scanned ${scanResult.summary.totalFiles} files in ${scanResult.summary.totalDirectories} directories`);
        } catch (scanError) {
          scanSpinner.stop();
          ui.warning(`Could not scan codebase: ${scanError.message}`);
        }
      }

      // Build enhanced prompt with priority:
      // 1. System Prompt (embedded in backend)
      // 2. Skills.md (persistent skills)
      // 3. Coderrr.md (task-specific guidance)
      // 4. User prompt
      let enhancedPrompt = prompt;

      // Prepend task-specific prompt (Coderrr.md) if available
      if (this.customPrompt) {
        enhancedPrompt = `[TASK GUIDANCE]\n${this.customPrompt}\n\n[USER REQUEST]\n${enhancedPrompt}`;
      }

      // Prepend skills prompt (Skills.md) if available - comes before task prompt
      if (this.skillsPrompt) {
        enhancedPrompt = `[SKILLS]\n${this.skillsPrompt}\n\n${enhancedPrompt}`;
      }

      if (this.codebaseContext) {
        const osType = process.platform === 'win32' ? 'Windows' :
          process.platform === 'darwin' ? 'macOS' : 'Linux';

        enhancedPrompt = `${enhancedPrompt}

SYSTEM ENVIRONMENT:
Operating System: ${osType}
Platform: ${process.platform}
Node Version: ${process.version}

EXISTING PROJECT STRUCTURE:
Working Directory: ${this.codebaseContext.structure.workingDir}
Total Files: ${this.codebaseContext.structure.totalFiles}
Total Directories: ${this.codebaseContext.structure.totalDirectories}
DIRECTORIES:
${this.codebaseContext.directories.slice(0, 20).join('\n')}
EXISTING FILES:
${this.codebaseContext.files.slice(0, 30).map(f => `- ${f.path} (${f.size} bytes)`).join('\n')}

When editing existing files, use EXACT filenames from the list above. When creating new files, ensure they don't conflict with existing ones.
For command execution on ${osType}, use appropriate command separators (${osType === 'Windows' ? 'semicolon (;)' : 'ampersand (&&)'}).`;
      }

      const spinner = ui.spinner('Thinking...');
      spinner.start();

      // Include conversation history for context continuity
      const requestPayload = {
        prompt: enhancedPrompt,
        temperature: options.temperature || 0.2,
        max_tokens: options.max_tokens || 2000,
        top_p: options.top_p || 1.0
      };

      // Add provider configuration if user has configured one
      if (this.providerConfig) {
        requestPayload.provider = this.providerConfig.provider;
        requestPayload.api_key = this.providerConfig.apiKey;
        requestPayload.model = this.providerConfig.model;
        if (this.providerConfig.endpoint) {
          requestPayload.endpoint = this.providerConfig.endpoint;
        }
      }

      // Add conversation history if available (for multi-turn conversations)
      if (this.conversationHistory.length > 0) {
        requestPayload.conversation_history = this.getFormattedHistory();
      }

      const response = await axios.post(`${this.backendUrl}/chat`, requestPayload);

      spinner.stop();

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      // Handle both new format (direct object with explanation/plan) and legacy format (wrapped in response)
      return response.data.response || response.data;
    } catch (error) {
      // Sanitize error to prevent logging sensitive data
      const sanitized = sanitizeAxiosError(error);
      const userMessage = formatUserError(sanitized, this.backendUrl);

      if (isNetworkError(error)) {
        ui.error(`Cannot connect to backend at ${this.backendUrl}`);
        ui.warning('Make sure the backend is running:');
        console.log('  uvicorn main:app --reload --port 5000');
      } else {
        ui.error(`Failed to communicate with backend: ${userMessage}`);
      }

      // Throw a sanitized error, not the raw Axios error with sensitive data
      throw createSafeError(error);
    }
  }

  /**
   * Parse JSON from AI response (handles markdown code blocks)
   */
  parseJsonResponse(text) {
    try {
      // Try direct JSON parse first
      return JSON.parse(text);
    } catch (e) {
      // Try to extract JSON from markdown code blocks
      const jsonMatch = text.match(/```json\s*\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[1]);
        } catch (e2) {
          // Fall through
        }
      }

      // Try to find any JSON object in the text
      const objectMatch = text.match(/\{[\s\S]*\}/);
      if (objectMatch) {
        try {
          return JSON.parse(objectMatch[0]);
        } catch (e3) {
          // Fall through
        }
      }

      throw new Error('Could not parse JSON from response');
    }
  }

  /**
   * Check if an error is retryable (can be fixed by AI) or non-retryable (config/permission issue)
   * Non-retryable errors should skip AI retry and immediately ask user
   */
  isRetryableError(errorMessage) {
    const nonRetryablePatterns = [
      /file already exists/i,
      /already exists/i,
      /permission denied/i,
      /access is denied/i,
      /EEXIST/i,
      /EACCES/i,
      /EPERM/i,
      /ENOENT.*no such file or directory/i,
      /invalid path/i,
      /path too long/i,
      /ENAMETOOLONG/i,
      /cannot create directory/i,
      /directory not empty/i,
      /ENOTEMPTY/i,
      /read-only file system/i,
      /EROFS/i,
      /disk quota exceeded/i,
      /EDQUOT/i,
      /no space left/i,
      /ENOSPC/i,
    ];

    const isNonRetryable = nonRetryablePatterns.some(pattern => pattern.test(errorMessage));
    return !isNonRetryable;
  }

  /**
   * Execute a plan with self-healing retry mechanism
   *
   * This method processes each step in the plan, handling both file operations and command execution.
   * It includes automatic retry logic for failed steps using AI-generated fixes when enabled.
   * The retry mechanism distinguishes between retryable errors (logic issues that AI can fix)
   * and non-retryable errors (permission/config issues that require user intervention).
   *
   * @param {Array<Object>} plan - Array of operation objects from AI response
   * @param {string} plan[].action - Operation type ('create_file', 'update_file', 'patch_file', 'delete_file', 'read_file', 'run_command')
   * @param {string} plan[].path - File path for file operations
   * @param {string} plan[].content - File content for create/update operations
   * @param {string} plan[].command - Shell command for run_command operations
   * @param {string} plan[].summary - Human-readable description of the step
   * @returns {Promise<Object>} Execution statistics {completed, total, pending}
   */
  async executePlan(plan) {
    if (!Array.isArray(plan) || plan.length === 0) {
      ui.warning('No plan to execute');
      return { stats: { completed: 0, total: 0, pending: 0 }, executionLog: [] };
    }

    const executionLog = [];

    // Parse and display TODOs
    this.todoManager.parseTodos(plan);
    this.todoManager.display();

    // Git pre-execution hook
    if (this.gitEnabled) {
      const gitValid = await this.git.validateGitSetup();
      if (gitValid) {
        // Check for uncommitted changes
        const canProceed = await this.git.checkUncommittedChanges();
        if (!canProceed) {
          ui.warning('Execution cancelled by user');
          return;
        }
        // Create checkpoint
        const planDescription = plan[0]?.summary || 'Execute plan';
        await this.git.createCheckpoint(planDescription);
      }
    }

    ui.section('Executing Plan');

    // Track completed steps for context in self-healing
    const completedSteps = [];

    // Execute each step
    for (let i = 0; i < plan.length; i++) {
      const step = plan[i];
      this.todoManager.setInProgress(i);

      ui.info(`Step ${i + 1}/${plan.length}: ${step.summary || step.action}`);

      let retryCount = 0;
      let stepSuccess = false;
      let stepResult = null;

      while (!stepSuccess && retryCount <= this.maxRetries) {
        try {
          if (step.action === 'run_command') {
            // Execute command in a separate terminal window
            // This prevents long-running or infinite loop commands from blocking Coderrr
            const result = await this.executor.executeInSeparateTerminal(step.command, {
              requirePermission: true,
              cwd: this.workingDir,
              monitorOutput: true
            });

            if (result.cancelled) {
              ui.warning('Command cancelled by user');
              stepSuccess = true; // Consider cancelled as completed
              stepResult = `Cancelled command: "${step.command}"`;
            } else if (result.success) {
              stepResult = `Started command in separate terminal: "${step.command}"`;
              stepSuccess = true;

              // Store the process handle for potential cleanup later
              if (!this.runningProcesses) {
                this.runningProcesses = [];
              }
              this.runningProcesses.push(result);

              ui.info('Command is running in separate terminal. Coderrr remains responsive.');
              ui.info('The terminal window will show the command output.');
            } else {
              const errorMsg = result.error || 'Unknown error';
              stepResult = `Failed to start command: "${step.command}". Error: ${errorMsg}`;

              // Check if this error is retryable (can be fixed by AI)
              if (!this.isRetryableError(errorMsg)) {
                ui.error(`Non-retryable error: ${errorMsg}`);
                ui.warning('This type of error cannot be auto-fixed (file/permission/config issue)');
                break; // Don't retry, let the outer loop ask user what to do
              }

              // Command failed - attempt self-healing if enabled and error is retryable
              if (this.autoRetry && retryCount < this.maxRetries) {
                ui.warning(`Command failed (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
                ui.info('Analyzing error and generating fix...');

                const fixedStep = await this.selfHeal(step, errorMsg, retryCount, completedSteps);

                if (fixedStep && this.validateFixedStep(fixedStep)) {
                  Object.assign(step, fixedStep);
                  retryCount++;
                  continue; // Retry with fixed command
                } else {
                  ui.error('Could not generate automatic fix');
                  break;
                }
              } else {
                ui.error(`Command failed${this.autoRetry ? ` after ${this.maxRetries + 1} attempts` : ''}, stopping execution`);
                break;
              }
            }
          } else {
            // File operation
            const result = await this.fileOps.execute(step);
            stepResult = `${step.action}: "${step.path}"`;
            stepSuccess = true;

            // Display diff if available (for create, update, patch, delete)
            if (result && (result.oldContent !== undefined || result.newContent !== undefined)) {
              ui.displayDiff(step.path, result.oldContent, result.newContent);
            }
          }

          if (stepSuccess) {
            this.todoManager.complete(i);
            executionLog.push(`✓ Step ${i + 1}: ${stepResult}`);
            // Track completed step for context in case later steps fail
            completedSteps.push({ ...step, result: stepResult });
          }
        } catch (error) {
          const errorMsg = error.message || 'Unknown error';

          // Check if this error is retryable (can be fixed by AI)
          if (!this.isRetryableError(errorMsg)) {
            ui.error(`Non-retryable error: ${errorMsg}`);
            ui.warning('This type of error cannot be auto-fixed (file/permission/config issue)');
            break; // Don't retry, let the outer loop ask user what to do
          }

          if (!stepSuccess && retryCount === this.maxRetries) {
            executionLog.push(`✗ Step ${i + 1} Failed: ${error.message}`);
          }

          if (this.autoRetry && retryCount < this.maxRetries) {
            ui.warning(`Step failed: ${errorMsg} (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
            ui.info('Analyzing error and generating fix...');

            const fixedStep = await this.selfHeal(step, errorMsg, retryCount, completedSteps);

            if (fixedStep && this.validateFixedStep(fixedStep)) {
              Object.assign(step, fixedStep);
              retryCount++;
              continue; // Retry with fixed step
            } else {
              ui.error('Could not generate automatic fix');
              break;
            }
          } else {
            ui.error(`Failed to execute step${this.autoRetry ? ` after ${this.maxRetries + 1} attempts` : ''}: ${errorMsg}`);
            const shouldContinue = await ui.confirm('Continue with remaining steps?', false);
            if (!shouldContinue) {
              break;
            }
          }
        }
      }

      // If step still failed after retries, ask user what to do
      if (!stepSuccess) {
        const shouldContinue = await ui.confirm('Step failed. Continue with remaining steps?', false);
        if (!shouldContinue) {
          break;
        }
      }
    }

    // Show completion stats
    const stats = this.todoManager.getStats();
    ui.section('Execution Summary');
    ui.success(`Completed: ${stats.completed}/${stats.total} tasks`);

    if (stats.pending > 0) {
      ui.warning(`Skipped: ${stats.pending} tasks`);
    }

    // Git post-execution hook - commit if all successful
    if (this.gitEnabled && stats.completed === stats.total && stats.total > 0) {
      const gitValid = await this.git.isGitRepository();
      if (gitValid) {
        const planDescription = plan[0]?.summary || 'Completed plan';
        await this.git.commitChanges(planDescription);
      }
    }

    return { stats, executionLog };
  }

  /**
   * Validate that a fixed step has all required fields for its action type
   */
  validateFixedStep(fixedStep) {
    if (!fixedStep || typeof fixedStep !== 'object') {
      return false;
    }

    const action = fixedStep.action;
    if (!action) {
      return false;
    }

    switch (action) {
      case 'run_command':
        return typeof fixedStep.command === 'string' && fixedStep.command.trim().length > 0;

      case 'create_file':
      case 'update_file':
        return typeof fixedStep.path === 'string' && fixedStep.path.trim().length > 0 &&
          typeof fixedStep.content === 'string';

      case 'patch_file':
        return typeof fixedStep.path === 'string' && fixedStep.path.trim().length > 0 &&
          typeof fixedStep.oldContent === 'string' && fixedStep.oldContent.trim().length > 0 &&
          typeof fixedStep.newContent === 'string' && fixedStep.newContent.trim().length > 0;

      case 'delete_file':
      case 'read_file':
      case 'create_dir':
      case 'delete_dir':
      case 'list_dir':
        return typeof fixedStep.path === 'string' && fixedStep.path.trim().length > 0;

      case 'rename_dir':
        return (typeof fixedStep.path === 'string' && fixedStep.path.trim().length > 0 &&
          typeof fixedStep.newPath === 'string' && fixedStep.newPath.trim().length > 0) ||
          (typeof fixedStep.oldPath === 'string' && fixedStep.oldPath.trim().length > 0 &&
            typeof fixedStep.newPath === 'string' && fixedStep.newPath.trim().length > 0);

      default:
        return false;
    }
  }

  /**
   * Self-healing: Ask AI to fix a failed step
   * @param {Object} failedStep - The step that failed
   * @param {string} errorMessage - The error message
   * @param {number} attemptNumber - Current attempt number
   * @param {Array} completedSteps - Steps already successfully completed in this plan
   */
  async selfHeal(failedStep, errorMessage, attemptNumber, completedSteps = []) {
    try {
      // Build context about what has already been completed
      let completedContext = '';
      if (completedSteps.length > 0) {
        completedContext = `\nALREADY COMPLETED STEPS (do NOT repeat these or try to access deleted files):
${completedSteps.map((s, i) => `  ${i + 1}. ${s.action}: ${s.path || s.command || ''} - ${s.summary}`).join('\n')}

IMPORTANT: The above actions have ALREADY been executed. Files that were deleted NO LONGER EXIST.
`;
      }

      // Use the same format as normal requests so it passes backend validation
      const healingPrompt = `The following step failed with an error. Please analyze the error and provide a fixed version of the step.

FAILED STEP:
Action: ${failedStep.action}
${failedStep.command ? `Command: ${failedStep.command}` : ''}
${failedStep.path ? `Path: ${failedStep.path}` : ''}
Summary: ${failedStep.summary}

ERROR:
${errorMessage}
${completedContext}
CONTEXT:
- Working directory: ${this.workingDir}
- Attempt number: ${attemptNumber + 1}
- Available files: ${this.codebaseContext ? this.codebaseContext.files.map(f => f.path).slice(0, 10).join(', ') : 'Unknown'}

IMPORTANT REMINDERS:
- NEVER delete Coderrr.md, Skills.md, or .coderrr directory (these are protected)
- If a file was already deleted in a previous step, it no longer exists
- For patch_file, you MUST use the EXACT content from the file, not placeholders

Please provide ONLY a JSON object with the fixed step. Use the standard plan format:
{
  "explanation": "Brief explanation of what went wrong and how you fixed it",
  "plan": [
    {
      "action": "${failedStep.action}",
      "command": "corrected command if action is run_command",
      "path": "corrected path if file operation",
      "content": "corrected content if needed",
      "oldContent": "old content for patch_file",
      "newContent": "new content for patch_file",
      "summary": "updated summary"
    }
  ]
}`;

      ui.info('Requesting fix from AI...');
      const response = await this.chat(healingPrompt);

      // Handle both object response (from new backend) and string response
      const parsed = typeof response === 'object' && response !== null && response.plan
        ? response
        : this.parseJsonResponse(response);

      if (parsed.explanation) {
        ui.info(`Fix: ${parsed.explanation}`);
      }

      // Extract the fixed step from the plan array
      if (parsed.plan && parsed.plan.length > 0) {
        return parsed.plan[0];
      }

      return null;
    } catch (error) {
      ui.warning(`Self-healing failed: ${error.message}`);
      return null;
    }
  }

  /**
   * Detect and run tests automatically
   */
  async runTests() {
    ui.section('Running Tests');

    const testCommands = [
      { cmd: 'npm test', file: 'package.json' },
      { cmd: 'npx jest', file: 'jest.config.js' },
      { cmd: 'npx jest', file: 'jest.config.ts' },
      { cmd: 'pytest', file: 'pytest.ini' },
      { cmd: 'cargo test', file: 'Cargo.toml' },
      { cmd: 'go test ./...', file: 'go.mod' },
      { cmd: 'mvn test', file: 'pom.xml' },
      { cmd: 'gradle test', file: 'build.gradle' }
    ];

    // Find applicable test command
    let testCommand = null;
    for (const { cmd, file } of testCommands) {
      const filePath = path.join(this.workingDir, file);
      if (fs.existsSync(filePath)) {
        testCommand = cmd;
        break;
      }
    }

    if (!testCommand) {
      const testDirs = ['tests', 'test'];
      for (const dir of testDirs) {
        const dirPath = path.join(this.workingDir, dir);
        if (fs.existsSync(dirPath)) {
          try {
            const stats = fs.statSync(dirPath);
            if (stats.isDirectory()) {
              const files = fs.readdirSync(dirPath);
              // Check for JS/TS files -> Jest
              if (files.some(f => /\.(js|ts|jsx|tsx)$/.test(f))) {
                testCommand = 'npx jest';
                break;
              }
              if (files.some(f => /\.py$/.test(f))) {
                testCommand = 'pytest';
                break;
              }
            }
          } catch (e) {
            console.log(e);
          }
        }
      }
    }

    if (!testCommand) {
      ui.warning('No test framework detected');
      return;
    }

    ui.info(`Detected test command: ${testCommand}`);

    const shouldRun = await ui.confirm('Run tests now?', true);
    if (!shouldRun) {
      ui.warning('Skipped tests');
      return;
    }

    const result = await this.executor.execute(testCommand, {
      requirePermission: false, // Already confirmed above
      cwd: this.workingDir
    });

    if (result.success) {
      ui.success('All tests passed!');
    } else {
      ui.error('Some tests failed');
    }

    return result;
  }

  /**
   * Main agent loop - process user request
   */
  async process(userRequest, options = {}) {
    const { trackHistory = true } = options;

    try {
      ui.section('Processing Request');
      ui.info(`Request: ${userRequest}`);

      // Add user message to history before processing
      if (trackHistory) {
        this.addToHistory('user', userRequest);
      }

      // Get AI response
      const response = await this.chat(userRequest);

      // Try to parse JSON plan - handle both object responses (new backend) and string responses
      let plan;
      let explanation = '';
      let stats = { completed: 0, total: 0, pending: 0 };
      let executionLog = [];

      try {
        // If response is already an object with explanation/plan, use it directly
        const parsed = typeof response === 'object' && response !== null && response.plan
          ? response
          : this.parseJsonResponse(response);

        // Show explanation if present
        if (parsed.explanation) {
          explanation = parsed.explanation;
          ui.section('Plan');
          console.log(parsed.explanation);
          ui.space();
        }

        plan = parsed.plan;

        // ✅ Special handling for read_file queries (questions about files)
        // If the plan only contains read_file actions, execute them and ask AI to interpret
        const isReadOnlyQuery = Array.isArray(plan) &&
          plan.length > 0 &&
          plan.every(step => step.action === 'read_file');

        if (isReadOnlyQuery) {
          ui.info('Reading files to answer your question...');

          // Read all requested files
          const fileContents = [];
          for (const step of plan) {
            try {
              const result = await this.fileOps.readFile(step.path);
              fileContents.push({
                path: step.path,
                content: result.content
              });
            } catch (error) {
              fileContents.push({
                path: step.path,
                error: error.message
              });
            }
          }

          // Make follow-up call with file contents
          const followUpPrompt = `Based on the following file contents, please answer the user's original question: "${userRequest}"

FILE CONTENTS:
${fileContents.map(f => f.error
            ? `--- ${f.path} ---\nError: ${f.error}`
            : `--- ${f.path} ---\n${f.content}`
          ).join('\n\n')}

Provide a helpful explanation. Return JSON with "explanation" containing your answer and an empty "plan" array.`;

          const followUpResponse = await this.chat(followUpPrompt);
          const followUpParsed = typeof followUpResponse === 'object' && followUpResponse !== null
            ? followUpResponse
            : this.parseJsonResponse(followUpResponse);

          ui.section('Response');
          console.log(followUpParsed.explanation || followUpResponse);
          ui.space();

          if (trackHistory) {
            this.addToHistory('assistant', followUpParsed.explanation || 'Answered question about file contents.');
          }

          ui.success('Question answered.');
          return;
        }

        // ✅ Fix: Handle plain queries (no plan / empty plan)
        if (!Array.isArray(plan) || plan.length === 0) {
          ui.section('Response');
          console.log(explanation || response);
          ui.space();

          ui.success('No tasks generated (plain query). Nothing to execute.');
          return;
        }

        // Execute the plan (now that plan is defined)
        const result = await this.executePlan(plan);
        stats = result.stats;
        executionLog = result.executionLog;

        // Add assistant response to history (summarized for context efficiency)
        if (trackHistory) {
          const historySummary = explanation ||
            `Executed ${plan?.length || 0} step(s): ${plan?.map(s => s.summary || s.action).join(', ')}`;
          this.addToHistory('assistant', historySummary);
        }
      } catch (error) {
        ui.warning('Could not parse structured plan from response');
        console.log(response);

        // Still add to history even if parsing failed
        if (trackHistory && executionLog && executionLog.length > 0) {
          const memoryUpdate = `
SYSTEM REPORT - EXECUTION COMPLETED:
The following actions were performed successfully:
${executionLog.join('\n')}

Current State:
- Tasks Completed: ${stats.completed}/${stats.total}
- Ready for next instruction.
`;
          this.addToHistory('assistant', memoryUpdate);
        }

        const shouldContinue = await ui.confirm('Try manual execution mode?', false);
        if (!shouldContinue) {
          return;
        }

        // No structured plan available
        return;
      }

      // Run tests if all tasks completed successfully
      if (this.autoTest && stats.completed === stats.total && stats.total > 0) {
        await this.runTests();
      }

      ui.section('Complete');
      ui.success('Agent finished processing request');

    } catch (error) {
      ui.error(`Agent error: ${error.message}`);
      throw error;
    }
  }

  /**
   * Interactive mode - continuous conversation with history
   */
  async interactive() {
    ui.showBanner();
    ui.info('Interactive mode - Type your requests or "exit" to quit');
    ui.info('Commands: "clear" (reset conversation), "history" (show context), "refresh" (rescan codebase)');
    ui.space();

    while (true) {
      const request = await ui.input('You:', '');

      if (!request.trim()) {
        continue;
      }

      const command = request.toLowerCase().trim();

      // Handle special commands
      if (command === 'exit' || command === 'quit') {
        ui.info('Goodbye! 👋');
        break;
      }

      if (command === 'clear' || command === 'reset') {
        this.clearHistory();
        ui.success('Starting fresh conversation');
        ui.space();
        continue;
      }

      if (command === 'history') {
        if (this.conversationHistory.length === 0) {
          ui.info('No conversation history yet');
        } else {
          ui.section(`Conversation History (${this.conversationHistory.length} messages)`);
          this.conversationHistory.forEach((msg, i) => {
            const prefix = msg.role === 'user' ? '👤 You:' : '🤖 Coderrr:';
            const content = msg.content.length > 100
              ? msg.content.substring(0, 100) + '...'
              : msg.content;
            console.log(`  ${i + 1}. ${prefix} ${content}`);
          });
        }
        ui.space();
        continue;
      }

      if (command === 'refresh') {
        this.refreshCodebase();
        ui.space();
        continue;
      }

      if (command === 'help') {
        ui.section('Available Commands');
        console.log('  exit, quit    - Exit interactive mode');
        console.log('  clear, reset  - Clear conversation history');
        console.log('  history       - Show conversation history');
        console.log('  refresh       - Rescan the codebase');
        console.log('  help          - Show this help message');
        console.log('  Or just type your coding request!');
        ui.space();
        continue;
      }

      try {
        await this.process(request);
      } catch (error) {
        // Error is already handled and displayed in process()
        // Just continue the interactive loop without crashing
        ui.warning('You can continue with a new request or type "exit" to quit.');
      }
      ui.space();
    }
  }

  /**
   * Manually refresh codebase scan
   */
  refreshCodebase() {
    ui.info('Refreshing codebase scan...');
    this.scanner.clearCache();
    const scanResult = this.scanner.scan(true);
    this.codebaseContext = this.scanner.getSummaryForAI();
    ui.success(`Rescanned ${scanResult.summary.totalFiles} files in ${scanResult.summary.totalDirectories} directories`);
    return scanResult;
  }

  /**
   * Find files by name or pattern
   */
  findFiles(searchTerm) {
    return this.scanner.findFiles(searchTerm);
  }

  /**
   * Get codebase summary
   */
  getCodebaseSummary() {
    if (!this.codebaseContext) {
      const scanResult = this.scanner.scan();
      this.codebaseContext = this.scanner.getSummaryForAI();
    }
    return this.codebaseContext;
  }
}

module.exports = Agent;