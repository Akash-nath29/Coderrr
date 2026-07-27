"""Tier 2 sandbox: run inside a container.

Shells out to the ``docker`` CLI rather than taking the Docker SDK as a
dependency -- one less package for every user, and the CLI is the more stable
interface.

Unlike the scratch tier this genuinely isolates the filesystem and, with
``network=False``, the network too.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import time
from pathlib import Path

from coderrr.sandbox.base import ExecResult, SandboxTier


def docker_available() -> bool:
    """True when a usable docker CLI and daemon are present."""
    if shutil.which("docker") is None:
        return False
    try:
        result = os.system("docker info >/dev/null 2>&1")
        return result == 0
    except OSError:  # pragma: no cover
        return False


class DockerSandbox:
    """Runs commands in a container with the workspace mounted."""

    tier = SandboxTier.DOCKER

    def __init__(
        self,
        workspace: Path,
        *,
        image: str = "python:3.12-slim",
        default_timeout: int = 300,
        network: bool = False,
        memory_mb: int = 2048,
    ) -> None:
        self.workspace = workspace
        self.image = image
        self.default_timeout = default_timeout
        self.network = network
        self.memory_mb = memory_mb

    def _docker_argv(self, command: str, timeout: int) -> list[str]:
        argv = [
            "docker",
            "run",
            "--rm",
            "--interactive=false",
            f"--memory={self.memory_mb}m",
            "--pids-limit=512",
            # Drop every capability; a build does not need any of them.
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--workdir=/workspace",
            "--volume",
            f"{self.workspace.resolve()}:/workspace",
        ]
        if not self.network:
            argv.append("--network=none")
        argv.extend(["--env", "CODERRR_SANDBOX=docker"])
        argv.extend([self.image, "sh", "-lc", command])
        return argv

    async def run(
        self,
        command: str,
        *,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        limit = timeout or self.default_timeout
        argv = self._docker_argv(command, limit)

        for key, value in (env or {}).items():
            # Insert before the image argument.
            index = argv.index(self.image)
            argv[index:index] = ["--env", f"{key}={value}"]

        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=limit)
        except asyncio.TimeoutError:
            timed_out = True
            with contextlib.suppress(ProcessLookupError, OSError):
                process.kill()
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

    def cleanup(self) -> None:
        # `--rm` means containers clean themselves up.
        return
