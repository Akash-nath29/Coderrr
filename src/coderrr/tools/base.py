"""Tool interface and the execution context handed to every tool."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel

from coderrr.agent.modes import AgentMode
from coderrr.llm.types import ToolClass, ToolSpec

if TYPE_CHECKING:
    from coderrr.config import Config
    from coderrr.mcp.manager import McpManager
    from coderrr.sandbox.base import Sandbox
    from coderrr.skills.loader import SkillManager
    from coderrr.spec.store import SpecRef, SpecStore
    from coderrr.ui.console import Console
    from coderrr.verify import Verifier


@dataclass
class ToolResult:
    """What a tool hands back to the model."""

    content: str
    is_error: bool = False
    #: Short one-line summary for the terminal; falls back to a content excerpt.
    display: str = ""

    @classmethod
    def ok(cls, content: str, *, display: str = "") -> ToolResult:
        return cls(content=content, is_error=False, display=display)

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(content=message, is_error=True, display=message.splitlines()[0])


def _empty_mcp() -> McpManager:
    """A manager with no servers.

    Imported here rather than at module scope because :mod:`coderrr.mcp.manager`
    imports this module for :class:`Tool`. By the time a context is built, this
    module is fully loaded, so the cycle never closes.
    """
    from coderrr.config import McpConfig
    from coderrr.mcp.manager import McpManager

    return McpManager(config=McpConfig())


@dataclass
class ToolContext:
    """Everything a tool is allowed to touch.

    Tools receive this rather than reaching for globals, which is what makes the
    whole surface testable with a temp directory and a fake console.
    """

    workspace: Path
    config: Config
    ui: Console
    specs: SpecStore
    sandbox: Sandbox
    skills: SkillManager
    verifier: Verifier
    mode: AgentMode = AgentMode.PLANNING

    #: Connected MCP servers, when any are configured. Defaults to an empty
    #: manager so every existing construction site keeps working unchanged.
    mcp: McpManager = field(default_factory=lambda: _empty_mcp())

    #: Spec currently being planned or executed.
    active_spec: SpecRef | None = None
    #: Set by ask_review when the user declines to continue.
    aborted: bool = False
    #: Free-form per-session scratch space for tools that need continuity.
    scratch: dict[str, Any] = field(default_factory=dict)

    def require_spec(self) -> SpecRef:
        if self.active_spec is None:
            raise ValueError("No active spec. Create one with write_spec before using this tool.")
        return self.active_spec


class Tool(ABC):
    """Base class for every tool.

    ``Input`` is a pydantic model; its JSON Schema is what the provider sees, so
    field descriptions are the tool's real documentation. Read and write tools
    carry their guidance here rather than in the system prompt -- only system
    tools are documented there.

    :meth:`spec` and :meth:`validate_input` are instance methods rather than
    class-level ones so a tool discovered at runtime can supply both. An MCP
    tool's name, description and schema arrive from a server during the session
    and differ per instance, so there is no class to hang them on.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    klass: ClassVar[ToolClass]
    Input: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, inp: Any, ctx: ToolContext) -> ToolResult:
        """Execute. ``inp`` is whatever :meth:`validate_input` returned."""

    def spec(self) -> ToolSpec:
        schema = self.Input.model_json_schema()
        # Providers only need the object shape; the generated title is noise.
        schema.pop("title", None)
        return ToolSpec(
            name=self.name,
            description=self.description.strip(),
            input_schema=schema,
            klass=self.klass,
        )

    def validate_input(self, raw: dict[str, Any]) -> Any:
        """Coerce the model's raw arguments, raising ``ValidationError`` if bad."""
        return self.Input.model_validate(raw)
