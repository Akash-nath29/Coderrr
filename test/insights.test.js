const insights = require('../src/insights');
const fs = require('fs');

describe('Insights Module', () => {
    test('should record and retrieve a session', () => {
        const initialTasks = insights.getStats().totals.tasks;
        insights.recordSession({ task: 'Test Task', success: true, filesChanged: 2, healings: 1 });
        const updatedStats = insights.getStats();
        expect(updatedStats.totals.tasks).toBe(initialTasks + 1);
    });
});