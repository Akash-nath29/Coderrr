const doctor = require('../src/doctor');

describe('Doctor Module', () => {
    test('should detect node version', () => {
        const node = doctor.checkNode();
        expect(node.status).toBe(true);
        expect(node.version).toContain('v');
    });
});