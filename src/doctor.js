const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class CoderrrDoctor {
    checkEnv() {
        return fs.existsSync(path.join(process.cwd(), '.env'));
    }

    checkPython() {
        try {
            const version = execSync('python --version').toString().trim();
            return { status: true, version };
        } catch {
            return { status: false, version: 'Not found' };
        }
    }

    checkNode() {
        return { status: true, version: process.version };
    }

    async checkBackend(url) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);
            return response.ok;
        } catch {
            return false;
        }
    }
}

module.exports = new CoderrrDoctor();