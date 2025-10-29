const ui = require('./ui');

/**
 * TODO manager for tracking tasks
 */

class TodoManager {
  constructor() {
    this.todos = [];
    this.currentIndex = -1;
  }

  /**
   * Parse TODO items from AI response
   */
  parseTodos(plan) {
    if (!plan || !Array.isArray(plan)) {
      return [];
    }

    this.todos = plan.map((item, index) => ({
      id: index + 1,
      title: item.summary || item.action || 'Unnamed task',
      details: `${item.action}: ${item.path || item.command || ''}`,
      action: item,
      completed: false,
      inProgress: false
    }));

    return this.todos;
  }

  /**
   * Set a TODO as in progress
   */
  setInProgress(index) {
    if (index >= 0 && index < this.todos.length) {
      this.todos[index].inProgress = true;
      this.currentIndex = index;
    }
  }

  /**
   * Mark a TODO as completed
   */
  complete(index) {
    if (index >= 0 && index < this.todos.length) {
      this.todos[index].completed = true;
      this.todos[index].inProgress = false;
    }
  }

  /**
   * Get all TODOs
   */
  getAll() {
    return this.todos;
  }

  /**
   * Get current TODO
   */
  getCurrent() {
    return this.currentIndex >= 0 ? this.todos[this.currentIndex] : null;
  }

  /**
   * Get next incomplete TODO
   */
  getNext() {
    const nextIndex = this.todos.findIndex((todo, idx) => 
      idx > this.currentIndex && !todo.completed
    );
    return nextIndex >= 0 ? this.todos[nextIndex] : null;
  }

  /**
   * Check if all TODOs are completed
   */
  isComplete() {
    return this.todos.length > 0 && this.todos.every(todo => todo.completed);
  }

  /**
   * Display current TODO list
   */
  display() {
    ui.displayTodos(this.todos);
  }

  /**
   * Clear all TODOs
   */
  clear() {
    this.todos = [];
    this.currentIndex = -1;
  }

  /**
   * Get completion stats
   */
  getStats() {
    const total = this.todos.length;
    const completed = this.todos.filter(t => t.completed).length;
    const inProgress = this.todos.filter(t => t.inProgress).length;
    const pending = total - completed - inProgress;

    return { total, completed, inProgress, pending };
  }
}

module.exports = TodoManager;
