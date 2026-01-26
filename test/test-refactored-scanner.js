const path = require('path');
const FileScanner = require('../src/fileScanner');
const CacheManager = require('../src/cacheManager');
const SearchEngine = require('../src/searchEngine');
const ContentProcessor = require('../src/contentProcessor');
const CodebaseScanner = require('../src/codebaseScanner');

console.log('🧪 Testing Refactored CodebaseScanner Components...\n');

// Test FileScanner
function testFileScanner() {
  console.log('Testing FileScanner...');
  const scanner = new FileScanner(__dirname);

  try {
    const result = scanner.scanDirectory(__dirname);
    console.log('✅ FileScanner.scanDirectory() works');
    console.log(`   Found ${Object.keys(result.files).length} files`);
    console.log(`   Found ${result.structure.filter(s => s.type === 'directory').length} directories`);
    return true;
  } catch (error) {
    console.log('❌ FileScanner test failed:', error.message);
    return false;
  }
}

// Test CacheManager
function testCacheManager() {
  console.log('Testing CacheManager...');
  const cache = new CacheManager(1000); // 1 second cache

  try {
    // Test empty cache
    if (cache.get() === null) {
      console.log('✅ CacheManager returns null for empty cache');
    } else {
      console.log('❌ CacheManager should return null for empty cache');
      return false;
    }

    // Test setting cache
    const testData = { test: 'data' };
    cache.set(testData);
    if (JSON.stringify(cache.get()) === JSON.stringify(testData)) {
      console.log('✅ CacheManager.set() and .get() work');
    } else {
      console.log('❌ CacheManager.set()/.get() failed');
      return false;
    }

    // Test cache validity
    if (cache.isCacheValid()) {
      console.log('✅ CacheManager.isCacheValid() works');
    } else {
      console.log('❌ CacheManager.isCacheValid() failed');
      return false;
    }

    // Test cache clearing
    cache.clear();
    if (cache.get() === null) {
      console.log('✅ CacheManager.clear() works');
    } else {
      console.log('❌ CacheManager.clear() failed');
      return false;
    }

    return true;
  } catch (error) {
    console.log('❌ CacheManager test failed:', error.message);
    return false;
  }
}

// Test SearchEngine
function testSearchEngine() {
  console.log('Testing SearchEngine...');
  const searchEngine = new SearchEngine();

  try {
    // Test fuzzy matching
    const score = searchEngine.fuzzyMatchScore('test', 'testing');
    if (score >= 80) {
      console.log('✅ SearchEngine.fuzzyMatchScore() works');
    } else {
      console.log('❌ SearchEngine.fuzzyMatchScore() failed');
      return false;
    }

    // Test semantic keywords
    const keywords = searchEngine.getSemanticKeywords('auth');
    if (keywords.includes('authentication') && keywords.includes('login')) {
      console.log('✅ SearchEngine.getSemanticKeywords() works');
    } else {
      console.log('❌ SearchEngine.getSemanticKeywords() failed');
      return false;
    }

    // Test file finding with mock data
    const mockFiles = {
      'src/auth.js': { name: 'auth.js', content: 'login function' },
      'src/user.js': { name: 'user.js', content: 'user management' }
    };

    const results = searchEngine.findFiles(mockFiles, 'auth');
    if (results.length > 0 && results[0].name === 'auth.js') {
      console.log('✅ SearchEngine.findFiles() works');
    } else {
      console.log('❌ SearchEngine.findFiles() failed');
      return false;
    }

    return true;
  } catch (error) {
    console.log('❌ SearchEngine test failed:', error.message);
    return false;
  }
}

// Test ContentProcessor
function testContentProcessor() {
  console.log('Testing ContentProcessor...');
  const processor = new ContentProcessor();

  try {
    // Test chunking
    const content = 'This is a test content for chunking purposes.';
    const chunks = processor.chunkContent(content, 10);

    if (chunks.length > 1 && chunks[0].content.length <= 10) {
      console.log('✅ ContentProcessor.chunkContent() works');
    } else {
      console.log('❌ ContentProcessor.chunkContent() failed');
      return false;
    }

    // Test match finding
    const matches = processor.findMatchesInText('This is a test', 'test');
    if (matches.length > 0 && matches[0].keyword === 'test') {
      console.log('✅ ContentProcessor.findMatchesInText() works');
    } else {
      console.log('❌ ContentProcessor.findMatchesInText() failed');
      return false;
    }

    return true;
  } catch (error) {
    console.log('❌ ContentProcessor test failed:', error.message);
    return false;
  }
}

