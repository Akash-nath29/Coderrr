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

    // Semantic keyword mappings for concept-based search
    this.semanticMappings = {
      'auth': ['auth', 'authentication', 'login', 'logout', 'oauth', 'jwt', 'token', 'session', 'user', 'password', 'signin', 'signup'],
      'database': ['db', 'database', 'sql', 'mongo', 'postgres', 'mysql', 'sqlite', 'orm', 'model', 'schema', 'migration'],
      'api': ['api', 'endpoint', 'route', 'controller', 'service', 'rest', 'graphql', 'http', 'request', 'response'],
      'config': ['config', 'settings', 'env', 'environment', 'constants', 'options'],
      'test': ['test', 'spec', 'mock', 'fixture', 'assert', 'expect', 'describe', 'it'],
      'ui': ['ui', 'component', 'view', 'template', 'html', 'css', 'style', 'layout', 'render'],
      'utils': ['util', 'helper', 'common', 'shared', 'tool', 'function', 'library'],
      'error': ['error', 'exception', 'catch', 'throw', 'try', 'fail', 'debug', 'log'],
      'security': ['security', 'encrypt', 'decrypt', 'hash', 'salt', 'key', 'cert', 'ssl', 'tls']
    };

    // Chunk size for large file processing (100KB chunks)
    this.chunkSize = 100 * 1024;
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
   * Calculate fuzzy match score between two strings
   */
  fuzzyMatchScore(searchTerm, target) {
    const search = searchTerm.toLowerCase();
    const targetLower = target.toLowerCase();

    // Exact match gets highest score
    if (targetLower === search) return 100;

    // Starts with search term
    if (targetLower.startsWith(search)) return 90;

    // Contains search term
    if (targetLower.includes(search)) return 80;

    // Fuzzy matching - check for character sequence
    let score = 0;
    let searchIndex = 0;

    for (let i = 0; i < targetLower.length && searchIndex < search.length; i++) {
      if (targetLower[i] === search[searchIndex]) {
        score += 10;
        searchIndex++;
      }
    }

    // Bonus for consecutive matches
    if (searchIndex === search.length) {
      score += 20;
    }

    return Math.min(score, 70); // Cap at 70 for non-exact matches
  }

  /**
   * Get semantic keywords for a search term
   */
  getSemanticKeywords(searchTerm) {
    const term = searchTerm.toLowerCase();
    const keywords = [term]; // Always include the original term

    // Add semantic mappings
    for (const [concept, terms] of Object.entries(this.semanticMappings)) {
      if (terms.some(t => t.includes(term) || term.includes(t))) {
        keywords.push(...terms);
        keywords.push(concept);
      }
    }

    // Add common variations
    if (term.endsWith('s')) {
      keywords.push(term.slice(0, -1)); // Remove plural
    } else {
      keywords.push(term + 's'); // Add plural
    }

    return [...new Set(keywords)]; // Remove duplicates
  }

  /**
   * Perform semantic search across files and content
   */
  semanticSearch(searchTerm, options = {}) {
    const scanResult = this.scan();
    const results = [];
    const keywords = this.getSemanticKeywords(searchTerm);

    const {
      maxResults = 50,
      includeContent = true,
      minScore = 30,
      searchContent = true
    } = options;

    for (const [filePath, fileData] of Object.entries(scanResult.files)) {
      let bestScore = 0;
      let matchType = 'filename';
      let matchedKeyword = '';

      // Check filename/path matches
      for (const keyword of keywords) {
        const nameScore = this.fuzzyMatchScore(keyword, fileData.name);
        const pathScore = this.fuzzyMatchScore(keyword, filePath);

        if (nameScore > bestScore) {
          bestScore = nameScore;
          matchedKeyword = keyword;
        }
        if (pathScore > bestScore) {
          bestScore = pathScore;
          matchedKeyword = keyword;
          matchType = 'path';
        }
      }

      // Check content matches if enabled and file has content
      if (searchContent && fileData.content && includeContent) {
        const content = fileData.content.toLowerCase();
        for (const keyword of keywords) {
          if (content.includes(keyword)) {
            const contentScore = 60; // Content matches get good score
            if (contentScore > bestScore) {
              bestScore = contentScore;
              matchType = 'content';
              matchedKeyword = keyword;
            }
          }
        }
      }

      // Add to results if score meets threshold
      if (bestScore >= minScore) {
        const result = {
          path: filePath,
          name: fileData.name,
          size: fileData.size,
          extension: fileData.extension,
          score: bestScore,
          matchType,
          matchedKeyword
        };

        // Add content preview if content match and requested
        if (matchType === 'content' && includeContent && fileData.content) {
          const content = fileData.content;
          const keywordIndex = content.toLowerCase().indexOf(matchedKeyword.toLowerCase());
          const start = Math.max(0, keywordIndex - 50);
          const end = Math.min(content.length, keywordIndex + 50 + matchedKeyword.length);
          result.preview = '...' + content.slice(start, end) + '...';
        }

        results.push(result);
      }
    }

    // Sort by score descending and limit results
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, maxResults);
  }

  /**
   * Chunk large file content for processing
   */
  chunkContent(content, chunkSize = this.chunkSize) {
    const chunks = [];
    for (let i = 0; i < content.length; i += chunkSize) {
      chunks.push({
        content: content.slice(i, i + chunkSize),
        start: i,
        end: Math.min(i + chunkSize, content.length),
        index: chunks.length
      });
    }
    return chunks;
  }

  /**
   * Search within file chunks for large files
   */
  searchInChunks(filePath, searchTerm, options = {}) {
    try {
      const fullPath = path.join(this.workingDir, filePath);
      const stats = fs.statSync(fullPath);

      if (stats.size <= this.maxFileSize) {
        // Use regular search for smaller files
        return this.semanticSearch(searchTerm, { ...options, searchContent: true });
      }

      // For large files, read in chunks
      const stream = fs.createReadStream(fullPath, { encoding: 'utf8' });
      const chunks = [];
      let currentChunk = '';
      let chunkIndex = 0;

      return new Promise((resolve, reject) => {
        stream.on('data', (chunk) => {
          currentChunk += chunk;

          if (currentChunk.length >= this.chunkSize) {
            chunks.push({
              content: currentChunk,
              index: chunkIndex++,
              matches: this.findMatchesInText(currentChunk, searchTerm)
            });
            currentChunk = '';
          }
        });

        stream.on('end', () => {
          // Process remaining chunk
          if (currentChunk.length > 0) {
            chunks.push({
              content: currentChunk,
              index: chunkIndex,
              matches: this.findMatchesInText(currentChunk, searchTerm)
            });
          }

          const results = chunks
            .filter(chunk => chunk.matches.length > 0)
            .map(chunk => ({
              path: filePath,
              chunkIndex: chunk.index,
              matches: chunk.matches,
              preview: chunk.content.slice(0, 200) + '...'
            }));

          resolve(results);
        });

        stream.on('error', reject);
      });
    } catch (error) {
      return Promise.reject(error);
    }
  }

  /**
   * Find matches in text content
   */
  findMatchesInText(text, searchTerm) {
    const keywords = this.getSemanticKeywords(searchTerm);
    const matches = [];
    const textLower = text.toLowerCase();

    for (const keyword of keywords) {
      let index = textLower.indexOf(keyword.toLowerCase());
      while (index !== -1) {
        matches.push({
          keyword,
          position: index,
          context: text.slice(Math.max(0, index - 30), Math.min(text.length, index + keyword.length + 30))
        });
        index = textLower.indexOf(keyword.toLowerCase(), index + 1);
      }
    }

    return matches;
  }

  /**
   * Advanced search with multiple modes
   */
  advancedSearch(query, mode = 'auto', options = {}) {
    switch (mode) {
      case 'filename':
        return this.findFiles(query);
      case 'semantic':
        return this.semanticSearch(query, options);
      case 'regex':
        return this.regexSearch(query, options);
      case 'auto':
      default:
        // Try semantic first, fall back to filename
        const semanticResults = this.semanticSearch(query, options);
        if (semanticResults.length > 0) {
          return semanticResults;
        }
        return this.findFiles(query);
    }
  }

  /**
   * Regex-based search
   */
  regexSearch(pattern, options = {}) {
    const scanResult = this.scan();
    const results = [];
    const regex = new RegExp(pattern, options.caseSensitive ? 'g' : 'gi');

    const { maxResults = 50, includeContent = true } = options;

    for (const [filePath, fileData] of Object.entries(scanResult.files)) {
      let matches = [];

      // Check filename
      const filenameMatches = fileData.name.match(regex);
      if (filenameMatches) {
        matches.push(...filenameMatches.map(match => ({ type: 'filename', match })));
      }

      // Check content
      if (includeContent && fileData.content) {
        const contentMatches = fileData.content.match(regex);
        if (contentMatches) {
          matches.push(...contentMatches.map(match => ({ type: 'content', match })));
        }
      }

      if (matches.length > 0) {
        results.push({
          path: filePath,
          name: fileData.name,
          size: fileData.size,
          extension: fileData.extension,
          matches
        });
      }
    }

    return results.slice(0, maxResults);
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
