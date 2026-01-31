/**
 * Skills UI for Coderrr CLI
 * 
 * Provides CLI commands for managing agent skills.
 * Supports both local and remote (marketplace) installation.
 */

const path = require('path');
const fs = require('fs');
const chalk = require('chalk');
const inquirer = require('inquirer');
const skillRegistry = require('./skillRegistry');
const marketplace = require('./skillMarketplace');
const { checkPythonAvailable, installSkillDependencies } = require('./skillRunner');

/**
 * Display list of installed skills
 */
function displaySkillsList() {
    const skills = skillRegistry.loadAllSkills();

    if (skills.length === 0) {
        console.log(chalk.yellow('\n▲ No skills installed.'));
        console.log(chalk.gray('  Install skills with: coderrr install <skill-name>'));
        console.log(chalk.gray('  Browse marketplace with: coderrr market\n'));
        return;
    }

    console.log(chalk.cyan.bold('\n├─ Installed Skills\n'));

    for (const skill of skills) {
        console.log(`  ${chalk.white.bold(skill.name)} - ${chalk.gray(skill.description)}`);
        for (const tool of skill.tools) {
            const params = tool.parameters.length > 0 ? `(${tool.parameters.join(', ')})` : '()';
            console.log(`    ${chalk.green('•')} ${tool.name}${chalk.gray(params)}`);
        }
        console.log();
    }
}

/**
 * Install a skill from local path
 * @param {string} sourcePath - Resolved path to skill folder
 */
async function installLocalSkill(sourcePath) {
    if (!fs.existsSync(sourcePath)) {
        console.log(chalk.red(`\n✗ Source not found: ${sourcePath}\n`));
        return false;
    }

    const validation = skillRegistry.validateSkillStructure(sourcePath);
    if (!validation.valid) {
        console.log(chalk.red(`\n✗ Invalid skill: ${validation.error}`));
        console.log(chalk.gray('\n  Required structure:'));
        console.log(chalk.gray('  <skill>/'));
        console.log(chalk.gray('  ├── Skills.md'));
        console.log(chalk.gray('  └── tools/'));
        console.log(chalk.gray('      └── *.py\n'));
        return false;
    }

    const skillName = path.basename(sourcePath);
    const targetPath = path.join(skillRegistry.SKILLS_DIR, skillName);

    if (fs.existsSync(targetPath)) {
        console.log(chalk.yellow(`\n▲ Skill "${skillName}" already installed.`));
        console.log(chalk.gray(`  Use: coderrr uninstall ${skillName}\n`));
        return false;
    }

    skillRegistry.ensureSkillsDir();
    fs.cpSync(sourcePath, targetPath, { recursive: true });

    const depsResult = await installSkillDependencies(skillName);
    if (!depsResult.success && depsResult.error) {
        console.log(chalk.yellow(`\n▲ Warning: ${depsResult.error}`));
    }

    const skill = skillRegistry.loadSkill(skillName);
    console.log(chalk.green(`\n■ Skill "${skillName}" installed!`));
    console.log(`  Tools: ${skill.tools.map(t => t.name).join(', ')}\n`);
    return true;
}

/**
 * Install a skill from marketplace
 * @param {string} skillName - Name of skill in registry
 */
async function installRemoteSkill(skillName) {
    console.log(`  Fetching "${skillName}" from marketplace...`);

    const result = await marketplace.downloadSkill(skillName);

    if (!result.success) {
        console.log(chalk.red(`\n✗ ${result.error}\n`));
        return false;
    }

    console.log(chalk.green(`\n■ Skill "${skillName}" installed!`));
    console.log(`  Tools: ${result.skill.tools.join(', ')}\n`);
    return true;
}

/**
 * Install a skill (auto-detect local vs remote)
 * @param {string} source - Local path or skill name
 */
async function installSkill(source) {
    console.log(chalk.cyan.bold('\n├─ Installing Skill\n'));

    const python = await checkPythonAvailable();
    if (!python.available) {
        console.log(chalk.red('✗ Python not available. Skills require Python 3.8+.\n'));
        return false;
    }
    console.log(chalk.green(`  ■ Python ${python.version} found`));

    if (marketplace.isLocalPath(source)) {
        return await installLocalSkill(path.resolve(source));
    } else {
        return await installRemoteSkill(source);
    }
}

/**
 * Uninstall a skill
 * @param {string} skillName - Name of the skill
 */
async function uninstallSkill(skillName) {
    if (!skillRegistry.isSkillInstalled(skillName)) {
        console.log(chalk.yellow(`\n▲ Skill "${skillName}" not installed.\n`));
        return false;
    }

    const { confirm } = await inquirer.prompt([{
        type: 'confirm',
        name: 'confirm',
        message: `Remove skill "${skillName}"?`,
        default: false
    }]);

    if (!confirm) {
        console.log(chalk.yellow('\n▲ Cancelled.\n'));
        return false;
    }

    if (skillRegistry.removeSkill(skillName)) {
        console.log(chalk.green(`\n■ Skill "${skillName}" uninstalled.\n`));
        return true;
    } else {
        console.log(chalk.red(`\n✗ Failed to uninstall.\n`));
        return false;
    }
}

