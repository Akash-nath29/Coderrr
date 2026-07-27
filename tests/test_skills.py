"""Skill registry, integrity checking, and ephemeral lifecycle.

Fixtures mirror the live registry at
https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/registry.json
"""

from __future__ import annotations

import hashlib

import httpx
import pytest
import respx

from coderrr.config import DEFAULT_SKILLS_REGISTRY, SkillsConfig
from coderrr.skills.loader import SkillManager, strip_frontmatter
from coderrr.skills.registry import SkillError, SkillIndex, fetch_index

REGISTRY_URL = "https://example.test/registry.json"

# Verbatim shape of two live entries.
INDEX = {
    "version": "1.0",
    "registry_url": REGISTRY_URL,
    "skills": {
        "web-scraper": {
            "name": "web-scraper",
            "displayName": "Web Scraper",
            "description": (
                "Fetch, parse, and extract content from web pages. Use this skill "
                "when the user asks to scrape websites, extract text from URLs, "
                "parse HTML content, download web pages, or analyze website content."
            ),
            "version": "1.0.0",
            "author": "Akash Nath",
            "repository": "https://github.com/Akash-nath29/coderrr-skills",
            "download_url": "https://example.test/skills/web-scraper",
            "tools": ["fetch_page", "extract_text"],
            "tags": ["web", "scraping", "http", "html", "parsing"],
        },
        "pdf": {
            "name": "pdf",
            "displayName": "PDF Toolkit",
            "description": (
                "Comprehensive PDF toolkit for document manipulation. Use this skill "
                "when the user asks to extract text from PDFs, create PDF documents, "
                "merge or split PDFs, or analyze PDF structure."
            ),
            "version": "1.0.0",
            "author": "Akash Nath",
            "download_url": "https://example.test/skills/pdf",
            "tools": ["extract_pdf", "create_pdf", "merge_pdf"],
            "tags": ["pdf", "document", "extract", "merge", "split"],
        },
    },
}

# Skills.md carries YAML frontmatter duplicating name and description.
SKILL_BODY = """\
---
name: web-scraper
description: Fetch, parse, and extract content from web pages.
---

This skill enables fetching and parsing web content.

## Approach

Chain fetch_page with extract_text for readable content.
"""


def make_manager(**overrides: object) -> SkillManager:
    config = SkillsConfig(registry=REGISTRY_URL, ephemeral=True, **overrides)  # type: ignore[arg-type]
    return SkillManager(config=config)


def mock_registry() -> None:
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=INDEX))


def mock_skill(name: str = "web-scraper", body: str = SKILL_BODY) -> None:
    respx.get(f"https://example.test/skills/{name}/Skills.md").mock(
        return_value=httpx.Response(200, text=body)
    )


# -- configuration -------------------------------------------------------


def test_default_registry_points_at_registry_json() -> None:
    """The live index is registry.json, not index.json."""
    assert DEFAULT_SKILLS_REGISTRY.endswith("/registry.json")
    assert "Akash-nath29/coderrr-skills" in DEFAULT_SKILLS_REGISTRY


# -- index parsing -------------------------------------------------------


def test_parses_live_schema() -> None:
    index = SkillIndex.parse(INDEX)
    assert index.version == "1.0"

    skill = index.get("web-scraper")
    assert skill is not None
    assert skill.download_url == "https://example.test/skills/web-scraper"
    assert skill.entry == "Skills.md"
    assert skill.document_url == "https://example.test/skills/web-scraper/Skills.md"
    assert skill.display_name == "Web Scraper"
    assert skill.label == "Web Scraper"
    assert skill.version == "1.0.0"
    assert skill.author == "Akash Nath"
    assert skill.tools == ("fetch_page", "extract_text")
    assert "scraping" in skill.tags


def test_accepts_plain_url_as_fallback() -> None:
    """A hand-written index may use `url` instead of `download_url`."""
    index = SkillIndex.parse(
        {"skills": {"x": {"url": "https://example.test/x", "description": "d"}}}
    )
    assert index.get("x").download_url == "https://example.test/x"


