#!/usr/bin/env node

/**
 * Quick preview of the TUI banner
 */

const blessed = require('blessed');
require('dotenv').config();

const screen = blessed.screen({ smartCSR: true, title: 'Coderrr Banner Preview' });

const messagesBox = blessed.box({
  top: 0, left: 0, width: '100%', height: '100%',
  tags: true, scrollable: true, alwaysScroll: true,
  keys: true, mouse: true, vi: true,
  border: { type: 'line' },
  style: { fg: 'white', border: { fg: '#00afff' } }
});

screen.append(messagesBox);

const BACKEND = process.env.CODERRR_BACKEND;

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

{bold}{cyan-fg}Coderrr{/cyan-fg}{/bold} {grey-fg}10:30 PM{/grey-fg}:
  I'm ready to help! Type your coding request and I'll create a plan for you.

`;

const lines = banner.split('\n');
lines.forEach(line => messagesBox.pushLine(line));

messagesBox.pushLine('');
messagesBox.pushLine('{grey-fg}Press Ctrl+C to exit preview{/grey-fg}');

screen.key(['C-c'], () => process.exit(0));
screen.render();
