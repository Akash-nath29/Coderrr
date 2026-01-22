const { isPlainQuery, isTaskCommand } = require("./utils/queryClassifier.js");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const ui = require("./ui");
const FileOperations = require("./fileOps");
const CommandExecutor = require("./executor").CommandExecutor;
const TodoManager = require("./todoManager");
const CodebaseScanner = require("./codebaseScanner");
const GitOperations = require("./gitOps");
const {
  sanitizeAxiosError,
  formatUserError,
  createSafeError,
  isNetworkError,
} = require("./errorHandler");
const configManager = require("./configManager");
const { getProvider } = require("./providers");

/**
 * Core AI Agent that communicates with backend and executes plans
 */
class Agent {
  constructor(options = {}) {
    const DEFAULT_BACKEND = "https://coderrr-backend.vercel.app";
    this.backendUrl =
      options.backendUrl || process.env.CODERRR_BACKEND || DEFAULT_BACKEND;

    this.workingDir = options.workingDir || process.cwd();
    this.fileOps = new FileOperations(this.workingDir);
    this.executor = new CommandExecutor();
    this.todoManager = new TodoManager();
    this.scanner = new CodebaseScanner(this.workingDir);
    this.git = new GitOperations(this.workingDir);
    this.conversationHistory = [];

    this.autoTest = options.autoTest !== false;
    this.autoRetry = options.autoRetry !== false;
    this.maxRetries = options.maxRetries || 2;

    this.codebaseContext = null;
    this.scanOnFirstRequest = options.scanOnFirstRequest !== false;

    this.gitEnabled = options.gitEnabled || false;
    this.maxHistoryLength = options.maxHistoryLength || 10;

    // Load user provider configuration
    this.providerConfig = configManager.getConfig();
  }

  /**
   * Add a message to conversation history
   */
  addToHistory(role, content) {
    this.conversationHistory.push({ role, content });

    // Each turn = 2 messages (user + assistant), so maxHistoryLength * 2
    const maxMessages = this.maxHistoryLength * 2;
    if (this.conversationHistory.length > maxMessages) {
      this.conversationHistory = this.conversationHistory.slice(-maxMessages);
    }
  }

  /**
   * Clear conversation history
   */
  clearHistory() {
    this.conversationHistory = [];
    ui.info("Conversation history cleared");
  }

