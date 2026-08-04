# CLAUDE.md

## 1. Git Restrictions

- **Do NOT run write-based git commands.** This includes (but is not limited to): `git push`, `git pull`, `git commit`, `git add`, `git merge`, `git rebase`, `git reset`, `git checkout` (when it modifies state), `git stash`, `git tag`, `git branch -d/-D`, and any other command that alters repository state.
- **Read-only git commands are allowed.** For example: `git status`, `git log`, `git diff`, `git show`, `git branch` (list), `git remote -v`, `git blame`.
- If a task seems to require a write-based git command, **stop and ask me** to run it myself or to explicitly approve it.

## 2. Workflow: Plan First, Spec Second, Code Only on Approval

- **Always plan before acting.** For any task, first present a clear plan describing what you intend to do and how — grounded in whatever specs you read per Section 3, not the raw codebase alone.
- **Do NOT write, edit, or execute code** until I explicitly give a green light (e.g. "go ahead", "execute", "proceed", "do it"). Presenting a plan is not permission to implement it.
- If any part of the task is ambiguous or has unknown variables, **ask me before proceeding** rather than assuming.
- **Substantial tasks** — new features, architecture changes, non-trivial bug fixes, refactors — get a spec (Section 3).
- **Trivial tasks** — typo fixes, one-line config tweaks, formatting — don't need one. Say so explicitly ("this is trivial, skipping the spec") so I can override if I disagree.

## 3. Spec System (`project_spec/`)

### 3.1 First time in a project
If `project_spec/` doesn't exist yet, stop and ask me before doing anything else: should we backfill specs describing the current state of the codebase first, or start the spec trail fresh from this point forward? Don't assume either way — it depends on how much of the existing code is still in flux.

### 3.2 Read specs before reading the codebase
Whenever a task requires understanding existing code, check `project_spec/` first — before opening source files. This is how you avoid re-reading the whole codebase every turn.

- Always start with `project_spec/INDEX.md` — a one-line-per-spec table of contents. It's small; read it every time specs exist.
- **Glance (default mode):** for work scoped to a known module, read only the spec(s) `INDEX.md` marks `current` for that module. Skip everything else.
- **History mode (only when the task calls for it):** trigger this when I ask how something evolved, ask for an audit/onboarding writeup, or a change is big enough that understanding *why* past decisions were made actually matters. In that case, read every spec for the affected module(s), in numeric order — `current` and `superseded` alike.
- If code has no matching spec, say so explicitly instead of guessing intent from the code alone.

### 3.3 Creating and updating a spec (substantial tasks only)
Once I approve the plan:

1. Before touching code, create `project_spec/NNN-slug.md` (next sequential number, 3-digit zero-padded, e.g. `007-rate-limit-middleware.md`) using the template below. Status starts as `draft`.
2. Implement the approved plan. Keep code comments minimal — see Section 4.
3. After I've reviewed the implementation, update the spec: fill in the real "Files touched" pointers and set status to `current`. If this spec replaces an earlier one for the same module, set that older spec's status to `superseded` — leave its content untouched, it's part of the history now.
4. Add or update its row in `project_spec/INDEX.md`.

**`INDEX.md` format:**

| # | File | Module | Status | Summary |
|---|------|--------|--------|---------|
| 001 | 001-auth-jwt.md | auth | superseded | Initial JWT auth flow |
| 004 | 004-auth-refresh.md | auth | current | Refresh-token rotation, replaces 001 |

Rows are append-only. Only the `Status` column of a past row ever changes.

**Spec template:**

```
---
spec: NNN
date: YYYY-MM-DD
module: <area/module name>
status: draft
supersedes: <spec # or none>
---

## Objective
What this change is for — one paragraph.

## Context
Why now: the problem, request, or prior spec behind this.

## Decisions
Key design/architecture decisions and the reasoning behind them. This is the
"why" that code comments no longer need to carry.

## Files touched
- `path/to/file` — one-line purpose

## Open questions / follow-ups
Anything deferred or still uncertain.
```

## 4. Code Comments

- No block comments explaining what a function or module does, or why it's designed a certain way — that reasoning lives in its spec, not inline.
- Every file created or meaningfully changed under an active spec gets exactly one pointer line near the top, in the language's comment syntax:
  `// Spec: project_spec/NNN-slug.md`
- Inline comments are fine only for genuinely non-obvious one-liners — a regex, a workaround for a library quirk, the source of a magic number. One line, no more.
- No commented-out code left behind.
- If you're already editing a file that has legacy long comments and it has (or is getting) a spec, trim the comment down to a pointer as part of that edit — don't leave stale bloat sitting next to the new one. Don't go hunting for other files to clean up unprompted; if you notice more, propose it as its own task instead of doing it silently.