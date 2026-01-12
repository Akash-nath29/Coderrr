/**
 * Provider definitions for Coderrr
 * 
 * Defines available LLM providers, their models, and configuration requirements.
 */

const PROVIDERS = {
    openai: {
        id: 'openai',
        name: 'OpenAI',
        description: 'GPT-4o, GPT-4, GPT-3.5 Turbo',
        requiresKey: true,
        keyEnvVar: 'OPENAI_API_KEY',
        keyPlaceholder: 'sk-...',
        keyPattern: /^sk-[a-zA-Z0-9-_]{20,}$/,
        models: [
            { id: 'gpt-4o', name: 'GPT-4o (Recommended)', description: 'Most capable, multimodal' },
            { id: 'gpt-4o-mini', name: 'GPT-4o Mini', description: 'Fast and affordable' },
            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', description: 'High capability, 128k context' },
            { id: 'gpt-4', name: 'GPT-4', description: 'Original GPT-4' },
            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and cheap' }
        ],
        defaultModel: 'gpt-4o'
    },

    anthropic: {
        id: 'anthropic',
        name: 'Anthropic (Claude)',
        description: 'Claude 4, Claude 3.5 Sonnet, Opus',
        requiresKey: true,
        keyEnvVar: 'ANTHROPIC_API_KEY',
        keyPlaceholder: 'sk-ant-...',
        keyPattern: /^sk-ant-[a-zA-Z0-9-_]{20,}$/,
        models: [
            { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4 (Recommended)', description: 'Latest, best for coding' },
            { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', description: 'Fast and capable' },
            { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', description: 'Most powerful Claude 3' },
            { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', description: 'Fast and affordable' }
        ],
        defaultModel: 'claude-sonnet-4-20250514'
    },

    openrouter: {
        id: 'openrouter',
        name: 'OpenRouter',
        description: 'Multiple providers, free models available',
        requiresKey: true,
        keyEnvVar: 'OPENROUTER_API_KEY',
        keyPlaceholder: 'sk-or-...',
        keyPattern: /^sk-or-[a-zA-Z0-9-_]{20,}$/,
        endpoint: 'https://openrouter.ai/api/v1',
        models: [
            { id: 'meta-llama/llama-3.3-70b-instruct:free', name: 'Llama 3.3 70B (FREE)', description: 'Free, high quality', free: true },
            { id: 'qwen/qwen-2.5-coder-32b-instruct:free', name: 'Qwen 2.5 Coder 32B (FREE)', description: 'Free, great for coding', free: true },
            { id: 'deepseek/deepseek-chat-v3-0324:free', name: 'DeepSeek Chat V3 (FREE)', description: 'Free, very capable', free: true },
            { id: 'google/gemini-2.0-flash-001', name: 'Gemini 2.0 Flash', description: 'Fast Google model' },
            { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', description: 'Via OpenRouter' },
            { id: 'openai/gpt-4o', name: 'GPT-4o', description: 'Via OpenRouter' }
        ],
        defaultModel: 'meta-llama/llama-3.3-70b-instruct:free'
    },

    ollama: {
        id: 'ollama',
        name: 'Ollama (Local)',
        description: 'Run models locally, completely free',
        requiresKey: false,
        endpoint: 'http://localhost:11434',
        customEndpoint: true,
        models: [
            { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder 7B (Recommended)', description: 'Best for coding tasks' },
            { id: 'qwen2.5-coder:14b', name: 'Qwen 2.5 Coder 14B', description: 'Larger coding model' },
            { id: 'llama3.2:3b', name: 'Llama 3.2 3B', description: 'Fast, lightweight' },
            { id: 'llama3.1:8b', name: 'Llama 3.1 8B', description: 'Good balance' },
            { id: 'codellama:7b', name: 'Code Llama 7B', description: 'Code-focused' },
            { id: 'mistral:7b', name: 'Mistral 7B', description: 'Fast and capable' },
            { id: 'deepseek-coder-v2:16b', name: 'DeepSeek Coder V2 16B', description: 'Great for coding' }
        ],
        defaultModel: 'qwen2.5-coder:7b',
        note: 'Requires Ollama installed locally. Run: ollama pull <model>'
    },

    azure: {
        id: 'azure',
        name: 'Azure AI / GitHub Models',
        description: 'Azure-hosted models via GitHub token',
        requiresKey: true,
        keyEnvVar: 'GITHUB_TOKEN',
        keyPlaceholder: 'ghp_... or github_pat_...',
        keyPattern: /^(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})/,
        endpoint: 'https://models.github.ai/inference',
        models: [
            { id: 'openai/gpt-4o', name: 'GPT-4o', description: 'Via GitHub Models' },
            { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', description: 'Fast and affordable' },
            { id: 'microsoft/Phi-4-reasoning', name: 'Phi-4 Reasoning', description: 'Microsoft reasoning model' },
            { id: 'meta/Llama-3.3-70B-Instruct', name: 'Llama 3.3 70B', description: 'Meta large model' },
            { id: 'mistral/Mistral-large-2411', name: 'Mistral Large', description: 'Mistral flagship' }
        ],
        defaultModel: 'openai/gpt-4o'
    }
};

/**
 * Get list of provider IDs
 */
function getProviderIds() {
    return Object.keys(PROVIDERS);
}

/**
 * Get provider by ID
 */
function getProvider(id) {
    return PROVIDERS[id] || null;
}

/**
 * Get all providers as array for selection
 */
function getProviderChoices() {
    return Object.values(PROVIDERS).map(p => ({
        name: `${p.name} - ${p.description}`,
        value: p.id
    }));
}

/**
 * Get model choices for a provider
 */
function getModelChoices(providerId) {
    const provider = PROVIDERS[providerId];
    if (!provider) return [];

    return provider.models.map(m => ({
        name: m.free ? `${m.name} ⭐` : m.name,
        value: m.id,
        description: m.description
    }));
}

/**
 * Validate API key format for a provider
 */
function validateApiKey(providerId, apiKey) {
    const provider = PROVIDERS[providerId];
    if (!provider) return { valid: false, error: 'Unknown provider' };
    if (!provider.requiresKey) return { valid: true };

    if (!apiKey || apiKey.trim() === '') {
        return { valid: false, error: 'API key is required' };
    }

    // Basic format validation if pattern exists
    if (provider.keyPattern && !provider.keyPattern.test(apiKey)) {
        return {
            valid: false,
            error: `Invalid key format. Expected format: ${provider.keyPlaceholder}`
        };
    }

    return { valid: true };
}

module.exports = {
    PROVIDERS,
    getProviderIds,
    getProvider,
    getProviderChoices,
    getModelChoices,
    validateApiKey
};
