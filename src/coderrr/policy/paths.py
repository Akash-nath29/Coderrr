"""Workspace path containment.

This is the deterministic security boundary. The LLM verifier judges whether
*content* is sound; this module guarantees the *destination* is inside the
project. Nothing here may depend on model output or on a prompt instruction.

Every path that reaches the filesystem passes through :func:`resolve_read` or
:func:`resolve_write`. Both resolve symlinks before testing containment, so a
symlink inside the workspace pointing outward is rejected on the resolved
target, not the literal path.
"""

from __future__ import annotations

from pathlib import Path, PurePath

__all__ = [
    "WRITE_DENY_PREFIXES",
    "PathPolicyError",
    "is_within",
    "resolve_read",
    "resolve_write",
]


class PathPolicyError(ValueError):
    """A path was rejected by workspace policy."""


# Directories that are never writable even though they sit inside the workspace.
# `.coderrr/specs` is deliberately absent -- the spec tools must write there.
WRITE_DENY_PREFIXES: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
)


def is_within(candidate: PurePath, root: PurePath) -> bool:
    """True when ``candidate`` is ``root`` or sits beneath it."""
    try:
        return candidate == root or candidate.is_relative_to(root)
    except (ValueError, TypeError):
        return False


def _resolve(raw: str, workspace: Path) -> Path:
    if not raw or not raw.strip():
        raise PathPolicyError("Path is empty.")
    if "\x00" in raw:
        raise PathPolicyError("Path contains a null byte.")

    root = workspace.resolve()
    candidate = Path(raw)
    target = candidate if candidate.is_absolute() else root / candidate

    # strict=False so paths that do not exist yet (creates) still normalize and
    # resolve any symlinked ancestors.
    try:
        resolved = target.resolve(strict=False)
    except (OSError, RuntimeError) as exc:  # RuntimeError: symlink loop
        raise PathPolicyError(f"Path could not be resolved: {raw}") from exc

    if not is_within(resolved, root):
        raise PathPolicyError(f"Path escapes the workspace: {raw!r} resolves outside {root}")

    return resolved


def resolve_read(raw: str, workspace: Path) -> Path:
    """Resolve a path for reading. Raises :class:`PathPolicyError` if it escapes."""
    return _resolve(raw, workspace)


def resolve_write(raw: str, workspace: Path) -> Path:
    """Resolve a path for writing.

    Adds the write deny-list on top of containment: version-control metadata is
    off limits even inside the workspace, because a corrupted ``.git`` destroys
    the user's ability to recover from anything else the agent did.
    """
    resolved = _resolve(raw, workspace)
    root = workspace.resolve()

    try:
        relative = resolved.relative_to(root)
    except ValueError:  # pragma: no cover - _resolve already guarantees this
        raise PathPolicyError(f"Path escapes the workspace: {raw!r}") from None

    parts = relative.parts
    if parts and parts[0] in WRITE_DENY_PREFIXES:
        raise PathPolicyError(
            f"Writes to {parts[0]}/ are not permitted (version-control metadata)."
        )

    return resolved
