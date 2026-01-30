const chalk = require('chalk');
const insights = require('./insights');

function displayInsights() {
    const data = insights.getStats();
    console.log('\n' + chalk.cyan.bold('📊 CODERRR INSIGHTS DASHBOARD'));
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
    
    console.log(`${chalk.white('Total Tasks Processed: ')} ${chalk.green.bold(data.totals.tasks)}`);
    console.log(`${chalk.white('Files Modified:       ')} ${chalk.yellow.bold(data.totals.filesChanged)}`);
    console.log(`${chalk.white('Self-Healing Events:  ')} ${chalk.magenta.bold(data.totals.healings)}`);
    
    console.log('\n' + chalk.cyan.bold('🕒 RECENT ACTIVITY'));
    data.sessions.slice(-5).reverse().forEach(s => {
        const status = s.success ? chalk.green('✔') : chalk.red('✘');
        const date = new Date(s.timestamp).toLocaleDateString();
        console.log(`${status} ${chalk.gray(`[${date}]`)} ${s.task.substring(0, 40)}...`);
    });
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
}

module.exports = { displayInsights };