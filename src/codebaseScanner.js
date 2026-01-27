const FileScanner = require('./fileScanner');
const CacheManager = require('./cacheManager');
const SearchEngine = require('./searchEngine');
const ContentProcessor = require('./contentProcessor');

/**
 * Codebase Scanner - Facade for codebase scanning and search operations
 * Orchestrates FileScanner, CacheManager, SearchEngine, and ContentProcessor
 * Maintains backward compatibility with existing interface
 */

class CodebaseScanner {
  constructor(workingDir = process.cwd()) {
    this.workingDir = workingDir;

    // Initialize component classes
    this.fileScanner = new FileScanner(workingDir);
    this.cacheManager = new CacheManager(60000); // 1 minute cache
    this.searchEngine = new SearchEngine();
    this.contentProcessor = new ContentProcessor();
  }



  /**
   * Get project structure and file contents
   */
  scan(forceRefresh = false) {
    // Return cached result if available and fresh
    if (!forceRefresh && this.cacheManager.isCacheValid()) {
      return this.cacheManager.get();
    }

    // Perform scan
    const result = this.fileScanner.scanDirectory(this.workingDir);

    // Add summary
    result.summary = {
      totalFiles: Object.keys(result.files).length,
      totalDirectories: result.structure.filter(s => s.type === 'directory').length,
      totalSize: Object.values(result.files).reduce((sum, f) => sum + (f.size || 0), 0),
      scannedAt: new Date().toISOString(),
      workingDir: this.workingDir
    };

    // Cache the result
    this.cacheManager.set(result);

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
    return this.searchEngine.findFiles(scanResult.files, searchTerm);
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
    return this.searchEngine.semanticSearch(scanResult.files, searchTerm, options);
  }

  /**
   * Chunk large file content for processing
   */
  chunkContent(content, chunkSize) {
    return this.contentProcessor.chunkContent(content, chunkSize);
  }

  /**
   * Search within file chunks for large files
   */
  async searchInChunks(filePath, searchTerm, options = {}) {
    const scanResult = this.scan();
    const semanticKeywords = this.searchEngine.getSemanticKeywords(searchTerm);
    return this.contentProcessor.searchInChunks(
      this.workingDir,
      filePath,
      searchTerm,
      semanticKeywords,
      this.fileScanner.maxFileSize
    );
  }

  /**
   * Advanced search with multiple modes
   */
  advancedSearch(query, mode = 'auto', options = {}) {
    const scanResult = this.scan();
    return this.searchEngine.advancedSearch(scanResult.files, query, mode, options);
  }

  /**
   * Regex-based search
   */
  regexSearch(pattern, options = {}) {
    const scanResult = this.scan();
    return this.searchEngine.regexSearch(scanResult.files, pattern, options);
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cacheManager.clear();
  }
}

module.exports = CodebaseScanner;
