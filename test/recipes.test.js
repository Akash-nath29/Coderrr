const recipeManager = require('../src/recipeManager');

describe('Recipe System', () => {
    test('should find the default ping recipe', () => {
        const recipes = recipeManager.listRecipes();
        const ping = recipes.find(r => r.id === 'ping');
        expect(ping).toBeDefined();
        expect(ping.name).toBe('ping');
    });
});