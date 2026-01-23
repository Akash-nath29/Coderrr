/**
 * Memory Manager for Coderrr
 * 
 * Handles reading/writing user memory to ~/.coderrr/memory.json
 * Stores historical conversations, decisions, and errors to provide long-term context.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const MEMORY_DIR = path.join(os.homedir(), '.coderrr');
const MEMORY_FILE = path.join(MEMORY_DIR, 'memory.json');
const MAX_ENTRIES = 30;
const CURRENT_VERSION = '1.0.0';

class MemoryManager {
    constructor(storagePath = null) {
        this.memoryFile = storagePath || MEMORY_FILE;
        this.memoryDir = path.dirname(this.memoryFile);
        this.memory = this.loadMemory();
    }

    /**
     * Ensure memory directory exists
     */
    ensureMemoryDir() {
        if (!fs.existsSync(this.memoryDir)) {
            fs.mkdirSync(this.memoryDir, { recursive: true });
        }
    }


    /**
     * Load memory from file
     * @returns {Object} Memory object
     */
    loadMemory() {
        try {
            if (!fs.existsSync(this.memoryFile)) {
                return this.getDefaultMemory();
            }
            const content = fs.readFileSync(this.memoryFile, 'utf-8');
            const parsed = JSON.parse(content);

            
            // Handle version migrations if needed in future
            if (parsed.version !== CURRENT_VERSION) {
                // For now, just reset if version mismatch, or migrate
                return this.migrateMemory(parsed);
            }
            
            return parsed;
        } catch (error) {
            // If corrupt, return default
            return this.getDefaultMemory();
        }
    }

    /**
     * Get default memory structure
     */
    getDefaultMemory() {
        return {
            version: CURRENT_VERSION,
            conversations: [],
            decisions: [],
            errors: []
        };
    }

    /**
     * Simple migration logic
     */
    migrateMemory(oldMemory) {
        const defaultMemory = this.getDefaultMemory();
        return {
            ...defaultMemory,
            ...oldMemory,
            version: CURRENT_VERSION
        };
    }

    /**
     * Save memory to file
     */
    save() {
        try {
            this.ensureMemoryDir();
            fs.writeFileSync(this.memoryFile, JSON.stringify(this.memory, null, 2));
        } catch (error) {
            console.error('Failed to save memory:', error.message);
        }
    }


    /**
     * Add a conversation entry
     * @param {string} summary - Brief summary of the conversation
     */
    addConversation(summary) {
        this.addEntry('conversations', {
            timestamp: new Date().toISOString(),
            summary
        });
    }

    /**
     * Add a decision entry
     * @param {string} action - Action taken
     * @param {string} reason - Why the action was taken
     */
    addDecision(action, reason) {
        this.addEntry('decisions', {
            timestamp: new Date().toISOString(),
            action,
            reason
        });
    }

    /**
     * Add an error entry
     * @param {string} error - Error message
     * @param {string} context - What was happening when error occurred
     */
    addError(error, context) {
        this.addEntry('errors', {
            timestamp: new Date().toISOString(),
            error,
            context
        });
    }

    /**
     * Generic method to add entry and prune FIFO
     */
    addEntry(category, entry) {
        if (!this.memory[category]) {
            this.memory[category] = [];
        }
        
        this.memory[category].push(entry);
        
        // Keep only last MAX_ENTRIES
        if (this.memory[category].length > MAX_ENTRIES) {
            this.memory[category] = this.memory[category].slice(-MAX_ENTRIES);
        }
        
        this.save();
    }

    /**
     * Get summary of memory for AI context injection
     */
    getSummaryForAI() {
        let summary = 'HISTORICAL CONTEXT (CROSS-SESSION MEMORY):\n';
        
        if (this.memory.conversations.length > 0) {
            summary += '\nPAST CONVERSATIONS:\n';
            this.memory.conversations.slice(-5).forEach(c => {
                summary += `- [${c.timestamp.split('T')[0]}] ${c.summary}\n`;
            });
        }
        
        if (this.memory.decisions.length > 0) {
            summary += '\nKEY DECISIONS & PREFERENCES:\n';
            this.memory.decisions.slice(-10).forEach(d => {
                summary += `- ${d.action}: ${d.reason}\n`;
            });
        }
        
        if (this.memory.errors.length > 0) {
            summary += '\nRECURRING ISSUES/ERRORS:\n';
            this.memory.errors.slice(-5).forEach(e => {
                summary += `- ${e.error} (Context: ${e.context})\n`;
            });
        }

        if (summary === 'HISTORICAL CONTEXT (CROSS-SESSION MEMORY):\n') {
            return ''; // Don't inject if empty
        }

        return summary;
    }

    /**
     * Clear all memory
     */
    clear() {
        this.memory = this.getDefaultMemory();
        if (fs.existsSync(this.memoryFile)) {
            fs.unlinkSync(this.memoryFile);
        }
    }

}

module.exports = new MemoryManager();
