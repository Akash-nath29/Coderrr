// src/utils/queryClassifier.js

function isPlainQuery(input) {
  if (!input) return true;

  const text = input.trim().toLowerCase();

  // very short input -> plain query
  if (text.length < 4) return true;

  // question words
  const questionWords = [
    "what", "why", "how", "when", "where", "who",
    "explain", "define", "describe", "tell me",
    "difference", "compare", "meaning", "does", "do"
  ];

  // ends with question mark
  if (text.endsWith("?")) return true;

  // starts with question words
  for (const word of questionWords) {
    if (text.startsWith(word + " ")) return true;
  }

  return false;
}

function isTaskCommand(input) {
  if (!input) return false;

  const text = input.trim().toLowerCase();

  // task-like keywords
  const taskKeywords = [
    "create", "build", "make", "generate", "write",
    "fix", "implement", "add", "remove", "update",
    "refactor", "optimize", "debug"
  ];

  for (const word of taskKeywords) {
    if (text.startsWith(word + " ")) return true;
  }

  return false;
}

module.exports = { isPlainQuery, isTaskCommand };
