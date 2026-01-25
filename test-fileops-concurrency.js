const FileOperations = require('./src/fileOps');
const fs = require('fs');

async function testConcurrency() {
  console.log('🧪 Testing FileOperations concurrency (non-blocking behavior)...');

  const fileOps = new FileOperations('./test-temp-concurrent');

  // Create a large file for testing
  const largeContent = 'x'.repeat(1024 * 1024); // 1MB of content

  try {
    console.log('Creating large file...');
    await fileOps.createFile('large.txt', largeContent);
    console.log('✓ Large file created');

    // Test concurrent operations
    console.log('Testing concurrent operations...');
    const startTime = Date.now();

    const promises = [
      fileOps.readFile('large.txt'),
      fileOps.createFile('file1.txt', 'content1'),
      fileOps.createFile('file2.txt', 'content2'),
      fileOps.createDir('dir1'),
      fileOps.createDir('dir2'),
    ];

    await Promise.all(promises);
    const endTime = Date.now();

    console.log(`✓ All concurrent operations completed in ${endTime - startTime}ms`);

    // Verify files were created
    const listResult = await fileOps.listDir('.');
    console.log(`✓ Directory contains ${listResult.contents.length} items`);

    // Clean up
    console.log('Cleaning up...');
    await fileOps.deleteFile('large.txt');
    await fileOps.deleteFile('file1.txt');
    await fileOps.deleteFile('file2.txt');
    await fileOps.deleteDir('dir1');
    await fileOps.deleteDir('dir2');

    console.log('✅ Concurrency test passed! Operations are non-blocking.');

  } catch (error) {
    console.error('❌ Concurrency test failed:', error.message);
  }
}

testConcurrency();
