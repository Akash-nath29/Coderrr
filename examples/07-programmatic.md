# Programmatic Usage

This example shows how to use Coderrr as a library in your own Node.js scripts.

## Installation

```bash
npm link coderrr
# Or in your project:
# npm install /path/to/coderrr
```

## Basic Usage

### Example 1: Simple Script

**File**: `my-script.js`

```javascript
const Agent = require('coderrr/src/agent');

async function main() {
  // Initialize agent
  const agent = new Agent({
    workingDir: process.cwd()
  });

  // Process a request
  await agent.process('Create a utils.js file with a sum function');
  
  console.log('Done!');
}

main().catch(console.error);
```

**Run**:
```bash
node my-script.js
```

---

## Advanced Usage

### Example 2: Custom Workflow

```javascript
const Agent = require('coderrr/src/agent');
const path = require('path');

async function customWorkflow() {
  const agent = new Agent({
    workingDir: path.join(process.cwd(), 'my-project')
  });

  // Step 1: Create project structure
  await agent.process('Create a basic Express.js project structure with src/, routes/, and controllers/ directories');

  // Step 2: Add authentication
  await agent.process('Add JWT authentication middleware in src/middleware/auth.js');

  // Step 3: Create API endpoints
  await agent.process('Create REST API endpoints for user CRUD operations in routes/users.js');

  // Step 4: Add tests
  await agent.process('Create integration tests for the user API');

  // Step 5: Run tests
  await agent.runTests();

  console.log('Project setup complete!');
}

customWorkflow().catch(console.error);
```

---

### Example 3: Using Individual Components

```javascript
const Agent = require('coderrr/src/agent');
const FileOperations = require('coderrr/src/fileOps');
const Executor = require('coderrr/src/executor');
const CodebaseScanner = require('coderrr/src/codebaseScanner');

async function componentUsage() {
  const workingDir = process.cwd();

  // 1. Scan codebase
  const scanner = new CodebaseScanner(workingDir);
  const scan = await scanner.scan();
  console.log('Found files:', scan.summary.totalFiles);

  // 2. Find specific files
  const jsFiles = scanner.findFiles('.js');
  console.log('JavaScript files:', jsFiles.length);

  // 3. File operations
  const fileOps = new FileOperations(workingDir);
  await fileOps.createFile('config.json', JSON.stringify({
    port: 3000,
    env: 'development'
  }, null, 2));

  // 4. Execute commands
  const executor = new Executor(workingDir);
  const result = await executor.execute('npm install express', {
    requirePermission: true
  });
  console.log('Command output:', result.stdout);

  // 5. Chat with backend
  const agent = new Agent({ workingDir });
  const response = await agent.chat('What is the best way to structure an Express app?');
  console.log('AI response:', response);
}

componentUsage().catch(console.error);
```

---

### Example 4: Error Handling

```javascript
const Agent = require('coderrr/src/agent');

async function withErrorHandling() {
  const agent = new Agent();

  try {
    await agent.process('Create a complex microservices architecture');
  } catch (error) {
    if (error.code === 'ECONNREFUSED') {
      console.error('Backend is not running!');
      console.log('Start it with: uvicorn main:app --reload --port 5000');
    } else if (error.message.includes('JSON')) {
      console.error('Failed to parse AI response');
      console.log('The AI may have returned invalid JSON');
    } else {
      console.error('Unknown error:', error.message);
    }
    
    process.exit(1);
  }
}

withErrorHandling();
```

---

### Example 5: Codebase Intelligence

```javascript
const Agent = require('coderrr/src/agent');

async function codebaseIntelligence() {
  const agent = new Agent();

  // Get codebase summary
  const summary = agent.getCodebaseSummary();
  console.log(summary);

  // Find files by pattern
  const tests = agent.findFiles('test');
  console.log('Test files:', tests.map(f => f.path));

  // Refresh codebase scan
  await agent.refreshCodebase();
  console.log('Codebase refreshed!');

  // Use in a request with context
  await agent.process('Add error handling to all API routes');
  // Coderrr will know which files are API routes
}

codebaseIntelligence().catch(console.error);
```

---

### Example 6: Build Automation

```javascript
const Agent = require('coderrr/src/agent');
const fs = require('fs').promises;

async function automatedBuild() {
  const agent = new Agent();

  console.log('Starting automated build...');

  // 1. Scaffold project
  await agent.process('Create a React app with TypeScript in src/');

  // 2. Add features
  const features = [
    'Add a login form component',
    'Add a dashboard component',
    'Add routing with react-router',
    'Add Redux state management'
  ];

  for (const feature of features) {
    console.log(`Adding: ${feature}`);
    await agent.process(feature);
  }

  // 3. Add tests
  await agent.process('Create unit tests for all components');

  // 4. Run tests
  console.log('Running tests...');
  await agent.runTests();

  // 5. Generate documentation
  await agent.process('Create API documentation in docs/');

  console.log('Build complete!');
}

automatedBuild().catch(console.error);
```

---

### Example 7: CI/CD Integration

