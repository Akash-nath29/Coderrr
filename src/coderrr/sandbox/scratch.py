"""Tier 1 sandbox: a throwaway copy of the workspace plus a plain subprocess.

What this gives you: the agent can build and run the project, read real exit
codes and stderr, and fix its own mistakes -- without a bad build touching the
user's working tree.

What it does not give you: protection from deliberately malicious code. There is
no namespace or network isolation here. Use the Docker tier when that matters.
This limitation is surfaced through :attr:`SandboxTier.description` rather than
buried in a docstring.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import tempfile
import time
from pathlib import Path

from coderrr.sandbox.base import ExecResult, SandboxTier

#: Excluded from the scratch copy: version-control metadata, and dependency
#: trees that are large and reproducible from manifests.
COPY_EXCLUDES = shutil.ignore_patterns(
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "*.pyc",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    "dist",
    "build",
    ".next",
    ".coderrr",
)


class ScratchSandbox:
    """Runs commands in a disposable copy of the workspace."""

    tier = SandboxTier.SCRATCH

    def __init__(
        self,
        workspace: Path,
        *,
        default_timeout: int = 300,
        memory_mb: int | None = 2048,
    ) -> None:
        self.workspace = workspace
        self.default_timeout = default_timeout
        self.memory_mb = memory_mb
        self._root: Path | None = None

    # -- lifecycle -------------------------------------------------------

    def _ensure_root(self) -> Path:
        """Materialize the scratch copy lazily, once per sandbox instance."""
        if self._root is not None and self._root.exists():
            return self._root

        root = Path(tempfile.mkdtemp(prefix="coderrr-sandbox-"))
        os.chmod(root, 0o700)
        target = root / self.workspace.name
        shutil.copytree(
            self.workspace,
            target,
            ignore=COPY_EXCLUDES,
            symlinks=False,
            dirs_exist_ok=True,
        )
        self._root = target
        return target

    def refresh(self) -> None:
        """Discard the scratch copy so the next run picks up current files."""
        self.cleanup()

    def cleanup(self) -> None:
        if self._root is None:
            return
        parent = self._root.parent
        with contextlib.suppress(OSError):
            shutil.rmtree(parent, ignore_errors=True)
        self._root = None

    # -- execution -------------------------------------------------------

    def _preexec(self) -> None:  # pragma: no cover - POSIX only, runs in child
        """Apply resource limits in the child before exec.

        Deliberately does not set RLIMIT_NPROC: that limit is per *real UID* and
        counts every process the user already has running, so a modest value
        makes fork fail instantly on a normally-loaded desktop. Process-count
        limiting belongs to the Docker tier's --pids-limit, which is scoped to
        the container.
        """
        try:
            import resource
        except ImportError:
            return
        os.setsid()  # own process group, so timeout kills the whole tree
        if self.memory_mb:
            limit = self.memory_mb * 1024 * 1024
            with contextlib.suppress(ValueError, OSError):
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    async def run(
        self,
        command: str,
        *,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        cwd = self._ensure_root()
        limit = timeout or self.default_timeout
        started = time.monotonic()

        child_env = {**os.environ, **(env or {})}
        child_env["CODERRR_SANDBOX"] = "scratch"

        kwargs: dict[str, object] = {}
        if os.name == "posix":
            kwargs["preexec_fn"] = self._preexec

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            env=child_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            **kwargs,  # type: ignore[arg-type]
        )

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=limit)
        except asyncio.TimeoutError:
            timed_out = True
            _kill_tree(process)
            with contextlib.suppress(Exception):
                await process.wait()
            stdout_b, stderr_b = b"", b""

        return ExecResult(
            command=command,
            exit_code=process.returncode if process.returncode is not None else -1,
            stdout=stdout_b.decode("utf-8", "replace"),
            stderr=stderr_b.decode("utf-8", "replace"),
            duration=time.monotonic() - started,
            timed_out=timed_out,
            tier=self.tier,
        )


def _kill_tree(process: asyncio.subprocess.Process) -> None:
    """Kill the whole process group, not just the shell we spawned."""
    if process.returncode is not None:
        return
    if os.name == "posix":
        import signal

        with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            return
    with contextlib.suppress(ProcessLookupError, OSError):
        process.kill()
