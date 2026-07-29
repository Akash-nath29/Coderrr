# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.0.x   | ✅ |
| 1.x     | ❌ End of life — see [docs/V2-MIGRATION.md](docs/V2-MIGRATION.md) |

## Reporting a Vulnerability

Please do **not** open a public issue.

Open a [GitHub Security Advisory](https://github.com/Akash-nath29/Coderrr/security/advisories/new)
including:

- Type of vulnerability
- Step-by-step reproduction
- Potential impact
- A suggested fix, if you have one

**What to expect:** acknowledgment within 48 hours, assessment within 5 business
days, a fix timeline within 10 business days, and coordinated disclosure.

---

## Security model

Coderrr runs an LLM with filesystem access on your machine. These are the
boundaries it enforces, and their limits.

### Approval gate

Nothing is modified until you approve a plan. During the planning phase the
write tools are **absent from the model's tool list** — the agent is not
instructed to refrain from editing, it has no tool that edits. This is enforced
structurally in `agent/modes.py` and `tools/registry.py`, not by prompt.

`--yes` skips the prompt. Use it only where you would accept the agent's output
unreviewed.

### Workspace containment

Every filesystem path passes through `policy/paths.py`, which resolves symlinks
before testing containment and rejects anything outside the workspace root.
Writes to `.git/`, `.hg/` and `.svn/` are refused even inside the workspace.

This is deterministic code and is the actual security boundary.

### Write verification

The optional LLM verifier (`verify.py`) checks proposed file contents for
truncation, wrong-file edits, mass deletion, and embedded credentials.

**It is a correctness check, not a security control.** A model can be argued out
of a judgement; path containment cannot. Never rely on the verifier alone.

### Sandbox

Coderrr has no tool that runs commands against your working tree.

| Tier | Isolation |
|---|---|
| **scratch** (default) | Throwaway copy + subprocess with a timeout and memory cap. Limits blast radius. **Not** a barrier against deliberately hostile code — no namespace or network isolation. |
| **docker** (auto when available) | Container with `--network none`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, memory and PID limits. |

`coderrr doctor` reports the active tier. If you run untrusted generated code,
install Docker.

### Credentials

API keys resolve from environment variables, then the OS keyring
(`pip install 'coderrr[keyring]'`), then `~/.coderrr/config.toml`, which is
created with mode `0600`. Keys are never written to logs and are masked in
`coderrr config show`.

Keys go directly from your machine to your chosen provider. Coderrr operates no
server and proxies nothing.

### Skills

Skills are markdown guidance, not executable code — they add no capability to an
agent whose tools are already gated. Downloads are size-limited and, where the
registry publishes a `sha256`, integrity-checked. They are deleted after use.

---

## Recommendations

- Run Coderrr inside a git repository so changes are reviewable and revertible.
- Read the spec before approving. Editing `tasks.md` first is the cheapest way
  to steer the work.
- Install Docker if the agent will execute code you would not run yourself.
- Set `confirm_writes = true` in `[agent]` for per-write prompting.
- Prefer environment variables or the keyring over storing keys in config.

## Known considerations

**Prompt injection.** Content the agent reads — source files, dependency
manifests, skills — can attempt to influence it. The approval gate and path
containment hold regardless of what the model is persuaded to attempt, but a
plan generated from poisoned input can still be wrong. Read plans before
approving.

**AI-generated code.** Review it as you would any contribution. Passing tests in
the sandbox is evidence, not proof.
