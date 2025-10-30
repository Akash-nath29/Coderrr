/**
 * Coderrr CLI - Phase 2
 * - TUI chat (blessed)
 * - Sends prompt to backend /chat
 * - Parses structured JSON 'plan' in backend response
 * - Shows plan and asks for confirmation
 * - Calls executor to perform safe file ops & commands
 */

const blessed = require('blessed');
const axios = require('axios');
const { executePlan } = require('../src/executor');
const { tryExtractJSON } = require('../src/utils');
require('dotenv').config();

const BACKEND = process.env.CODERRR_BACKEND;
const TIMEOUT_MS = parseInt(process.env.TIMEOUT_MS || '120000');

// screen
const screen = blessed.screen({ smartCSR: true, title: 'Coderrr' });

// messages box
const messagesBox = blessed.box({
  top: 0, left: 0, width: '100%', height: '85%-1',
  tags: true, scrollable: true, alwaysScroll: true,
  scrollbar: { ch: ' ', inverse: true },
  keys: true, mouse: true, vi: true,
  border: { type: 'line' },
  style: { fg: 'white', border: { fg: '#00afff' } }
});

// status bar with improved styling
const status = blessed.box({
  bottom: 3, left: 0, height: 1, width: '100%', tags: true,
  style: { fg: '#aaaaaa', bg: '#1a1a1a' }
});

// Set initial status
status.setContent('{green-fg}● Ready{/green-fg} {grey-fg}|{/grey-fg} {cyan-fg}Waiting for your request...{/cyan-fg}');

// input
const input = blessed.textbox({
  bottom: 0, left: 0, height: 3, width: '100%',
  keys: true, mouse: true, inputOnFocus: true,
  padding: { left: 1 }, style: { fg: 'white', bg: '#222222' },
  border: { type: 'line', fg: '#00ff88' }
});

screen.append(messagesBox);
screen.append(status);
screen.append(input);

let conversation = [];

function appendMessage(who, text) {
  const time = new Date().toLocaleTimeString();
  const tag = who === 'user' ? '{bold}{green-fg}You{/}' : '{bold}{cyan-fg}Coderrr{/}';
  messagesBox.pushLine(`${tag} {grey-fg}${time}{/}:`);
  const lines = String(text).split('\n');
  for (const line of lines) messagesBox.pushLine('  ' + line);
  messagesBox.pushLine('');
  messagesBox.setScrollPerc(100);
  screen.render();
}

// Helper: show simple JSON plan prettily
function renderPlan(planObj) {
  try {
    if (!planObj || !Array.isArray(planObj.plan)) {
      appendMessage('assistant', 'No structured plan found in response.');
      return;
    }
    appendMessage('assistant', 'Structured Plan:');
    planObj.plan.forEach((step, i) => {
      appendMessage('assistant', `${i + 1}. ${step.action} — ${step.path || step.command || ''}`);
      if (step.summary) appendMessage('assistant', `   summary: ${step.summary}`);
    });
  } catch (e) {
    appendMessage('assistant', 'Failed to render plan: ' + String(e));
  }
}

async function sendToBackend(payload) {
  try {
    status.setContent('{yellow-fg}● Thinking{/yellow-fg} {grey-fg}|{/grey-fg} {cyan-fg}Processing your request...{/cyan-fg}');
    screen.render();
    const resp = await axios.post(BACKEND + '/chat', payload, { timeout: TIMEOUT_MS });
    status.setContent('{green-fg}● Ready{/green-fg} {grey-fg}|{/grey-fg} {cyan-fg}Response received{/cyan-fg}');
    screen.render();
    return resp.data;
  } catch (err) {
    status.setContent('{red-fg}● Error{/red-fg} {grey-fg}|{/grey-fg} {red-fg}Failed to connect to backend{/red-fg}');
    screen.render();
    if (err.response && err.response.data) {
      return { error: 'Backend error', details: err.response.data };
    }
    return { error: 'Request error', details: err.message || String(err) };
  }
}

