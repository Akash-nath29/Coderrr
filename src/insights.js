const fs = require('fs');
const path = require('path');
const os = require('os');

const INSIGHTS_PATH = path.join(os.homedir(), '.coderrr', 'insights.json');

class InsightsManager {
    constructor() {
        this.ensureStorage();
    }

    ensureStorage() {
        const dir = path.dirname(INSIGHTS_PATH);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        if (!fs.existsSync(INSIGHTS_PATH)) {
            fs.writeFileSync(INSIGHTS_PATH, JSON.stringify({ sessions: [], totals: { tasks: 0, filesChanged: 0, healings: 0 } }));
        }
    }

    recordSession(data) {
        try {
            const content = JSON.parse(fs.readFileSync(INSIGHTS_PATH, 'utf8'));
            const session = {
                timestamp: new Date().toISOString(),
                task: data.task || 'Unknown Task',
                success: data.success || false,
                filesChanged: data.filesChanged || 0,
                healings: data.healings || 0
            };

            content.sessions.push(session);
            content.totals.tasks += 1;
            content.totals.filesChanged += session.filesChanged;
            content.totals.healings += session.healings;

            // Keep last 50 sessions to save space
            if (content.sessions.length > 50) content.sessions.shift();

            fs.writeFileSync(INSIGHTS_PATH, JSON.stringify(content, null, 2));
        } catch (error) {
            // Fail silently to not disturb the main process
        }
    }

    getStats() {
        return JSON.parse(fs.readFileSync(INSIGHTS_PATH, 'utf8'));
    }
}

module.exports = new InsightsManager();