# Contributing to Coderrr

Thank you for considering contributing to Coderrr! 🎉

## Code of Conduct

This project is governed by our commitment to a welcoming community for all.
See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## How can I contribute?

### Reporting bugs

Check existing issues first. When filing one, include:

* A clear, descriptive title
* Exact steps to reproduce
* What you observed, and what you expected instead
* Your environment (OS, Python version, provider and model, Coderrr version —
  `coderrr doctor` prints most of this)
* Relevant output or logs

### Suggesting enhancements

* A clear, descriptive title
* A step-by-step description of the suggestion
* Current behaviour vs. the behaviour you want
* Why it would be useful

---

## Development setup

**Prerequisites:** Python 3.10+, git, and [uv](https://docs.astral.sh/uv/)
(recommended). Docker is optional — it enables the container sandbox tier.

```bash
git clone https://github.com/YOUR-USERNAME/Coderrr.git
cd Coderrr
uv sync --all-extras --dev
uv run coderrr --help
```

### The four gates

All of these are blocking in CI. Run them before opening a PR:

```bash
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy                          # strict mode
```

### Project layout

```
src/coderrr/
├── cli.py          typer entry point
├── agent/          loop.py, session.py, modes.py, state.py
├── llm/            normalized types + adapters (openai_compat, anthropic, google)
│                   schema.py — JSON Schema $ref flattening for tool payloads
├── tools/          read/ · write/ · system/
├── spec/           spec artifact store, models, markdown parser
├── sandbox/        scratch and docker tiers
├── skills/         registry client, ephemeral loader
├── mcp/            custom MCP servers — see below
├── policy/         paths.py (containment), gate.py (approval)
├── prompts/        system prompt assembly
└── verify.py       LLM write verification
tests/              pytest suite; runs fully offline
docs/               architecture and migration docs
```

The `mcp/` package is layered so that only one module speaks the wire protocol,
which is what keeps the rest testable with a fake connection:

```
mcp/
├── types.py        plain dataclasses + the Connection protocol
├── client.py       JSON-RPC 2.0 over Streamable HTTP and stdio
├── oauth.py        RFC 9728/8414 discovery, 7591 registration, PKCE, tokens
├── credentials.py  token storage: keyring, else a 0600 file
├── naming.py       mcp__<server>__<tool>, sanitized to provider rules
├── bridge.py       one MCP tool → one Coderrr Tool (generated subclass)
├── manager.py      connection lifetimes, and "may this tool run?"
├── setup.py        shared by `coderrr mcp` and the REPL's /mcp
└── catalog.py      built-in server shorthands (currently empty)
```

There is no MCP SDK dependency. The client is hand-written over `httpx` for the
same reason the provider adapters are: the official SDK bundles its server half,
and `starlette`/`uvicorn` have no business in a CLI.

### Design invariants

Changes that weaken any of these need a strong justification in the PR:

1. **Write tools are absent from the model's tool list in Planning mode.** Safety
   comes from the tool not existing, not from a prompt asking the model to
   behave.
2. **Path containment (`policy/paths.py`) is deterministic code.** The LLM
   verifier checks content quality; it is not a security boundary.
3. **No tool runs commands against the user's working tree** — only
   `run_in_sandbox`.
4. **Tool failures return `ToolResult.error(...)`, never raise.** The model must
   be able to recover.
5. **Read/write tools document themselves via their pydantic schemas.** Only
   SYSTEM tools belong in the system prompt.
6. **What an MCP server says about itself never decides anything.** Tool
   annotations such as `readOnlyHint` may shape what a prompt *says*; the gate
   reads the user's stored answer, never the server's claim.
7. **No browser opens during a run.** OAuth's interactive leg belongs to
   `mcp add` / `mcp login` only. Silent token refresh anywhere is fine; a task
   that blocks on a browser window is not.
8. **Only `mcp/client.py` speaks the MCP wire format.** Everything above it uses
   `mcp/types.py`. That boundary is why the SDK could be dropped by rewriting one
   file, and why the rest of the package tests without a network.

### Testing

The suite runs entirely offline. `tests/fakes.py::FakeProvider` replays scripted
model turns, so you can test the agent loop with no network and no API key;
provider adapters are tested against recorded SSE fixtures with `respx`.

* Add tests for new behaviour, covering both success and failure paths
* Tests must never touch the real `~/.coderrr` — root everything in `tmp_path`
* Anything touching `policy/paths.py` should get property-based coverage

**MCP.** Use `tests/test_mcp.py::FakeConnection` rather than a live server; it
satisfies the `Connection` protocol, so tool naming, schema handling, approval and
result rendering are all reachable without a network or a subprocess.

The OAuth flow is tested end to end anyway: `open_url` is injected, so a fake
browser fetches a **real loopback socket** while `respx` stands in for the remote
endpoints. Two things to know if you touch it:

* `respx` intercepts *every* httpx request, including the one to `127.0.0.1`. Add
  `respx.mock.route(host="127.0.0.1").pass_through()` or the redirect never
  arrives and the login waits for its full timeout.
* Pass a short `timeout=` to `oauth.login` in tests. The production default is
  300 seconds, which turns a regression into a hung suite.

Credential tests must construct `CredentialStore(use_keyring=False)`. The default
would write to the developer's real OS keyring.

---

## Pull requests

**Branch model:** `feature/*` → `dev` → `main`. Direct feature-to-main PRs are
blocked by CI.

```bash
git checkout dev && git pull origin dev
git checkout -b feature/your-feature-name
# ... work, run the four gates ...
git push origin feature/your-feature-name
```

Open the PR against **`dev`**, fill in the template, and wait for CI.

**Requirements:**

* All four gates pass
* New behaviour has tests
* Docs updated for user-facing changes
* Files end with a newline

## Style

**Python.** PEP 8 via `ruff` (100-column lines). Full type annotations — `mypy`
runs in strict mode. Docstrings on modules and public functions; explain *why* a
non-obvious approach was chosen, not what the code does.

**Commit messages.** Present tense, imperative mood, first line ≤ 72 characters,
conventional prefixes:

`feat:` · `fix:` · `docs:` · `style:` · `refactor:` · `test:` · `chore:`

```
feat: add workspace containment for symlinked paths

- Resolve symlinks before testing containment
- Add property-based tests for traversal depth

Closes #42
```

## Documentation

* [README.md](README.md) for user-facing changes
* [.github/copilot-instructions.md](.github/copilot-instructions.md) for
  architecture changes
* [docs/V2-IMPLEMENTATION-PLAN.md](docs/V2-IMPLEMENTATION-PLAN.md) records the
  decisions behind v2 and their rationale

## A note on v1

Coderrr v1 was a Node CLI with a hosted FastAPI backend. It is retired and
preserved on the `v1-legacy` branch. Please do not send PRs against it — see
[docs/V2-MIGRATION.md](docs/V2-MIGRATION.md).
