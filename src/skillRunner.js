/**
 * Skill Runner for Coderrr
 * 
 * Executes Python tools from installed skills in isolated subprocess.
 * Captures output and returns structured results to the agent.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { SKILLS_DIR } = require('./skillRegistry');

/**
 * Execute a Python tool from a skill
 * @param {string} skillName - Name of the skill
 * @param {string} toolName - Name of the tool (without .py extension)
 * @param {Object} args - Arguments to pass to the tool
 * @param {Object} options - Execution options
 * @param {string} options.cwd - Working directory for the tool
 * @param {number} options.timeout - Timeout in milliseconds (default: 30000)
 * @returns {Promise<Object>} { success, output, error, exitCode }
 */
async function executeTool(skillName, toolName, args = {}, options = {}) {
    const { cwd = process.cwd(), timeout = 30000 } = options;

    const toolPath = path.join(SKILLS_DIR, skillName, 'tools', `${toolName}.py`);

    // Validate tool exists
    if (!fs.existsSync(toolPath)) {
        return {
            success: false,
            output: '',
            error: `Tool not found: ${skillName}/${toolName}`,
            exitCode: 1
        };
    }

    // Convert args object to command line arguments
    const argsList = buildArgsList(args);

    return new Promise((resolve) => {
        let stdout = '';
        let stderr = '';
        let resolved = false;

        const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';

        const proc = spawn(pythonCommand, [toolPath, ...argsList], {
            cwd,
            env: {
                ...process.env,
                CODERRR_SKILL: skillName,
                CODERRR_TOOL: toolName,
                CODERRR_CWD: cwd
            },
            shell: true,
            timeout
        });

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            if (resolved) return;
            resolved = true;

            resolve({
                success: code === 0,
                output: stdout.trim(),
                error: stderr.trim(),
                exitCode: code
            });
        });

        proc.on('error', (err) => {
            if (resolved) return;
            resolved = true;

            resolve({
                success: false,
                output: '',
                error: `Failed to execute tool: ${err.message}`,
                exitCode: 1
            });
        });

        // Timeout handler
        setTimeout(() => {
            if (resolved) return;
            resolved = true;

            proc.kill('SIGTERM');
            resolve({
                success: false,
                output: stdout.trim(),
                error: `Tool execution timed out after ${timeout}ms`,
                exitCode: 124
            });
        }, timeout);
    });
}

/**
 * Convert an arguments object to a list of command line arguments
 * @param {Object} args - Arguments object
 * @returns {string[]} List of arguments
 */
function buildArgsList(args) {
    const argsList = [];

    for (const [key, value] of Object.entries(args)) {
        if (value === true) {
            // Boolean flag: --flag
            argsList.push(`--${key}`);
        } else if (value === false) {
            // Skip false booleans
            continue;
        } else if (Array.isArray(value)) {
            // Array: --key value1 --key value2
            for (const v of value) {
                argsList.push(`--${key}`, String(v));
            }
        } else if (value !== null && value !== undefined) {
            // Key-value: --key value
            argsList.push(`--${key}`, String(value));
        }
    }

    return argsList;
}

/**
 * Parse tool output as JSON if possible
 * @param {string} output - Raw output string
 * @returns {Object|string} Parsed JSON or original string
 */
function parseToolOutput(output) {
    try {
        return JSON.parse(output);
    } catch {
        return output;
    }
}

/**
 * Check if Python is available on the system
 * @returns {Promise<Object>} { available, version, command }
 */
async function checkPythonAvailable() {
    return new Promise((resolve) => {
        const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';

        const proc = spawn(pythonCommand, ['--version'], { shell: true });

        let output = '';
        proc.stdout.on('data', (data) => {
            output += data.toString();
        });
        proc.stderr.on('data', (data) => {
            output += data.toString();
        });

        proc.on('close', (code) => {
            if (code === 0) {
                const versionMatch = output.match(/Python\s+(\d+\.\d+\.\d+)/);
                resolve({
                    available: true,
                    version: versionMatch ? versionMatch[1] : 'unknown',
                    command: pythonCommand
                });
            } else {
                resolve({
                    available: false,
                    version: null,
                    command: null
                });
            }
        });

        proc.on('error', () => {
            resolve({
                available: false,
                version: null,
                command: null
            });
        });
    });
}

/**
 * Install Python dependencies for a skill (if requirements.txt exists)
 * @param {string} skillName - Name of the skill
 * @returns {Promise<Object>} { success, output, error }
 */
async function installSkillDependencies(skillName) {
    const requirementsPath = path.join(SKILLS_DIR, skillName, 'requirements.txt');

    if (!fs.existsSync(requirementsPath)) {
        return { success: true, output: 'No requirements.txt found', error: '' };
    }

    return new Promise((resolve) => {
        const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';

        const proc = spawn(pythonCommand, ['-m', 'pip', 'install', '-r', requirementsPath], {
            shell: true,
            timeout: 120000 // 2 minute timeout for pip install
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            resolve({
                success: code === 0,
                output: stdout.trim(),
                error: stderr.trim()
            });
        });

        proc.on('error', (err) => {
            resolve({
                success: false,
                output: '',
                error: err.message
            });
        });
    });
}

module.exports = {
    executeTool,
    buildArgsList,
    parseToolOutput,
    checkPythonAvailable,
    installSkillDependencies
};
