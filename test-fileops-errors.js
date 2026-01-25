const FileOperations = require('./src/fileOps');

async function testErrorHandling() {
  console.log('🧪 Testing FileOperations error handling...');

  const fileOps = new FileOperations('./test-temp-errors');

  try {
    // Test 1: Try to read non-existent file
    console.log('Test 1: Reading non-existent file...');
    try {
      await fileOps.readFile('nonexistent.txt');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 2: Try to create file that already exists
    console.log('Test 2: Creating duplicate file...');
    await fileOps.createFile('test.txt', 'content');
    try {
      await fileOps.createFile('test.txt', 'duplicate');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 3: Try to update non-existent file
    console.log('Test 3: Updating non-existent file...');
    try {
      await fileOps.updateFile('nonexistent.txt', 'content');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 4: Try to patch with non-existent pattern
    console.log('Test 4: Patching with wrong pattern...');
    try {
      await fileOps.patchFile('test.txt', 'nonexistent', 'replacement');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 5: Try to delete non-existent file
    console.log('Test 5: Deleting non-existent file...');
    try {
      await fileOps.deleteFile('nonexistent.txt');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 6: Try to create directory that already exists
    console.log('Test 6: Creating duplicate directory...');
    await fileOps.createDir('test-dir');
    try {
      await fileOps.createDir('test-dir');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Test 7: Try to delete non-empty directory
    console.log('Test 7: Deleting non-empty directory...');
    await fileOps.createFile('test-dir/file.txt', 'content');
    try {
      await fileOps.deleteDir('test-dir');
      console.log('❌ Should have thrown error');
    } catch (error) {
      console.log('✓ Correctly threw error:', error.message);
    }

    // Clean up
    console.log('Cleaning up...');
    await fileOps.deleteFile('test-dir/file.txt');
    await fileOps.deleteDir('test-dir');
    await fileOps.deleteFile('test.txt');

    console.log('✅ All error handling tests passed!');

  } catch (error) {
    console.error('❌ Error handling test failed:', error.message);
  }
}

testErrorHandling();
