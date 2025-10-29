const jsdiff = require('diff');

// Attempts to find JSON object in arbitrary model text
function tryExtractJSON(text) {
  if (!text) return null;
  // First try to find a code block like ```json ... ```
  const codeBlockJson = /```(?:json)?\s*([\s\S]*?)```/i.exec(text);
  let jsonText = null;
  if (codeBlockJson && codeBlockJson[1]) {
    jsonText = codeBlockJson[1].trim();
  } else {
    // fallback: try to locate first { ... } that parses
    const firstBrace = text.indexOf('{');
    const lastBrace = text.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
      const candidate = text.slice(firstBrace, lastBrace + 1);
      jsonText = candidate;
    }
  }

  if (!jsonText) return null;
  try {
    const parsed = JSON.parse(jsonText);
    return parsed;
  } catch (e) {
    // try best-effort to fix common issues (replace trailing commas)
    try {
      const cleaned = jsonText.replace(/,\s*}/g, '}').replace(/,\s*\]/g, ']');
      return JSON.parse(cleaned);
    } catch (e2) {
      return null;
    }
  }
}

// unified diff using jsdiff
function unifiedDiff(a, b, filename = 'file') {
  if (a === null || a === undefined) a = '';
  if (b === null || b === undefined) b = '';
  const patch = jsdiff.createPatch(filename, a, b, '', '');
  // Strip the header lines for brevity
  return patch.split('\n').slice(2).join('\n');
}

module.exports = { tryExtractJSON, unifiedDiff };
