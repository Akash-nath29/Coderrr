const fs = require('fs');
const path = require('path');
const os = require('os');
const axios = require('axios');
const { execSync } = require('child_process');
const ui = require('./ui');

class SkillManager {
    constructor(workingDir) {
        this.workingDir = workingDir;
        // Skills are installed globally in user's home directory
        this.skillsBaseDir = path.join(os.homedir(), '.coderrr', 'skills');
        this.registryUrl = 'https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/registry.json';

        // Ensure skills directory exists
        if (!fs.existsSync(this.skillsBaseDir)) {
            fs.mkdirSync(this.skillsBaseDir, { recursive: true });
        }
    }

    /**
     * Fetch the registry.json from GitHub
     */
    async fetchRegistry() {
        try {
            const response = await axios.get(this.registryUrl);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to fetch registry: ${error.message}`);
        }
    }

    /**
     * Install a skill by name
     * @param {string} skillName 
     */
    async installSkill(skillName) {
        const spinner = ui.spinner(`Installing skill: ${skillName}...`);
        spinner.start();

        try {
            // 1. Fetch registry to verify skill exists
            const registry = await this.fetchRegistry();
            const skill = registry.skills[skillName];

            if (!skill) {
                throw new Error(`Skill '${skillName}' not found in registry.`);
            }

            // 2. Prepare temp directory for cloning
            const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'coderrr-skills-'));

            // 3. Clone the repo (shallow clone for speed)
            // We assume git is available since Coderrr depends on it
            try {
                execSync('git clone --depth 1 https://github.com/Akash-nath29/coderrr-skills.git .', {
                    cwd: tempDir,
                    stdio: 'ignore'
                });
            } catch (gitError) {
                throw new Error('Failed to clone skills repository. Please ensure git is installed and accessible.');
            }

            // 4. Copy the specific skill folder to installation directory
            const sourcePath = path.join(tempDir, 'skills', skillName);
            const destPath = path.join(this.skillsBaseDir, skillName);

            if (!fs.existsSync(sourcePath)) {
                throw new Error(`Skill source not found in repository at skills/${skillName}`);
            }

            // Remove existing installation if any
            if (fs.existsSync(destPath)) {
                fs.rmSync(destPath, { recursive: true, force: true });
            }

            // Copy directory
            this.copyRecursiveSync(sourcePath, destPath);

            // 5. Cleanup temp dir
            fs.rmSync(tempDir, { recursive: true, force: true });

            spinner.stop();
            ui.success(`Successfully installed skill: ${skillName}`);
            console.log(`Location: ${destPath}`);

        } catch (error) {
            spinner.stop();
            ui.error(`Installation failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Recursive copy helper
     */
    copyRecursiveSync(src, dest) {
        const exists = fs.existsSync(src);
        const stats = exists && fs.statSync(src);
        const isDirectory = exists && stats.isDirectory();

        if (isDirectory) {
            if (!fs.existsSync(dest)) {
                fs.mkdirSync(dest);
            }
            fs.readdirSync(src).forEach((childItemName) => {
                this.copyRecursiveSync(path.join(src, childItemName), path.join(dest, childItemName));
            });
        } else {
            fs.copyFileSync(src, dest);
        }
    }

    /**
     * Get formatting instructions for relevant skills based on prompt
     * @param {string} prompt - User's prompt
     * @returns {string} - Combined markdown instructions from applicable skills
     */
    getRelevantSkillsInstructions(prompt) {
        if (!prompt) return '';

        const installedSkills = this.getInstalledSkills();
        let combinedInstructions = '';
        const lowerPrompt = prompt.toLowerCase();

        // Naive keyword matching: check if skill name is in prompt
        // Can be enhanced to check tags or description keywords from a local registry cache
        for (const skillName of installedSkills) {
            // Check if skill name is mentioned (e.g., "use pdf skill")
            const nameMatch = lowerPrompt.includes(skillName.toLowerCase());

            // Check if any tool names are mentioned (would need to read skill.json/Skills.md to know tools)
            // For now, we'll verify if Skills.md exists and check basic connection
            const skillPath = path.join(this.skillsBaseDir, skillName);
            const readmePath = path.join(skillPath, 'Skills.md');

            // Determine if we should activate this skill
            // TODO: Improve this logic. For now, strict name matching or explicit list
            // Maybe we can cache the keywords for each installed skill

            // Simple heuristic: if prompt contains skill name, activate it.
            if (nameMatch && fs.existsSync(readmePath)) {
                const content = fs.readFileSync(readmePath, 'utf8');
                // We must process the content to ensure tool paths are absolute!
                // The Tools usually are referenced like `python tools/fetch_page.py`
                // We need to replace `tools/` with `${skillPath}/tools/`

                // Normalize path separators for Windows
                const absoluteSkillPath = skillPath.replace(/\\/g, '/');

                // Regex to replace relative tool paths "tools/" with absolute path
                const processedContent = content.replace(/tools\//g, `${absoluteSkillPath}/tools/`);

                combinedInstructions += `\n\n## Available Skill: ${skillName}\n${processedContent}`;
            }
        }

        return combinedInstructions;
    }

    /**
     * List all installed skills
     */
    getInstalledSkills() {
        if (!fs.existsSync(this.skillsBaseDir)) {
            return [];
        }
        return fs.readdirSync(this.skillsBaseDir).filter(file => {
            return fs.statSync(path.join(this.skillsBaseDir, file)).isDirectory();
        });
    }

    /**
     * Display installed skills with details
     */
    listInstalledSkillsWithDetails() {
        const skills = this.getInstalledSkills();
        const chalk = require('chalk');

        if (skills.length === 0) {
            ui.info('No skills installed. Run `coderrr marketplace` to see available skills.');
            return;
        }

        console.log(chalk.bold('\nInstalled Skills:'));
        skills.forEach(skill => {
            console.log(`- ${skill}`);
        });
        console.log('');
    }

    /**
     * List available skills from registry
     */
    async listAvailableSkills() {
        const spinner = ui.spinner('Fetching skill registry...');
        spinner.start();
        try {
            const registry = await this.fetchRegistry();
            spinner.stop();

            const chalk = require('chalk');
            console.log(chalk.bold('\nCoderrr Skill Marketplace'));
            console.log(chalk.gray('Run `coderrr install <name>` to install a skill.\n'));

            Object.values(registry.skills).forEach(skill => {
                console.log(chalk.cyan.bold(skill.name));
                console.log(chalk.white(skill.description));
                console.log(chalk.gray(`v${skill.version} by ${skill.author}`));
                if (skill.tags) {
                    console.log(chalk.blue(skill.tags.map(t => `#${t}`).join(' ')));
                }
                console.log(''); // Empty line
            });

        } catch (error) {
            spinner.stop();
            ui.error(`Failed to fetch marketplace: ${error.message}`);
        }
    }
}

module.exports = SkillManager;
