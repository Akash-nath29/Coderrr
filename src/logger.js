/**
 * Centralized Logger for Coderrr CLI
 *
 * Provides configurable logging with different levels to control output
 * in development vs production environments.
 */

class Logger {
  constructor() {
    // Log levels in order of verbosity
    this.levels = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
      none: 4
    };

    // Default to info level (shows info, warn, error)
    this.currentLevel = this.levels[process.env.LOG_LEVEL || 'info'];

    // Colors for different log levels
    this.colors = {
      debug: '\x1b[36m', // cyan
      info: '\x1b[32m',  // green
      warn: '\x1b[33m',  // yellow
      error: '\x1b[31m'  // red
    };
    this.reset = '\x1b[0m';
  }

  /**
   * Set the minimum log level
   */
  setLevel(level) {
    if (this.levels.hasOwnProperty(level)) {
      this.currentLevel = this.levels[level];
    } else {
      this.error(`Invalid log level: ${level}. Using 'info' instead.`);
      this.currentLevel = this.levels.info;
    }
  }

  /**
   * Format log message with timestamp and level
   */
  formatMessage(level, message, ...args) {
    const timestamp = new Date().toISOString();
    const levelUpper = level.toUpperCase();
    const color = this.colors[level] || '';
    const formattedArgs = args.length > 0 ? ' ' + args.join(' ') : '';

    return `${color}[${timestamp}] ${levelUpper}: ${message}${formattedArgs}${this.reset}`;
  }

  /**
   * Log debug message
   */
  debug(message, ...args) {
    if (this.currentLevel <= this.levels.debug) {
      console.log(this.formatMessage('debug', message, ...args));
    }
  }

  /**
   * Log info message
   */
  info(message, ...args) {
    if (this.currentLevel <= this.levels.info) {
      console.log(this.formatMessage('info', message, ...args));
    }
  }

  /**
   * Log warning message
   */
  warn(message, ...args) {
    if (this.currentLevel <= this.levels.warn) {
      console.warn(this.formatMessage('warn', message, ...args));
    }
  }

  /**
   * Log error message
   */
  error(message, ...args) {
    if (this.currentLevel <= this.levels.error) {
      console.error(this.formatMessage('error', message, ...args));
    }
  }
}

// Export singleton instance
module.exports = new Logger();
