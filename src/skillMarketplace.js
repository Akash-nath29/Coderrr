/**
 * Skill Marketplace - Remote Registry Client
 * 
 * Connects Coderrr to the remote skill marketplace hosted on GitHub.
 * Handles fetching registry, downloading skills, and caching.
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const os = require('os');
const skillRegistry = require('./skillRegistry');
const { installSkillDependencies } = require('./skillRunner');

// Registry configuration
const REGISTRY_URL = 'https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/registry.json';
const CACHE_DIR = path.join(os.homedir(), '.coderrr');
const CACHE_FILE = path.join(CACHE_DIR, 'registry-cache.json');
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Ensure cache directory exists
 */
function ensureCacheDir() {
    if (!fs.existsSync(CACHE_DIR)) {
        fs.mkdirSync(CACHE_DIR, { recursive: true });
    }
}

/**
 * Load cached registry if valid
 * @returns {Object|null} Cached registry or null if expired/missing
 */
function loadCache() {
    try {
        if (!fs.existsSync(CACHE_FILE)) return null;

        const cache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
        const age = Date.now() - cache.timestamp;

        if (age < CACHE_TTL) {
            return cache.data;
        }
        return null;
    } catch (e) {
        return null;
    }
}

/**
 * Save registry to cache
 * @param {Object} data - Registry data
 */
function saveCache(data) {
    ensureCacheDir();
    const cache = {
        timestamp: Date.now(),
        data: data
    };
    fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2), 'utf8');
}

/**
 * Fetch the remote registry with caching
 * @returns {Promise<Object>} Registry object
 */
async function fetchRegistry() {
    // Check cache first
    const cached = loadCache();
    if (cached) {
        return cached;
    }

    try {
        const response = await axios.get(REGISTRY_URL, { timeout: 10000 });
        const registry = response.data;

        // Cache the result
        saveCache(registry);

        return registry;
    } catch (error) {
        if (error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
            throw new Error('Could not connect to skill registry. Check your internet connection.');
        }
        throw new Error(`Failed to fetch registry: ${error.message}`);
    }
}

/**
 * Search skills by query
 * @param {string} query - Search query
 * @returns {Promise<Array>} Matching skills
 */
async function searchSkills(query) {
    const registry = await fetchRegistry();
    const q = query.toLowerCase();

    return Object.values(registry.skills).filter(skill =>
        skill.name.toLowerCase().includes(q) ||
        skill.description.toLowerCase().includes(q) ||
        (skill.tags && skill.tags.some(tag => tag.toLowerCase().includes(q)))
    );
}

/**
 * Get skill info by name
 * @param {string} name - Skill name
 * @returns {Promise<Object|null>} Skill info or null
 */
async function getSkillInfo(name) {
    const registry = await fetchRegistry();
    return registry.skills[name] || null;
}

/**
 * List all available skills in the marketplace
 * @returns {Promise<Array>} All skills
 */
async function listAvailableSkills() {
    const registry = await fetchRegistry();
    return Object.values(registry.skills);
}

/**
 * Download a file from URL
 * @param {string} url - File URL
 * @returns {Promise<string>} File content
 */
async function downloadFile(url) {
    const response = await axios.get(url, {
        timeout: 30000,
        responseType: 'text'
    });
    return response.data;
}

/**
 * Download and install a skill from the marketplace
 * @param {string} skillName - Name of the skill to install
 * @returns {Promise<Object>} Installation result
 */
async function downloadSkill(skillName) {
    const skillInfo = await getSkillInfo(skillName);

    if (!skillInfo) {
        return { success: false, error: `Skill not found: ${skillName}` };
    }

    // Check if already installed
    if (skillRegistry.isSkillInstalled(skillName)) {
        return { success: false, error: `Skill "${skillName}" is already installed.` };
    }

    const skillDir = path.join(skillRegistry.SKILLS_DIR, skillName);
    const toolsDir = path.join(skillDir, 'tools');
    const baseUrl = skillInfo.download_url;

    try {
        // Create directories
        skillRegistry.ensureSkillsDir();
        fs.mkdirSync(toolsDir, { recursive: true });

        // Download Skills.md
        console.log(`  Downloading Skills.md...`);
        const skillsMd = await downloadFile(`${baseUrl}/Skills.md`);
        fs.writeFileSync(path.join(skillDir, 'Skills.md'), skillsMd, 'utf8');

        // Try to download requirements.txt (optional)
        try {
            const requirements = await downloadFile(`${baseUrl}/requirements.txt`);
            fs.writeFileSync(path.join(skillDir, 'requirements.txt'), requirements, 'utf8');
            console.log(`  Found requirements.txt`);
        } catch (e) {
            // requirements.txt is optional, ignore
        }

        // Download each tool
        for (const tool of skillInfo.tools) {
            console.log(`  Downloading ${tool}.py...`);
            try {
                const toolContent = await downloadFile(`${baseUrl}/tools/${tool}.py`);
                fs.writeFileSync(path.join(toolsDir, `${tool}.py`), toolContent, 'utf8');
            } catch (e) {
                console.warn(`  Warning: Could not download ${tool}.py`);
            }
        }

        // Install Python dependencies if requirements.txt exists
        const depsResult = await installSkillDependencies(skillName);
        if (!depsResult.success && depsResult.error) {
            console.log(`  Note: ${depsResult.error}`);
        }

        return {
            success: true,
            skill: skillInfo,
            message: `Skill "${skillName}" installed successfully`
        };

    } catch (error) {
        // Cleanup on failure
        try {
            if (fs.existsSync(skillDir)) {
                fs.rmSync(skillDir, { recursive: true });
            }
        } catch (e) {
            // Ignore cleanup errors
        }
        return { success: false, error: `Installation failed: ${error.message}` };
    }
}

/**
 * Check if a source is a local path or remote skill name
 * @param {string} source - Source string
 * @returns {boolean} True if local path
 */
function isLocalPath(source) {
    // Local if starts with ./, ../, /, or contains drive letter (Windows)
    return source.startsWith('./') ||
        source.startsWith('../') ||
        source.startsWith('/') ||
        /^[a-zA-Z]:/.test(source);
}

/**
 * Clear the registry cache
 */
function clearCache() {
    try {
        if (fs.existsSync(CACHE_FILE)) {
            fs.unlinkSync(CACHE_FILE);
        }
    } catch (e) {
        // Ignore
    }
}

module.exports = {
    REGISTRY_URL,
    fetchRegistry,
    searchSkills,
    getSkillInfo,
    listAvailableSkills,
    downloadSkill,
    isLocalPath,
    clearCache
};
