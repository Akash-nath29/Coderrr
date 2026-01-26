/**
 * CacheManager - Handles caching of scan results
 * Provides simple time-based caching with configurable duration
 */

class CacheManager {
  constructor(cacheDuration = 60000) { // 1 minute default
    this.cache = null;
    this.cacheTimestamp = null;
    this.cacheDuration = cacheDuration;
  }

  /**
   * Check if cache is valid (not expired)
   */
  isCacheValid() {
    if (!this.cache || !this.cacheTimestamp) {
      return false;
    }

    const now = Date.now();
    return (now - this.cacheTimestamp) < this.cacheDuration;
  }

  /**
   * Get cached data if valid
   */
  get() {
    return this.isCacheValid() ? this.cache : null;
  }

  /**
   * Set cache data with current timestamp
   */
  set(data) {
    this.cache = data;
    this.cacheTimestamp = Date.now();
  }

  /**
   * Clear the cache
   */
  clear() {
    this.cache = null;
    this.cacheTimestamp = null;
  }

  /**
   * Set cache duration
   */
  setCacheDuration(duration) {
    this.cacheDuration = duration;
  }
}

module.exports = CacheManager;
