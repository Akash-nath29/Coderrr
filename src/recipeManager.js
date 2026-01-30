const fs = require('fs');
const path = require('path');
const os = require('os');

const RECIPES_DIR = path.join(os.homedir(), '.coderrr', 'recipes');

class RecipeManager {
    constructor() {
        this.ensureDirectory();
    }

    ensureDirectory() {
        if (!fs.existsSync(RECIPES_DIR)) {
            fs.mkdirSync(RECIPES_DIR, { recursive: true });
            // Add a default "Hello World" recipe
            const defaultRecipe = {
                name: "ping",
                description: "A simple health check for the recipe system",
                tasks: ["Create a file named ALIVE.md with the text 'Coderrr is here'"]
            };
            fs.writeFileSync(path.join(RECIPES_DIR, 'ping.json'), JSON.stringify(defaultRecipe, null, 2));
        }
    }

    listRecipes() {
        const files = fs.readdirSync(RECIPES_DIR).filter(f => f.endsWith('.json'));
        return files.map(f => {
            const content = JSON.parse(fs.readFileSync(path.join(RECIPES_DIR, f), 'utf8'));
            return { id: f.replace('.json', ''), ...content };
        });
    }

    getRecipe(name) {
        const filePath = path.join(RECIPES_DIR, `${name}.json`);
        if (fs.existsSync(filePath)) {
            return JSON.parse(fs.readFileSync(filePath, 'utf8'));
        }
        return null;
    }
}

module.exports = new RecipeManager();