/**
 * Search marketplace for skills
 * @param {string} query - Search query
 */
async function searchMarketplace(query) {
    console.log(chalk.cyan.bold('\n├─ Searching Marketplace\n'));

    try {
        const results = await marketplace.searchSkills(query);

        if (results.length === 0) {
            console.log(chalk.yellow(`  No skills found for: "${query}"\n`));
            return;
        }

        console.log(`  Found ${results.length} skill(s):\n`);

        for (const skill of results) {
            const installed = skillRegistry.isSkillInstalled(skill.name);
            const status = installed ? chalk.green(' [installed]') : '';

            console.log(`  ${chalk.cyan.bold(skill.name)}${status}`);
            console.log(`    ${skill.description}`);
            if (skill.tags && skill.tags.length > 0) {
                console.log(`    ${chalk.gray('Tags: ' + skill.tags.join(', '))}`);
            }
            console.log();
        }
    } catch (error) {
        console.log(chalk.red(`  ✗ ${error.message}\n`));
    }
}

/**
 * List all available skills in marketplace
 */
async function listMarketplace() {
    console.log(chalk.cyan.bold('\n├─ Available Skills (Marketplace)\n'));

    try {
        const skills = await marketplace.listAvailableSkills();

        if (skills.length === 0) {
            console.log(chalk.yellow('  No skills available in marketplace.\n'));
            return;
        }

        for (const skill of skills) {
            const installed = skillRegistry.isSkillInstalled(skill.name);
            const status = installed ? chalk.green(' ✓') : '';

            console.log(`  ${chalk.cyan(skill.name)}${status} - ${skill.description}`);
        }
        console.log();
        console.log(chalk.gray(`  Install with: coderrr install <skill-name>\n`));
    } catch (error) {
        console.log(chalk.red(`  ✗ ${error.message}\n`));
    }
}

/**
 * Show detailed info about a skill
 * @param {string} skillName - Name of skill
 */
async function showSkillInfo(skillName) {
    console.log(chalk.cyan.bold('\n├─ Skill Info\n'));

    try {
        const skill = await marketplace.getSkillInfo(skillName);

        if (!skill) {
            console.log(chalk.red(`  Skill not found: ${skillName}\n`));
            return;
        }

        const installed = skillRegistry.isSkillInstalled(skillName);

        console.log(`  ${chalk.white.bold(skill.displayName || skill.name)}\n`);
        console.log(`  Name:        ${skill.name}`);
        console.log(`  Status:      ${installed ? chalk.green('Installed') : chalk.yellow('Not installed')}`);
        console.log(`  Version:     ${skill.version}`);
        console.log(`  Author:      ${skill.author}`);
        console.log(`  Description: ${skill.description}`);
        console.log(`  Tools:       ${skill.tools.join(', ')}`);
        if (skill.tags && skill.tags.length > 0) {
            console.log(`  Tags:        ${skill.tags.join(', ')}`);
        }
        console.log();

        if (!installed) {
            console.log(chalk.gray(`  Install with: coderrr install ${skillName}\n`));
        }
    } catch (error) {
        console.log(chalk.red(`  ✗ ${error.message}\n`));
    }
}

/**
 * Register skill commands with commander program
 * @param {Command} program - Commander program instance
 */
function registerSkillCommands(program) {
    // List installed skills
    program
        .command('skills')
        .description('List all installed agent skills')
        .action(() => {
            displaySkillsList();
        });

    // Install a skill (local or from marketplace)
    program
        .command('install <source>')
        .description('Install a skill (name from marketplace or local path)')
        .action(async (source) => {
            await installSkill(source);
        });

    // Uninstall a skill
    program
        .command('uninstall <skill-name>')
        .description('Uninstall an installed skill')
        .action(async (skillName) => {
            await uninstallSkill(skillName);
        });

    // Search marketplace
    program
        .command('search <query>')
        .description('Search for skills in the marketplace')
        .action(async (query) => {
            await searchMarketplace(query);
        });

    // List all available skills in marketplace
    program
        .command('market')
        .description('Browse all available skills in the marketplace')
        .action(async () => {
            await listMarketplace();
        });

    // Show skill info
    program
        .command('info <skill-name>')
        .description('Show detailed information about a skill')
        .action(async (skillName) => {
            await showSkillInfo(skillName);
        });
}

module.exports = {
    displaySkillsList,
    installSkill,
    uninstallSkill,
    searchMarketplace,
    listMarketplace,
    showSkillInfo,
    registerSkillCommands
};
