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
    """

    name: ClassVar[str]
    description: ClassVar[str]
    klass: ClassVar[ToolClass]
    Input: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, inp: Any, ctx: ToolContext) -> ToolResult:
        """Execute. ``inp`` is a validated instance of ``self.Input``."""

    @classmethod
    def spec(cls) -> ToolSpec:
        schema = cls.Input.model_json_schema()
        # Providers only need the object shape; the generated title is noise.
        schema.pop("title", None)
        return ToolSpec(
            name=cls.name,
            description=cls.description.strip(),
            input_schema=schema,
            klass=cls.klass,
        )