// Test Refactored CodebaseScanner Integration
function testRefactoredCodebaseScanner() {
  console.log('Testing Refactored CodebaseScanner Integration...');
  const scanner = new CodebaseScanner(__dirname);

  try {
    // Test that all components are initialized
    if (scanner.fileScanner && scanner.cacheManager && scanner.searchEngine && scanner.contentProcessor) {
      console.log('✅ CodebaseScanner components initialized correctly');
    } else {
      console.log('❌ CodebaseScanner components not initialized');
      return false;
    }

    // Test scan method
    const result = scanner.scan();
    if (result && result.files && result.structure) {
      console.log('✅ CodebaseScanner.scan() works');
    } else {
      console.log('❌ CodebaseScanner.scan() failed');
      return false;
    }

    // Test search methods
    const searchResults = scanner.findFiles('test');
    if (Array.isArray(searchResults)) {
      console.log('✅ CodebaseScanner.findFiles() works');
    } else {
      console.log('❌ CodebaseScanner.findFiles() failed');
      return false;
    }

    // Test semantic search
    const semanticResults = scanner.semanticSearch('function');
    if (Array.isArray(semanticResults)) {
      console.log('✅ CodebaseScanner.semanticSearch() works');
    } else {
      console.log('❌ CodebaseScanner.semanticSearch() failed');
      return false;
    }

    // Test regex search
    const regexResults = scanner.regexSearch('test');
    if (Array.isArray(regexResults)) {
      console.log('✅ CodebaseScanner.regexSearch() works');
    } else {
      console.log('❌ CodebaseScanner.regexSearch() failed');
      return false;
    }

    // Test cache clearing
    scanner.clearCache();
    console.log('✅ CodebaseScanner.clearCache() works');

    return true;
  } catch (error) {
    console.log('❌ CodebaseScanner integration test failed:', error.message);
    return false;
  }
}

// Test Backward Compatibility
function testBackwardCompatibility() {
  console.log('Testing Backward Compatibility...');
  const scanner = new CodebaseScanner(__dirname);

  try {
    // Test that all original methods still exist and work
    const methods = ['scan', 'getSummaryForAI', 'getFileContents', 'findFiles',
                     'semanticSearch', 'regexSearch', 'advancedSearch', 'clearCache'];

    for (const method of methods) {
      if (typeof scanner[method] !== 'function') {
        console.log(`❌ Method ${method} is missing`);
        return false;
      }
    }

    console.log('✅ All original methods are present');

    // Test that scan returns expected structure
    const result = scanner.scan();
    if (result.summary && result.files && result.structure) {
      console.log('✅ Scan result structure is backward compatible');
    } else {
      console.log('❌ Scan result structure changed');
      return false;
    }

    return true;
  } catch (error) {
    console.log('❌ Backward compatibility test failed:', error.message);
    return false;
  }
}

// Run all tests
async function runAllTests() {
  const tests = [
    testFileScanner,
    testCacheManager,
    testSearchEngine,
    testContentProcessor,
    testRefactoredCodebaseScanner,
    testBackwardCompatibility
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    try {
      if (await test()) {
        passed++;
      } else {
        failed++;
      }
    } catch (error) {
      console.log(`❌ Test ${test.name} threw exception:`, error.message);
      failed++;
    }
    console.log(''); // Empty line between tests
  }

  console.log(`📊 Test Results: ${passed} passed, ${failed} failed`);

  if (failed === 0) {
    console.log('🎉 All tests passed! Refactoring is successful.');
  } else {
    console.log('⚠️  Some tests failed. Please review the implementation.');
  }
}

// Run the tests
runAllTests().catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});
