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

class FileOperations {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;
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
      return { success: true, path: absolutePath };
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

      // Write file
      fs.writeFileSync(absolutePath, content, 'utf8');
      ui.displayFileOp('update_file', filePath, 'success');
      return { success: true, path: absolutePath };
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
      let content = fs.readFileSync(absolutePath, 'utf8');

      // Replace old content with new content
      if (!content.includes(oldContent)) {
        throw new Error(`Pattern not found in file: ${filePath}`);
      }

      content = content.replace(oldContent, newContent);

      // Write back
      fs.writeFileSync(absolutePath, content, 'utf8');
      ui.displayFileOp('patch_file', filePath, 'success');
      return { success: true, path: absolutePath };
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
      
      // Check if file exists
      if (!fs.existsSync(absolutePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      // Delete file
      fs.unlinkSync(absolutePath);
      ui.displayFileOp('delete_file', filePath, 'success');
      return { success: true, path: absolutePath };
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
   * Execute a file operation based on action type
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
      
      default:
        throw new Error(`Unknown file action: ${action.action}`);
    }
  }
}

module.exports = FileOperations;
