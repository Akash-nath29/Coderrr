const { exec } = require('child_process');
const { promisify } = require('util');
const ui = require('./ui');
const fs = require('fs');
const path = require('path');

const execAsync = promisify(exec);

/**
 * Git operations manager for safety checkpoints and rollback
 */
class GitOperations {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;
    this.gitAvailable = null;
    this.isRepo = null;
  }

  /**
   * Check if git command is available on the system
   */
  async isGitAvailable() {
    if (this.gitAvailable !== null) {
      return this.gitAvailable;
    }

    try {
      await execAsync('git --version');
      this.gitAvailable = true;
      return true;
    } catch (error) {
      this.gitAvailable = false;
      return false;
    }
  }

  /**
   * Check if current directory is a git repository
   */
  async isGitRepository() {
    if (this.isRepo !== null) {
      return this.isRepo;
    }

    try {
      await execAsync('git rev-parse --git-dir', { cwd: this.workingDir });
      this.isRepo = true;
      return true;
    } catch (error) {
      this.isRepo = false;
      return false;
    }
  }

  /**
   * Check if there are uncommitted changes in the working directory
   */
  async hasUncommittedChanges() {
    try {
      const { stdout } = await execAsync('git status --porcelain', { cwd: this.workingDir });
      return stdout.trim().length > 0;
    } catch (error) {
      ui.warning(`Could not check git status: ${error.message}`);
      return false;
    }
  }

  /**
   * Get current branch name
   */
  async getCurrentBranch() {
    try {
      const { stdout } = await execAsync('git rev-parse --abbrev-ref HEAD', { cwd: this.workingDir });
      return stdout.trim();
    } catch (error) {
      return 'unknown';
    }
  }

  /**
   * Create a checkpoint commit before making changes
   */
  async createCheckpoint(description) {
    try {
      // Stage all changes
      await execAsync('git add .', { cwd: this.workingDir });

      // Create checkpoint commit
      const message = `[Coderrr Checkpoint] Before: ${description}`;
      await execAsync(`git commit -m "${message}"`, { cwd: this.workingDir });

      ui.success(`Created checkpoint: ${description}`);
      return true;
    } catch (error) {
      // If there's nothing to commit, that's okay
      if (error.message.includes('nothing to commit')) {
        ui.info('No changes to checkpoint');
        return true;
      }
      ui.warning(`Could not create checkpoint: ${error.message}`);
      return false;
    }
  }

  /**
   * Commit changes after successful operation
   */
  async commitChanges(description) {
    try {
      // Stage all changes
      await execAsync('git add .', { cwd: this.workingDir });

      // Check if there's anything to commit
      const { stdout } = await execAsync('git status --porcelain', { cwd: this.workingDir });
      if (stdout.trim().length === 0) {
        ui.info('No changes to commit');
        return true;
      }

      // Create commit
      const message = `[Coderrr] ${description}`;
      const { stdout: commitOutput } = await execAsync(`git commit -m "${message}"`, { cwd: this.workingDir });

      // Extract commit hash
      const hashMatch = commitOutput.match(/\[.+ ([a-f0-9]+)\]/);
      const hash = hashMatch ? hashMatch[1] : '';

      ui.success(`Auto-committed changes${hash ? ` (${hash})` : ''}`);
      return true;
    } catch (error) {
      ui.warning(`Could not auto-commit: ${error.message}`);
      return false;
    }
  }

  /**
   * Get list of recent Coderrr commits for rollback menu
   */
  async getCoderrCommits(limit = 10) {
    try {
      const { stdout } = await execAsync(
        `git log --grep="\\[Coderrr\\]" --grep="\\[Coderrr Checkpoint\\]" --oneline -n ${limit}`,
        { cwd: this.workingDir }
      );

      if (!stdout.trim()) {
        return [];
      }

      const commits = stdout.trim().split('\n').map(line => {
        const match = line.match(/^([a-f0-9]+)\s+(.+)$/);
        if (match) {
          return {
            hash: match[1],
            message: match[2],
            shortHash: match[1].substring(0, 7)
          };
        }
        return null;
      }).filter(Boolean);

      return commits;
    } catch (error) {
      ui.warning(`Could not get commit history: ${error.message}`);
      return [];
    }
  }

  /**
   * Get detailed commit information
   */
  async getCommitDetails(commitHash) {
    try {
      const { stdout } = await execAsync(
        `git show --stat --format="%an|%ar|%s" ${commitHash}`,
        { cwd: this.workingDir }
      );

      const lines = stdout.split('\n');
      const [author, timeAgo, subject] = lines[0].split('|');

      return {
        author,
        timeAgo,
        subject,
        hash: commitHash
      };
    } catch (error) {
      return null;
    }
  }

  /**
   * Revert a specific commit
   */
  async revertCommit(commitHash) {
    try {
      ui.info(`Reverting commit ${commitHash}...`);
      
      const { stdout } = await execAsync(`git revert ${commitHash} --no-edit`, { cwd: this.workingDir });
      
      ui.success('Successfully rolled back changes');
      return true;
    } catch (error) {
      // Handle merge conflicts
      if (error.message.includes('conflict')) {
        ui.error('Rollback caused merge conflicts');
        ui.warning('Please resolve conflicts manually or run: git revert --abort');
        return false;
      }

      ui.error(`Rollback failed: ${error.message}`);
      return false;
    }
  }

  /**
   * Interactive rollback - show menu and let user select commit to revert
   */
  async interactiveRollback() {
    // Check git availability
    const gitAvailable = await this.isGitAvailable();
    if (!gitAvailable) {
      ui.error('Git is not installed or not available');
      return false;
    }

    const isRepo = await this.isGitRepository();
    if (!isRepo) {
      ui.error('Not a git repository');
      return false;
    }

    // Get commits
    ui.info('Fetching Coderrr commits...');
    const commits = await this.getCoderrCommits(10);

    if (commits.length === 0) {
      ui.warning('No Coderrr commits found to rollback');
      return false;
    }

    // Show interactive menu
    ui.section('Available Rollback Points');
    const choices = commits.map((commit, idx) => ({
      name: `${commit.shortHash} - ${commit.message}`,
      value: commit.hash
    }));

    choices.push({
      name: 'Cancel',
      value: null
    });

    const selected = await ui.select('Select commit to revert:', choices);

    if (!selected) {
      ui.info('Rollback cancelled');
      return false;
    }

    // Get commit details
    const details = await this.getCommitDetails(selected);
    if (details) {
      ui.info(`Commit by: ${details.author} (${details.timeAgo})`);
    }

    // Confirm
    const confirmed = await ui.confirm('This will revert the selected commit. Continue?', false);
    if (!confirmed) {
      ui.info('Rollback cancelled');
      return false;
    }

    // Perform revert
    return await this.revertCommit(selected);
  }

  /**
   * Validate git setup and show warnings if needed
   */
  async validateGitSetup() {
    const gitAvailable = await this.isGitAvailable();
    
    if (!gitAvailable) {
      ui.warning('Git not detected. Auto-commit features disabled.');
      ui.info('Install git to enable automatic checkpoints and rollback.');
      return false;
    }

    const isRepo = await this.isGitRepository();
    
    if (!isRepo) {
      ui.info('Not a git repository. Auto-commit features disabled.');
      return false;
    }

    ui.success('Git repository detected');
    return true;
  }

  /**
   * Check and warn about uncommitted changes
   */
  async checkUncommittedChanges() {
    const hasChanges = await this.hasUncommittedChanges();
    
    if (hasChanges) {
      ui.warning('You have uncommitted changes in your working directory');
      const proceed = await ui.confirm('Proceed with Coderrr operation?', true);
      return proceed;
    }

    return true;
  }
}

module.exports = GitOperations;
