const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');
const debounce = require('./hooks/useDebounce'); // Import our new utility

/**
 * UI utilities for Coderrr CLI
 */

const ui = {
  /**
   * Display welcome banner
   */
  showBanner() {
    console.log(chalk.cyan.bold('\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓'));
    console.log(chalk.cyan.bold('┃                                                            ┃'));
    console.log(chalk.cyan.bold('┃   ') + chalk.white.bold('██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗') + chalk.cyan.bold('  ┃'));
    console.log(chalk.cyan.bold('┃  ') + chalk.white.bold('██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗') + chalk.cyan.bold(' ┃'));
    console.log(chalk.cyan.bold('┃  ') + chalk.white.bold('██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝') + chalk.cyan.bold(' ┃'));
    console.log(chalk.cyan.bold('┃  ') + chalk.white.bold('██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗') + chalk.cyan.bold(' ┃'));
    console.log(chalk.cyan.bold('┃  ') + chalk.white.bold('╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║') + chalk.cyan.bold(' ┃'));
    console.log(chalk.cyan.bold('┃   ') + chalk.white.bold('╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝') + chalk.cyan.bold(' ┃'));
    console.log(chalk.cyan.bold('┃                                                            ┃'));
    console.log(chalk.cyan.bold('┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫'));
    console.log(chalk.cyan.bold('┃  ') + chalk.yellow.bold('Your friendly neighbourhood Open Source Coding Agent') + chalk.cyan.bold('      ┃'));
    console.log(chalk.cyan.bold('┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n'));
    

    console.log(chalk.yellow.bold('\n💡 Quick Commands:'));
    console.log(chalk.gray('  • Type "exit" or "quit" to leave'));
    console.log(chalk.gray('  • Just start typing your coding request'));
    console.log();
  },

  /**
   * Display info message
   */
  info(message) {
    console.log(chalk.blue('ℹ '), message);
  },

  /**
   * Display success message
   */
  success(message) {
    console.log(chalk.green('✓'), message);
  },

  /**
   * Display warning message
   */
  warning(message) {
    console.log(chalk.yellow('⚠'), message);
  },

  /**
   * Display error message
   */
  error(message) {
    console.log(chalk.red('✗'), message);
  },

  /**
   * Display section header
   */
  section(title) {
    console.log(chalk.bold.cyan(`\n▶ ${title}`));
  },

  /**
   * Create a spinner
   */
  spinner(text) {
    return ora({
      text,
      color: 'cyan',
      spinner: 'dots'
    });
  },

  /**
   * Ask user for confirmation
   */
  async confirm(message, defaultValue = false) {
    const { confirmed } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirmed',
        message,
        default: defaultValue
      }
    ]);
    return confirmed;
  },

  /**
   * Ask user for text input with optional debounced processing
   * Updated for Issue #3 optimization
   */
  async input(message, defaultValue = '', onUpdate = null) {
    // If an onUpdate callback is provided, we debounce it
    const debouncedUpdate = onUpdate ? debounce(onUpdate, 400) : null;

    const { answer } = await inquirer.prompt([
      {
        type: 'input',
        name: 'answer',
        message,
        default: defaultValue,
        // Inquirer validate can act as a listener for keystrokes in some setups
        validate: (val) => {
            if (debouncedUpdate) debouncedUpdate(val);
            return true;
        }
      }
    ]);
    return answer;
  },

  /**
   * Ask user to select from a list
   */
  async select(message, choices) {
    const { answer } = await inquirer.prompt([
      {
        type: 'list',
        name: 'answer',
        message,
        choices
      }
    ]);
    return answer;
  },

  /**
   * Display TODO list
   */
  displayTodos(todos) {
    console.log(chalk.bold.cyan('\n📋 TODO List:'));
    todos.forEach((todo, index) => {
      const status = todo.completed 
        ? chalk.green('✓') 
        : todo.inProgress 
          ? chalk.yellow('⋯') 
          : chalk.gray('○');
      const title = todo.completed 
        ? chalk.gray.strikethrough(todo.title) 
        : todo.inProgress 
          ? chalk.yellow(todo.title) 
          : chalk.white(todo.title);
      console.log(`  ${status} ${index + 1}. ${title}`);
      if (todo.details && !todo.completed) {
        console.log(chalk.gray(`     ${todo.details}`));
      }
    });
    console.log();
  },

  /**
   * Display file operation
   */
  displayFileOp(action, path, status = 'pending') {
    const icons = {
      create_file: '📄',
      update_file: '📝',
      patch_file: '🔧',
      delete_file: '🗑️',
      read_file: '👁️'
    };
    const colors = {
      pending: chalk.yellow,
      success: chalk.green,
      error: chalk.red
    };
    const icon = icons[action] || '📁';
    const color = colors[status] || chalk.white;
    console.log(color(`  ${icon} ${action}: ${path}`));
  },

  /**
   * Display command execution prompt
   */
  displayCommand(command) {
    console.log(chalk.bold.magenta('\n💻 Command to execute:'));
    console.log(chalk.cyan(`   ${command}`));
  },

  /**
   * Clear console
   */
  clear() {
    console.clear();
  },

  /**
   * Add spacing
   */
  space() {
    console.log();
  }
};

module.exports = ui;