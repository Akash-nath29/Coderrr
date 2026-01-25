const Agent = require('../../src/agent');
const { program } = require('commander');
const path = require('path');

// Mock dependencies
jest.mock('../../src/agent');
jest.mock('../../src/configManager', () => ({
  getConfigSummary: jest.fn(),
  getConfig: jest.fn(),
  clearConfig: jest.fn(),
  saveConfig: jest.fn(),
  getConfigPath: jest.fn(),
  maskApiKey: jest.fn()
}));
jest.mock('../../src/providers', () => ({
  getProviderChoices: jest.fn(),
  getModelChoices: jest.fn(),
  getProvider: jest.fn(),
  validateApiKey: jest.fn()
}));

describe('CLI Commands', () => {
  let agentInstance;
  let consoleLogMock;
  let processExitMock;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleLogMock = jest.spyOn(console, 'log').mockImplementation(() => {});
    processExitMock = jest.spyOn(process, 'exit').mockImplementation(() => {});
    
    agentInstance = {
      process: jest.fn().mockResolvedValue({ completed: 1, total: 1, pending: 0 }),
      chat: jest.fn().mockResolvedValue({ explanation: 'Test Plan', plan: [] }),
      interactive: jest.fn().mockResolvedValue()
    };
    Agent.mockImplementation(() => agentInstance);

    // Reset commander program
    program.commands.forEach(cmd => {
        // This is a bit hacky but commander doesn't have a great way to "reset" 
        // if we require the same program object.
        // However, for unit testing we can just re-require or rely on the fact that
        // bin/coderrr.js will add its commands.
    });
  });

  afterEach(() => {
    consoleLogMock.mockRestore();
    processExitMock.mockRestore();
  });

  it('exec command should initialize Agent and call process', async () => {
    // We need to bypass the top-level parse in coderrr.js for fine-grained testing
    // or just run it via commander.
    // Since bin/coderrr.js runs immediately on require, we might need a different approach.
    // For now, let's assume we can trigger the action handler.
    
    // Require the CLI to register commands
    // Note: We need to make sure it doesn't execute parse() immediately or we mock parse.
    const programParseSpy = jest.spyOn(program, 'parse').mockImplementation(() => {});
    require('../../bin/coderrr.js');
    
    const execCommand = program.commands.find(c => c.name() === 'exec');
    expect(execCommand).toBeDefined();

    // Manually trigger the action
    await execCommand._actionHandler(['echo Hello', { backend: 'http://test', dir: '.' }]);

    expect(Agent).toHaveBeenCalled();
    expect(agentInstance.process).toHaveBeenCalledWith('echo Hello');
    expect(processExitMock).toHaveBeenCalledWith(0);
    programParseSpy.mockRestore();
  });

  it('analyze command should initialize Agent and call chat then output JSON', async () => {
    const programParseSpy = jest.spyOn(program, 'parse').mockImplementation(() => {});
    // Clear cache to re-require if needed, but commander keeps state in the same object
    // require('../../bin/coderrr.js'); 

    const analyzeCommand = program.commands.find(c => c.name() === 'analyze');
    expect(analyzeCommand).toBeDefined();

    const mockPlan = { explanation: 'Analysis', plan: [{ action: 'echo' }] };
    agentInstance.chat.mockResolvedValue(mockPlan);

    await analyzeCommand._actionHandler(['simple task', { backend: 'http://test', dir: '.' }]);

    expect(Agent).toHaveBeenCalled();
    expect(agentInstance.chat).toHaveBeenCalledWith('simple task');
    expect(consoleLogMock).toHaveBeenCalledWith(JSON.stringify(mockPlan, null, 2));
    expect(processExitMock).toHaveBeenCalledWith(0);
    programParseSpy.mockRestore();
  });
});
