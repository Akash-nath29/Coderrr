const fs = require('fs');
const path = require('path');
const Agent = require('../../src/agent');

// Mock dependencies
jest.mock('../../src/ui', () => ({
    info: jest.fn(),
    warning: jest.fn(),
    success: jest.fn(),
    error: jest.fn(),
    spinner: jest.fn(() => ({ start: jest.fn(), stop: jest.fn() })),
    section: jest.fn(),
    space: jest.fn(),
    confirm: jest.fn(),
    displayFileOp: jest.fn(),
    displayDiff: jest.fn()
}));

jest.mock('../../src/configManager', () => ({
    initializeProjectStorage: jest.fn(),
    loadProjectMemory: jest.fn(() => []),
    saveProjectMemory: jest.fn(),
    clearProjectMemory: jest.fn(),
    getConfig: jest.fn()
}));

jest.mock('axios');

describe('Skills.md Loading', () => {
    let tempDir;
    const originalCwd = process.cwd();

    beforeEach(() => {
        jest.clearAllMocks();
        // Create a temporary directory for testing
        tempDir = path.join(originalCwd, 'test-temp-skills');
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }
    });

    afterEach(() => {
        // Clean up temporary directory
        if (fs.existsSync(tempDir)) {
            const files = fs.readdirSync(tempDir);
            for (const file of files) {
                fs.unlinkSync(path.join(tempDir, file));
            }
            fs.rmdirSync(tempDir);
        }
    });

    describe('loadSkillsPrompt', () => {
        it('should load Skills.md when it exists', () => {
            const skillsContent = '# Frontend Skills\n- Use modern design patterns';
            fs.writeFileSync(path.join(tempDir, 'Skills.md'), skillsContent);

            const agent = new Agent({ workingDir: tempDir });
            agent.loadSkillsPrompt();

            expect(agent.skillsPrompt).toBe(skillsContent);
        });

        it('should not set skillsPrompt when Skills.md does not exist', () => {
            const agent = new Agent({ workingDir: tempDir });
            agent.loadSkillsPrompt();

            expect(agent.skillsPrompt).toBeNull();
        });

        it('should handle empty Skills.md gracefully', () => {
            fs.writeFileSync(path.join(tempDir, 'Skills.md'), '   ');

            const agent = new Agent({ workingDir: tempDir });
            agent.loadSkillsPrompt();

            expect(agent.skillsPrompt).toBe('');
        });
    });

    describe('loadCustomPrompt', () => {
        it('should load Coderrr.md when it exists', () => {
            const taskContent = '# Task: Build landing page';
            fs.writeFileSync(path.join(tempDir, 'Coderrr.md'), taskContent);

            const agent = new Agent({ workingDir: tempDir });
            agent.loadCustomPrompt();

            expect(agent.customPrompt).toBe(taskContent);
        });

        it('should not set customPrompt when Coderrr.md does not exist', () => {
            const agent = new Agent({ workingDir: tempDir });
            agent.loadCustomPrompt();

            expect(agent.customPrompt).toBeNull();
        });
    });

    describe('Prompt Priority Order', () => {
        it('should construct prompt with Skills.md before Coderrr.md', () => {
            const skillsContent = '# Skills\n- Be modern';
            const taskContent = '# Task\n- Build a form';
            fs.writeFileSync(path.join(tempDir, 'Skills.md'), skillsContent);
            fs.writeFileSync(path.join(tempDir, 'Coderrr.md'), taskContent);

            const agent = new Agent({ workingDir: tempDir, scanOnFirstRequest: false });
            agent.loadSkillsPrompt();
            agent.loadCustomPrompt();

            // Simulate prompt construction (from chat method logic)
            let enhancedPrompt = 'User request';

            // Task guidance first (will be wrapped by skills)
            if (agent.customPrompt) {
                enhancedPrompt = `[TASK GUIDANCE]\n${agent.customPrompt}\n\n[USER REQUEST]\n${enhancedPrompt}`;
            }

            // Skills prepended (comes before everything else)
            if (agent.skillsPrompt) {
                enhancedPrompt = `[SKILLS]\n${agent.skillsPrompt}\n\n${enhancedPrompt}`;
            }

            // Verify priority order: Skills comes first
            expect(enhancedPrompt.startsWith('[SKILLS]')).toBe(true);
            expect(enhancedPrompt.indexOf('[SKILLS]')).toBeLessThan(enhancedPrompt.indexOf('[TASK GUIDANCE]'));
            expect(enhancedPrompt.indexOf('[TASK GUIDANCE]')).toBeLessThan(enhancedPrompt.indexOf('[USER REQUEST]'));
        });

        it('should work with only Skills.md (no Coderrr.md)', () => {
            const skillsContent = '# Skills\n- Be creative';
            fs.writeFileSync(path.join(tempDir, 'Skills.md'), skillsContent);

            const agent = new Agent({ workingDir: tempDir, scanOnFirstRequest: false });
            agent.loadSkillsPrompt();
            agent.loadCustomPrompt();

            let enhancedPrompt = 'User request';

            if (agent.customPrompt) {
                enhancedPrompt = `[TASK GUIDANCE]\n${agent.customPrompt}\n\n[USER REQUEST]\n${enhancedPrompt}`;
            }

            if (agent.skillsPrompt) {
                enhancedPrompt = `[SKILLS]\n${agent.skillsPrompt}\n\n${enhancedPrompt}`;
            }

            expect(enhancedPrompt).toContain('[SKILLS]');
            expect(enhancedPrompt).not.toContain('[TASK GUIDANCE]');
            expect(enhancedPrompt).toContain('User request');
        });

        it('should work with only Coderrr.md (no Skills.md)', () => {
            const taskContent = '# Task\n- Do something';
            fs.writeFileSync(path.join(tempDir, 'Coderrr.md'), taskContent);

            const agent = new Agent({ workingDir: tempDir, scanOnFirstRequest: false });
            agent.loadSkillsPrompt();
            agent.loadCustomPrompt();

            let enhancedPrompt = 'User request';

            if (agent.customPrompt) {
                enhancedPrompt = `[TASK GUIDANCE]\n${agent.customPrompt}\n\n[USER REQUEST]\n${enhancedPrompt}`;
            }

            if (agent.skillsPrompt) {
                enhancedPrompt = `[SKILLS]\n${agent.skillsPrompt}\n\n${enhancedPrompt}`;
            }

            expect(enhancedPrompt).not.toContain('[SKILLS]');
            expect(enhancedPrompt).toContain('[TASK GUIDANCE]');
            expect(enhancedPrompt).toContain('User request');
        });

        it('should work with neither Skills.md nor Coderrr.md', () => {
            const agent = new Agent({ workingDir: tempDir, scanOnFirstRequest: false });
            agent.loadSkillsPrompt();
            agent.loadCustomPrompt();

            let enhancedPrompt = 'User request';

            if (agent.customPrompt) {
                enhancedPrompt = `[TASK GUIDANCE]\n${agent.customPrompt}\n\n[USER REQUEST]\n${enhancedPrompt}`;
            }

            if (agent.skillsPrompt) {
                enhancedPrompt = `[SKILLS]\n${agent.skillsPrompt}\n\n${enhancedPrompt}`;
            }

            expect(enhancedPrompt).toBe('User request');
        });
    });
});
