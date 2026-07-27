"""Workspace containment tests.

The highest-value tests in the suite: this module is the deterministic security
boundary, so it gets both hand-picked attack cases and property-based coverage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from coderrr.policy.paths import (
    PathPolicyError,
    is_within,
    resolve_read,
    resolve_write,
)

ESCAPES = [
    "../outside.txt",
    "../../etc/passwd",
    "src/../../outside.txt",
    "./../../outside.txt",
    "a/b/c/../../../../outside.txt",
    "/etc/passwd",
    "/tmp/evil",
    "~/.ssh/id_rsa",  # literal '~' dir, still must resolve inside
]

INSIDE = [
    "file.txt",
    "./file.txt",
    "src/app.py",
    "src/../src/app.py",
    "a/b/../c/d.txt",
    "deeply/nested/new/file.md",
]


@pytest.mark.parametrize("candidate", ESCAPES)
def test_read_rejects_escapes(workspace: Path, candidate: str) -> None:
    if candidate.startswith("~"):
        pytest.skip("'~' is not expanded; covered by test_tilde_is_literal")
    with pytest.raises(PathPolicyError):
        resolve_read(candidate, workspace)


@pytest.mark.parametrize("candidate", ESCAPES)
def test_write_rejects_escapes(workspace: Path, candidate: str) -> None:
    if candidate.startswith("~"):
        pytest.skip("'~' is not expanded; covered by test_tilde_is_literal")
    with pytest.raises(PathPolicyError):
        resolve_write(candidate, workspace)


@pytest.mark.parametrize("candidate", INSIDE)
def test_accepts_paths_inside(workspace: Path, candidate: str) -> None:
    resolved = resolve_read(candidate, workspace)
    assert is_within(resolved, workspace.resolve())


def test_tilde_is_literal(workspace: Path) -> None:
    """'~' must not expand to the home directory."""
    resolved = resolve_read("~/notes.md", workspace)
    assert is_within(resolved, workspace.resolve())
    assert "~" in str(resolved)


def test_absolute_path_inside_workspace_is_allowed(workspace: Path) -> None:
    absolute = str(workspace / "src" / "app.py")
    assert resolve_read(absolute, workspace) == (workspace / "src" / "app.py").resolve()


def test_nonexistent_paths_resolve_for_writes(workspace: Path) -> None:
    """Creates target paths that do not exist yet."""
    resolved = resolve_write("new/dir/file.txt", workspace)
    assert is_within(resolved, workspace.resolve())
    assert not resolved.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_symlink_escaping_workspace_is_rejected(workspace: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")

    (workspace / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathPolicyError):
        resolve_read("link/secret.txt", workspace)
    with pytest.raises(PathPolicyError):
        resolve_write("link/planted.txt", workspace)


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_symlink_inside_workspace_is_allowed(workspace: Path) -> None:
    (workspace / "alias").symlink_to(workspace / "src", target_is_directory=True)
    resolved = resolve_read("alias/app.py", workspace)
    assert is_within(resolved, workspace.resolve())


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_symlink_loop_is_rejected(workspace: Path) -> None:
    a = workspace / "a"
    b = workspace / "b"
    a.symlink_to(b)
    b.symlink_to(a)
    # Either rejected outright or resolved to something still contained.
    try:
        resolved = resolve_read("a/x", workspace)
    except PathPolicyError:
        return
    assert is_within(resolved, workspace.resolve())


@pytest.mark.parametrize("candidate", ["", "   ", "\t"])
def test_empty_paths_rejected(workspace: Path, candidate: str) -> None:
    with pytest.raises(PathPolicyError):
        resolve_read(candidate, workspace)


def test_null_byte_rejected(workspace: Path) -> None:
    with pytest.raises(PathPolicyError):
        resolve_read("file\x00.txt", workspace)


@pytest.mark.parametrize("denied", [".git/config", ".git/hooks/pre-commit", ".hg/x"])
def test_write_denylist(workspace: Path, denied: str) -> None:
    with pytest.raises(PathPolicyError, match="not permitted"):
        resolve_write(denied, workspace)


def test_git_is_readable_but_not_writable(workspace: Path) -> None:
    """Reading VCS metadata is fine; corrupting it is not."""
    resolve_read(".git/config", workspace)  # must not raise
    with pytest.raises(PathPolicyError):
        resolve_write(".git/config", workspace)


def test_specs_directory_is_writable(workspace: Path) -> None:
    """The spec tools must be able to write their own artifacts."""
    resolved = resolve_write(".coderrr/specs/001-x/tasks.md", workspace)
    assert is_within(resolved, workspace.resolve())


# -- property-based ------------------------------------------------------

_SEGMENTS = st.sampled_from(["a", "b", "src", "..", ".", "x.py", "nested", "dir", "..."])


@settings(max_examples=250, deadline=None)
@given(segments=st.lists(_SEGMENTS, min_size=1, max_size=8))
def test_result_is_always_contained_or_raises(
    tmp_path_factory: pytest.TempPathFactory, segments: list[str]
) -> None:
    """For any assembled relative path: either contained, or an explicit error.

    There is no third outcome -- no silent escape, no unexpected exception type.
    """
    root = tmp_path_factory.mktemp("ws")
    candidate = "/".join(segments)

    for resolver in (resolve_read, resolve_write):
        try:
            resolved = resolver(candidate, root)
        except PathPolicyError:
            continue
        assert is_within(resolved, root.resolve()), (
            f"{resolver.__name__} escaped: {candidate!r} -> {resolved}"
        )


@settings(max_examples=120, deadline=None)
@given(depth=st.integers(min_value=1, max_value=40))
def test_traversal_of_any_depth_is_rejected(
    tmp_path_factory: pytest.TempPathFactory, depth: int
) -> None:
    root = tmp_path_factory.mktemp("ws")
    candidate = "/".join([".."] * depth) + "/target.txt"
    with pytest.raises(PathPolicyError):
        resolve_read(candidate, root)


@settings(max_examples=100, deadline=None)
@given(
    name=st.text(
        alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
        min_size=1,
        max_size=30,
    )
)
def test_arbitrary_filenames_never_escape(
    tmp_path_factory: pytest.TempPathFactory, name: str
) -> None:
    root = tmp_path_factory.mktemp("ws")
    try:
        resolved = resolve_read(name, root)
    except (PathPolicyError, OSError, ValueError):
        return
    if sys.platform == "win32" and ":" in name:
        return  # drive-relative forms are platform-specific
    assert is_within(resolved, root.resolve())
