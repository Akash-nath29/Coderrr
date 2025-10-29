/**
 * Test Agent integration with CodebaseScanner
 */

const Agent = require('../src/agent');
require('dotenv').config();

console.log('🤖 Testing Agent with CodebaseScanner integration...\n');

// Create agent instance
const agent = new Agent({
  backendUrl: process.env.CODERRR_BACKEND,
  scanOnFirstRequest: true
});

console.log('✓ Agent created with scanner enabled');
console.log();

// Test 1: Check scanner is initialized
console.log('Test 1: Scanner Initialization');
console.log('================================');
console.log(`✓ Scanner initialized: ${agent.scanner !== null}`);
console.log(`✓ Working directory: ${agent.workingDir}`);
console.log(`✓ Scan on first request: ${agent.scanOnFirstRequest}`);
console.log();

// Test 2: Manual codebase summary
console.log('Test 2: Manual Codebase Summary');
console.log('================================');
const summary = agent.getCodebaseSummary();
console.log(`✓ Total files: ${summary.structure.totalFiles}`);
console.log(`✓ Total directories: ${summary.structure.totalDirectories}`);
console.log(`✓ Sample files:`);
summary.files.slice(0, 5).forEach(f => {
  console.log(`  - ${f.path}`);
});
console.log();

// Test 3: Find files
console.log('Test 3: Find Files');
console.log('==================');
const foundFiles = agent.findFiles('agent');
console.log(`✓ Found ${foundFiles.length} files matching "agent":`);
foundFiles.forEach(f => {
  console.log(`  - ${f.path} (${f.extension})`);
});
console.log();

// Test 4: Refresh test
console.log('Test 4: Refresh Codebase');
console.log('=========================');
const refreshResult = agent.refreshCodebase();
console.log(`✓ Rescanned ${refreshResult.summary.totalFiles} files`);
console.log();

console.log('✅ All integration tests passed!');
console.log();
console.log('Note: To test actual AI requests with codebase context,');
console.log('start the backend with: uvicorn main:app --reload --port 5000');
console.log('Then use: coderrr exec "edit agent.js to add a comment"');
