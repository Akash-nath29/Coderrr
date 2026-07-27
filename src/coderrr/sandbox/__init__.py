"""Sandbox selection.

``tier = "auto"`` prefers Docker when it is available and falls back to the
scratch tier otherwise, so the agent always has *some* way to run what it wrote.
The chosen tier is reported to the user rather than assumed.
"""

from __future__ import annotations

from pathlib import Path

from coderrr.config import SandboxConfig
from coderrr.sandbox.base import ExecResult, Sandbox, SandboxTier
from coderrr.sandbox.docker import DockerSandbox, docker_available
from coderrr.sandbox.scratch import ScratchSandbox

__all__ = [
    "DockerSandbox",
    "ExecResult",
    "Sandbox",
    "SandboxTier",
    "ScratchSandbox",
    "build_sandbox",
    "docker_available",
]


def build_sandbox(workspace: Path, config: SandboxConfig) -> Sandbox:
    """Construct the sandbox implied by config, degrading gracefully."""
    if config.tier == "docker":
        if not docker_available():
            raise RuntimeError(
                "sandbox.tier is 'docker' but Docker is not available. "
                "Start Docker, or set sandbox.tier = 'auto'."
            )
        return DockerSandbox(
            workspace,
            image=config.image,
            default_timeout=config.timeout,
            network=config.network,
        )

    if config.tier == "auto" and docker_available():
        return DockerSandbox(
            workspace,
            image=config.image,
            default_timeout=config.timeout,
            network=config.network,
        )

    return ScratchSandbox(workspace, default_timeout=config.timeout)