def test_entry_is_overridable() -> None:
    index = SkillIndex.parse(
        {"skills": {"x": {"download_url": "https://e.test/x", "entry": "SKILL.md"}}}
    )
    assert index.get("x").document_url == "https://e.test/x/SKILL.md"


def test_skips_entries_without_a_location() -> None:
    index = SkillIndex.parse(
        {
            "skills": {
                "good": {"download_url": "u", "description": "d"},
                "bad": {"description": "no url"},
                "worse": "not even a dict",
            }
        }
    )
    assert set(index.skills) == {"good"}


def test_label_falls_back_to_name() -> None:
    index = SkillIndex.parse({"skills": {"x": {"download_url": "u", "name": "x"}}})
    assert index.get("x").label == "x"


# -- search --------------------------------------------------------------


def test_search_ranks_exact_name_first() -> None:
    assert SkillIndex.parse(INDEX).search("pdf")[0].name == "pdf"


def test_search_shortlists_the_right_skill_for_ambiguous_phrasing() -> None:
    """Where a query shares generic verbs with several skills, the contract is
    that the right one is *in the shortlist* -- retrieval is agent-driven, and
    the model picks from candidates it can read descriptions for.

    "extract text from URLs" is genuinely ambiguous to a bag-of-words scorer:
    `extract` is a tag on pdf, while the real discriminator `urls` appears only
    in web-scraper's prose. Both are returned; ranking between them is not
    something this scorer promises.
    """
    hits = SkillIndex.parse(INDEX).search("extract text from URLs")
    assert {h.name for h in hits} >= {"web-scraper", "pdf"}


def test_search_matches_tags() -> None:
    assert SkillIndex.parse(INDEX).search("html")[0].name == "web-scraper"


def test_search_returns_nothing_unrelated() -> None:
    assert SkillIndex.parse(INDEX).search("quantum chromodynamics") == []


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("extract text from a pdf", "pdf"),
        ("merge two pdfs together", "pdf"),
        ("scrape a website for me", "web-scraper"),
        ("parse some html", "web-scraper"),
        ("download a web page", "web-scraper"),
    ],
)
def test_multiword_intents_rank_the_right_skill_first(query: str, expected: str) -> None:
    """Regression: scoring used to test `query in name`, which is never true for
    a phrase, so ranking collapsed onto generic description overlap and returned
    near-arbitrary results. Multi-word intent is the common case."""
    hits = SkillIndex.parse(INDEX).search(query)
    assert hits, f"no hits for {query!r}"
    assert hits[0].name == expected


def test_the_right_skill_wins_by_a_margin() -> None:
    """Not just correctly ordered -- clearly separated, so the model is not
    choosing between near-identical scores."""
    index = SkillIndex.parse(INDEX)
    scores = sorted(
        (s.matches("extract text from a pdf") for s in index.skills.values()),
        reverse=True,
    )
    assert scores[0] >= scores[1] * 3


def test_name_and_tag_hits_outweigh_description_hits() -> None:
    """Descriptions share generic verbs, so they must not dominate ranking."""
    index = SkillIndex.parse(INDEX)
    pdf = index.get("pdf")
    scraper = index.get("web-scraper")
    # "extract" appears in both descriptions; only pdf has it as a name/tag hit.
    assert pdf.matches("pdf") > scraper.matches("extract")


def test_stopwords_do_not_inflate_scores() -> None:
    index = SkillIndex.parse(INDEX)
    assert index.search("please can you help me with the thing") == []


def test_search_handles_empty_query() -> None:
    assert SkillIndex.parse(INDEX).search("   ") == []


def test_search_respects_limit() -> None:
    assert len(SkillIndex.parse(INDEX).search("use this skill", limit=1)) == 1


# -- fetch ---------------------------------------------------------------


@respx.mock
async def test_fetch_index() -> None:
    mock_registry()
    index = await fetch_index(REGISTRY_URL)
    assert set(index.skills) == {"web-scraper", "pdf"}


@respx.mock
async def test_registry_outage_raises() -> None:
    respx.get(REGISTRY_URL).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(SkillError, match="Could not reach"):
        await fetch_index(REGISTRY_URL)


