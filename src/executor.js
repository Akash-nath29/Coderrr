/**
 * Command executor with user permission prompts (like GitHub Copilot)
 * Refactored to work with new Agent architecture
 */

const { spawn, exec } = require('child_process');
const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');
const os = require('os');
const ui = require('./ui');
const skillRunner = require('./skillRunner');

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

  /**
   * Execute command in a separate terminal window (cross-platform)
   * This allows Coderrr to continue while the command runs in a detached process
   * 
   * @param {string} command - Command to execute
   * @param {Object} options - Execution options
   * @returns {Promise<Object>} Result with process info and monitoring capabilities
   */
  async executeInSeparateTerminal(command, options = {}) {
    const {
      requirePermission = true,
      cwd = process.cwd(),
      timeout = 0, // 0 means no timeout
      monitorOutput = true
    } = options;

    // Normalize command based on OS
    const normalizedCommand = this.normalizeCommand(command);

    ui.displayCommand(normalizedCommand);
    ui.info('(Will run in separate terminal window)');

    // Ask for permission if required
    if (requirePermission) {
      const confirmed = await ui.confirm('Execute this command in a separate terminal?', false);
      if (!confirmed) {
        ui.warning('Command execution cancelled by user');
        return { success: false, cancelled: true };
      }
    }

    // Create unique output file for monitoring
    const timestamp = Date.now();
    const outputFile = path.join(os.tmpdir(), `coderrr-output-${timestamp}.log`);
    const pidFile = path.join(os.tmpdir(), `coderrr-pid-${timestamp}.txt`);

    // Initialize output file
    fsSync.writeFileSync(outputFile, '', 'utf8');

    const platform = process.platform;
    let terminalProcess = null;
    let childPid = null;

    try {
      if (platform === 'win32') {
        // Windows: Use start command with cmd.exe
        const result = await this.spawnWindowsTerminal(normalizedCommand, cwd, outputFile, pidFile);
        terminalProcess = result.process;
        childPid = result.pid;
      } else if (platform === 'darwin') {
        // macOS: Use osascript to open Terminal.app
        const result = await this.spawnMacTerminal(normalizedCommand, cwd, outputFile, pidFile);
        terminalProcess = result.process;
        childPid = result.pid;
      } else {
        // Linux: Try gnome-terminal, konsole, or xterm
        const result = await this.spawnLinuxTerminal(normalizedCommand, cwd, outputFile, pidFile);
        terminalProcess = result.process;
        childPid = result.pid;
      }

      ui.success('Command started in separate terminal window');

      // Start monitoring output if requested
      let outputWatcher = null;
      let lastReadPosition = 0;

      if (monitorOutput) {
        outputWatcher = this.startOutputMonitoring(outputFile, (newContent) => {
          if (newContent.trim()) {
            process.stdout.write(newContent);
          }
        });
      }

      // Create result object with control methods
      const result = {
        success: true,
        pid: childPid,
        outputFile,
        pidFile,
        command: normalizedCommand,
        startTime: Date.now(),

        // Method to stop the spawned process
        stop: async () => {
          return this.terminateProcess(childPid, platform);
        },

        // Method to stop monitoring
        stopMonitoring: () => {
          if (outputWatcher) {
            outputWatcher.close();
            outputWatcher = null;
          }
        },

        // Method to get current output
        getOutput: () => {
          try {
            return fsSync.readFileSync(outputFile, 'utf8');
          } catch (e) {
            return '';
          }
        },

        // Method to check if process is still running
        isRunning: async () => {
          return this.isProcessRunning(childPid, platform);
        },

        // Method to wait for process completion with optional timeout
        waitForCompletion: async (timeoutMs = 0) => {
          return this.waitForProcess(childPid, platform, timeoutMs, outputFile);
        }
      };

      // Store in history
      this.history.push({
        command: normalizedCommand,
        pid: childPid,
        separateTerminal: true,
        startTime: result.startTime
      });

      // If timeout is specified, set up auto-termination
      if (timeout > 0) {
        setTimeout(async () => {
          const stillRunning = await result.isRunning();
          if (stillRunning) {
            ui.warning(`Command timed out after ${timeout}ms, terminating...`);
            await result.stop();
          }
        }, timeout);
      }

      return result;

    } catch (error) {
      ui.error(`Failed to spawn separate terminal: ${error.message}`);
      return {
        success: false,
        error: error.message,
        command: normalizedCommand
      };
    }
  }

  /**
   * Spawn terminal on Windows
   */
  async spawnWindowsTerminal(command, cwd, outputFile, pidFile) {
    return new Promise((resolve, reject) => {
      // Create a PowerShell script that runs the command, shows output, AND logs to file
      const psScript = path.join(os.tmpdir(), `coderrr-cmd-${Date.now()}.ps1`);

      // PowerShell script that:
      // 1. Changes to working directory
      // 2. Runs command with output visible AND teed to log file
      // 3. Shows completion message
      // 4. Waits for user to close
      const psContent = `
$ErrorActionPreference = "Continue"
Set-Location -Path "${cwd.replace(/\\/g, '\\\\')}"
Write-Host "=== Coderrr Task ===" -ForegroundColor Cyan
Write-Host "Working Directory: ${cwd.replace(/\\/g, '\\\\')}" -ForegroundColor Gray
Write-Host "Command: ${command.replace(/"/g, '\\"')}" -ForegroundColor Yellow
Write-Host "Started at: $(Get-Date)" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Log start to file
"Command started at $(Get-Date)" | Out-File -FilePath "${outputFile.replace(/\\/g, '\\\\')}" -Encoding UTF8

try {
    # Run command and tee output to both console and file
    Invoke-Expression "${command.replace(/"/g, '\\"')}" 2>&1 | Tee-Object -FilePath "${outputFile.replace(/\\/g, '\\\\')}" -Append
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    $_ | Out-File -FilePath "${outputFile.replace(/\\/g, '\\\\')}" -Append
    $exitCode = 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Command finished with exit code: $exitCode at $(Get-Date)" -ForegroundColor $(if($exitCode -eq 0){"Green"}else{"Red"})
"Command finished with exit code $exitCode at $(Get-Date)" | Out-File -FilePath "${outputFile.replace(/\\/g, '\\\\')}" -Append

Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
`;
      fsSync.writeFileSync(psScript, psContent, 'utf8');

      // Use exec with start command - exec handles the shell properly
      const startCmd = `start "Coderrr Task" powershell.exe -ExecutionPolicy Bypass -File "${psScript}"`;

      // Use exec instead of spawn to avoid quote escaping issues
      exec(startCmd, { cwd, windowsHide: false }, (error) => {
        // The exec callback fires immediately after start launches the window
        // We don't wait for the PowerShell script to complete
        if (error) {
          // Only reject on actual errors, not on expected behavior
          if (!error.message.includes('is not recognized')) {
            // Start command itself failed
          }
        }
      });

      // Resolve immediately - don't wait for the terminal
      // The command is now running independently
      setTimeout(() => {
        // Try to get the PowerShell process PID
        exec('wmic process where "name=\'powershell.exe\'" get ProcessId,CommandLine /format:csv', (err, out) => {
          let pid = null;
          if (!err && out) {
            // Look for our script in the output
            const lines = out.split('\n');
            for (const line of lines) {
              if (line.includes('coderrr-cmd-')) {
                const match = line.match(/,(\d+)$/);
                if (match) {
                  pid = parseInt(match[1]);
                  break;
                }
              }
            }
            // Fallback: get any recent powershell
            if (!pid) {
              const matches = out.match(/,(\d+)\r?\n/g);
              if (matches && matches.length > 0) {
                const lastMatch = matches[matches.length - 1];
                pid = parseInt(lastMatch.replace(/[,\r\n]/g, ''));
              }
            }
          }

          if (pid) {
            fsSync.writeFileSync(pidFile, pid.toString(), 'utf8');
          }

          resolve({ process: null, pid });
        });
      }, 300); // Short delay to let the window open
    });
  }

  /**
   * Spawn terminal on macOS
   */
  async spawnMacTerminal(command, cwd, outputFile, pidFile) {
    return new Promise((resolve, reject) => {
      // Create a shell script that shows output AND logs to file
      const shellScript = path.join(os.tmpdir(), `coderrr-cmd-${Date.now()}.sh`);
      const scriptContent = `#!/bin/bash
cd "${cwd}"
echo "=== Coderrr Task ==="
echo "Working Directory: ${cwd}"
echo "Command: ${command}"
echo "Started at: $(date)"
echo "========================================"
echo ""

# Log start to file
echo "Command started at $(date)" > "${outputFile}"

# Run command with output to both terminal AND file using tee
${command} 2>&1 | tee -a "${outputFile}"
EXITCODE=\${PIPESTATUS[0]}

echo ""
echo "========================================"
echo "Command finished with exit code $EXITCODE at $(date)"
echo "Command finished with exit code $EXITCODE at $(date)" >> "${outputFile}"

echo ""
echo "Press Enter to close this terminal..."
read
`;
      fsSync.writeFileSync(shellScript, scriptContent, { mode: 0o755 });

      // Use osascript to open Terminal.app and run the script
      const appleScript = `
tell application "Terminal"
  activate
  do script "bash '${shellScript}'; echo $$ > '${pidFile}'"
end tell
`;

      exec(`osascript -e '${appleScript}'`, (error, stdout, stderr) => {
        if (error) {
          reject(error);
          return;
        }

        // Wait a bit for PID file to be created
        setTimeout(() => {
          let pid = null;
          try {
            if (fsSync.existsSync(pidFile)) {
              pid = parseInt(fsSync.readFileSync(pidFile, 'utf8').trim());
            }
          } catch (e) {
            // Ignore
          }

          resolve({ process: null, pid });
        }, 1000);
      });
    });
  }

  /**
   * Spawn terminal on Linux
   */
  async spawnLinuxTerminal(command, cwd, outputFile, pidFile) {
    return new Promise((resolve, reject) => {
      // Create a shell script that shows output AND logs to file
      const shellScript = path.join(os.tmpdir(), `coderrr-cmd-${Date.now()}.sh`);
      const scriptContent = `#!/bin/bash
cd "${cwd}"
echo "=== Coderrr Task ==="
echo "Working Directory: ${cwd}"
echo "Command: ${command}"
echo "Started at: $(date)"
echo "========================================"
echo ""

# Log start to file
echo "Command started at $(date)" > "${outputFile}"

# Run command with output to both terminal AND file using tee
${command} 2>&1 | tee -a "${outputFile}"
EXITCODE=\${PIPESTATUS[0]}

echo ""
echo "========================================"
echo "Command finished with exit code $EXITCODE at $(date)"
echo "Command finished with exit code $EXITCODE at $(date)" >> "${outputFile}"

echo ""
echo "Press Enter to close this terminal..."
read
`;
      fsSync.writeFileSync(shellScript, scriptContent, { mode: 0o755 });

      // Try different terminal emulators in order of preference
      const terminals = [
        { cmd: 'gnome-terminal', args: ['--', 'bash', '-c', `${shellScript}; echo $$ > ${pidFile}`] },
        { cmd: 'konsole', args: ['-e', 'bash', '-c', `${shellScript}; echo $$ > ${pidFile}`] },
        { cmd: 'xfce4-terminal', args: ['-e', `bash -c "${shellScript}; echo $$ > ${pidFile}"`] },
        { cmd: 'xterm', args: ['-e', `bash -c "${shellScript}; echo $$ > ${pidFile}"`] }
      ];

      const tryTerminal = async (index) => {
        if (index >= terminals.length) {
          reject(new Error('No suitable terminal emulator found. Tried: gnome-terminal, konsole, xfce4-terminal, xterm'));
          return;
        }

        const term = terminals[index];

        // Check if terminal exists
        exec(`which ${term.cmd}`, async (error) => {
          if (error) {
            // Terminal not found, try next
            tryTerminal(index + 1);
            return;
          }

          // Terminal found, spawn it
          const child = spawn(term.cmd, term.args, {
            cwd,
            detached: true,
            stdio: 'ignore'
          });

          child.unref();

          // Wait for PID file
          setTimeout(() => {
            let pid = child.pid;
            try {
              if (fsSync.existsSync(pidFile)) {
                pid = parseInt(fsSync.readFileSync(pidFile, 'utf8').trim());
              }
            } catch (e) {
              // Use child.pid as fallback
            }

            resolve({ process: child, pid });
          }, 1000);
        });
      };

      tryTerminal(0);
    });
  }

  /**
   * Start monitoring output file for changes
   */
  startOutputMonitoring(outputFile, callback) {
    let lastSize = 0;

    const checkForChanges = () => {
      try {
        const stats = fsSync.statSync(outputFile);
        if (stats.size > lastSize) {
          const fd = fsSync.openSync(outputFile, 'r');
          const buffer = Buffer.alloc(stats.size - lastSize);
          fsSync.readSync(fd, buffer, 0, buffer.length, lastSize);
          fsSync.closeSync(fd);

          const newContent = buffer.toString('utf8');
          callback(newContent);
          lastSize = stats.size;
        }
      } catch (e) {
        // File might not exist yet or be locked
      }
    };

    // Check every 500ms
    const intervalId = setInterval(checkForChanges, 500);

    return {
      close: () => clearInterval(intervalId)
    };
  }

  /**
   * Terminate a process by PID
   */
  async terminateProcess(pid, platform) {
    if (!pid) return false;

    return new Promise((resolve) => {
      try {
        if (platform === 'win32') {
          exec(`taskkill /PID ${pid} /T /F`, (error) => {
            if (error) {
              ui.warning(`Could not terminate process ${pid}: ${error.message}`);
              resolve(false);
            } else {
              ui.success(`Terminated process ${pid}`);
              resolve(true);
            }
          });
        } else {
          exec(`kill -TERM ${pid}`, (error) => {
            if (error) {
              // Try SIGKILL as fallback
              exec(`kill -KILL ${pid}`, (err2) => {
                if (err2) {
                  ui.warning(`Could not terminate process ${pid}`);
                  resolve(false);
                } else {
                  ui.success(`Terminated process ${pid}`);
                  resolve(true);
                }
              });
            } else {
              ui.success(`Terminated process ${pid}`);
              resolve(true);
            }
          });
        }
      } catch (e) {
        ui.warning(`Error terminating process: ${e.message}`);
        resolve(false);
      }
    });
  }

  /**
   * Check if a process is running
   */
  async isProcessRunning(pid, platform) {
    if (!pid) return false;

    return new Promise((resolve) => {
      if (platform === 'win32') {
        exec(`tasklist /FI "PID eq ${pid}" /NH`, (error, stdout) => {
          resolve(!error && stdout.includes(pid.toString()));
        });
      } else {
        exec(`ps -p ${pid}`, (error) => {
          resolve(!error);
        });
      }
    });
  }

  /**
   * Wait for a process to complete
   */
  async waitForProcess(pid, platform, timeoutMs, outputFile) {
    const startTime = Date.now();

    return new Promise((resolve) => {
      const checkInterval = setInterval(async () => {
        const running = await this.isProcessRunning(pid, platform);

        if (!running) {
          clearInterval(checkInterval);

          // Read final output
          let output = '';
          try {
            output = fsSync.readFileSync(outputFile, 'utf8');
          } catch (e) {
            // Ignore
          }

          // Check if command succeeded (look for exit code in output)
          const exitCodeMatch = output.match(/exit code (\d+)/i);
          const exitCode = exitCodeMatch ? parseInt(exitCodeMatch[1]) : 0;

          resolve({
            success: exitCode === 0,
            code: exitCode,
            output,
            duration: Date.now() - startTime
          });
          return;
        }

        // Check timeout
        if (timeoutMs > 0 && (Date.now() - startTime) > timeoutMs) {
          clearInterval(checkInterval);
          resolve({
            success: false,
            timedOut: true,
            duration: Date.now() - startTime
          });
        }
      }, 1000);
    });
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

    let confirmNeeded = ['create_file', 'update_file', 'patch_file', 'delete_file', 'run_command'].includes(step.action);
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
          if (!ov) { appendMessage('assistant', 'Skipped creation.'); continue; }
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
