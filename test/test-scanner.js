/**
 * Test script for CodebaseScanner functionality
 */

const CodebaseScanner = require('../src/codebaseScanner');
const path = require('path');

console.log('🔍 Testing CodebaseScanner...\n');

// Test 1: Basic scan
console.log('Test 1: Basic Scan');
console.log('==================');
const scanner = new CodebaseScanner(process.cwd());
const result = scanner.scan();

console.log(`✓ Scanned ${result.summary.totalFiles} files`);
console.log(`✓ Found ${result.summary.totalDirectories} directories`);
console.log(`✓ Total size: ${(result.summary.totalSize / 1024).toFixed(2)} KB`);
console.log();

// Test 2: Get AI Summary
console.log('Test 2: AI Summary');
console.log('==================');
const summary = scanner.getSummaryForAI();
console.log(`✓ Structure summary created`);
console.log(`✓ Directories: ${summary.directories.length}`);
console.log(`✓ Files in summary: ${summary.files.length}`);
console.log();

// Test 3: Find files
console.log('Test 3: Find Files');
console.log('==================');
const agentFiles = scanner.findFiles('agent');
console.log(`✓ Found ${agentFiles.length} files matching "agent":`);
agentFiles.forEach(f => console.log(`  - ${f.path}`));
console.log();

// Test 4: Cache test
console.log('Test 4: Cache Test');
console.log('==================');
const start1 = Date.now();
scanner.scan(); // Should use cache
const cached = Date.now() - start1;
console.log(`✓ Cached scan took: ${cached}ms`);

scanner.clearCache();
const start2 = Date.now();
scanner.scan(true); // Force refresh
const fresh = Date.now() - start2;
console.log(`✓ Fresh scan took: ${fresh}ms`);
console.log();

// Test 5: Display sample file structure
console.log('Test 5: Sample File Structure');
console.log('==============================');
const sampleFiles = summary.files.slice(0, 10);
console.log('First 10 files:');
sampleFiles.forEach(f => {
  console.log(`  ${f.path.padEnd(40)} ${(f.size / 1024).toFixed(2)} KB`);
});
console.log();

console.log('✅ All tests completed successfully!');
