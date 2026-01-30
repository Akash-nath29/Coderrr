/**
 * Helps format diagnostic logs for potential export
 */
const generateReport = (results) => {
    return `Coderrr Diagnostic Report - ${new Date().toISOString()}\n` +
           `Status: ${results.allPassed ? 'HEALTHY' : 'ISSUES DETECTED'}\n`;
};

module.exports = { generateReport };