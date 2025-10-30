#!/usr/bin/env node

/**
 * Coderrr - AI Coding Agent CLI
 * Like Claude Code, but yours!
 */

const { program } = require('commander');
const path = require('path');
const os = require('os');
const fs = require('fs');
const Agent = require('../src/agent');

// Optional: Load .env from user's home directory (for advanced users who want custom backend)
const homeConfigPath = path.join(os.homedir(), '.coderrr', '.env');
if (fs.existsSync(homeConfigPath)) {
  require('dotenv').config({ path: homeConfigPath });
}

// For development: Load .env from package directory
const packageConfigPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(packageConfigPath)) {
  require('dotenv').config({ path: packageConfigPath, override: false });
}

program
  .name('coderrr')
  .description('AI Coding Agent CLI - Your personal coding assistant')
  .version('1.0.0');

program
  .command('start')
  .description('Start interactive agent mode')
  .option('-b, --backend <url>', 'Backend URL', process.env.CODERRR_BACKEND)
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .option('--no-auto-test', 'Disable automatic test running')
  .option('--no-auto-retry', 'Disable automatic retry on errors (self-healing)')
  .option('--max-retries <number>', 'Maximum retry attempts per step', '2')
  .action(async (options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest,
      autoRetry: options.autoRetry,
      maxRetries: parseInt(options.maxRetries)
    });

    await agent.interactive();
  });

program
  .command('exec <request>')
  .description('Execute a single request and exit')
  .option('-b, --backend <url>', 'Backend URL', process.env.CODERRR_BACKEND)
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .option('--no-auto-test', 'Disable automatic test running')
  .option('--no-auto-retry', 'Disable automatic retry on errors (self-healing)')
  .option('--max-retries <number>', 'Maximum retry attempts per step', '2')
  .action(async (request, options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest,
      autoRetry: options.autoRetry,
      maxRetries: parseInt(options.maxRetries)
    });

    await agent.process(request);
    process.exit(0);
  });

// Default command - start interactive mode
program
  .action(async (options) => {
    const agent = new Agent({
      backendUrl: process.env.CODERRR_BACKEND,
      workingDir: process.cwd(),
      autoTest: true,
      autoRetry: true,
      maxRetries: 2
    });

    await agent.interactive();
  });

program.parse();
