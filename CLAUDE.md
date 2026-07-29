# CLAUDE.md

## Git Restrictions

- **Do NOT run write-based git commands.** This includes (but is not limited to): `git push`, `git pull`, `git commit`, `git add`, `git merge`, `git rebase`, `git reset`, `git checkout` (when it modifies state), `git stash`, `git tag`, `git branch -d/-D`, and any other command that alters repository state.
- **Read-only git commands are allowed.** For example: `git status`, `git log`, `git diff`, `git show`, `git branch` (list), `git remote -v`, `git blame`.
- If a task seems to require a write-based git command, **stop and ask me** to run it myself or to explicitly approve it.

## Workflow: Plan First, Code Only on Approval

- **Always plan before acting.** When given a task, first present a clear plan describing what you intend to do and how.
- **Do NOT write, edit, or execute code** until I explicitly give a green flag (e.g., "go ahead", "execute", "proceed", "do it").
- Presenting a plan is not permission to implement it — wait for my confirmation.
- If any part of the task is ambiguous or has unknown variables, **ask me before proceeding** rather than making assumptions.