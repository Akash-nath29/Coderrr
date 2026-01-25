const fs = require('fs');
const path = require('path');
const ui = require('./ui');

/**
 * File Operations Module for Coderrr
 *
 * Provides safe file manipulation operations with automatic directory creation,
 * path resolution, and comprehensive error handling. All operations are
 * synchronous to ensure atomicity and predictable behavior.
 */

// Protected paths that should never be deleted by Coderrr
const PROTECTED_PATHS = [
  'Coderrr.md',
  '.coderrr'
];

class FileOperations {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;
  }

  /**
   * Check if a path is protected (Coderrr config files that should never be deleted)
   * @param {string} filePath - Path to check
   * @returns {boolean} True if path is protected
   */
  isProtectedPath(filePath) {
    const basename = path.basename(filePath);
    const relativePath = path.isAbsolute(filePath)
      ? path.relative(this.workingDir, filePath)
      : filePath;

    // Check if the file/folder itself is protected
    if (PROTECTED_PATHS.includes(basename)) {
      return true;
    }

    // Check if path is inside a protected folder
    for (const protectedPath of PROTECTED_PATHS) {
      if (relativePath.startsWith(protectedPath + path.sep) || relativePath.startsWith(protectedPath + '/')) {
        return true;
      }
    }

    return false;
  }

  /**
   * Resolve absolute path from relative path
   */
  resolvePath(filePath) {
    return path.isAbsolute(filePath)
      ? filePath
      : path.join(this.workingDir, filePath);
  }

  /**
   * Ensure directory exists
   */
  ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
  }

  /**
   * Create a new file with the specified content
   *
   * @param {string} filePath - Relative or absolute path to the file to create
   * @param {string} content - Content to write to the file
   * @returns {Promise<Object>} Result object with success status and absolute path
   * @throws {Error} If file already exists or write operation fails
   */
  async createFile(filePath, content) {
    try {
      const absolutePath = this.resolvePath(filePath);
      const dir = path.dirname(absolutePath);

      // Check if file already exists
      if (fs.existsSync(absolutePath)) {
        throw new Error(`File already exists: ${filePath}`);
      }

      // Ensure directory exists
      this.ensureDir(dir);

      // Write file
      fs.writeFileSync(absolutePath, content, 'utf8');
      ui.displayFileOp('create_file', filePath, 'success');

      // Return with diff data (new file = empty old content)
      return {
        success: true,
        path: absolutePath,
        oldContent: '',
        newContent: content
      };
    } catch (error) {
      ui.displayFileOp('create_file', filePath, 'error');
      throw error;
    }
  }

  /**
   * Update an existing file (replace entire content)
   */
  async updateFile(filePath, content) {
    try {
      const absolutePath = this.resolvePath(filePath);

      // Check if file exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      // Read existing content for diff
      const oldContent = fs.readFileSync(absolutePath, 'utf8');

      // Write file
      fs.writeFileSync(absolutePath, content, 'utf8');
      ui.displayFileOp('update_file', filePath, 'success');

      return {
        success: true,
        path: absolutePath,
        oldContent: oldContent,
        newContent: content
      };
    } catch (error) {
      ui.displayFileOp('update_file', filePath, 'error');
      throw error;
    }
  }

  /**
   * Patch a file (partial update)
   */
  async patchFile(filePath, oldContent, newContent) {
    try {
      const absolutePath = this.resolvePath(filePath);

      // Check if file exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      // Read current content
      const originalContent = fs.readFileSync(absolutePath, 'utf8');

      // Replace old content with new content
      if (!originalContent.includes(oldContent)) {
        throw new Error(`Pattern not found in file: ${filePath}`);
      }

      const patchedContent = originalContent.replace(oldContent, newContent);

      // Write back
      fs.writeFileSync(absolutePath, patchedContent, 'utf8');
      ui.displayFileOp('patch_file', filePath, 'success');

      return {
        success: true,
        path: absolutePath,
        oldContent: originalContent,
        newContent: patchedContent
      };
    } catch (error) {
      ui.displayFileOp('patch_file', filePath, 'error');
      throw error;
    }
  }

  /**
   * Delete a file
   */
  async deleteFile(filePath) {
    try {
      const absolutePath = this.resolvePath(filePath);

      // Check if path is protected
      if (this.isProtectedPath(filePath)) {
        ui.warning(`Protected path cannot be deleted: ${filePath}`);
        throw new Error(`Cannot delete protected Coderrr config: ${filePath}`);
      }

      // Check if file exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      // Read content before deleting for diff
      const oldContent = fs.readFileSync(absolutePath, 'utf8');

      // Delete file
      fs.unlinkSync(absolutePath);
      ui.displayFileOp('delete_file', filePath, 'success');

      return {
        success: true,
        path: absolutePath,
        oldContent: oldContent,
        newContent: ''
      };
    } catch (error) {
      ui.displayFileOp('delete_file', filePath, 'error');
      throw error;
    }
  }

  /**
   * Read a file
   */
  async readFile(filePath) {
    try {
      const absolutePath = this.resolvePath(filePath);

      // Check if file exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      // Read file
      const content = fs.readFileSync(absolutePath, 'utf8');
      ui.displayFileOp('read_file', filePath, 'success');
      return { success: true, content, path: absolutePath };
    } catch (error) {
      ui.displayFileOp('read_file', filePath, 'error');
      throw error;
    }
  }

  /**
   * Create a new directory
   *
   * @param {string} dirPath - Relative or absolute path to the directory to create
   * @returns {Promise<Object>} Result object with success status and absolute path
   * @throws {Error} If directory already exists or creation fails
   */
  async createDir(dirPath) {
    try {
      const absolutePath = this.resolvePath(dirPath);

      // Check if directory already exists
      if (fs.existsSync(absolutePath)) {
        throw new Error(`Directory already exists: ${dirPath}`);
      }

      // Create directory (recursive)
      fs.mkdirSync(absolutePath, { recursive: true });
      ui.displayFileOp('create_dir', dirPath, 'success');
      return { success: true, path: absolutePath };
    } catch (error) {
      ui.displayFileOp('create_dir', dirPath, 'error');
      throw error;
    }
  }

  /**
   * Delete an empty directory
   *
   * @param {string} dirPath - Relative or absolute path to the directory to delete
   * @returns {Promise<Object>} Result object with success status and absolute path
   * @throws {Error} If directory not found, not empty, or deletion fails
   */
  async deleteDir(dirPath) {
    try {
      const absolutePath = this.resolvePath(dirPath);

      // Check if path is protected
      if (this.isProtectedPath(dirPath)) {
        ui.warning(`Protected directory cannot be deleted: ${dirPath}`);
        throw new Error(`Cannot delete protected Coderrr config: ${dirPath}`);
      }

      // Check if directory exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`Directory not found: ${dirPath}`);
      }

      // Check if it's actually a directory
      if (!fs.statSync(absolutePath).isDirectory()) {
        throw new Error(`Path is not a directory: ${dirPath}`);
      }

      // Check if directory is empty
      const contents = fs.readdirSync(absolutePath);
      if (contents.length > 0) {
        throw new Error(`Directory not empty: ${dirPath}`);
      }

      // Delete directory
      fs.rmdirSync(absolutePath);
      ui.displayFileOp('delete_dir', dirPath, 'success');
      return { success: true, path: absolutePath };
    } catch (error) {
      ui.displayFileOp('delete_dir', dirPath, 'error');
      throw error;
    }
  }

  /**
   * List contents of a directory
   *
   * @param {string} dirPath - Relative or absolute path to the directory to list
   * @returns {Promise<Object>} Result object with success status, absolute path, and contents array
   * @throws {Error} If directory not found or listing fails
   */
  async listDir(dirPath) {
    try {
      const absolutePath = this.resolvePath(dirPath);

      // Check if directory exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`Directory not found: ${dirPath}`);
      }

      // Check if it's actually a directory
      if (!fs.statSync(absolutePath).isDirectory()) {
        throw new Error(`Path is not a directory: ${dirPath}`);
      }

      // List contents
      const contents = fs.readdirSync(absolutePath);
      ui.displayFileOp('list_dir', dirPath, 'success');
      return { success: true, path: absolutePath, contents };
    } catch (error) {
      ui.displayFileOp('list_dir', dirPath, 'error');
      throw error;
    }
  }

  /**
   * Rename/move a directory
   *
   * @param {string} oldDirPath - Relative or absolute path to the directory to rename
   * @param {string} newDirPath - Relative or absolute path for the new directory name/location
   * @returns {Promise<Object>} Result object with success status and absolute paths
   * @throws {Error} If source directory not found, destination exists, or rename fails
   */
  async renameDir(oldDirPath, newDirPath) {
    try {
      const oldAbsolutePath = this.resolvePath(oldDirPath);
      const newAbsolutePath = this.resolvePath(newDirPath);

      // Check if source directory exists
      if (!fs.existsSync(oldAbsolutePath)) {
        throw new Error(`Directory not found: ${oldDirPath}`);
      }

      // Check if it's actually a directory
      if (!fs.statSync(oldAbsolutePath).isDirectory()) {
        throw new Error(`Source path is not a directory: ${oldDirPath}`);
      }

      // Check if destination already exists
      if (fs.existsSync(newAbsolutePath)) {
        throw new Error(`Destination already exists: ${newDirPath}`);
      }

      // Ensure parent directory of destination exists
      const newDirParent = path.dirname(newAbsolutePath);
      this.ensureDir(newDirParent);

      // Rename/move directory
      fs.renameSync(oldAbsolutePath, newAbsolutePath);
      ui.displayFileOp('rename_dir', `${oldDirPath} -> ${newDirPath}`, 'success');
      return { success: true, oldPath: oldAbsolutePath, newPath: newAbsolutePath };
    } catch (error) {
      ui.displayFileOp('rename_dir', `${oldDirPath} -> ${newDirPath}`, 'error');
      throw error;
    }
  }

  /**
   * Execute a file or directory operation based on action type
   */
  async execute(action) {
    switch (action.action) {
      case 'create_file':
        return await this.createFile(action.path, action.content || '');

      case 'update_file':
        return await this.updateFile(action.path, action.content || '');

      case 'patch_file':
        return await this.patchFile(
          action.path,
          action.oldContent || action.patch?.old || '',
          action.newContent || action.patch?.new || action.content || ''
        );

      case 'delete_file':
        return await this.deleteFile(action.path);

      case 'read_file':
        return await this.readFile(action.path);

      case 'create_dir':
        return await this.createDir(action.path);

      case 'delete_dir':
        return await this.deleteDir(action.path);

      case 'list_dir':
        return await this.listDir(action.path);

      case 'rename_dir':
        return await this.renameDir(action.oldPath || action.path, action.newPath);

      default:
        throw new Error(`Unknown action: ${action.action}`);
    }
  }
}

module.exports = FileOperations;
