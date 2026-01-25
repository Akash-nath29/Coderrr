/**
 * SearchEngine - Handles all search functionalities
 * Provides semantic search, regex search, fuzzy matching, and file finding
 */

class SearchEngine {
  constructor() {
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
   * Find files by name or partial name
   */
  findFiles(files, searchTerm) {
    const results = [];
    const searchLower = searchTerm.toLowerCase();

    for (const [filePath, fileData] of Object.entries(files)) {
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
   * Perform semantic search across files and content
   */
  semanticSearch(files, searchTerm, options = {}) {
    const results = [];
    const keywords = this.getSemanticKeywords(searchTerm);

    const {
      maxResults = 50,
      includeContent = true,
      minScore = 30,
      searchContent = true
    } = options;

    for (const [filePath, fileData] of Object.entries(files)) {
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
   * Regex-based search
   */
  regexSearch(files, pattern, options = {}) {
    const results = [];
    const regex = new RegExp(pattern, options.caseSensitive ? 'g' : 'gi');

    const { maxResults = 50, includeContent = true } = options;

    for (const [filePath, fileData] of Object.entries(files)) {
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
   * Advanced search with multiple modes
   */
  advancedSearch(files, query, mode = 'auto', options = {}) {
    switch (mode) {
      case 'filename':
        return this.findFiles(files, query);
      case 'semantic':
        return this.semanticSearch(files, query, options);
      case 'regex':
        return this.regexSearch(files, query, options);
      case 'auto':
      default:
        // Try semantic first, fall back to filename
        const semanticResults = this.semanticSearch(files, query, options);
        if (semanticResults.length > 0) {
          return semanticResults;
        }
        return this.findFiles(files, query);
    }
  }
}

module.exports = SearchEngine;
