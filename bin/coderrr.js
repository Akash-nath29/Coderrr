#!/usr/bin/env node

/**
 * Coderrr - AI Coding Agent CLI
 * Like Claude Code, but yours!
 */

const { program } = require('commander');
const path = require('path');
const os = require('os');
const fs = require('fs');
const inquirer = require('inquirer');
const chalk = require('chalk');
const Agent = require('../src/agent');
const configManager = require('../src/configManager');
const { getProviderChoices, getModelChoices, getProvider, validateApiKey } = require('../src/providers');
const { tryExtractJSON } = require('../src/utils');
const { displayRecipeList } = require('../src/recipeUI');
const recipeManager = require('../src/recipeManager');
program
  .command('recipe [name]')
  .description('Manage and run custom coding recipes')
  .option('-l, --list', 'List all available recipes')
  .action((name, options) => {
    if (options.list || !name) {
      displayRecipeList();
    } else {
      const recipe = recipeManager.getRecipe(name);
      if (recipe) {
        console.log(`Running recipe: ${recipe.name}...`);
        // Logic to pass tasks to the agent would go here
      } else {
        console.log(`Recipe "${name}" not found.`);
      }
    }
  });
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

// Config command - configure provider and API key
program
  .command('config')
  .description('Configure AI provider, API key, and model')
  .option('--show', 'Show current configuration')
  .option('--clear', 'Clear saved configuration')
  .action(async (options) => {
    // Show current config
    if (options.show) {
      const summary = configManager.getConfigSummary();
      if (!summary) {
        console.log(chalk.yellow('\n▲ No configuration found.'));
        console.log(chalk.gray('  Run `coderrr config` to set up your provider.\n'));
      } else {
        console.log(chalk.cyan.bold('\n├─ Current Configuration\n'));
        console.log(`  Provider: ${chalk.white(summary.provider)}`);
        console.log(`  Model:    ${chalk.white(summary.model)}`);
        console.log(`  API Key:  ${chalk.gray(summary.apiKey)}`);
        if (summary.endpoint !== 'Default') {
          console.log(`  Endpoint: ${chalk.gray(summary.endpoint)}`);
        }
        console.log(`\n  Config file: ${chalk.gray(configManager.getConfigPath())}\n`);
      }
      return;
    }

    // Clear config
    if (options.clear) {
      configManager.clearConfig();
      console.log(chalk.green('■ Configuration cleared.\n'));
      return;
    }

    // Interactive configuration
    console.log(chalk.cyan.bold('\n├─ Coderrr Configuration\n'));
    console.log(chalk.gray('   Configure your AI provider and API key.\n'));

    try {
      // Step 1: Select provider
      const { provider } = await inquirer.prompt([
        {
          type: 'list',
          name: 'provider',
          message: 'Select your AI provider:',
          choices: getProviderChoices()
        }
      ]);

      const providerInfo = getProvider(provider);

      // Step 2: API Key (if required)
      let apiKey = null;
      if (providerInfo.requiresKey) {
        console.log(chalk.gray(`\n  ${providerInfo.name} requires an API key.`));
        if (providerInfo.keyEnvVar) {
          console.log(chalk.gray(`  You can also set ${providerInfo.keyEnvVar} environment variable.\n`));
        }

        const { key } = await inquirer.prompt([
          {
            type: 'password',
            name: 'key',
            message: `Enter your ${providerInfo.name} API key:`,
            mask: '*',
            validate: (input) => {
              const result = validateApiKey(provider, input);
              return result.valid ? true : result.error;
            }
          }
        ]);
        apiKey = key;
      } else {
        console.log(chalk.green(`\n  ■ ${providerInfo.name} doesn't require an API key.\n`));
      }

      // Step 2.5: Custom endpoint (for Ollama)
      let endpoint = providerInfo.endpoint || null;
      if (providerInfo.customEndpoint) {
        const { customEndpoint } = await inquirer.prompt([
          {
            type: 'input',
            name: 'customEndpoint',
            message: 'Enter Ollama endpoint:',
            default: providerInfo.endpoint
          }
        ]);
        endpoint = customEndpoint;

        // Show note for Ollama
        if (providerInfo.note) {
          console.log(chalk.yellow(`\n  ▲ ${providerInfo.note}\n`));
        }
      }

      // Step 3: Select model
      const modelChoices = getModelChoices(provider);
      const { model } = await inquirer.prompt([
        {
          type: 'list',
          name: 'model',
          message: 'Select a model:',
          choices: modelChoices,
          default: providerInfo.defaultModel
        }
      ]);

      // Save configuration
      const config = {
        provider,
        apiKey,
        model,
        endpoint
      };

      configManager.saveConfig(config);

      console.log(chalk.green('\n■ Configuration saved!\n'));
      console.log(`  Provider: ${chalk.white(providerInfo.name)}`);
      console.log(`  Model:    ${chalk.white(model)}`);
      if (apiKey) {
        console.log(`  API Key:  ${chalk.gray(configManager.maskApiKey(apiKey))}`);
      }
      console.log(`\n  Config file: ${chalk.gray(configManager.getConfigPath())}\n`);

      console.log(chalk.cyan('Run `coderrr` to start using your configured provider!\n'));

    } catch (error) {
      if (error.name === 'ExitPromptError') {
        console.log(chalk.yellow('\n▲ Configuration cancelled.\n'));
      } else {
        console.error(chalk.red(`\n✗ Error: ${error.message}\n`));
      }
    }
  });