@respx.mock
async def test_invalid_json_raises() -> None:
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, text="not json"))
    with pytest.raises(SkillError, match="invalid JSON"):
        await fetch_index(REGISTRY_URL)


@respx.mock
async def test_non_object_payload_raises() -> None:
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=[1, 2]))
    with pytest.raises(SkillError, match="must be a JSON object"):
        await fetch_index(REGISTRY_URL)


# -- frontmatter ---------------------------------------------------------


def test_strip_frontmatter_removes_yaml_block() -> None:
    stripped = strip_frontmatter(SKILL_BODY)
    assert stripped.startswith("This skill enables")
    assert "name: web-scraper" not in stripped


def test_strip_frontmatter_leaves_plain_markdown_alone() -> None:
    body = "# Heading\n\nBody text.\n"
    assert strip_frontmatter(body) == body


def test_strip_frontmatter_does_not_eat_later_rules() -> None:
    body = "# Title\n\nText\n\n---\n\nMore text\n"
    assert strip_frontmatter(body) == body


# -- load / unload -------------------------------------------------------


@respx.mock
async def test_load_fetches_document_and_strips_frontmatter() -> None:
    mock_registry()
    mock_skill()

    manager = make_manager()
    skill = await manager.load("web-scraper")

    assert skill.content.startswith("This skill enables")
    assert "web-scraper" in manager.loaded
    assert skill.info.label == "Web Scraper"


@respx.mock
async def test_load_is_idempotent() -> None:
    mock_registry()
    route = respx.get("https://example.test/skills/web-scraper/Skills.md").mock(
        return_value=httpx.Response(200, text=SKILL_BODY)
    )

    manager = make_manager()
    await manager.load("web-scraper")
    await manager.load("web-scraper")
    assert route.call_count == 1


@respx.mock
async def test_unload_all_clears_context() -> None:
    mock_registry()
    mock_skill()

    manager = make_manager()
    await manager.load("web-scraper")
    manager.unload_all()

    assert manager.loaded == {}
    assert manager.context_block() == ""


@respx.mock
async def test_unknown_skill_lists_alternatives() -> None:
    mock_registry()
    manager = make_manager()
    with pytest.raises(SkillError, match="Available: pdf, web-scraper"):
        await manager.load("does-not-exist")


@respx.mock
async def test_context_block_uses_display_name() -> None:
    mock_registry()
    mock_skill()

    manager = make_manager()
    await manager.load("web-scraper")
    block = manager.context_block()

    assert "Active Skills" in block
    assert "Skill: Web Scraper" in block
    assert "fetch_page" in block


# -- integrity -----------------------------------------------------------


@respx.mock
async def test_checksum_mismatch_refuses_to_load() -> None:
    index = {
        "skills": {
            "pinned": {
                "description": "d",
                "download_url": "https://example.test/skills/pinned",
                "sha256": "0" * 64,
            }
        }
    }
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=index))
    mock_skill("pinned", "tampered content")

    with pytest.raises(SkillError, match="Checksum mismatch"):
        await make_manager().load("pinned")


@respx.mock
async def test_matching_checksum_loads() -> None:
    body = "# Pinned\n\nGuidance.\n"
    index = {
        "skills": {
            "pinned": {
                "description": "d",
                "download_url": "https://example.test/skills/pinned",
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
            }
        }
    }
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=index))
    mock_skill("pinned", body)

    assert (await make_manager().load("pinned")).content == body


@respx.mock
async def test_oversized_skill_is_refused() -> None:
    index = {
        "skills": {"big": {"description": "d", "download_url": "https://example.test/skills/big"}}
    }
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=index))
    mock_skill("big", "x" * (300 * 1024))

    with pytest.raises(SkillError, match="over the"):
        await make_manager().load("big")


@respx.mock
async def test_missing_document_raises() -> None:
    mock_registry()
    respx.get("https://example.test/skills/pdf/Skills.md").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    with pytest.raises(SkillError, match="Could not download"):
        await make_manager().load("pdf")
