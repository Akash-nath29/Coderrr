/**
 * Command executor with user permission prompts (like GitHub Copilot)
 * Refactored to work with new Agent architecture
 */

const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const ui = require('./ui');

class CommandExecutor {
  constructor() {
    this.history = [];
  }

  // Add this utility function at the top of the class
  getCommandSeparator() {
    // Returns the appropriate command separator based on OS
    return process.platform === 'win32' ? ';' : '&&';
  }

  // Add this method to normalize commands based on OS
  normalizeCommand(command) {
    const isWindows = process.platform === 'win32';
    
    if (isWindows) {
      // Replace && with ; for Windows PowerShell
      return command.replace(/&&/g, ';');
    }
    // Keep && for Unix-like systems
    return command;
  }

  /**
   * Execute a shell command with user permission
   */
  async execute(command, options = {}) {
    const {
      requirePermission = true,
      cwd = process.cwd(),
      shell = process.platform === 'win32' ? 'powershell.exe' : '/bin/bash'
    } = options;

    // Normalize command based on OS
    const normalizedCommand = this.normalizeCommand(command);
    
    ui.displayCommand(normalizedCommand);
    
    // Ask for permission if required
    if (requirePermission) {
      const confirmed = await ui.confirm('Execute this command?', false);
      if (!confirmed) {
        ui.warning('Command execution cancelled by user');
        return { success: false, cancelled: true };
      }
    }

    // Execute command
    return new Promise((resolve) => {
      ui.info('Executing...');
      
      const startTime = Date.now();
      let stdout = '';
      let stderr = '';
      const child = spawn(normalizedCommand, {
        cwd,
        shell,
        stdio: ['inherit', 'pipe', 'pipe']
      });
      
      child.stdout.on('data', (data) => {
        const text = data.toString();
        stdout += text;
        process.stdout.write(text);
      });
      
      child.stderr.on('data', (data) => {
        const text = data.toString();
        stderr += text;
        process.stderr.write(text);
      });
      
      child.on('close', (code) => {
        const duration = Date.now() - startTime;
        const result = {
          success: code === 0,
          code,
          stdout,
          stderr,
          duration,
          command: normalizedCommand
        };
        this.history.push(result);
        if (code === 0) {
          ui.success(`Command completed successfully (${duration}ms)`);
        } else {
          ui.error(`Command failed with exit code ${code}`);
        }
        resolve(result);
      });
      
      child.on('error', (error) => {
        ui.error(`Failed to execute command: ${error.message}`);
        resolve({
          success: false,
          error: error.message,
          command: normalizedCommand
        });
      });
    });
  }

  /**
   * Execute multiple commands in sequence
   */
  async executeBatch(commands, options = {}) {
    const results = [];
    
    for (const command of commands) {
      const result = await this.execute(command, options);
      results.push(result);
      
      // Stop on first failure unless continueOnError is true
      if (!result.success && !options.continueOnError) {
        break;
      }
    }

    return results;
  }

  /**
   * Get command execution history
   */
  getHistory() {
    return this.history;
  }

  /**
   * Clear history
   */
  clearHistory() {
    this.history = [];
  }
}

// Legacy function for backward compatibility with old blessed TUI code
async function safeWriteFile(filePath, content) {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(filePath, content, 'utf8');
}

async function safeReadFile(filePath) {
  try {
    const txt = await fs.readFile(filePath, 'utf8');
    return txt;
  } catch (e) {
    return null;
  }
}

async function executePlan(plan, ctx) {
  // Legacy function - kept for backward compatibility
  const { appendMessage, askYesNo, status } = ctx;
  for (let i = 0; i < plan.length; ++i) {
    const step = plan[i];
    const idx = i + 1;
    appendMessage('assistant', `Step ${idx}/${plan.length}: ${step.action} ${step.path || step.command || ''}`);
    status.setContent(`Executing step ${idx}/${plan.length} — ${step.action}`);
    
    let confirmNeeded = ['create_file','update_file','patch_file','delete_file','run_command'].includes(step.action);
    let ok = true;
    if (confirmNeeded) {
      ok = await askYesNo(`Proceed with step ${idx}: ${step.action} ${step.path || step.command || ''}?`);
    }

    if (!ok) {
      appendMessage('assistant', `Skipped step ${idx} by user.`);
      continue;
    }

    try {
      if (step.action === 'create_file') {
        const exists = await safeReadFile(step.path);
        if (exists !== null) {
          appendMessage('assistant', `File ${step.path} already exists. Asking before overwrite.`);
          const ov = await askYesNo(`File ${step.path} exists. Overwrite?`);
          if (!ov) { appendMessage('assistant','Skipped creation.'); continue; }
        }
        await safeWriteFile(step.path, step.content || '');
        appendMessage('assistant', `✅ Created/overwritten ${step.path}`);
      } else if (step.action === 'update_file' || step.action === 'patch_file') {
        const old = await safeReadFile(step.path);
        if (old === null) {
          appendMessage('assistant', `File ${step.path} doesn't exist — will create.`);
        }
        await safeWriteFile(step.path, step.content || '');
        appendMessage('assistant', `✅ Updated ${step.path}`);
      } else if (step.action === 'delete_file') {
        const exists = await safeReadFile(step.path);
        if (exists === null) {
          appendMessage('assistant', `File ${step.path} does not exist — nothing to delete.`);
        } else {
          await fs.unlink(step.path);
          appendMessage('assistant', `✅ Deleted ${step.path}`);
        }
      } else if (step.action === 'read_file') {
        const txt = await safeReadFile(step.path);
        appendMessage('assistant', `Contents of ${step.path}:\n${txt === null ? '[NOT FOUND]' : txt}`);
      } else if (step.action === 'run_command') {
        const executor = new CommandExecutor();
        const result = await executor.execute(step.command, { requirePermission: true, cwd: process.cwd() });
        if (!result.success) {
          appendMessage('assistant', `Command failed. Stopping further steps.`);
          break;
        }
      } else {
        appendMessage('assistant', `Unknown action: ${JSON.stringify(step)}`);
      }
    } catch (e) {
      appendMessage('assistant', `Error during step: ${String(e)}`);
    }
  }
  status.setContent('{green-fg}Idle{/}');
}

module.exports = { CommandExecutor, executePlan, safeWriteFile, safeReadFile };
