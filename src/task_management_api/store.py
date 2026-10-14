from uuid import UUID

from task_management_api.models import Task


class TaskStore:
    """Small in-memory repository; replace with a database-backed adapter for persistence."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def get(self, task_id: UUID) -> Task | None:
        return self._tasks.get(task_id)

    def list(self) -> list[Task]:
        return list(self._tasks.values())

    def delete(self, task_id: UUID) -> bool:
        return self._tasks.pop(task_id, None) is not None
