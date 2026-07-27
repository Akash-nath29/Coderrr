"""Shared fixtures.

Every fixture is rooted in a tmp_path. Nothing in the suite may touch the real
``~/.coderrr`` -- v1's tests permanently incremented the user's own counters.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.fakes import RecordingConsole

from coderrr.agent.modes import AgentMode
from coderrr.config import Config
from coderrr.sandbox.scratch import ScratchSandbox
from coderrr.skills.loader import SkillManager
from coderrr.spec.store import SpecStore
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ToolRegistry
from coderrr.verify import NullVerifier


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("# Demo project\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text(
        'def greet(name):\n    return f"hello {name}"\n', encoding="utf-8"
    )
    return root


@pytest.fixture
def config() -> Config:
    cfg = Config()
    cfg.verify.mode = "off"
    cfg.ui.stream = False
    cfg.agent.max_tool_turns = 12
    return cfg


@pytest.fixture
def ui() -> RecordingConsole:
    return RecordingConsole()


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def ctx(workspace: Path, config: Config, ui: RecordingConsole) -> ToolContext:
    store = SpecStore(workspace)
    store.ensure_layout()
    return ToolContext(
        workspace=workspace,
        config=config,
        ui=ui,  # type: ignore[arg-type]
        specs=store,
        sandbox=ScratchSandbox(workspace, default_timeout=30),
        skills=SkillManager(config=config.skills),
        verifier=NullVerifier(),
        mode=AgentMode.PLANNING,
    )


@pytest.fixture
def exec_ctx(ctx: ToolContext) -> ToolContext:
    ctx.mode = AgentMode.EXECUTION
    return ctx