  /**
   * Get formatted conversation history for backend
   */
  getFormattedHistory() {
    return this.conversationHistory.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));
  }

  /**
   * Send a prompt to backend
   */
  async chat(prompt, options = {}) {
    try {
      // Scan codebase on first request if enabled
      if (this.scanOnFirstRequest && !this.codebaseContext) {
        const scanSpinner = ui.spinner("Scanning codebase...");
        scanSpinner.start();

        try {
          const scanResult = this.scanner.scan();
          this.codebaseContext = this.scanner.getSummaryForAI();
          scanSpinner.stop();

          ui.success(
            `Scanned ${scanResult.summary.totalFiles} files in ${scanResult.summary.totalDirectories} directories`
          );
        } catch (scanError) {
          scanSpinner.stop();
          ui.warning(`Could not scan codebase: ${scanError.message}`);
        }
      }

      // Enhance prompt with codebase context
      let enhancedPrompt = prompt;

      if (this.codebaseContext) {
        const osType =
          process.platform === "win32"
            ? "Windows"
            : process.platform === "darwin"
            ? "macOS"
            : "Linux";

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
${this.codebaseContext.directories.slice(0, 20).join("\n")}
EXISTING FILES:
${this.codebaseContext.files
  .slice(0, 30)
  .map((f) => `- ${f.path} (${f.size} bytes)`)
  .join("\n")}

When editing existing files, use EXACT filenames from the list above. When creating new files, ensure they don't conflict with existing ones.
For command execution on ${osType}, use appropriate command separators (${
          osType === "Windows" ? "semicolon (;)" : "ampersand (&&)"
        }).`;
      }

      const spinner = ui.spinner("Thinking...");
      spinner.start();

      const requestPayload = {
        prompt: enhancedPrompt,
        temperature: options.temperature || 0.2,
        max_tokens: options.max_tokens || 2000,
        top_p: options.top_p || 1.0,
      };

      // Add provider config if user configured one
      if (this.providerConfig) {
        requestPayload.provider = this.providerConfig.provider;
        requestPayload.api_key = this.providerConfig.apiKey;
        requestPayload.model = this.providerConfig.model;
        if (this.providerConfig.endpoint) {
          requestPayload.endpoint = this.providerConfig.endpoint;
        }
      }

      // Add conversation history
      if (this.conversationHistory.length > 0) {
        requestPayload.conversation_history = this.getFormattedHistory();
      }

      const response = await axios.post(
        `${this.backendUrl}/chat`,
        requestPayload
      );

      spinner.stop();

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      return response.data.response || response.data;
    } catch (error) {
      const sanitized = sanitizeAxiosError(error);
      const userMessage = formatUserError(sanitized, this.backendUrl);

      if (isNetworkError(error)) {
        ui.error(`Cannot connect to backend at ${this.backendUrl}`);
        ui.warning("Make sure the backend is running:");
        console.log("  uvicorn main:app --reload --port 5000");
      } else {
        ui.error(`Failed to communicate with backend: ${userMessage}`);
      }

      throw createSafeError(error);
    }
  }

  /**
   * Parse JSON from AI response (handles markdown blocks)
   */
  parseJsonResponse(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      const jsonMatch = text.match(/```json\s*\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[1]);
        } catch (e2) {}
      }

      const objectMatch = text.match(/\{[\s\S]*\}/);
      if (objectMatch) {
        try {
          return JSON.parse(objectMatch[0]);
        } catch (e3) {}
      }

      throw new Error("Could not parse JSON from response");
    }
  }

  /**
   * Check if error is retryable
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

    const isNonRetryable = nonRetryablePatterns.some((pattern) =>
      pattern.test(errorMessage)
    );

    return !isNonRetryable;
  }

  /**
   * Execute a plan
   */
  async executePlan(plan) {
    if (!Array.isArray(plan) || plan.length === 0) {
      ui.warning("No plan to execute");
      return;
    }

    // Parse and display TODOs
    this.todoManager.parseTodos(plan);
    this.todoManager.display();

    ui.section("Executing Plan");

    for (let i = 0; i < plan.length; i++) {
      const step = plan[i];
      this.todoManager.setInProgress(i);

      ui.info(`Step ${i + 1}/${plan.length}: ${step.summary || step.action}`);

      let retryCount = 0;
      let stepSuccess = false;

      while (!stepSuccess && retryCount <= this.maxRetries) {
        try {
          if (step.action === "run_command") {
            const result = await this.executor.execute(step.command, {
              requirePermission: true,
              cwd: this.workingDir,
            });

            if (!result.success && !result.cancelled) {
              const errorMsg =
                result.error || result.output || "Unknown error";

              if (!this.isRetryableError(errorMsg)) {
                ui.error(`Non-retryable error: ${errorMsg}`);
                break;
              }

              if (this.autoRetry && retryCount < this.maxRetries) {
                ui.warning(
                  `Command failed (attempt ${retryCount + 1}/${
                    this.maxRetries + 1
                  })`
                );
                retryCount++;
                continue;
              } else {
                ui.error("Command failed, stopping execution");
                break;
              }
            }

            stepSuccess = true;
          } else {
            await this.fileOps.execute(step);
            stepSuccess = true;
          }

          if (stepSuccess) {
            this.todoManager.complete(i);
          }
        } catch (error) {
          const errorMsg = error.message || "Unknown error";

          if (!this.isRetryableError(errorMsg)) {
            ui.error(`Non-retryable error: ${errorMsg}`);
            break;
          }

          if (this.autoRetry && retryCount < this.maxRetries) {
            ui.warning(
              `Step failed: ${errorMsg} (attempt ${retryCount + 1}/${
                this.maxRetries + 1
              })`
            );
            retryCount++;
            continue;
          } else {
            ui.error(`Failed to execute step: ${errorMsg}`);
            break;
          }
        }
      }

      if (!stepSuccess) {
        ui.warning("Step failed. Stopping execution.");
        break;
      }
    }

    const stats = this.todoManager.getStats();
    ui.section("Execution Summary");
    ui.success(`Completed: ${stats.completed}/${stats.total} tasks`);

    if (stats.pending > 0) {
      ui.warning(`Skipped: ${stats.pending} tasks`);
    }

    return stats;
  }

  /**
   * Run tests (basic)
   */
  async runTests() {
    ui.section("Running Tests");

    const testCommands = [
      { cmd: "npm test", file: "package.json" },
      { cmd: "npx jest", file: "jest.config.js" },
      { cmd: "npx jest", file: "jest.config.ts" },
    ];

    let testCommand = null;
    for (const { cmd, file } of testCommands) {
      const filePath = path.join(this.workingDir, file);
      if (fs.existsSync(filePath)) {
        testCommand = cmd;
        break;
      }
    }

    if (!testCommand) {
      ui.warning("No test framework detected");
      return;
    }

    ui.info(`Detected test command: ${testCommand}`);

    const shouldRun = await ui.confirm("Run tests now?", true);
    if (!shouldRun) {
      ui.warning("Skipped tests");
      return;
    }

    const result = await this.executor.execute(testCommand, {
      requirePermission: false,
      cwd: this.workingDir,
    });

    if (result.success) {
      ui.success("All tests passed! ✨");
    } else {
      ui.error("Some tests failed");
    }

    return result;
  }

  /**
   * Main agent loop - process user request
   */
  async process(userRequest, options = {}) {
    const { trackHistory = true } = options;

    try {
      ui.section("Processing Request");
      ui.info(`Request: ${userRequest}`);

      // ✅ Plain Query Handling (Issue #77)
      if (isPlainQuery(userRequest) && !isTaskCommand(userRequest)) {
        ui.section("Response");

        const q = userRequest.trim().toLowerCase();

        if (q.includes("what is coderrr") || q === "coderrr") {
          console.log(
            "Coderrr is an AI-powered CLI coding assistant. You can type a request like 'create a login page' or 'fix this bug', and Coderrr will generate a plan and help you update files or run commands safely."
          );
        } else {
          console.log(
            `You asked: "${userRequest}".\nThis is a plain query, so Coderrr will answer directly (no plan execution).`
          );
        }

        ui.space();
        ui.success("No tasks generated (plain query). Nothing to execute.");
        return;
      }

      // Add user to history
      if (trackHistory) {
        this.addToHistory("user", userRequest);
      }

      // Get AI response
      const response = await this.chat(userRequest);

      let plan;
      let explanation = "";

      try {
        const parsed =
          typeof response === "object" && response !== null && response.plan
            ? response
            : this.parseJsonResponse(response);

        if (parsed.explanation) {
          explanation = parsed.explanation;
          ui.section("Plan");
          console.log(parsed.explanation);
          ui.space();
        }

        plan = parsed.plan;

        // ✅ Handle empty plan safely
        if (!Array.isArray(plan) || plan.length === 0) {
          ui.section("Response");
          console.log(explanation || response);
          ui.space();
          ui.success("No tasks generated (plain query). Nothing to execute.");
          return;
        }

        // Add assistant summary to history
        if (trackHistory) {
          const historySummary =
            explanation ||
            `Executed ${plan?.length || 0} step(s): ${plan
              ?.map((s) => s.summary || s.action)
              .join(", ")}`;

          this.addToHistory("assistant", historySummary);
        }
      } catch (error) {
        ui.warning("Could not parse structured plan from response");
        console.log(response);
        return;
      }

      // Execute plan
      const stats = await this.executePlan(plan);

      // Auto run tests
      if (this.autoTest && stats?.completed === stats?.total && stats.total > 0) {
        await this.runTests();
      }

      ui.section("Complete");
      ui.success("Agent finished processing request");
    } catch (error) {
      ui.error(`Agent error: ${error.message}`);
      throw error;
    }
  }

  /**
   * Interactive mode
   */
  async interactive() {
    ui.showBanner();
    ui.info('Interactive mode - Type your requests or "exit" to quit');
    ui.info(
      'Commands: "clear" (reset conversation), "history" (show context), "refresh" (rescan codebase)'
    );
    ui.space();

    while (true) {
      const request = await ui.input("You:", "");

      if (!request.trim()) continue;

      const command = request.toLowerCase().trim();

      if (command === "exit" || command === "quit") {
        ui.info("Goodbye! 👋");
        break;
      }

      if (command === "clear" || command === "reset") {
        this.clearHistory();
        ui.success("Starting fresh conversation");
        ui.space();
        continue;
      }

      if (command === "history") {
        if (this.conversationHistory.length === 0) {
          ui.info("No conversation history yet");
        } else {
          ui.section(
            `Conversation History (${this.conversationHistory.length} messages)`
          );
          this.conversationHistory.forEach((msg, i) => {
            const prefix = msg.role === "user" ? "👤 You:" : "🤖 Coderrr:";
            const content =
              msg.content.length > 100
                ? msg.content.substring(0, 100) + "..."
                : msg.content;
            console.log(`  ${i + 1}. ${prefix} ${content}`);
          });
        }
        ui.space();
        continue;
      }

      if (command === "refresh") {
        this.refreshCodebase();
        ui.space();
        continue;
      }

      try {
        await this.process(request);
      } catch (error) {
        ui.warning(
          'You can continue with a new request or type "exit" to quit.'
        );
      }

      ui.space();
    }
  }

  /**
   * Rescan codebase
   */
  refreshCodebase() {
    ui.info("Refreshing codebase scan...");
    this.scanner.clearCache();
    const scanResult = this.scanner.scan(true);
    this.codebaseContext = this.scanner.getSummaryForAI();
    ui.success(
      `Rescanned ${scanResult.summary.totalFiles} files in ${scanResult.summary.totalDirectories} directories`
    );
    return scanResult;
  }
}

module.exports = Agent;
