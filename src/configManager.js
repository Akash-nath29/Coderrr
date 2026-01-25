/**
 * Configuration Manager for Coderrr
 * 
 * Handles reading/writing user configuration to ~/.coderrr/config.json
 * Stores provider selection, API keys, and model preferences.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const CONFIG_DIR = path.join(os.homedir(), '.coderrr');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const MEMORY_FILE = path.join(CONFIG_DIR, 'memory.json');
const MAX_MEMORY_CONVERSATIONS = 30; // Store last 30 conversations

/**
 * Ensure config directory exists
 */
function ensureConfigDir() {
    if (!fs.existsSync(CONFIG_DIR)) {
        fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }
}

/**
 * Get current configuration
 * @returns {Object|null} Configuration object or null if not configured
 */
function getConfig() {
    try {
        if (!fs.existsSync(CONFIG_FILE)) {
            return null;
        }
        const content = fs.readFileSync(CONFIG_FILE, 'utf-8');
        return JSON.parse(content);
    } catch (error) {
        console.error('Error reading config:', error.message);
        return null;
    }
}

/**
 * Save configuration
 * @param {Object} config - Configuration object to save
 */
function saveConfig(config) {
    ensureConfigDir();

    const configToSave = {
        provider: config.provider,
        apiKey: config.apiKey || null,
        model: config.model,
        endpoint: config.endpoint || null,
        updatedAt: new Date().toISOString()
    };

    fs.writeFileSync(CONFIG_FILE, JSON.stringify(configToSave, null, 2));
}

/**
 * Check if configuration exists
 * @returns {boolean}
 */
function hasConfig() {
    return fs.existsSync(CONFIG_FILE);
}

/**
 * Clear configuration
 */
function clearConfig() {
    if (fs.existsSync(CONFIG_FILE)) {
        fs.unlinkSync(CONFIG_FILE);
    }
}

/**
 * Get config file path (for display purposes)
 * @returns {string}
 */
function getConfigPath() {
    return CONFIG_FILE;
}

/**
 * Mask API key for display (show first 7 and last 4 chars)
 * @param {string} apiKey 
 * @returns {string}
 */
function maskApiKey(apiKey) {
    if (!apiKey || apiKey.length < 15) return '***';
    return `${apiKey.substring(0, 7)}...${apiKey.substring(apiKey.length - 4)}`;
}

/**
 * Get current config summary for display
 * @returns {Object|null}
 */
function getConfigSummary() {
    const config = getConfig();
    if (!config) return null;

    return {
        provider: config.provider,
        model: config.model,
        apiKey: config.apiKey ? maskApiKey(config.apiKey) : 'Not set',
        endpoint: config.endpoint || 'Default',
        updatedAt: config.updatedAt
    };
}

/**
 * Initialize the project-local .coderrr directory and memory.json file
 * @param {string} workingDir - The project working directory
 */
function initializeProjectStorage(workingDir) {
    const projectConfigDir = path.join(workingDir, '.coderrr');
    const projectMemoryFile = path.join(projectConfigDir, 'memory.json');

    if (!fs.existsSync(projectConfigDir)) {
        fs.mkdirSync(projectConfigDir, { recursive: true });
    }

    // Create memory.json if it doesn't exist
    if (!fs.existsSync(projectMemoryFile)) {
        fs.writeFileSync(projectMemoryFile, JSON.stringify({ conversations: [] }, null, 2));
    }

    return { projectConfigDir, projectMemoryFile };
}

/**
 * Load conversation memory from project-local disk
 * @param {string} workingDir - The project working directory
 * @returns {Array} Array of conversation messages
 */
function loadProjectMemory(workingDir) {
    try {
        const { projectMemoryFile } = initializeProjectStorage(workingDir);

        if (!fs.existsSync(projectMemoryFile)) {
            return [];
        }

        const content = fs.readFileSync(projectMemoryFile, 'utf-8');
        const data = JSON.parse(content);

        // Validate loaded data - ensure each message has role and content
        const conversations = data.conversations || [];
        return conversations.filter(msg =>
            msg &&
            typeof msg.role === 'string' &&
            (msg.role === 'user' || msg.role === 'assistant') &&
            typeof msg.content === 'string' &&
            msg.content.length > 0
        );
    } catch (error) {
        console.error('Error loading project memory:', error.message);
        return [];
    }
}

/**
 * Save conversation memory to project-local disk
 * Keeps only the last MAX_MEMORY_CONVERSATIONS messages
 * @param {string} workingDir - The project working directory
 * @param {Array} conversations - Array of conversation messages
 */
function saveProjectMemory(workingDir, conversations) {
    try {
        const { projectMemoryFile } = initializeProjectStorage(workingDir);

        // Keep only the last MAX_MEMORY_CONVERSATIONS * 2 messages (user + assistant pairs)
        const maxMessages = MAX_MEMORY_CONVERSATIONS * 2;
        const trimmedConversations = conversations.slice(-maxMessages);

        const data = {
            conversations: trimmedConversations,
            updatedAt: new Date().toISOString()
        };

        fs.writeFileSync(projectMemoryFile, JSON.stringify(data, null, 2));
    } catch (error) {
        console.error('Error saving project memory:', error.message);
    }
}

/**
 * Clear project-local conversation memory
 * @param {string} workingDir - The project working directory
 */
function clearProjectMemory(workingDir) {
    try {
        const { projectMemoryFile } = initializeProjectStorage(workingDir);
        fs.writeFileSync(projectMemoryFile, JSON.stringify({ conversations: [] }, null, 2));
    } catch (error) {
        console.error('Error clearing project memory:', error.message);
    }
}

/**
 * Get project memory file path (for display purposes)
 * @param {string} workingDir - The project working directory
 * @returns {string}
 */
function getProjectMemoryPath(workingDir) {
    return path.join(workingDir, '.coderrr', 'memory.json');
}

module.exports = {
    getConfig,
    saveConfig,
    hasConfig,
    clearConfig,
    getConfigPath,
    maskApiKey,
    getConfigSummary,
    initializeProjectStorage,
    loadProjectMemory,
    saveProjectMemory,
    clearProjectMemory,
    getProjectMemoryPath,
    CONFIG_DIR,
    CONFIG_FILE
};