// ask a yes/no using blessed.question
function askYesNo(question) {
  return new Promise((resolve) => {
    const q = blessed.question({
      parent: screen,
      left: 'center',
      top: 'center',
      width: '70%',
      height: 7,
      label: ' Confirm ',
      border: { type: 'line' },
      tags: true
    });

    q.ask(`${question}\n(y/n)`, (err, val) => {
      q.destroy();
      screen.render();
      const yes = String(val || '').toLowerCase();
      resolve(yes === 'y' || yes === 'yes');
    });
  });
}

// Display welcome banner with ASCII art
function displayWelcomeBanner() {
  const banner = `
{cyan-fg}{bold}
   ██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗ 
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝
  ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗
  ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
{/bold}{/cyan-fg}
{magenta-fg}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{/magenta-fg}
{yellow-fg}{bold}        Your friendly neighbourhood Open Source Coding Agent{/bold}{/yellow-fg}
{magenta-fg}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{/magenta-fg}


{yellow-fg}💡 Quick Tips:{/yellow-fg}
  {grey-fg}• Type your coding request and press Enter{/grey-fg}
  {grey-fg}• Use /quit or /exit to leave{/grey-fg}
  {grey-fg}• Press Tab to focus input, Ctrl+C to exit{/grey-fg}

{blue-fg}🔗 Backend:{/blue-fg} {white-fg}${BACKEND}{/white-fg}
{magenta-fg}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{/magenta-fg}
`;

  const lines = banner.split('\n');
  lines.forEach(line => messagesBox.pushLine(line));
  messagesBox.pushLine('');
  
  // Add welcome message
  appendMessage('assistant', "I'm ready to help! Type your coding request and I'll create a plan for you.");
  messagesBox.setScrollPerc(100);
}

// Display welcome banner
displayWelcomeBanner();
input.focus();

input.key('enter', async () => {
  const value = input.getValue().trim();
  input.clearValue();
  screen.render();
  if (!value) return;
  if (value === '/quit' || value === '/exit') process.exit(0);

  appendMessage('user', value);
  conversation.push({ role: 'user', content: value });

  // Send prompt + optional context (for now just prompt)
  const backendResp = await sendToBackend({ prompt: value });

  if (backendResp.error) {
    appendMessage('assistant', `Error: ${JSON.stringify(backendResp.details)}`);
    return;
  }

  // backend returns { response: <text> } and optionally parsed_json
  const rawText = backendResp.response || '';
  appendMessage('assistant', rawText);

  // Try to extract JSON plan from text
  const parsed = tryExtractJSON(rawText);
  if (!parsed) {
    appendMessage('assistant', 'Could not parse a structured JSON plan from the model response. Ask the model to output a JSON plan, or enable developer mode.');
    return;
  }

  // show plan summary
  renderPlan(parsed);

  // ask user to proceed with applying the plan
  const proceed = await askYesNo('Proceed to apply the above steps?');
  if (!proceed) {
    appendMessage('assistant', 'Operation aborted by user.');
    status.setContent('{yellow-fg}● Idle{/yellow-fg} {grey-fg}|{/grey-fg} {cyan-fg}Waiting for your next request...{/cyan-fg}');
    screen.render();
    return;
  }

  // execute plan — executor streams logs back via callbacks
  try {
    status.setContent('{cyan-fg}● Executing{/cyan-fg} {grey-fg}|{/grey-fg} {yellow-fg}Applying changes...{/yellow-fg}');
    screen.render();
    await executePlan(parsed.plan, {
      appendMessage,
      askYesNo,
      status
    });
    appendMessage('assistant', 'Plan execution finished.');
    status.setContent('{green-fg}● Complete{/green-fg} {grey-fg}|{/grey-fg} {green-fg}All tasks finished successfully{/green-fg}');
    screen.render();
  } catch (e) {
    appendMessage('assistant', 'Execution error: ' + String(e));
    status.setContent('{red-fg}● Error{/red-fg} {grey-fg}|{/grey-fg} {red-fg}Execution failed{/red-fg}');
    screen.render();
  }
});

// keybindings
screen.key(['C-c'], () => process.exit(0));
screen.key(['tab'], () => input.focus());
screen.render();
