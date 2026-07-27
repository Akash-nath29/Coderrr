"""Spec parsing, storage, and the gitignore split."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from coderrr.spec.models import Spec, Task, TaskStatus
from coderrr.spec.parser import parse_tasks, render_tasks
from coderrr.spec.store import SpecStore, slugify

CANONICAL = """\
# Tasks: Add authentication

## T001: Create the user model
- **status**: done
- **files**: `src/models.py`, `src/db.py`
- **depends**: none
- **acceptance**: model imports cleanly

## T002: Add the login endpoint
- **status**: pending
- **files**: `src/routes.py`
- **depends**: T001
- **acceptance**: POST /login returns a token
"""


def test_parses_canonical_format() -> None:
    title, tasks = parse_tasks(CANONICAL)
    assert title == "Add authentication"
    assert [t.id for t in tasks] == ["T001", "T002"]
    assert tasks[0].status is TaskStatus.DONE
    assert tasks[0].files == ["src/models.py", "src/db.py"]
    assert tasks[1].depends == ["T001"]


def test_round_trips() -> None:
    title, tasks = parse_tasks(CANONICAL)
    title2, tasks2 = parse_tasks(render_tasks(title, tasks))
    assert title2 == title
    assert [t.model_dump() for t in tasks2] == [t.model_dump() for t in tasks]


# The parser must survive a human editing tasks.md by hand.
HAND_EDITED = [
    pytest.param("## T001: Bare task\n", id="no-fields"),
    pytest.param("## T001 - Dash separator\n- status: pending\n", id="unbolded"),
    pytest.param("## T001: X\n* **status** : done\n", id="asterisk-and-spaces"),
    pytest.param("### T001: Deeper heading\n- **status**: wip\n", id="h3"),
    pytest.param("## t001: lowercase id\n- **status**: TODO\n", id="lowercase"),
    pytest.param(
        "## T001: X\n- **status**: done\n- **unknown_field**: whatever\n", id="extra-field"
    ),
    pytest.param("## T001: X\n- **files**: none\n- **depends**: n/a\n", id="none-values"),
]


@pytest.mark.parametrize("markdown", HAND_EDITED)
def test_forgiving_of_hand_edits(markdown: str) -> None:
    _, tasks = parse_tasks(markdown)
    assert len(tasks) == 1
    assert tasks[0].id == "T001"


def test_status_synonyms() -> None:
    _, tasks = parse_tasks(
        "## T001: a\n- **status**: wip\n"
        "## T002: b\n- **status**: completed\n"
        "## T003: c\n- **status**: stuck\n"
        "## T004: d\n- **status**: nonsense\n"
    )
    assert [t.status for t in tasks] == [
        TaskStatus.IN_PROGRESS,
        TaskStatus.DONE,
        TaskStatus.BLOCKED,
        TaskStatus.PENDING,
    ]


def test_prose_yields_no_tasks() -> None:
    _, tasks = parse_tasks("Some notes about the project.\n\nNothing structured here.")
    assert tasks == []


# -- model behaviour -----------------------------------------------------


def test_next_actionable_respects_dependencies() -> None:
    spec = Spec(
        slug="001-x",
        title="X",
        tasks=[
            Task(id="T001", title="first", status=TaskStatus.PENDING),
            Task(id="T002", title="second", depends=["T001"]),
        ],
    )
    assert spec.next_actionable().id == "T001"

    spec.tasks[0].status = TaskStatus.DONE
    assert spec.next_actionable().id == "T002"


def test_progress_and_completion() -> None:
    spec = Spec(
        slug="001-x",
        title="X",
        tasks=[
            Task(id="T001", title="a", status=TaskStatus.DONE),
            Task(id="T002", title="b", status=TaskStatus.BLOCKED),
        ],
    )
    assert spec.progress() == (1, 2)
    assert spec.is_complete  # every task is terminal


# -- store ---------------------------------------------------------------


def test_create_numbers_sequentially(workspace: Path) -> None:
    store = SpecStore(workspace)
    first = store.create("Add authentication")
    second = store.create("Add billing")
    assert first.name == "001-add-authentication"
    assert second.name == "002-add-billing"


def test_create_writes_three_documents(workspace: Path) -> None:
    store = SpecStore(workspace)
    ref = store.create("Add auth")
    for name in ("requirements.md", "design.md", "tasks.md"):
        assert (ref.path / name).exists()


def test_gitignore_separates_specs_from_transient_state(workspace: Path) -> None:
    """Specs are committed; cache and session are not."""
    store = SpecStore(workspace)
    store.ensure_layout()
    body = (workspace / ".coderrr" / ".gitignore").read_text()
    assert "cache/" in body
    assert "session/" in body
    assert "!specs/" in body


def test_find_by_number_slug_or_name(workspace: Path) -> None:
    store = SpecStore(workspace)
    ref = store.create("Add authentication")
    for identifier in ("001", "1", "add-authentication", ref.name):
        assert store.find(identifier) == ref
    assert store.find("nope") is None


def test_update_task_persists(workspace: Path) -> None:
    store = SpecStore(workspace)
    ref = store.create("X")
    store.write_document(ref, "tasks", CANONICAL)

    store.update_task(ref, "T002", status=TaskStatus.DONE, notes="shipped")
    reloaded = store.load(ref)
    task = reloaded.task("T002")
    assert task.status is TaskStatus.DONE
    assert task.notes == "shipped"


def test_update_unknown_task_raises(workspace: Path) -> None:
    store = SpecStore(workspace)
    ref = store.create("X")
    store.write_document(ref, "tasks", CANONICAL)
    with pytest.raises(KeyError, match="T999"):
        store.update_task(ref, "T999", status=TaskStatus.DONE)


# -- slugify -------------------------------------------------------------


@settings(max_examples=200, deadline=None)
@given(text=st.text(min_size=1, max_size=120))
def test_slug_is_always_filesystem_safe(text: str) -> None:
    slug = slugify(text)
    assert slug
    assert len(slug) <= 40
    assert all(c.isalnum() or c == "-" for c in slug)
    assert not slug.startswith("-") and not slug.endswith("-")
