const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');
const debounce = require('./debounce');
const Diff = require('diff');

/**
 * UI utilities for Coderrr CLI
 * 
 * Uses elegant Unicode box-drawing characters for a clean, minimal terminal UI.
 */

// Unicode symbols for consistent UI
const SYMBOLS = {
  // Status indicators
  info: '◇',
  success: '■',
  warning: '▲',
  error: '✗',

  // Progress indicators
  pending: '○',
  inProgress: '◆',
  complete: '■',

  // Tree structure
  branch: '├─',
  corner: '└─',
  line: '│',

  // File operations
  create: '+',
  update: '~',
  patch: '#',
  delete: '-',
  read: '?',
  dir: 'd',

  // Section headers
  section: '▸',

  // Command
  cmd: '$'
};

const ui = {
  /**
   * Display welcome banner
   */
  showBanner() {
    console.log(chalk.cyan.bold('\n┌──────────────────────────────────────────────────────────────┐'));
    console.log(chalk.cyan.bold('│                                                              │'));
    console.log(chalk.cyan.bold('│   ') + chalk.white.bold('██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗') + chalk.cyan.bold('  │'));
    console.log(chalk.cyan.bold('│  ') + chalk.white.bold('██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗') + chalk.cyan.bold(' │'));
    console.log(chalk.cyan.bold('│  ') + chalk.white.bold('██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝') + chalk.cyan.bold(' │'));
    console.log(chalk.cyan.bold('│  ') + chalk.white.bold('██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗') + chalk.cyan.bold(' │'));
    console.log(chalk.cyan.bold('│  ') + chalk.white.bold('╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║') + chalk.cyan.bold(' │'));
    console.log(chalk.cyan.bold('│   ') + chalk.white.bold('╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝') + chalk.cyan.bold(' │'));
    console.log(chalk.cyan.bold('│                                                              │'));
    console.log(chalk.cyan.bold('├──────────────────────────────────────────────────────────────┤'));
    console.log(chalk.cyan.bold('│  ') + chalk.yellow.bold('Your friendly neighbourhood Open Source Coding Agent') + chalk.cyan.bold('        │'));
    console.log(chalk.cyan.bold('└──────────────────────────────────────────────────────────────┘\n'));

    console.log(chalk.cyan.bold(`\n${SYMBOLS.section} Quick Commands`));
    console.log(chalk.gray(`  ${SYMBOLS.line}  Type your coding request`));
    console.log(chalk.gray(`  ${SYMBOLS.corner}  "exit" or "quit" to leave`));
    console.log();
  },

  /**
   * Display info message
   */
  info(message) {
    console.log(chalk.cyan(SYMBOLS.info), message);
  },

  /**
   * Display success message
   */
  success(message) {
    console.log(chalk.green(SYMBOLS.success), message);
  },

  /**
   * Display warning message
   */
  warning(message) {
    console.log(chalk.yellow(SYMBOLS.warning), message);
  },

  /**
   * Display error message
   */
  error(message) {
    console.log(chalk.red(SYMBOLS.error), message);
  },

  /**
   * Display section header
   */
  section(title) {
    console.log(chalk.bold.cyan(`\n${SYMBOLS.branch} ${title}`));
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
   */
  async input(message, defaultValue = '', onUpdate = null) {
    const debouncedUpdate = onUpdate ? debounce(onUpdate, 400) : null;

    const { answer } = await inquirer.prompt([
      {
        type: 'input',
        name: 'answer',
        message,
        default: defaultValue,
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
   * Display TODO list with tree structure
   */
  displayTodos(todos) {
    console.log(chalk.bold.cyan(`\n${SYMBOLS.branch} Task List`));

    todos.forEach((todo, index) => {
      const isLast = index === todos.length - 1;
      const prefix = isLast ? SYMBOLS.corner : SYMBOLS.branch;

      // Status indicator
      const status = todo.completed
        ? chalk.green(SYMBOLS.complete)
        : todo.inProgress
          ? chalk.yellow(SYMBOLS.inProgress)
          : chalk.gray(SYMBOLS.pending);

      // Title styling
      const title = todo.completed
        ? chalk.gray.strikethrough(todo.title)
        : todo.inProgress
          ? chalk.yellow(todo.title)
          : chalk.white(todo.title);

      console.log(chalk.cyan(`  ${prefix}`) + ` ${status} ${title}`);

      // Show details for non-completed items
      if (todo.details && !todo.completed) {
        const detailPrefix = isLast ? '   ' : `  ${SYMBOLS.line}`;
        console.log(chalk.gray(`  ${detailPrefix}    ${todo.details}`));
      }
    });
    console.log();
  },

  /**
   * Display file operation
   */
  displayFileOp(action, filePath, status = 'pending') {
    const icons = {
      create_file: `[${SYMBOLS.create}]`,
      update_file: `[${SYMBOLS.update}]`,
      patch_file: `[${SYMBOLS.patch}]`,
      delete_file: `[${SYMBOLS.delete}]`,
      read_file: `[${SYMBOLS.read}]`,
      create_dir: `[${SYMBOLS.dir}+]`,
      delete_dir: `[${SYMBOLS.d}-]`,
      list_dir: `[${SYMBOLS.dir}?]`,
      rename_dir: `[${SYMBOLS.dir}~]`
    };

    const colors = {
      pending: chalk.yellow,
      success: chalk.green,
      error: chalk.red
    };

    const icon = icons[action] || `[${SYMBOLS.dir}]`;
    const color = colors[status] || chalk.white;
    console.log(color(`  ${SYMBOLS.line} ${icon} ${action}: ${filePath}`));
  },

  /**
   * Display command execution prompt
   */
  displayCommand(command) {
    console.log(chalk.bold.magenta(`\n${SYMBOLS.branch} Command to execute`));
    console.log(chalk.cyan(`  ${SYMBOLS.line} ${SYMBOLS.cmd} ${command}`));
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
  },

  /**
   * Display a colored diff between old and new content
   * @param {string} filePath - File path for the diff header
   * @param {string} oldContent - Previous content (empty string for new files)
   * @param {string} newContent - New content (empty string for deleted files)
   * @param {number} maxLines - Maximum lines to display before truncating
   */
  displayDiff(filePath, oldContent = '', newContent = '', maxLines = 50) {
    // Generate unified diff
    const patch = Diff.createPatch(
      filePath,
      oldContent || '',
      newContent || '',
      'before',
      'after'
    );

    // Parse the diff lines
    const lines = patch.split('\n');
    let displayedLines = 0;
    let skippedLines = 0;
    let additions = 0;
    let deletions = 0;

    // First pass: count total additions and deletions
    for (let i = 4; i < lines.length; i++) {
      const line = lines[i];
      if (line.startsWith('+') && !line.startsWith('+++')) additions++;
      if (line.startsWith('-') && !line.startsWith('---')) deletions++;
    }

    // Show header with summary
    console.log(chalk.gray(`  ${SYMBOLS.line}`));
    const summary = [];
    if (additions > 0) summary.push(chalk.green(`+${additions}`));
    if (deletions > 0) summary.push(chalk.red(`-${deletions}`));
    console.log(chalk.gray(`  ${SYMBOLS.branch} Diff: ${filePath}`) + (summary.length ? ` (${summary.join(', ')})` : ''));

    // Second pass: display lines
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Skip the header lines (first 4 lines of unified diff)
      if (i < 4) continue;

      // Skip empty lines at the end
      if (line === '' && i === lines.length - 1) continue;

      // Check if we've exceeded max lines
      if (displayedLines >= maxLines) {
        skippedLines++;
        continue;
      }

      // Colorize based on line prefix
      if (line.startsWith('+')) {
        console.log(chalk.green(`  ${SYMBOLS.line}   ${line}`));
        displayedLines++;
      } else if (line.startsWith('-')) {
        console.log(chalk.red(`  ${SYMBOLS.line}   ${line}`));
        displayedLines++;
      } else if (line.startsWith('@@')) {
        // Hunk header
        console.log(chalk.cyan(`  ${SYMBOLS.line}   ${line}`));
        displayedLines++;
      } else if (line.trim() !== '') {
        // Context lines
        console.log(chalk.gray(`  ${SYMBOLS.line}    ${line}`));
        displayedLines++;
      }
    }

    // Show truncation message if needed
    if (skippedLines > 0) {
      console.log(chalk.gray(`  ${SYMBOLS.line}   ... ${skippedLines} more lines`));
    }

    console.log(chalk.gray(`  ${SYMBOLS.corner}`));
  }
};

module.exports = ui;