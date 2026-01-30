/**
 * Metrics Utility
 * * Provides helper functions to process session data and 
 * calculate productivity "wins" for the user.
 */

/**
 * Calculates estimated time saved based on the complexity of tasks
 * @param {Array} sessions - Array of session objects from insights.json
 * @returns {string} - Formatted string of time saved
 */
const calculateSavings = (sessions) => {
    if (!sessions || sessions.length === 0) return "0 minutes";

    // We estimate that each file operation or self-healing fix 
    // saves a developer roughly 10 minutes of manual work.
    const ESTIMATED_MINS_SAVED_PER_ACTION = 10;
    
    const totalActions = sessions.reduce((acc, session) => {
        const fileOps = session.filesChanged || 0;
        const healings = session.healings || 0;
        return acc + fileOps + healings;
    }, 0);

    const totalMinutes = totalActions * ESTIMATED_MINS_SAVED_PER_ACTION;

    if (totalMinutes >= 60) {
        const hours = (totalMinutes / 60).toFixed(1);
        return `${hours} hours`;
    }

    return `${totalMinutes} minutes`;
};

module.exports = {
    calculateSavings
};