```javascript
const Agent = require('coderrr/src/agent');

async function cicdPipeline() {
  const agent = new Agent();

  // Read pipeline configuration
  const config = JSON.parse(
    await require('fs').promises.readFile('pipeline.json', 'utf-8')
  );

  for (const task of config.tasks) {
    console.log(`Executing: ${task.description}`);
    
    try {
      await agent.process(task.request);
      
      if (task.runTests) {
        await agent.runTests();
      }
      
      console.log(`✓ ${task.description} completed`);
    } catch (error) {
      console.error(`✗ ${task.description} failed:`, error.message);
      
      if (task.required) {
        throw error; // Fail pipeline
      }
    }
  }
  
  console.log('Pipeline completed successfully!');
}

cicdPipeline().catch(error => {
  console.error('Pipeline failed:', error.message);
  process.exit(1);
});
```

**Example pipeline.json**:
```json
{
  "tasks": [
    {
      "description": "Setup project structure",
      "request": "Create a Node.js project with Express",
      "required": true
    },
    {
      "description": "Add API endpoints",
      "request": "Create REST API for user management",
      "required": true
    },
    {
      "description": "Add tests",
      "request": "Create integration tests",
      "runTests": true,
      "required": true
    },
    {
      "description": "Add documentation",
      "request": "Generate API documentation",
      "required": false
    }
  ]
}
```

---

## API Reference

See [docs/API.md](../docs/API.md) for complete API documentation.

### Key Classes

#### Agent
```javascript
const agent = new Agent(options);
// options: { workingDir, backendUrl }

await agent.process(request);
await agent.chat(prompt);
await agent.executePlan(plan);
await agent.runTests();
await agent.refreshCodebase();
agent.findFiles(searchTerm);
agent.getCodebaseSummary();
```

#### FileOperations
```javascript
const fileOps = new FileOperations(workingDir);

await fileOps.createFile(path, content);
await fileOps.readFile(path);
await fileOps.updateFile(path, content);
await fileOps.patchFile(path, content);
await fileOps.deleteFile(path);
await fileOps.execute(operation);
```

#### Executor
```javascript
const executor = new Executor(workingDir);

const result = await executor.execute(command, options);
// options: { requirePermission, cwd, shell }
```

#### CodebaseScanner
```javascript
const scanner = new CodebaseScanner(workingDir);

const scan = await scanner.scan(forceRefresh);
const summary = scanner.getSummaryForAI();
const files = scanner.findFiles(searchTerm);
scanner.clearCache();
```

---

## Best Practices

### 1. Always Handle Errors

```javascript
try {
  await agent.process(request);
} catch (error) {
  // Handle specific errors
  if (error.code === 'ECONNREFUSED') {
    // Backend not running
  } else if (error.code === 'ENOENT') {
    // File not found
  } else {
    // Generic error
  }
}
```

### 2. Use Appropriate Working Directory

```javascript
// For new projects
const agent = new Agent({
  workingDir: path.join(process.cwd(), 'new-project')
});

// For existing projects
const agent = new Agent({
  workingDir: '/path/to/existing/project'
});
```

### 3. Chain Related Operations

```javascript
// Good: Single request for related changes
await agent.process('Create server.js with Express and add routes/');

// Less efficient: Separate requests
await agent.process('Create server.js');
await agent.process('Add Express to server.js');
await agent.process('Create routes directory');
```

### 4. Use Codebase Scanner

```javascript
// Let Coderrr know about your project structure
const summary = agent.getCodebaseSummary();
console.log(summary); // Review before making changes

// Find files before modifying
const apiFiles = agent.findFiles('api');
console.log('Will modify:', apiFiles.map(f => f.path));
```

### 5. Permission Awareness

```javascript
// Commands require permission by default
const executor = new Executor(workingDir);

// User will be prompted
await executor.execute('npm install', {
  requirePermission: true  // default
});

// Only bypass for trusted operations
await executor.execute('echo "test"', {
  requirePermission: false  // use sparingly
});
```

---

## Testing Your Scripts

```javascript
// test-script.js
const Agent = require('coderrr/src/agent');
const fs = require('fs').promises;
const path = require('path');
const assert = require('assert');

async function test() {
  const testDir = path.join(__dirname, 'test-project');
  
  // Create test directory
  await fs.mkdir(testDir, { recursive: true });
  
  const agent = new Agent({ workingDir: testDir });
  
  // Test 1: Create file
  await agent.process('Create index.js with console.log("test")');
  const exists = await fs.access(path.join(testDir, 'index.js'))
    .then(() => true)
    .catch(() => false);
  assert(exists, 'index.js should exist');
  
  // Test 2: Read file
  const content = await fs.readFile(path.join(testDir, 'index.js'), 'utf-8');
  assert(content.includes('console.log'), 'Should contain console.log');
  
  // Cleanup
  await fs.rm(testDir, { recursive: true });
  
  console.log('All tests passed!');
}

test().catch(console.error);
```

---

## Next Steps

- See [API.md](../docs/API.md) for detailed API reference
- See [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for system design
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines
