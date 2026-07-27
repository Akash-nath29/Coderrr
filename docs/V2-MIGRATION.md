# Migrating from Coderrr v1 (npm) to v2 (PyPI)

v2 is a Python package distributed on PyPI. The npm package `coderrr-cli` is
deprecated.

```bash
npm uninstall -g coderrr-cli
pipx install coderrr          # or: uv tool install coderrr
```

## What changed

| v1 | v2 |
|---|---|
| `npm i -g coderrr-cli` | `pipx install coderrr` |
| Node CLI + hosted Python backend | Single Python CLI, no backend |
| Keys POSTed to `coderrr-backend.vercel.app` | Keys stay local; the CLI calls providers directly |
| Model emits a whole plan up front, blind | Agent loop: read → act → observe → repeat |
| File edits applied with no confirmation | Spec written and approved before anything is edited |
| `run_command` against your working tree | `run_in_sandbox` against an isolated copy |
| `~/.coderrr/config.json`, mode 0644 | OS keyring, or `config.toml` at mode 0600 |
| Conversation history as memory | Spec artifacts as memory |

## Command mapping

| v1 | v2 |
|---|---|
| `coderrr` / `coderrr start` | `coderrr run "<request>"` |
| `coderrr exec "<request>"` | `coderrr run "<request>"` |
| `coderrr analyze "<request>"` | `coderrr run "<request>"` then decline the plan |
| `coderrr config` | `coderrr config` |
| `coderrr doctor` | `coderrr doctor` |
| `coderrr market` / `install` / `skills` | `coderrr skills search` (skills are now fetched on demand) |
| `coderrr rollback` | use `git revert`; v2 never auto-commits |

## Behaviour you should expect to differ

**You approve a plan, not individual edits.** v2 writes `requirements.md`,
`design.md` and `tasks.md` into `.coderrr/specs/NNN-slug/`, shows you the plan,
and stops. Nothing is modified until you say yes. You can edit the spec files
before approving to steer the work.

**Nothing runs against your working tree.** `run_command` is gone. Commands run
in a sandbox — a scratch copy of the project by default, a container when Docker
is available. `coderrr doctor` reports which tier is active.

**Skills are guidance, not code.** v1 skills shipped Python tools that were
installed and executed. v2 skills are markdown documents fetched when relevant
and deleted after use. They add no executable capability.

**No auto-commit.** v1's `--auto-commit` ran `git add .`, which swept unrelated
work into `[Coderrr]` commits. v2 leaves version control to you.

## Config migration

There is no automatic import — the shapes differ too much. Run `coderrr config`
once:

```bash
coderrr config          # pick provider, model, key
coderrr config show     # verify (key is masked)
```

Keys go to the OS keyring when `keyring` is installed
(`pipx install 'coderrr[keyring]'`), otherwise to `~/.coderrr/config.toml` at
mode 0600. Environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`GOOGLE_API_KEY`, `OPENROUTER_API_KEY`) override both.

Delete the old file when you are done: `rm ~/.coderrr/config.json`.

## Add specs to version control

`.coderrr/specs/` is meant to be committed — it is project documentation and
reviewable in pull requests. The generated `.coderrr/.gitignore` already excludes
`cache/` and `session/`.

## Retiring v1

- `coderrr-backend.vercel.app` stays up through the v2 beta, then shuts down.
- npm: `npm deprecate coderrr-cli@"*" "Coderrr has moved to PyPI — pip install coderrr"`
- The Node implementation is preserved on the `v1-legacy` branch.
