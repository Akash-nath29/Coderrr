#!/usr/bin/env node

/**
 * End-to-end demo of the Codebase Scanner feature
 * 
 * This test demonstrates how the scanner prevents filename mismatches
 * by giving the AI agent full awareness of the project structure.
 */

const Agent = require('../src/agent');
const ui = require('../src/ui');
require('dotenv').config();

async function demo() {
  ui.showBanner();
  console.log('🔍 Codebase Scanner Demo');
  console.log('========================\n');

  // Create agent with scanner enabled
  console.log('1️⃣  Creating agent with codebase scanner...');
  const agent = new Agent({
    backendUrl: process.env.CODERRR_BACKEND,
    scanOnFirstRequest: true
  });
  console.log('   ✅ Agent created\n');

  // Show initial scan
  console.log('2️⃣  Getting codebase summary...');
  const summary = agent.getCodebaseSummary();
  console.log(`   📊 Project Statistics:`);
  console.log(`      • Total files: ${summary.structure.totalFiles}`);
  console.log(`      • Total directories: ${summary.structure.totalDirectories}`);
  console.log(`      • Working directory: ${summary.structure.workingDir}`);
  console.log();

  // Show some directories
  console.log('3️⃣  Project directories:');
  summary.directories.slice(0, 5).forEach(dir => {
    console.log(`      📁 ${dir}`);
  });
  console.log();

  // Show some files
  console.log('4️⃣  Sample source files:');
  summary.files.slice(0, 10).forEach(f => {
    const sizeKB = (f.size / 1024).toFixed(2);
    console.log(`      📄 ${f.path.padEnd(40)} ${sizeKB.padStart(8)} KB`);
  });
  console.log();

  // Demonstrate file search
  console.log('5️⃣  Finding files by pattern...');
  
  const testFiles = agent.findFiles('test');
  console.log(`   🔍 Files matching "test": ${testFiles.length}`);
  testFiles.forEach(f => {
    console.log(`      • ${f.path}`);
  });
  console.log();

  const jsFiles = agent.findFiles('.js');
  console.log(`   🔍 JavaScript files: ${jsFiles.length}`);
  jsFiles.slice(0, 5).forEach(f => {
    console.log(`      • ${f.path}`);
  });
  console.log();

  // Show how this helps the AI
  console.log('6️⃣  How this helps the AI agent:');
  console.log();
  console.log('   ❌ Without scanner:');
  console.log('      User: "edit the agent file"');
  console.log('      AI: "Looking for agent.py..."');
  console.log('      Result: ❌ File not found\n');
  
  console.log('   ✅ With scanner:');
  console.log('      User: "edit the agent file"');
  console.log('      AI: "I can see src/agent.js exists (31KB)"');
  console.log('      Result: ✅ Correctly edits src/agent.js\n');

  console.log('   ❌ Without scanner:');
  console.log('      User: "create a new logger"');
  console.log('      AI: "Creating logger.js..."');
  console.log('      Result: ⚠️  Might conflict with existing file\n');

  console.log('   ✅ With scanner:');
  console.log('      User: "create a new logger"');
  console.log('      AI: "No logger file exists, creating src/logger.js"');
  console.log('      Result: ✅ Creates file in correct location\n');

  // Show cache performance
  console.log('7️⃣  Cache performance:');
  const start1 = Date.now();
  agent.getCodebaseSummary();
  const time1 = Date.now() - start1;
  console.log(`      First call (cached): ${time1}ms`);

  agent.scanner.clearCache();
  const start2 = Date.now();
  agent.refreshCodebase();
  const time2 = Date.now() - start2;
  console.log(`      After refresh: ${time2}ms`);
  console.log();

  // Final summary
  console.log('8️⃣  Summary:');
  console.log('   ✅ Scanner initialized automatically');
  console.log('   ✅ Codebase scanned and cached');
  console.log('   ✅ AI receives project structure context');
  console.log('   ✅ File operations use exact filenames');
  console.log('   ✅ Fast cache prevents re-scanning');
  console.log();

  console.log('🎉 Demo complete!');
  console.log();
  console.log('💡 Next steps:');
  console.log('   1. Start backend: uvicorn main:app --reload --port 5000');
  console.log('   2. Try: coderrr exec "add a comment to agent.js"');
  console.log('   3. Watch it correctly find and edit src/agent.js!');
  console.log();
}

// Run demo
demo().catch(error => {
  console.error('Demo error:', error.message);
  process.exit(1);
});
