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

### MCP servers

Connecting an MCP server is the one action that grants the agent capability
Coderrr did not write. Four boundaries apply.

**Per-tool approval.** Bridged tools are class `EXTERNAL` and every one of them
asks the first time it is called, then remembers the answer in
`[mcp.servers.<name>].allowed_tools`. Plan approval covers edits to your files;
it does not cover filing a ticket in someone else's system.

**Server claims are never trusted.** MCP tool annotations such as `readOnlyHint`
are hints from an unverified peer. Coderrr shows them next to the approval prompt
and uses them for nothing else. The spec makes the same point: clients should not
make tool-use decisions from annotations.

**Tool output is untrusted data.** Every result is labelled as external content
in context, and the system prompt states that instructions found inside it are an
attack rather than a request. A ticket description, a design comment, or a page a
server fetched can be written by anyone. This is mitigation, not a boundary — the
approval gate and path containment are what actually hold.

**stdio servers run outside the sandbox.** A stdio server is a program on your
machine with your environment, not a sandboxed subprocess. Coderrr prints the
exact command and asks before saving it; adding a server by URL does not ask,
because typing the URL is itself the decision. Only add commands you would run
yourself.

### MCP credentials

OAuth tokens go to the OS keyring when one is available, otherwise
`~/.coderrr/credentials.json`, created with mode `0600`. They are deliberately
never written to `config.toml`: that file is meant to be read, edited and
committed, and it is rewritten wholesale on every save.

**On Windows those mode bits are not enforced** — the OS ignores everything but
the read-only flag, so the file is protected by the user-profile ACL rather than
by Coderrr. In practice the keyring is the normal path there, since Credential
Manager is always available. The same caveat applies to `config.toml`.

Coderrr registers itself dynamically with each authorization server (RFC 7591)
and requests a public client, so where the server allows it there is no client
secret to store. The flow uses PKCE (S256), a `state` check, a loopback redirect
on `127.0.0.1`, and the RFC 8707 `resource` parameter so tokens are bound to the
one MCP server they were issued for.

**A browser only opens when you ask for it** — `mcp add`, `mcp login`, `/mcp
login`. Access tokens refresh silently, including during a run, but nothing
during a task will open a browser or prompt for credentials.

`coderrr mcp logout <name>` discards a server's tokens; `coderrr mcp reset
<name>` forgets its remembered tool approvals.

---

## Recommendations

- Run Coderrr inside a git repository so changes are reviewable and revertible.
- Read the spec before approving. Editing `tasks.md` first is the cheapest way
  to steer the work.
- Install Docker if the agent will execute code you would not run yourself.
- Set `confirm_writes = true` in `[agent]` for per-write prompting.
- Prefer environment variables or the keyring over storing keys in config.
- Add MCP servers you trust with the data in your workspace, and prefer HTTP
  servers over stdio ones where both exist.
- Use `denied_tools` to hide any MCP tool you would rather keep unreachable,
  rather than relying on declining it each time.

## Known considerations

**Prompt injection.** Content the agent reads — source files, dependency
manifests, skills, and MCP tool results — can attempt to influence it. The
approval gate and path containment hold regardless of what the model is persuaded
to attempt, but a plan generated from poisoned input can still be wrong. Read
plans before approving.

MCP results deserve particular care because they are the one input an outside
party can write directly. A server that returns issue text or page content is
relaying data from whoever authored it.

**MCP tools are available while planning.** External tools are exposed in both
modes, because reading a design or an issue is usually how a plan gets grounded.
The consequence is that a filesystem-style MCP server, once you allow one of its
write tools, can modify files during a phase that otherwise has no write tool.
The `WRITE` class remains absent from planning; this is a capability arriving from
outside that taxonomy. Use `denied_tools`, or do not connect such a server.

**AI-generated code.** Review it as you would any contribution. Passing tests in
the sandbox is evidence, not proof.
