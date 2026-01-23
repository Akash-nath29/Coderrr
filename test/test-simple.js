const fs = require('fs');
const path = require('path');

// Test the custom prompt loading functionality directly
function loadCustomPrompt(workingDir) {
  try {
    const customPromptPath = path.join(workingDir, 'Coderrr.md');
    if (fs.existsSync(customPromptPath)) {
      const content = fs.readFileSync(customPromptPath, 'utf8').trim();
      console.log('Loaded custom system prompt from Coderrr.md');
      return content;
    }
  } catch (error) {
    console.log(`Could not load Coderrr.md: ${error.message}`);
  }
  return null;
}

console.log('Testing custom prompt loading...');
const workingDir = process.cwd();
const customPrompt = loadCustomPrompt(workingDir);

if (customPrompt) {
  console.log('✅ Custom prompt loaded successfully!');
  console.log('Content preview:', customPrompt.substring(0, 100) + '...');
} else {
  console.log('❌ No custom prompt found');
}

// Test backward compatibility - remove Coderrr.md temporarily
console.log('\nTesting backward compatibility...');
const coderrrPath = path.join(workingDir, 'Coderrr.md');
const backupPath = path.join(workingDir, 'Coderrr.md.backup');

if (fs.existsSync(coderrrPath)) {
  fs.renameSync(coderrrPath, backupPath);
  console.log('Temporarily moved Coderrr.md to test backward compatibility');
}

const customPrompt2 = loadCustomPrompt(workingDir);
if (!customPrompt2) {
  console.log('✅ Backward compatibility confirmed - no errors when Coderrr.md is missing');
} else {
  console.log('❌ Backward compatibility issue - custom prompt loaded when file should not exist');
}

// Restore the file
if (fs.existsSync(backupPath)) {
  fs.renameSync(backupPath, coderrrPath);
  console.log('Restored Coderrr.md');
}

console.log('\nTest completed!');
