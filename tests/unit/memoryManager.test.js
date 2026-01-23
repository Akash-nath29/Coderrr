const fs = require('fs');
const path = require('path');
const os = require('os');
const MemoryManager = require('../../src/memoryManager').constructor;

describe('MemoryManager', () => {
    const testDir = path.join(os.tmpdir(), 'coderrr-test-' + Date.now());
    const testFile = path.join(testDir, 'memory.json');
    let memoryManager;

    beforeEach(() => {
        if (!fs.existsSync(testDir)) {
            fs.mkdirSync(testDir, { recursive: true });
        }
        memoryManager = new MemoryManager(testFile);
    });

    afterEach(() => {
        if (fs.existsSync(testDir)) {
            fs.rmSync(testDir, { recursive: true, force: true });
        }
    });

    test('should initialize with default memory if file doesn\'t exist', () => {
        expect(memoryManager.memory.version).toBe('1.0.0');
        expect(memoryManager.memory.conversations).toEqual([]);
        expect(memoryManager.memory.decisions).toEqual([]);
        expect(memoryManager.memory.errors).toEqual([]);
    });

    test('should add and prune conversations', () => {
        // Add 35 conversations
        for (let i = 1; i <= 35; i++) {
            memoryManager.addConversation(`Test conversation ${i}`);
        }

        expect(memoryManager.memory.conversations.length).toBe(30);
        expect(memoryManager.memory.conversations[0].summary).toBe('Test conversation 6');
        expect(memoryManager.memory.conversations[29].summary).toBe('Test conversation 35');
    });

    test('should add and prune decisions', () => {
        for (let i = 1; i <= 35; i++) {
            memoryManager.addDecision(`Action ${i}`, `Reason ${i}`);
        }

        expect(memoryManager.memory.decisions.length).toBe(30);
        expect(memoryManager.memory.decisions[0].action).toBe('Action 6');
    });

    test('should add and prune errors', () => {
        for (let i = 1; i <= 35; i++) {
            memoryManager.addError(`Error ${i}`, `Context ${i}`);
        }

        expect(memoryManager.memory.errors.length).toBe(30);
        expect(memoryManager.memory.errors[0].error).toBe('Error 6');
    });

    test('should save and load memory correctly', () => {
        memoryManager.addConversation('Saved conversation');
        memoryManager.save();

        const newManager = new MemoryManager(testFile);
        expect(newManager.memory.conversations.length).toBe(1);
        expect(newManager.memory.conversations[0].summary).toBe('Saved conversation');
    });

    test('should generate summary for AI', () => {
        memoryManager.addConversation('Old conversation');
        memoryManager.addDecision('Preferred framework', 'Jest');
        memoryManager.addError('Connection failed', 'When calling API');

        const summary = memoryManager.getSummaryForAI();
        expect(summary).toContain('HISTORICAL CONTEXT');
        expect(summary).toContain('Old conversation');
        expect(summary).toContain('Preferred framework: Jest');
        expect(summary).toContain('Connection failed (Context: When calling API)');
    });

    test('should return empty string for AI summary if memory is empty', () => {
        const summary = memoryManager.getSummaryForAI();
        expect(summary).toBe('');
    });
});
