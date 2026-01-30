/**
 * Validates the structure of a custom recipe
 */
const validateRecipe = (recipe) => {
    const errors = [];
    if (!recipe.name) errors.push("Missing 'name' field");
    if (!Array.isArray(recipe.tasks) || recipe.tasks.length === 0) {
        errors.push("'tasks' must be a non-empty array");
    }
    return {
        valid: errors.length === 0,
        errors
    };
};

module.exports = { validateRecipe };