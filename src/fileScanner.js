const fs = require('fs');
const path = require('path');
const logger = require('./logger');

/**
 * FileScanner - Handles directory scanning and file discovery
 * Responsible for finding source files while respecting ignore rules
 */

class FileScanner {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;

    // Directories to ignore
    this.ignoreDirs = new Set([
      'node_modules',
      'env',
      '.env',
      'venv',
      '.venv',
      '__pycache__',
      '.git',
      '.github',
      'dist',
      'build',
      'out',
      'target',
      '.next',
      '.nuxt',
      'coverage',
      '.pytest_cache',
      '.mypy_cache',
      '.tox',
      'vendor',
      'bower_components'
    ]);

    // Files to ignore
    this.ignoreFiles = new Set([
      '.DS_Store',
      'Thumbs.db',
      '.gitignore',
      '.dockerignore',
      'package-lock.json',
      'yarn.lock',
      'pnpm-lock.yaml',
      'poetry.lock',
      'Pipfile.lock',
      '.env',
      '.env.local',
      '.env.example'
    ]);

    // Source file extensions to include
    this.sourceExtensions = new Set([
      '.js', '.jsx', '.ts', '.tsx',
      '.py', '.pyi',
      '.java', '.kt', '.scala',
      '.go', '.rs',
      '.c', '.cpp', '.cc', '.h', '.hpp',
      '.cs', '.vb',
      '.rb', '.php',
      '.swift', '.m',
      '.sh', '.bash',
      '.sql',
      '.vue', '.svelte',
      '.html', '.css', '.scss', '.less',
      '.json', '.yaml', '.yml', '.toml',
      '.md', '.txt'
    ]);

    // Max file size to read (500KB)
    this.maxFileSize = 500 * 1024;
  }

  /**
   * Check if path should be ignored
   */
  shouldIgnore(filePath, stats) {
    const basename = path.basename(filePath);

    // Ignore specific files
    if (this.ignoreFiles.has(basename)) {
      return true;
    }

    // Ignore directories
    if (stats.isDirectory() && this.ignoreDirs.has(basename)) {
      return true;
    }

    // Ignore hidden files/directories (except .github is already ignored)
    if (basename.startsWith('.') && !basename.match(/\.(js|ts|py|md|json|yaml|yml)$/)) {
      return true;
    }

    return false;
  }

  /**
   * Check if file is a source file we want to read
   */
  isSourceFile(filePath, stats) {
    if (!stats.isFile()) {
      return false;
    }

    const ext = path.extname(filePath);
    return this.sourceExtensions.has(ext);
  }

  /**
   * Recursively scan directory for source files
   */
  scanDirectory(dirPath, result = { structure: [], files: {} }) {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        const relativePath = path.relative(this.workingDir, fullPath);
        const stats = fs.statSync(fullPath);

        // Skip if should ignore
        if (this.shouldIgnore(fullPath, stats)) {
          continue;
        }

        if (entry.isDirectory()) {
          // Add to structure
          result.structure.push({
            type: 'directory',
            path: relativePath,
            name: entry.name
          });

          // Recursively scan
          this.scanDirectory(fullPath, result);
        } else if (this.isSourceFile(fullPath, stats)) {
          // Check file size
          if (stats.size > this.maxFileSize) {
            result.structure.push({
              type: 'file',
              path: relativePath,
              name: entry.name,
              size: stats.size,
              skipped: true,
              reason: 'File too large'
            });
            continue;
          }

          // Add to structure
          result.structure.push({
            type: 'file',
            path: relativePath,
            name: entry.name,
            size: stats.size
          });

          // Read file content
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            result.files[relativePath] = {
              path: relativePath,
              name: entry.name,
              size: stats.size,
              extension: path.extname(entry.name),
              content: content,
              lines: content.split('\n').length
            };
          } catch (readError) {
            // Skip files we can't read
            result.files[relativePath] = {
              path: relativePath,
              name: entry.name,
              error: 'Could not read file'
            };
          }
        }
      }
    } catch (error) {
      // Skip directories we can't access
      logger.error(`Error scanning ${dirPath}:`, error.message);
    }

    return result;
  }
}

module.exports = FileScanner;
