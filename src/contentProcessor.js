const fs = require('fs');
const path = require('path');

/**
 * ContentProcessor - Handles content processing for large files
 * Provides chunking functionality and content analysis
 */

class ContentProcessor {
  constructor(chunkSize = 100 * 1024) { // 100KB chunks
    this.chunkSize = chunkSize;
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
   * Find matches in text content
   */
  findMatchesInText(text, searchTerm, semanticKeywords) {
    const keywords = semanticKeywords || [searchTerm];
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
   * Search within file chunks for large files
   */
  async searchInChunks(workingDir, filePath, searchTerm, semanticKeywords, maxFileSize) {
    try {
      const fullPath = path.join(workingDir, filePath);
      const stats = fs.statSync(fullPath);

      if (stats.size <= maxFileSize) {
        // For smaller files, return empty result (handled by regular search)
        return [];
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
              matches: this.findMatchesInText(currentChunk, searchTerm, semanticKeywords)
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
              matches: this.findMatchesInText(currentChunk, searchTerm, semanticKeywords)
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
}

module.exports = ContentProcessor;
