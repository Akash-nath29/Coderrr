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

module.exports = {
    getConfig,
    saveConfig,
    hasConfig,
    clearConfig,
    getConfigPath,
    maskApiKey,
    getConfigSummary,
    CONFIG_DIR,
    CONFIG_FILE
};