program
  .command('start')
  .description('Start interactive agent mode')
  .option('-b, --backend <url>', 'Backend URL', process.env.CODERRR_BACKEND)
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .option('--no-auto-test', 'Disable automatic test running')
  .option('--no-auto-retry', 'Disable automatic retry on errors (self-healing)')
  .option('--max-retries <number>', 'Maximum retry attempts per step', '2')
  .option('--auto-commit', 'Enable git auto-commit and checkpoint features')
  .action(async (options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest,
      autoRetry: options.autoRetry,
      maxRetries: parseInt(options.maxRetries),
      gitEnabled: options.autoCommit || false
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
  .option('--auto-commit', 'Enable git auto-commit and checkpoint features')
  .action(async (request, options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      autoTest: options.autoTest,
      autoRetry: options.autoRetry,
      maxRetries: parseInt(options.maxRetries),
      gitEnabled: options.autoCommit || false
    });

    await agent.process(request);
    process.exit(0);
  });

program
  .command('analyze <request>')
  .description('Analyze a request and return a structured plan without executing it')
  .option('-b, --backend <url>', 'Backend URL', process.env.CODERRR_BACKEND)
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .action(async (request, options) => {
    const agent = new Agent({
      backendUrl: options.backend,
      workingDir: path.resolve(options.dir),
      scanOnFirstRequest: true
    });

    try {
      const response = await agent.chat(request);

      // Handle both object responses (new backend) and string responses
      const parsed = typeof response === 'object' && response !== null && response.plan
        ? response
        : tryExtractJSON(response);

      if (parsed) {
        console.log(JSON.stringify(parsed, null, 2));
      } else {
        console.log(chalk.yellow('\n▲ Could not parse a structured plan from the AI response.'));
        console.log(chalk.gray('Raw response:'));
        console.log(response);
      }
      process.exit(0);
    } catch (error) {
      console.error(chalk.red(`\n✗ Error during analysis: ${error.message}\n`));
      process.exit(1);
    }
  });

// Rollback command - revert Coderrr changes
program
  .command('rollback')
  .description('Rollback recent Coderrr changes via interactive menu')
  .option('-d, --dir <path>', 'Working directory', process.cwd())
  .action(async (options) => {
    const GitOperations = require('../src/gitOps');
    const git = new GitOperations(path.resolve(options.dir));

    await git.interactiveRollback();
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
      maxRetries: 2,
      gitEnabled: false
    });

    await agent.interactive();
  });

program.parse();
