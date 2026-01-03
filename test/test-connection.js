const axios = require('axios');
require('dotenv').config();

const backendUrl = process.env.CODERRR_BACKEND;

console.log('=== Connection Test Debug ===');
console.log(`Backend URL from env: ${backendUrl}`);
console.log(`CODERRR_BACKEND set: ${!!process.env.CODERRR_BACKEND}`);
console.log(`NODE_ENV: ${process.env.NODE_ENV}`);
console.log('');

if (!backendUrl) {
  console.error('❌ ERROR: CODERRR_BACKEND environment variable is not set!');
  process.exit(1);
}

console.log(`🔍 Testing connection to ${backendUrl}...`);

axios.get(backendUrl, { timeout: 10000 })
  .then(response => {
    console.log('✅ Backend is running!');
    console.log('Status:', response.status);
    console.log('Response:', JSON.stringify(response.data, null, 2));
  })
  .catch(error => {
    console.error('❌ Connection failed!');
    console.error('Error code:', error.code);
    console.error('Error message:', error.message);

    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }

    if (error.code === 'ECONNREFUSED') {
      console.error('');
      console.error('💡 The backend is not running at this URL.');
      console.error('   Make sure the backend is started before running tests.');
    }

    process.exit(1);
  });
