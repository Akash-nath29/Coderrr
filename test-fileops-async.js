const FileOperations = require('./src/fileOps');

async function testAsyncFileOperations() {
  console.log('🧪 Testing FileOperations async behavior...');

  const fileOps = new FileOperations('./test-temp');

  try {
    // Test 1: Create a file
    console.log('Test 1: Creating a file...');
    const result1 = await fileOps.createFile('test.txt', 'Hello, async world!');
    console.log('✓ File created:', result1.path);

    // Test 2: Read the file
    console.log('Test 2: Reading the file...');
    const result2 = await fileOps.readFile('test.txt');
    console.log('✓ File content:', result2.content);

    // Test 3: Update the file
    console.log('Test 3: Updating the file...');
    const result3 = await fileOps.updateFile('test.txt', 'Updated content!');
    console.log('✓ File updated:', result3.path);

    // Test 4: Patch the file
    console.log('Test 4: Patching the file...');
    const result4 = await fileOps.patchFile('test.txt', 'Updated', 'Patched');
    console.log('✓ File patched:', result4.path);

    // Test 5: Create a directory
    console.log('Test 5: Creating a directory...');
    const result5 = await fileOps.createDir('test-dir');
    console.log('✓ Directory created:', result5.path);

    // Test 6: List directory
    console.log('Test 6: Listing directory...');
    const result6 = await fileOps.listDir('.');
    console.log('✓ Directory contents:', result6.contents.length, 'items');

    // Test 7: Delete file
    console.log('Test 7: Deleting the file...');
    const result7 = await fileOps.deleteFile('test.txt');
    console.log('✓ File deleted:', result7.path);

    // Test 8: Delete directory
    console.log('Test 8: Deleting the directory...');
    const result8 = await fileOps.deleteDir('test-dir');
    console.log('✓ Directory deleted:', result8.path);

    console.log('✅ All async FileOperations tests passed!');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

testAsyncFileOperations();
