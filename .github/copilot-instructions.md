# Coderrr — AI agent instructions

Coderrr v2 is a single Python CLI (`pip install coderrr`). There is no Node
frontend and no hosted backend; the CLI talks to LLM providers directly over
HTTP.

## Architecture

```
src/coderrr/
├── cli.py          typer entry point
├── agent/          loop.py (the runtime), session.py (two-phase flow), modes.py
├── llm/            normalized types + 3 HTTP adapters
├── tools/          read/ · write/ · system/
├── spec/           spec artifact store, models, markdown parser
├── sandbox/        scratch (default) and docker tiers
├── skills/         registry client, ephemeral loader
├── policy/         paths.py (containment), gate.py (approval)
├── prompts/        system prompt assembly
└── verify.py       LLM write verification
```

## The invariants — do not weaken these

**1. Write tools do not exist in Planning mode.** `agent/modes.py` maps each mode
to a set of tool classes; `ToolRegistry.exposed()` filters on it. The model is
never *told* to avoid editing — it has no tool that edits. `session.py::execute`
is the only place mode flips to EXECUTION, and only after user approval.

**2. Path containment is deterministic code, never a model judgement.**
`policy/paths.py` resolves symlinks before testing containment. The LLM verifier
in `verify.py` judges *content*; it is not the security boundary and must never
become one.

**3. No tool runs commands against the user's working tree.** `run_in_sandbox` is
the only execution path. v1's `run_command` was removed deliberately.

**4. Tool errors are returned, never raised.** `ToolRegistry.execute` catches
everything and returns `ToolResult.error(...)` so the model can recover. A tool
crash must not kill the loop.

## Conventions

- **Read/write tools document themselves** through pydantic field descriptions —
  those schemas are what the model sees. Only SYSTEM tools are described in
  `prompts/system.py`. Keep the system prompt from growing with the project.
- **Adapters translate outward** from the internal block model
  (`llm/types.py`), which follows Anthropic's shape. OpenAI's flat `tool_calls`
  maps into blocks; the reverse loses information.
- **Everything a tool touches comes from `ToolContext`.** No globals — that is
  what makes the surface testable with a temp dir and a fake console.
- Async throughout. `httpx` only; no provider SDKs.

## Testing

`tests/fakes.py::FakeProvider` replays scripted turns, so the agent loop is
tested deterministically with no network and no API key. Provider adapters are
tested against recorded SSE fixtures via `respx`.

Tests must never touch the real `~/.coderrr`. Everything roots in `tmp_path`.

```bash
uv sync --all-extras --dev
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy            # strict
```

All four gates are blocking in CI. Do not add `continue-on-error` to them.

## History

v1 was a Node CLI plus a hosted FastAPI backend. It is preserved on the
`v1-legacy` branch and is not maintained. See `docs/V2-MIGRATION.md` for the
mapping and `docs/V2-IMPLEMENTATION-PLAN.md` for the decisions behind v2.
