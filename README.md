# Coderrr

**A free, open-source CLI coding agent that plans before it edits.**

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

## Commands

| Command | What it does |
|---|---|
| `coderrr run "<request>"` | Plan, approve, implement |
| `coderrr run "..." --yes` | Skip the approval prompt |
| `coderrr spec list` / `spec show` | Inspect specs in this project |
| `coderrr config` / `config show` / `config clear` | Credentials and model |
| `coderrr skills search "<query>"` | Search the skill registry |
| `coderrr doctor` | Environment check |

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
mode  = "writes_only"   # always | writes_only | off
model = ""              # empty reuses the main model; point at a cheap one

[sandbox]
tier    = "auto"        # auto | scratch | docker
network = false
```

---

## Development

```bash
uv sync --all-extras --dev
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

- [Implementation plan](docs/V2-IMPLEMENTATION-PLAN.md) — architecture and decisions
- [Migration from v1](docs/V2-MIGRATION.md)

---

## License

MIT — see [LICENSE](LICENSE).
