/**
 * Skill Registry for Coderrr
 * 
 * Discovers, loads, and manages installed agent skills from ~/.coderrr/skills/
 * Each skill contains a Skills.md description and Python tools in tools/ directory.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const CODERRR_DIR = path.join(os.homedir(), '.coderrr');
const SKILLS_DIR = path.join(CODERRR_DIR, 'skills');

/**
 * Ensure the skills directory exists
 */
function ensureSkillsDir() {
    if (!fs.existsSync(SKILLS_DIR)) {
        fs.mkdirSync(SKILLS_DIR, { recursive: true });
    }
    return SKILLS_DIR;
}

/**
 * Get the skills directory path
 * @returns {string} Path to ~/.coderrr/skills/
 */
function getSkillsDir() {
    return SKILLS_DIR;
}

/**
 * Validate that a skill folder has the required structure
 * @param {string} skillPath - Full path to the skill folder
 * @returns {Object} { valid: boolean, error?: string }
 */
function validateSkillStructure(skillPath) {
    const skillsMarkdown = path.join(skillPath, 'Skills.md');
    const toolsDir = path.join(skillPath, 'tools');

    if (!fs.existsSync(skillsMarkdown)) {
        return { valid: false, error: 'Missing Skills.md file' };
    }

    if (!fs.existsSync(toolsDir)) {
        return { valid: false, error: 'Missing tools/ directory' };
    }

    const stats = fs.statSync(toolsDir);
    if (!stats.isDirectory()) {
        return { valid: false, error: 'tools/ is not a directory' };
    }

    // Check for at least one .py file in tools/
    const toolFiles = fs.readdirSync(toolsDir).filter(f => f.endsWith('.py'));
    if (toolFiles.length === 0) {
        return { valid: false, error: 'No Python tools found in tools/' };
    }

    return { valid: true };
}

/**
 * Parse the Skills.md file to extract skill metadata
 * @param {string} skillsMarkdownPath - Path to Skills.md
 * @returns {Object} { name: string, description: string, rawContent: string }
 */
function parseSkillsMarkdown(skillsMarkdownPath) {
    const content = fs.readFileSync(skillsMarkdownPath, 'utf-8');
    const lines = content.split('\n');

    let name = '';
    let description = '';

    // Extract name from first # header
    for (const line of lines) {
        const headerMatch = line.match(/^#\s+(.+)/);
        if (headerMatch) {
            name = headerMatch[1].trim();
            break;
        }
    }

    // Extract description - first non-empty line after header
    let foundHeader = false;
    for (const line of lines) {
        if (line.startsWith('#')) {
            foundHeader = true;
            continue;
        }
        if (foundHeader && line.trim()) {
            description = line.trim();
            break;
        }
    }

    return {
        name: name || path.basename(path.dirname(skillsMarkdownPath)),
        description: description || 'No description provided',
        rawContent: content
    };
}

/**
 * Extract tool metadata from a Python file by parsing docstrings
 * @param {string} toolPath - Path to the .py file
 * @returns {Object} { name: string, description: string, parameters: string[] }
 */
function parseToolMetadata(toolPath) {
    const content = fs.readFileSync(toolPath, 'utf-8');
    const toolName = path.basename(toolPath, '.py');

    let description = '';
    let parameters = [];

    // Try to extract docstring (simple pattern for triple-quoted strings)
    const docstringMatch = content.match(/^"""([\s\S]*?)"""|^'''([\s\S]*?)'''/m);
    if (docstringMatch) {
        description = (docstringMatch[1] || docstringMatch[2] || '').trim().split('\n')[0];
    }

    // Try to extract function parameters from main() or first def
    const funcMatch = content.match(/def\s+(?:main|run|\w+)\s*\(([^)]*)\)/);
    if (funcMatch && funcMatch[1]) {
        parameters = funcMatch[1]
            .split(',')
            .map(p => p.trim().split('=')[0].split(':')[0].trim())
            .filter(p => p && p !== 'self');
    }

    return {
        name: toolName,
        description: description || `Tool: ${toolName}`,
        parameters
    };
}

/**
 * Load a single skill from its directory
 * @param {string} skillName - Name of the skill (folder name)
 * @returns {Object|null} Skill object or null if invalid
 */
