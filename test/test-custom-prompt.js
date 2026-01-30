const Agent = require('../src/agent');

async function testCustomPrompt() {
  console.log('Testing custom prompt functionality...');

  // Create agent instance
  const agent = new Agent();

  // Check if custom prompt is loaded
  console.log('Custom prompt loaded:', agent.customPrompt ? 'YES' : 'NO');

  if (agent.customPrompt) {
    console.log('Custom prompt content:');
    console.log(agent.customPrompt);
  } else {
    console.log('No custom prompt found');
  }

  // Test chat method (this will load custom prompt if not already loaded)
  try {
    console.log('\nTesting chat method...');
    // We'll mock the axios call to avoid actual API calls
    // For now, just check if the method exists and can be called
    console.log('Chat method available:', typeof agent.chat === 'function');
  } catch (error) {
    console.log('Error testing chat method:', error.message);
  }
}

testCustomPrompt().catch(console.error);
