#!/usr/bin/env node

/**
 * Coderrr - AI Coding Agent CLI
 * Like Claude Code, but yours!
 */

const { program } = require('commander');
const path = require('path');
const Agent = require('../src/agent');
require('dotenv').config();

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
  .action(async (options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest
    });

    await agent.interactive();
  });

program
  .command('exec <request>')
  .description('Execute a single request and exit')
  .option('-b, --backend <url>', 'Backend URL', process.env.CODERRR_BACKEND)
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .option('--no-auto-test', 'Disable automatic test running')
  .action(async (request, options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest
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
      autoTest: true
    });

    await agent.interactive();
  });

program.parse();
