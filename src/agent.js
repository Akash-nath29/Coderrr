const axios = require('axios');
const fs = require('fs');
const path = require('path');
const ui = require('./ui');
const FileOperations = require('./fileOps');
const CommandExecutor = require('./executor').CommandExecutor;
const TodoManager = require('./todoManager');
const CodebaseScanner = require('./codebaseScanner');
const GitOperations = require('./gitOps');

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
    this.conversationHistory = [];
    this.autoTest = options.autoTest !== false; // Default to true
    this.autoRetry = options.autoRetry !== false; // Default to true - self-healing on errors
    this.maxRetries = options.maxRetries || 2; // Default 2 retries per step
    this.codebaseContext = null; // Cached codebase structure
    this.scanOnFirstRequest = options.scanOnFirstRequest !== false; // Default to true
    this.gitEnabled = options.gitEnabled || false; // Git auto-commit feature (opt-in)
    this.maxHistoryLength = options.maxHistoryLength || 10; // Max conversation turns to keep
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
  }

  /**
   * Clear conversation history (useful for starting fresh)
   */
  clearHistory() {
    this.conversationHistory = [];
    ui.info('Conversation history cleared');
  }

  /**
   * Get formatted conversation history for the backend
   */
  getFormattedHistory() {
    return this.conversationHistory.map(msg => ({
      role: msg.role,
      content: msg.content
    }));
  }

  /**
   * Send a prompt to the AI backend
   */
  async chat(prompt, options = {}) {
    try {
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

      // Enhance prompt with codebase context
      let enhancedPrompt = prompt;
      if (this.codebaseContext) {
        const osType = process.platform === 'win32' ? 'Windows' : 
                       process.platform === 'darwin' ? 'macOS' : 'Linux';
        
        enhancedPrompt = `${prompt}

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
      if (error.code === 'ECONNREFUSED') {
        ui.error(`Cannot connect to backend at ${this.backendUrl}`);
        ui.warning('Make sure the backend is running:');
        console.log('  uvicorn main:app --reload --port 5000');
      } else {
        ui.error(`Failed to communicate with backend: ${error.message}`);
      }
      throw error;
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
      return;
    }

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

    // Execute each step
    for (let i = 0; i < plan.length; i++) {
      const step = plan[i];
      this.todoManager.setInProgress(i);

      ui.info(`Step ${i + 1}/${plan.length}: ${step.summary || step.action}`);

      let retryCount = 0;
      let stepSuccess = false;

      while (!stepSuccess && retryCount <= this.maxRetries) {
        try {
          if (step.action === 'run_command') {
            // Execute command with permission
            const result = await this.executor.execute(step.command, {
              requirePermission: true,
              cwd: this.workingDir
            });

            if (!result.success && !result.cancelled) {
              const errorMsg = result.error || result.output || 'Unknown error';

              // Check if this error is retryable (can be fixed by AI)
              if (!this.isRetryableError(errorMsg)) {
                ui.error(`Non-retryable error: ${errorMsg}`);
                ui.warning('⚠️  This type of error cannot be auto-fixed (file/permission/config issue)');
                break; // Don't retry, let the outer loop ask user what to do
              }

              // Command failed - attempt self-healing if enabled and error is retryable
              if (this.autoRetry && retryCount < this.maxRetries) {
                ui.warning(`Command failed (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
                ui.info('🔧 Analyzing error and generating fix...');

                const fixedStep = await this.selfHeal(step, errorMsg, retryCount);

                if (fixedStep && fixedStep.command) {
                  step.command = fixedStep.command;
                  step.summary = fixedStep.summary || step.summary;
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

            if (result.cancelled) {
              ui.warning('Command cancelled by user');
              stepSuccess = true; // Consider cancelled as completed
            } else {
              stepSuccess = true;
            }
          } else {
            // File operation
            await this.fileOps.execute(step);
            stepSuccess = true;
          }

          if (stepSuccess) {
            this.todoManager.complete(i);
          }
        } catch (error) {
          const errorMsg = error.message || 'Unknown error';

          // Check if this error is retryable (can be fixed by AI)
          if (!this.isRetryableError(errorMsg)) {
            ui.error(`Non-retryable error: ${errorMsg}`);
            ui.warning('⚠️  This type of error cannot be auto-fixed (file/permission/config issue)');
            break; // Don't retry, let the outer loop ask user what to do
          }

          if (this.autoRetry && retryCount < this.maxRetries) {
            ui.warning(`Step failed: ${errorMsg} (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
            ui.info('🔧 Analyzing error and generating fix...');

            const fixedStep = await this.selfHeal(step, errorMsg, retryCount);

            if (fixedStep) {
              // Update step with fixed version - but validate it has required fields
              if (step.action === 'run_command' && !fixedStep.command) {
                ui.error('AI fix is missing command, cannot retry');
                break;
              }
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

    return stats;
  }

  /**
   * Self-healing: Ask AI to fix a failed step
   */
  async selfHeal(failedStep, errorMessage, attemptNumber) {
    try {
      // Use the same format as normal requests so it passes backend validation
      const healingPrompt = `The following step failed with an error. Please analyze the error and provide a fixed version of the step.

FAILED STEP:
Action: ${failedStep.action}
${failedStep.command ? `Command: ${failedStep.command}` : ''}
${failedStep.path ? `Path: ${failedStep.path}` : ''}
Summary: ${failedStep.summary}

ERROR:
${errorMessage}

CONTEXT:
- Working directory: ${this.workingDir}
- Attempt number: ${attemptNumber + 1}
- Available files: ${this.codebaseContext ? this.codebaseContext.files.map(f => f.path).slice(0, 10).join(', ') : 'Unknown'}

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

      ui.info('🔧 Requesting fix from AI...');
      const response = await this.chat(healingPrompt);

      // Handle both object response (from new backend) and string response
      const parsed = typeof response === 'object' && response !== null && response.plan
        ? response
        : this.parseJsonResponse(response);

      if (parsed.explanation) {
        ui.info(`💡 Fix: ${parsed.explanation}`);
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
      ui.success('All tests passed! ✨');
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
        if (trackHistory) {
          this.addToHistory('assistant', response.substring(0, 500));
        }

        const shouldContinue = await ui.confirm('Try manual execution mode?', false);
        if (!shouldContinue) {
          return;
        }

        // No structured plan available
        return;
      }

      // Execute the plan
      const stats = await this.executePlan(plan);

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

      await this.process(request);
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