function loadSkill(skillName) {
    const skillPath = path.join(SKILLS_DIR, skillName);

    if (!fs.existsSync(skillPath)) {
        return null;
    }

    const validation = validateSkillStructure(skillPath);
    if (!validation.valid) {
        console.warn(`Skill "${skillName}" is invalid: ${validation.error}`);
        return null;
    }

    // Parse Skills.md
    const skillsMarkdownPath = path.join(skillPath, 'Skills.md');
    const metadata = parseSkillsMarkdown(skillsMarkdownPath);

    // Load all tools
    const toolsDir = path.join(skillPath, 'tools');
    const toolFiles = fs.readdirSync(toolsDir).filter(f => f.endsWith('.py'));

    const tools = toolFiles.map(toolFile => {
        const toolPath = path.join(toolsDir, toolFile);
        return parseToolMetadata(toolPath);
    });

    return {
        name: skillName,
        displayName: metadata.name,
        description: metadata.description,
        path: skillPath,
        tools,
        rawSkillsContent: metadata.rawContent
    };
}

/**
 * List all installed skills (folder names in ~/.coderrr/skills/)
 * @returns {string[]} Array of skill names
 */
function listInstalledSkills() {
    ensureSkillsDir();

    if (!fs.existsSync(SKILLS_DIR)) {
        return [];
    }

    return fs.readdirSync(SKILLS_DIR).filter(name => {
        const skillPath = path.join(SKILLS_DIR, name);
        return fs.statSync(skillPath).isDirectory();
    });
}

/**
 * Load all valid installed skills
 * @returns {Object[]} Array of skill objects
 */
function loadAllSkills() {
    const skillNames = listInstalledSkills();
    const skills = [];

    for (const name of skillNames) {
        const skill = loadSkill(name);
        if (skill) {
            skills.push(skill);
        }
    }

    return skills;
}

/**
 * Get all available tools across all installed skills
 * @returns {Object[]} Array of { skill, tool } objects
 */
function getAvailableTools() {
    const skills = loadAllSkills();
    const tools = [];

    for (const skill of skills) {
        for (const tool of skill.tools) {
            tools.push({
                skillName: skill.name,
                skillDescription: skill.description,
                toolName: tool.name,
                toolDescription: tool.description,
                toolParameters: tool.parameters
            });
        }
    }

    return tools;
}

/**
 * Generate a tool manifest string for injection into LLM context
 * @returns {string} Formatted manifest of all available skills and tools
 */
function generateToolManifest() {
    const skills = loadAllSkills();

    if (skills.length === 0) {
        return '';
    }

    let manifest = 'AVAILABLE SKILLS & TOOLS:\n\n';

    for (const skill of skills) {
        manifest += `[${skill.name}] - ${skill.description}\n`;

        for (const tool of skill.tools) {
            const params = tool.parameters.length > 0
                ? `(${tool.parameters.join(', ')})`
                : '()';
            manifest += `  • ${tool.name}${params}: ${tool.description}\n`;
        }
        manifest += '\n';
    }

    return manifest.trim();
}

/**
 * Check if a specific skill is installed
 * @param {string} skillName - Name of the skill
 * @returns {boolean}
 */
function isSkillInstalled(skillName) {
    const skillPath = path.join(SKILLS_DIR, skillName);
    return fs.existsSync(skillPath) && validateSkillStructure(skillPath).valid;
}

/**
 * Remove an installed skill
 * @param {string} skillName - Name of the skill to remove
 * @returns {boolean} True if removed successfully
 */
function removeSkill(skillName) {
    const skillPath = path.join(SKILLS_DIR, skillName);

    if (!fs.existsSync(skillPath)) {
        return false;
    }

    // Recursively delete the skill folder
    fs.rmSync(skillPath, { recursive: true, force: true });
    return true;
}

module.exports = {
    CODERRR_DIR,
    SKILLS_DIR,
    ensureSkillsDir,
    getSkillsDir,
    validateSkillStructure,
    parseSkillsMarkdown,
    parseToolMetadata,
    loadSkill,
    listInstalledSkills,
    loadAllSkills,
    getAvailableTools,
    generateToolManifest,
    isSkillInstalled,
    removeSkill
};
