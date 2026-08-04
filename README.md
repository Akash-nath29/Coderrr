# Coderrr

**A free, open-source CLI coding agent that plans before it edits.**

[![PyPI](https://img.shields.io/pypi/v/coderrr)](https://pypi.org/project/coderrr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![GitHub issues](https://img.shields.io/github/issues/Akash-nath29/Coderrr)](https://github.com/Akash-nath29/Coderrr/issues)

```
   ██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝
  ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗
  ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

Coderrr writes a spec, shows it to you, and **stops**. Nothing on disk changes
until you approve. Then it implements the plan task by task, running the code in
a sandbox to check its own work.

> **v2 is a Python package on PyPI.** Coming from the npm package? See
> [docs/V2-MIGRATION.md](docs/V2-MIGRATION.md).

---

## Install

```bash
pipx install coderrr          # or: uv tool install coderrr
coderrr config                # pick a provider and model
coderrr run "add rate limiting to the API"
```

No provider SDKs required — every provider is reached over plain HTTP.

```bash
pipx install 'coderrr[keyring]'   # store API keys in the OS keyring
```

---

## How it works

```
your request
     │
  PLANNING ──► reads your code, pulls relevant skills
     │         writes requirements.md · design.md · tasks.md
     │
  ┌──┴───────────────────────────────────┐
  │  the plan is shown to you. it stops. │
  └──┬───────────────────────────────────┘
     │ you approve
  EXECUTION ──► per task: read → edit → run in sandbox → verify → mark done
```

**Write tools do not exist during planning.** They are absent from the model's
tool list entirely — the agent isn't asked to refrain from editing, it has no
tool that edits. Approval is what unlocks them.

Spec files live in `.coderrr/specs/NNN-slug/` and are meant to be committed.
They're also the agent's memory: a later session reads `tasks.md` to learn where
things stand instead of replaying a chat log. **You can edit them before
approving** to steer the work.

---

## Providers

| Provider | Key needed | Notes |
|---|---|---|
| **Ollama** | no | Default. Local or Ollama-hosted models. |
| Anthropic | yes | Claude |
| OpenAI | yes | GPT |
| Google | yes | Gemini |
| OpenRouter | yes | Many models behind one key |

The default is `gemma4:31b-cloud` via Ollama — tool-capable and usable on a free
Ollama account. Two notes on Ollama models:

- `kimi-k3:cloud` is stronger (1M context) but returns **403 without a paid
  Ollama subscription**, so it can't be the out-of-the-box default. Switch to it
  with `coderrr config` if you have one.
- Fully local models (`qwen2.5-coder:14b`, `llama3.1:8b`) need no account at all,
  but are noticeably weaker at the multi-turn tool use the agent loop depends on.

```bash
coderrr config              # interactive
coderrr config show         # current settings, key masked
coderrr run "..." -m gpt-4o # one-off model override
```

Keys resolve from environment variables first (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`), then the OS keyring,
then `~/.coderrr/config.toml` — which is written mode `0600`.

---

## The sandbox

Coderrr has no tool that runs commands against your working tree. Commands run
in a sandbox, and the agent reads the real exit code and output.

| Tier | What it is | Isolation |
|---|---|---|
| **scratch** (default) | Throwaway copy of the project + subprocess | Limits blast radius. **Not** a barrier against deliberately hostile code. |
| **docker** (auto when available) | Container, `--network none`, all capabilities dropped | Filesystem and network isolated |

`coderrr doctor` reports which tier is active. Dependency directories aren't
copied into the scratch tier, so the agent may need to install them first.

---

## Skills

Skills are markdown guidance — *how* to approach a class of problem — fetched
when the agent decides it needs them, and deleted after use. They add no
executable capability, so a bad skill can only give bad advice to an agent whose
tools are already gated.

Retrieval is automatic: the agent consults the registry while analysing intent
and loads only what is relevant. You can browse it yourself too:

```bash
coderrr skills search "pdf report"
```

The registry is [Akash-nath29/coderrr-skills](https://github.com/Akash-nath29/coderrr-skills)
— [`registry.json`](https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/registry.json)
indexes each skill's `Skills.md`. Point `[skills].registry` at your own index to
use a different one.

---

## MCP servers

Connect your own [MCP](https://modelcontextprotocol.io) servers and their tools
become tools Coderrr can call — Figma, Linear, Notion, or something internal.
**No extra install** — like every provider here, the client is plain HTTP.

From inside a session, paste a URL and you're done:

```
coderrr ❯ /mcp
  1. Add a server
  2. Done
? MCP: 1
? URL or command: http://127.0.0.1:3845/mcp
? Name for it: figma
◇ Connecting to figma...
■ figma connected — 1 tool(s): get_code
◇ Available as mcp__figma__* from your next request.
```

`/mcp add <url>` skips the menu. It takes effect on your next request — no
restart. Or from the shell:

```bash
# a URL is an HTTP server
coderrr mcp add figma http://127.0.0.1:3845/mcp

# after -- it's a command, run over stdio
coderrr mcp add sqlite -- npx -y @some/mcp-server --db ./app.db
```

Either way Coderrr connects immediately, so a wrong port or an app that isn't
running shows up there and not mid-task.

### Servers that need a login

For a server behind OAuth — Linear, Notion — adding it offers the sign-in there
and then:

```
coderrr ❯ /mcp add https://mcp.linear.app/mcp
? Name for it: linear
◇ Connecting to linear...
◇ linear requires you to sign in.
? Open your browser to authorize now? [y/n] (y): y
◇ Opening your browser to authorize...
■ Signed in to linear (https://mcp.linear.app).
```

Coderrr registers itself with the server, opens your browser with PKCE, catches
the redirect on a loopback port, and stores the tokens. Access tokens are renewed
silently when they expire; you only see a browser again if the refresh token
itself lapses.

**A browser only ever opens when you ask for it** — `mcp add`, `/mcp add`,
`mcp login`. Nothing during a task will open one, so agent runs never block on a
window you have to go and find.

```bash
coderrr mcp login linear               # sign in, or re-authorize
coderrr mcp login linear --no-browser  # print the URL instead (SSH, remote dev)
coderrr mcp logout linear              # discard stored credentials
```

Tokens live in your OS keyring when one is available, otherwise
`~/.coderrr/credentials.json` at mode 0600 — never in `config.toml`, which is
meant to be readable and committable.

For a server that uses a static token instead, skip OAuth entirely and pass the
header. Tokens belong in the environment, not in your config file:

```bash
coderrr mcp add notion https://mcp.notion.com/mcp -H 'Authorization=Bearer ${NOTION_TOKEN}'
```

Bridged tools are named `mcp__<server>__<tool>` and are available **while
planning as well as executing** — pulling a design or an issue description is
usually how a plan gets grounded in the first place.

**Each tool asks the first time it's used, then remembers.**

```
figma → get_code [read-only]
? Allow mcp__figma__get_code?
  1. Allow once
  2. Always allow this tool
  3. Deny
```

"Always" is saved to `allowed_tools` for that server, so it's one question per
tool rather than a prompt you learn to click through. `coderrr mcp reset <name>`
forgets those answers.

What a server claims about itself is never what decides. MCP tool annotations
like `readOnlyHint` are hints from an unverified peer — Coderrr shows them next
to the prompt and ignores them otherwise. Everything a server returns is labelled
as external data in context, because a ticket body or a design comment can be
written by anyone.

Two things worth knowing:

- **A stdio server runs on your machine, outside the sandbox**, with your
  environment. Coderrr shows the exact command and asks before saving it. Adding
  by URL doesn't ask — typing the URL is the decision.
- **MCP tools work during planning**, so a filesystem-style server, once
  allowed, can write files in a mode that otherwise has no write tool. Use
  `denied_tools` to hide anything you'd rather keep out of reach.

### When a server isn't available

By default a server that can't be reached is reported and skipped — a coding task
shouldn't die because a design tool is down. But that silently shortens the tool
list, and the same request then produces different work. If you depend on a
server, say so and get an error instead:

```toml
[mcp.servers.internal-api]
required = true    # a connect or login failure aborts the run
```

```bash
coderrr mcp list                  # what's configured, and what's signed in
coderrr mcp test figma            # connect and list its tools
coderrr mcp enable figma --off    # keep the config, stop using it
coderrr mcp remove figma
```

The client is written over `httpx` and `asyncio` — JSON-RPC 2.0 with Streamable
HTTP and stdio transports, plus OAuth 2.1 with dynamic client registration and
PKCE — for the same reason the provider adapters are: the official SDK ships its
server half too, and `uvicorn` has no business in a CLI. Tools only for now;
resources and prompts aren't implemented.

---

## Commands

| Command | What it does |
|---|---|
| `coderrr run "<request>"` | Plan, approve, implement |
| `coderrr run "..." --yes` | Skip the approval prompt |
| `coderrr spec list` / `spec show` | Inspect specs in this project |
| `coderrr config` / `config show` / `config clear` | Credentials and model |
| `coderrr skills search "<query>"` | Search the skill registry |
| `coderrr mcp add <name> <url>` | Connect an MCP server (or `/mcp` in a session) |
| `coderrr mcp login <name>` / `logout` | Sign in to a server that uses OAuth |
| `coderrr mcp list` / `test` / `remove` | Manage MCP servers |
| `coderrr doctor` | Environment check |
| `coderrr version` | Print the version |

---

## Configuration

`~/.coderrr/config.toml`:

```toml
[provider]
name  = "ollama"
model = "gemma4:31b-cloud"

[agent]
max_iter       = 5      # retries per task after a failure
max_tool_turns = 50     # tool calls per attempt before giving up
confirm_writes = false  # true prompts on every individual write

[verify]
mode        = "writes_only"  # always | writes_only | off
model       = ""             # empty reuses the main model; point at a cheap one
temperature = 0.3            # kept above zero so a false reject isn't repeatable

[sandbox]
tier    = "auto"        # auto | scratch | docker
network = false

# written by `coderrr mcp add`; hand-editable
[mcp.servers.figma]
transport     = "http"         # http | stdio
url           = "http://127.0.0.1:3845/mcp"
auth          = "auto"         # auto | none — OAuth when the server asks for it
required      = false          # true: a connect/login failure aborts the run
timeout       = 30.0           # seconds per request
allowed_tools = ["get_code"]   # answered "always allow"
denied_tools  = []             # never bridged at all
client_id     = ""             # only for servers without dynamic registration
scopes        = []             # overrides what the server advertises
```

A stdio server uses `command`, `args`, `env` and `cwd` instead of `url`. OAuth
tokens are never written here — see [MCP servers](#mcp-servers).

---

## Development

```bash
uv sync --all-extras
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
```

Not using `uv`? Pinned locks are checked in:

```bash
pip install -r requirements-dev.txt && pip install -e .
```

`pyproject.toml` is the source of truth; regenerate with
`uv pip compile pyproject.toml -o requirements.txt`.

The test suite runs entirely offline: a scripted fake provider drives the agent
loop, and provider adapters are tested against recorded SSE fixtures.

---

## Docs

- [Migration from v1](docs/V2-MIGRATION.md)
- [Changelog](CHANGELOG.md)

---

## License

MIT — see [LICENSE](LICENSE).
