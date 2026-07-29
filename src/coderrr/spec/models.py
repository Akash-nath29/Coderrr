"""Spec artifact models.

Only ``tasks.md`` is parsed into a structured model, because task status drives
the execution state machine. ``requirements.md`` and ``design.md`` stay as raw
markdown -- they are read by the model and by humans, and imposing a schema on
them would buy nothing while making them brittle to hand-editing.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"

    @property
    def marker(self) -> str:
        return {
            TaskStatus.PENDING: " ",
            TaskStatus.IN_PROGRESS: "~",
            TaskStatus.DONE: "x",
            TaskStatus.BLOCKED: "!",
        }[self]


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    files: list[str] = Field(default_factory=list)
    depends: list[str] = Field(default_factory=list)
    acceptance: str = ""
    notes: str = ""

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.DONE, TaskStatus.BLOCKED)


class Spec(BaseModel):
    """One feature's artifact set, living in ``.coderrr/specs/NNN-slug/``."""

    slug: str
    title: str
    requirements: str = ""
    design: str = ""
    tasks: list[Task] = Field(default_factory=list)

    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def next_actionable(self) -> Task | None:
        """First pending task whose dependencies are all done."""
        done = {t.id for t in self.tasks if t.status is TaskStatus.DONE}
        for task in self.tasks:
            if task.status is not TaskStatus.PENDING:
                continue
            if all(dep in done for dep in task.depends):
                return task
        return None

    def progress(self) -> tuple[int, int]:
        """(completed, total)"""
        return sum(1 for t in self.tasks if t.status is TaskStatus.DONE), len(self.tasks)

    @property
    def is_complete(self) -> bool:
        return bool(self.tasks) and all(t.is_terminal for t in self.tasks)
