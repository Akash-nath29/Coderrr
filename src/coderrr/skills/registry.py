"""Remote skill registry client.

A skill is a markdown document of workflow guidance -- *how* to approach a class
of task. Executable behaviour lives in :mod:`coderrr.tools`. That split is what
makes ephemeral skills safe to fetch: the worst a malicious skill can do is give
bad advice to a model whose tools are already gated.

The live index is ``registry.json`` in the coderrr-skills repository::

    {
      "version": "1.0",
      "skills": {
        "web-scraper": {
          "name": "web-scraper",
          "displayName": "Web Scraper",
          "description": "Fetch, parse, and extract content from web pages. Use
                          this skill when the user asks to scrape websites, ...",
          "version": "1.0.0",
          "author": "Akash Nath",
          "download_url": ".../main/skills/web-scraper",
          "tools": ["fetch_page", "extract_text"],
          "tags": ["web", "scraping", "http"]
        }
      }
    }

Each skill directory holds ``Skills.md`` (the guidance, with YAML frontmatter),
an optional ``requirements.txt``, and a ``tools/`` directory. v2 fetches only the
markdown -- see :mod:`coderrr.skills.loader` for why ``tools/`` is not used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

#: The guidance document inside each skill directory.
DEFAULT_ENTRY = "Skills.md"

_WORD = re.compile(r"[^a-z0-9]+")

#: Too common to discriminate between skills.
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "into",
        "this",
        "that",
        "use",
        "using",
        "when",
        "user",
        "asks",
        "want",
        "wants",
        "please",
        "make",
        "get",
        "all",
        "any",
        "how",
        "can",
        "you",
        "need",
        "help",
    }
)


def _tokenize(text: str) -> set[str]:
    return {
        token for token in _WORD.split(text.lower()) if len(token) > 2 and token not in _STOPWORDS
    }


class SkillError(RuntimeError):
    """Registry unreachable, skill missing, or integrity check failed."""


@dataclass(frozen=True)
class SkillInfo:
    name: str
    description: str
    download_url: str
    entry: str = DEFAULT_ENTRY
    display_name: str = ""
    version: str = ""
    author: str = ""
    tags: tuple[str, ...] = ()
    #: Tool script names declared by the skill. Recorded for provenance and for
    #: `coderrr skills search` output; v2 does not download or execute them.
    tools: tuple[str, ...] = ()
    #: Published integrity hash, when the registry provides one.
    sha256: str | None = None

    @property
    def label(self) -> str:
        return self.display_name or self.name

    @property
    def document_url(self) -> str:
        return f"{self.download_url.rstrip('/')}/{self.entry}"

    def matches(self, query: str) -> int:
        """Relevance score for a natural-language intent.

        Scored per query *token*, weighted by which field it hits. Matching the
        whole query against a short field instead -- ``query in self.name`` --
        looks reasonable but is never true for a multi-word intent like
        "extract text from a pdf", which collapses ranking onto generic
        description overlap and returns near-arbitrary results.

        Description hits are weighted lowest on purpose: registry descriptions
        are long and share verbs ("create", "extract", "analyze"), so they
        separate candidates poorly. Names and tags are what discriminate.
        """
        q = query.lower().strip()
        if not q:
            return 0

        tokens = _tokenize(q)
        if not tokens:
            return 0

        name_tokens = _tokenize(f"{self.name} {self.display_name}")
        tag_tokens = {t.lower() for t in self.tags}
        description_tokens = _tokenize(self.description)

        score = 0

        # Single-word queries that name the skill outright, e.g. "pdf".
        lowered = self.name.lower()
        if len(lowered) >= 3 and (lowered in q or q in lowered):
            score += 12

        for token in tokens:
            if token in name_tokens:
                score += 8
            elif token in tag_tokens:
                score += 5
            elif token in description_tokens:
                score += 1

        return score


@dataclass
class SkillIndex:
    version: str = ""
    skills: dict[str, SkillInfo] = field(default_factory=dict)

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> SkillIndex:
        entries = payload.get("skills") or {}
        skills: dict[str, SkillInfo] = {}

        for key, raw in entries.items():
            if not isinstance(raw, dict):
                continue
            # `download_url` is what the live registry publishes; `url` is
            # accepted so a simpler hand-written index also works.
            location = raw.get("download_url") or raw.get("url")
            if not location:
                continue

            skills[key] = SkillInfo(
                name=raw.get("name") or key,
                description=raw.get("description", ""),
                download_url=location,
                entry=raw.get("entry") or DEFAULT_ENTRY,
                display_name=raw.get("displayName") or raw.get("display_name") or "",
                version=str(raw.get("version") or ""),
                author=raw.get("author") or "",
                tags=tuple(raw.get("tags") or ()),
                tools=tuple(raw.get("tools") or ()),
                sha256=raw.get("sha256"),
            )

        return cls(version=str(payload.get("version") or ""), skills=skills)

    def search(self, query: str, *, limit: int = 5) -> list[SkillInfo]:
        scored = [(skill.matches(query), skill) for skill in self.skills.values()]
        ranked = sorted(scored, key=lambda pair: (-pair[0], pair[1].name))
        return [skill for score, skill in ranked if score > 0][:limit]

    def get(self, name: str) -> SkillInfo | None:
        return self.skills.get(name)


async def fetch_index(url: str, *, timeout: float = 15.0) -> SkillIndex:
    """Fetch and parse the registry index."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise SkillError(f"Could not reach the skill registry: {exc}") from exc
    except ValueError as exc:
        raise SkillError(f"Skill registry returned invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SkillError("Skill registry index must be a JSON object.")
    return SkillIndex.parse(payload)
