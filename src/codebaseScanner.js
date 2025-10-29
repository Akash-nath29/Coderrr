const fs = require('fs');
const path = require('path');

/**
 * Codebase Scanner - Discovers and reads source files in the project
 * Ignores common non-source directories and files
 */

class CodebaseScanner {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;
    this.cache = null;
    this.cacheTimestamp = null;
    this.cacheDuration = 60000; // 1 minute cache
    
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
      console.error(`Error scanning ${dirPath}:`, error.message);
    }
    
    return result;
  }

  /**
   * Get project structure and file contents
   */
  scan(forceRefresh = false) {
    // Return cached result if available and fresh
    const now = Date.now();
    if (!forceRefresh && this.cache && this.cacheTimestamp && 
        (now - this.cacheTimestamp) < this.cacheDuration) {
      return this.cache;
    }
    
    // Perform scan
    const result = this.scanDirectory(this.workingDir);
    
    // Add summary
    result.summary = {
      totalFiles: Object.keys(result.files).length,
      totalDirectories: result.structure.filter(s => s.type === 'directory').length,
      totalSize: Object.values(result.files).reduce((sum, f) => sum + (f.size || 0), 0),
      scannedAt: new Date().toISOString(),
      workingDir: this.workingDir
    };
    
    // Cache the result
    this.cache = result;
    this.cacheTimestamp = now;
    
    return result;
  }

  /**
   * Get a summary of the codebase for AI context
   */
  getSummaryForAI(maxFiles = 20) {
    const scanResult = this.scan();
    
    // Create a concise summary
    const summary = {
      structure: scanResult.summary,
      directories: scanResult.structure
        .filter(s => s.type === 'directory')
        .map(s => s.path),
      files: scanResult.structure
        .filter(s => s.type === 'file' && !s.skipped)
        .map(s => ({
          path: s.path,
          name: s.name,
          size: s.size
        }))
    };
    
    return summary;
  }

  /**
   * Get file contents for specific files or patterns
   */
  getFileContents(patterns = []) {
    const scanResult = this.scan();
    const matchedFiles = {};
    
    if (patterns.length === 0) {
      // Return all files if no patterns specified
      return scanResult.files;
    }
    
    // Match files against patterns
    for (const [filePath, fileData] of Object.entries(scanResult.files)) {
      for (const pattern of patterns) {
        if (filePath.includes(pattern) || fileData.name.includes(pattern)) {
          matchedFiles[filePath] = fileData;
          break;
        }
      }
    }
    
    return matchedFiles;
  }

  /**
   * Find files by name or partial name
   */
  findFiles(searchTerm) {
    const scanResult = this.scan();
    const results = [];
    
    const searchLower = searchTerm.toLowerCase();
    
    for (const [filePath, fileData] of Object.entries(scanResult.files)) {
      if (fileData.name.toLowerCase().includes(searchLower) ||
          filePath.toLowerCase().includes(searchLower)) {
        results.push({
          path: filePath,
          name: fileData.name,
          size: fileData.size,
          extension: fileData.extension
        });
      }
    }
    
    return results;
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache = null;
    this.cacheTimestamp = null;
  }
}

module.exports = CodebaseScanner;
