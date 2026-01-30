const chalk = require('chalk');
const recipeManager = require('./recipeManager');

function displayRecipeList() {
    const recipes = recipeManager.listRecipes();
    console.log('\n' + chalk.magenta.bold('📜 AVAILABLE CODERRR RECIPES'));
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
    
    if (recipes.length === 0) {
        console.log(chalk.yellow('No recipes found in ~/.coderrr/recipes'));
    } else {
        recipes.forEach(r => {
            console.log(`${chalk.cyan.bold(r.id)}: ${chalk.white(r.description || 'No description')}`);
        });
    }
    console.log(chalk.gray('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
}

module.exports = { displayRecipeList };