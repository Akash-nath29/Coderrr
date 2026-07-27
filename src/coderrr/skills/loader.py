"""Ephemeral skill loading: pull, use, delete.

Skills are removed after the task that needed them completes. Coderrr requires
network for inference regardless, so re-fetching costs a round trip and nothing
else, and it guarantees the agent always runs against current guidance.

Only the markdown guidance is fetched. Skill directories in the registry also
contain a ``tools/`` directory of Python scripts -- a v1 design where the CLI
downloaded and executed them. v2 does not, because that put unreviewed remote
code on the user's machine outside any sandbox. Registry guidance that still
instructs the reader to run ``python tools/<name>.py`` therefore refers to
scripts v2 will not provide; those documents need rewriting against Coderrr's
own tool set.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from coderrr.config import SkillsConfig
from coderrr.skills.registry import SkillError, SkillIndex, SkillInfo, fetch_index

#: Guidance documents are prose; anything larger is not a skill.
MAX_SKILL_BYTES = 256 * 1024

#: Skills.md opens with YAML frontmatter carrying name and description. The
#: registry already supplies both, so the body is what goes into context.
_FRONTMATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    return _FRONTMATTER.sub("", text, count=1).lstrip("\n")


@dataclass
class LoadedSkill:
    info: SkillInfo
    content: str
    path: Path | None = None


@dataclass
class SkillManager:
    """Fetches, holds, and disposes of skills for one session."""

    config: SkillsConfig
    _index: SkillIndex | None = None
    _loaded: dict[str, LoadedSkill] = field(default_factory=dict)
    _scratch: Path | None = None

    # -- registry --------------------------------------------------------

    async def index(self, *, refresh: bool = False) -> SkillIndex:
        if self._index is None or refresh:
            self._index = await fetch_index(self.config.registry)
        return self._index

    async def search(self, query: str, *, limit: int = 5) -> list[SkillInfo]:
        return (await self.index()).search(query, limit=limit)

    # -- load / unload ---------------------------------------------------

    async def load(self, name: str) -> LoadedSkill:
        """Fetch a skill and hold it for the current task."""
        if existing := self._loaded.get(name):
            return existing

        index = await self.index()
        info = index.get(name)
        if info is None:
            available = ", ".join(sorted(index.skills)) or "none"
            raise SkillError(f"No skill named '{name}'. Available: {available}")

        content = strip_frontmatter(await self._download(info))

        path: Path | None = None
        if not self.config.ephemeral:
            path = self._persist(info, content)

        loaded = LoadedSkill(info=info, content=content, path=path)
        self._loaded[name] = loaded
        return loaded

    def unload(self, name: str) -> bool:
        """Drop a skill from context and remove any on-disk copy."""
        loaded = self._loaded.pop(name, None)
        if loaded is None:
            return False
        if loaded.path is not None:
            with contextlib.suppress(OSError):
                loaded.path.unlink()
        return True

    def unload_all(self) -> None:
        for name in list(self._loaded):
            self.unload(name)
        if self._scratch is not None:
            shutil.rmtree(self._scratch, ignore_errors=True)
            self._scratch = None

    @property
    def loaded(self) -> dict[str, LoadedSkill]:
        return dict(self._loaded)

    def context_block(self) -> str:
        """Render currently loaded skills for injection into the prompt."""
        if not self._loaded:
            return ""
        sections = [
            f"### Skill: {skill.info.label}\n{skill.content.strip()}"
            for skill in self._loaded.values()
        ]
        return "## Active Skills\n\n" + "\n\n".join(sections)

    # -- internals -------------------------------------------------------

    async def _download(self, info: SkillInfo) -> str:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(info.document_url)
                response.raise_for_status()
                raw = response.content
        except httpx.HTTPError as exc:
            raise SkillError(f"Could not download skill '{info.name}': {exc}") from exc

        if len(raw) > MAX_SKILL_BYTES:
            raise SkillError(
                f"Skill '{info.name}' is {len(raw)} bytes, over the {MAX_SKILL_BYTES} byte limit."
            )

        if info.sha256:
            digest = hashlib.sha256(raw).hexdigest()
            if digest != info.sha256.lower():
                raise SkillError(
                    f"Checksum mismatch for skill '{info.name}'. "
                    f"Expected {info.sha256}, got {digest}. Refusing to load."
                )

        return raw.decode("utf-8", "replace")

    def _persist(self, info: SkillInfo, content: str) -> Path:
        if self._scratch is None:
            self._scratch = Path(tempfile.mkdtemp(prefix="coderrr-skills-"))
        target = self._scratch / f"{info.name}.md"
        target.write_text(content, encoding="utf-8")
        return target
