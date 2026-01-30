const chalk = require('chalk');
const doctor = require('./doctor');

async function runDiagnostics(backendUrl) {
    console.log('\n' + chalk.blue.bold('🩺 CODERRR DOCTOR - SYSTEM DIAGNOSTICS'));
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));

    const python = doctor.checkPython();
    const node = doctor.checkNode();
    const hasEnv = doctor.checkEnv();
    
    console.log(`${python.status ? chalk.green('✔') : chalk.red('✘')} Python: ${python.version}`);
    console.log(`${node.status ? chalk.green('✔') : chalk.red('✘')} Node.js: ${node.version}`);
    console.log(`${hasEnv ? chalk.green('✔') : chalk.red('✘')} Local .env file detected`);

    console.log(chalk.yellow('\nChecking Backend Connectivity...'));
    const backendStatus = await doctor.checkBackend(backendUrl || 'https://coderrr-backend.vercel.app');
    console.log(`${backendStatus ? chalk.green('✔') : chalk.red('✘')} Backend: ${backendStatus ? 'Connected' : 'Unreachable'}`);

    if (!backendStatus) {
        console.log(chalk.red('\n[!] Advice: Check your internet or custom CODERRR_BACKEND variable.'));
    }
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
}

module.exports = { runDiagnostics };