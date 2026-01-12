/**
 * Error Handler Utility for Coderrr CLI
 * 
 * Provides secure error handling that sanitizes sensitive data
 * before logging or displaying to users.
 * 
 * Set CODERRR_DEBUG=1 for additional diagnostic output (safe info only).
 */

const DEBUG = process.env.CODERRR_DEBUG === '1' || process.env.CODERRR_DEBUG === 'true';
/**
 * Sanitize an Axios error to extract only safe-to-display information.
 * Never exposes request bodies, headers, API keys, or internal connection details.
 * 
 * @param {Error} error - The error object (typically an AxiosError)
 * @returns {Object} Sanitized error information
 */
function sanitizeAxiosError(error) {
    const sanitized = {
        message: error.message || 'Unknown error',
        code: error.code || null,
        isNetworkError: false,
        isServerError: false,
        statusCode: null,
        serverMessage: null,
        url: null
    };

    // Check if it's an Axios error with a response
    if (error.response) {
        sanitized.statusCode = error.response.status;
        sanitized.isServerError = error.response.status >= 500;

        // Extract server error message if available (but not the full response)
        if (error.response.data) {
            if (typeof error.response.data === 'string') {
                sanitized.serverMessage = error.response.data.substring(0, 200);
            } else if (error.response.data.detail) {
                sanitized.serverMessage = error.response.data.detail;
            } else if (error.response.data.error) {
                sanitized.serverMessage = error.response.data.error;
            } else if (error.response.data.message) {
                sanitized.serverMessage = error.response.data.message;
            }
        }
    }

    // Check for network errors
    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' ||
        error.code === 'ETIMEDOUT' || error.code === 'ECONNRESET') {
        sanitized.isNetworkError = true;
    }

    // Extract just the base URL (without query params or sensitive paths)
    if (error.config && error.config.url) {
        try {
            const url = new URL(error.config.url);
            sanitized.url = `${url.protocol}//${url.host}`;
        } catch {
            // If URL parsing fails, don't include it
        }
    }

    return sanitized;
}

/**
 * Format a user-friendly error message from a sanitized error.
 * 
 * @param {Object} sanitized - Sanitized error object from sanitizeAxiosError
 * @param {string} backendUrl - The backend URL for connection errors
 * @returns {string} User-friendly error message
 */
function formatUserError(sanitized, backendUrl = null) {
    let message = '';

    // Network/connection errors
    if (sanitized.isNetworkError) {
        const url = backendUrl || sanitized.url || 'the backend';
        message = `Cannot connect to ${url}. Please check if the backend is running.`;
    }
    // Server errors (5xx)
    else if (sanitized.isServerError) {
        const statusMsg = sanitized.statusCode ? ` (${sanitized.statusCode})` : '';
        const detail = sanitized.serverMessage
            ? `: ${sanitized.serverMessage}`
            : '. Please try again.';
        message = `Backend error${statusMsg}${detail}`;
    }
    // Client errors (4xx)
    else if (sanitized.statusCode && sanitized.statusCode >= 400 && sanitized.statusCode < 500) {
        const detail = sanitized.serverMessage || 'Bad request';
        message = `Request error (${sanitized.statusCode}): ${detail}`;
    }
    // Generic error fallback
    else {
        message = sanitized.message || 'An unexpected error occurred. Please try again.';
    }

    // Add debug info if enabled
    if (DEBUG) {
        const debugInfo = [];
        if (sanitized.code) debugInfo.push(`code=${sanitized.code}`);
        if (sanitized.statusCode) debugInfo.push(`status=${sanitized.statusCode}`);
        if (sanitized.url) debugInfo.push(`url=${sanitized.url}`);
        debugInfo.push(`time=${new Date().toISOString()}`);

        message += `\n  [DEBUG] ${debugInfo.join(', ')}`;

        // Add troubleshooting hints based on error type
        if (sanitized.isServerError) {
            message += '\n  [DEBUG] Hint: Check backend logs for full error details';
        }
    }

    return message;
}

/**
 * Create a sanitized error that can be safely thrown.
 * The original error's sensitive details are removed.
 * 
 * @param {Error} originalError - The original error
 * @returns {Error} A new error with sanitized message
 */
function createSafeError(originalError) {
    const sanitized = sanitizeAxiosError(originalError);
    const message = formatUserError(sanitized);

    const safeError = new Error(message);
    safeError.code = sanitized.code;
    safeError.statusCode = sanitized.statusCode;
    safeError.isNetworkError = sanitized.isNetworkError;
    safeError.isServerError = sanitized.isServerError;

    return safeError;
}

/**
 * Check if an error is a network-related error.
 * 
 * @param {Error} error - The error to check
 * @returns {boolean} True if it's a network error
 */
function isNetworkError(error) {
    const networkCodes = ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ECONNRESET', 'ENETUNREACH'];
    return networkCodes.includes(error.code);
}

/**
 * Check if an error is a server-side error (5xx).
 * 
 * @param {Error} error - The error to check
 * @returns {boolean} True if it's a 5xx server error
 */
function isServerError(error) {
    return error.response && error.response.status >= 500;
}

module.exports = {
    sanitizeAxiosError,
    formatUserError,
    createSafeError,
    isNetworkError,
    isServerError
};
