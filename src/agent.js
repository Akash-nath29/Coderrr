const axios = require('axios');
const fs = require('fs');
const path = require('path');
const ui = require('./ui');
const FileOperations = require('./fileOps');
const CommandExecutor = require('./executor').CommandExecutor;
const TodoManager = require('./todoManager');
const CodebaseScanner = require('./codebaseScanner');

/**
 * Core AI Agent that communicates with backend and executes plans
 */

class Agent {
  constructor(options = {}) {
    // Default to hosted backend, can be overridden via options or env var
    const DEFAULT_BACKEND = 'https://coderrr-backend.vercel.app';
    this.backendUrl = options.backendUrl || process.env.CODERRR_BACKEND || DEFAULT_BACKEND;
    
    this.workingDir = options.workingDir || process.cwd();
    this.fileOps = new FileOperations(this.workingDir);
    this.executor = new CommandExecutor();
    this.todoManager = new TodoManager();
    this.scanner = new CodebaseScanner(this.workingDir);
    this.conversationHistory = [];
    this.autoTest = options.autoTest !== false; // Default to true
    this.autoRetry = options.autoRetry !== false; // Default to true - self-healing on errors
    this.maxRetries = options.maxRetries || 2; // Default 2 retries per step
    this.codebaseContext = null; // Cached codebase structure
    this.scanOnFirstRequest = options.scanOnFirstRequest !== false; // Default to true
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
        enhancedPrompt = `${prompt}

EXISTING PROJECT STRUCTURE:
Working Directory: ${this.codebaseContext.structure.workingDir}
Total Files: ${this.codebaseContext.structure.totalFiles}
Total Directories: ${this.codebaseContext.structure.totalDirectories}

DIRECTORIES:
${this.codebaseContext.directories.slice(0, 20).join('\n')}

EXISTING FILES:
${this.codebaseContext.files.slice(0, 30).map(f => `- ${f.path} (${f.size} bytes)`).join('\n')}

When editing existing files, use EXACT filenames from the list above. When creating new files, ensure they don't conflict with existing ones.`;
      }

      const spinner = ui.spinner('Thinking...');
      spinner.start();

      const response = await axios.post(`${this.backendUrl}/chat`, {
        prompt: enhancedPrompt,
        temperature: options.temperature || 0.2,
        max_tokens: options.max_tokens || 2000,
        top_p: options.top_p || 1.0
      });

      spinner.stop();

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      return response.data.response;
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
   * Execute a plan from the AI
   */
  /**
   * Execute a plan with self-healing retry mechanism
   */
  async executePlan(plan) {
    if (!Array.isArray(plan) || plan.length === 0) {
      ui.warning('No plan to execute');
      return;
    }

    // Parse and display TODOs
    this.todoManager.parseTodos(plan);
    this.todoManager.display();

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
              // Command failed - attempt self-healing if enabled
              if (this.autoRetry && retryCount < this.maxRetries) {
                ui.warning(`Command failed (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
                ui.info('🔧 Analyzing error and generating fix...');
                
                const fixedStep = await this.selfHeal(step, result.error || result.output, retryCount);
                
                if (fixedStep) {
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
          if (this.autoRetry && retryCount < this.maxRetries) {
            ui.warning(`Step failed: ${error.message} (attempt ${retryCount + 1}/${this.maxRetries + 1})`);
            ui.info('🔧 Analyzing error and generating fix...');
            
            const fixedStep = await this.selfHeal(step, error.message, retryCount);
            
            if (fixedStep) {
              // Update step with fixed version
              Object.assign(step, fixedStep);
              retryCount++;
              continue; // Retry with fixed step
            } else {
              ui.error('Could not generate automatic fix');
              break;
            }
          } else {
            ui.error(`Failed to execute step${this.autoRetry ? ` after ${this.maxRetries + 1} attempts` : ''}: ${error.message}`);
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

    return stats;
  }

  /**
   * Self-healing: Ask AI to fix a failed step
   */
  async selfHeal(failedStep, errorMessage, attemptNumber) {
    try {
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

Please provide ONLY a JSON object with the fixed step in this exact format:
{
  "explanation": "Brief explanation of what went wrong and how you fixed it",
  "fixed_step": {
    "action": "${failedStep.action}",
    "command": "corrected command if action is run_command",
    "path": "corrected path if file operation",
    "content": "corrected content if needed",
    "summary": "updated summary"
  }
}`;

      ui.info('🔧 Requesting fix from AI...');
      const response = await this.chat(healingPrompt);
      const parsed = this.parseJsonResponse(response);

      if (parsed.explanation) {
        ui.info(`💡 Fix: ${parsed.explanation}`);
      }

      if (parsed.fixed_step) {
        return parsed.fixed_step;
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
      { cmd: 'pytest', file: 'pytest.ini' },
      { cmd: 'pytest', file: 'tests/' },
      { cmd: 'python -m pytest', file: 'tests/' },
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
  async process(userRequest) {
    try {
      ui.section('Processing Request');
      ui.info(`Request: ${userRequest}`);

      // Get AI response
      const response = await this.chat(userRequest);

      // Try to parse JSON plan
      let plan;
      try {
        // DEBUG: Show raw response
        console.log('\n--- DEBUG: Raw Backend Response ---');
        console.log(response);
        console.log('--- END DEBUG ---\n');
        
        const parsed = this.parseJsonResponse(response);
        
        // Show explanation if present
        if (parsed.explanation) {
          ui.section('Plan');
          console.log(parsed.explanation);
          ui.space();
        }

        plan = parsed.plan;
      } catch (error) {
        ui.warning('Could not parse structured plan from response');
        console.log(response);
        
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
   * Interactive mode - continuous conversation
   */
  async interactive() {
    ui.showBanner();
    ui.info('Interactive mode - Type your requests or "exit" to quit');
    ui.space();

    while (true) {
      const request = await ui.input('You:', '');
      
      if (!request.trim()) {
        continue;
      }

      if (request.toLowerCase() === 'exit' || request.toLowerCase() === 'quit') {
        ui.info('Goodbye! 👋');
        break;
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
