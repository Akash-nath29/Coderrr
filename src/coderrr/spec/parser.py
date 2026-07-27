"""Round-trip ``tasks.md`` between markdown and :class:`Task` models.

The user editing ``tasks.md`` by hand to steer the agent is a first-class
affordance, so the parser is deliberately forgiving: bold markers are optional,
field order is free, unknown fields are ignored, and a task missing everything
but a heading still parses.
"""

from __future__ import annotations

import re

from coderrr.spec.models import Task, TaskStatus

# "## T001: Create scaffold"  /  "## T001 - Create scaffold"  /  "### T1 Create"
_TASK_HEADING = re.compile(
    r"^#{2,3}\s+(?P<id>T\d+)\s*[:\-—]?\s*(?P<title>.*)$",
    re.IGNORECASE,
)

# "- **status**: pending"  /  "- status: pending"  /  "* status : pending"
_FIELD = re.compile(
    r"^\s*[-*]\s*\*{0,2}(?P<key>[A-Za-z_]+)\*{0,2}\s*:\s*(?P<value>.*)$",
)

_TITLE_HEADING = re.compile(r"^#\s+Tasks?\s*:\s*(?P<title>.+)$", re.IGNORECASE)

_LIST_SEPARATORS = re.compile(r"[,;]")
_NONE_VALUES = {"", "none", "n/a", "-", "null", "nil"}


def _split_list(value: str) -> list[str]:
    cleaned = value.strip().strip("`")
    if cleaned.lower() in _NONE_VALUES:
        return []
    parts = (p.strip().strip("`").strip() for p in _LIST_SEPARATORS.split(cleaned))
    return [p for p in parts if p and p.lower() not in _NONE_VALUES]


def _parse_status(value: str) -> TaskStatus:
    normalized = value.strip().strip("`").lower().replace("-", "_").replace(" ", "_")
    try:
        return TaskStatus(normalized)
    except ValueError:
        # Tolerate common hand-written variants.
        if normalized in {"todo", "not_started", "open"}:
            return TaskStatus.PENDING
        if normalized in {"doing", "wip", "active", "in_flight"}:
            return TaskStatus.IN_PROGRESS
        if normalized in {"complete", "completed", "finished"}:
            return TaskStatus.DONE
        if normalized in {"stuck", "failed", "error"}:
            return TaskStatus.BLOCKED
        return TaskStatus.PENDING


def parse_tasks(markdown: str) -> tuple[str, list[Task]]:
    """Parse ``tasks.md``. Returns ``(document_title, tasks)``."""
    title = ""
    tasks: list[Task] = []
    current: dict[str, str] | None = None
    current_id = ""
    current_title = ""

    def flush() -> None:
        if current is None:
            return
        tasks.append(
            Task(
                id=current_id,
                title=current_title or current_id,
                status=_parse_status(current.get("status", "pending")),
                files=_split_list(current.get("files", "")),
                depends=_split_list(current.get("depends", "")),
                acceptance=current.get("acceptance", "").strip(),
                notes=current.get("notes", "").strip(),
            )
        )

    for line in markdown.splitlines():
        if not title and (match := _TITLE_HEADING.match(line)):
            title = match.group("title").strip()
            continue

        if match := _TASK_HEADING.match(line):
            flush()
            current_id = match.group("id").upper()
            current_title = match.group("title").strip()
            current = {}
            continue

        if current is not None and (match := _FIELD.match(line)):
            current[match.group("key").lower()] = match.group("value")

    flush()
    return title, tasks


def render_tasks(title: str, tasks: list[Task]) -> str:
    """Render tasks back to markdown in the canonical format."""
    lines = [f"# Tasks: {title}", ""]

    if not tasks:
        lines.append("_No tasks defined yet._")
        lines.append("")
        return "\n".join(lines)

    done, total = sum(1 for t in tasks if t.status is TaskStatus.DONE), len(tasks)
    lines.append(f"_Progress: {done}/{total} complete._")
    lines.append("")

    for task in tasks:
        lines.append(f"## {task.id}: {task.title}")
        lines.append(f"- **status**: {task.status.value}")
        lines.append(
            f"- **files**: {', '.join(f'`{f}`' for f in task.files) if task.files else 'none'}"
        )
        lines.append(f"- **depends**: {', '.join(task.depends) if task.depends else 'none'}")
        if task.acceptance:
            lines.append(f"- **acceptance**: {task.acceptance}")
        if task.notes:
            lines.append(f"- **notes**: {task.notes}")
        lines.append("")

    return "\n".join(lines)
