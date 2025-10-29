const axios = require('axios');
require('dotenv').config();

const backendUrl = process.env.CODERRR_BACKEND;

console.log(`🔍 Testing connection to ${backendUrl}...`);

axios.get(backendUrl)
  .then(response => {
    console.log('✅ Backend is running!');
    console.log('Response:', response.data);
  })
  .catch(error => {
    if (error.code === 'ECONNREFUSED') {
      console.log('❌ Cannot connect to backend');
      console.log(`   Backend URL: ${backendUrl}`);
      console.log('\n💡 Start the backend with:');
      console.log('   uvicorn main:app --reload --port 5000');
    } else {
      console.log('❌ Error:', error.message);
    }
    process.exit(1);
  });
