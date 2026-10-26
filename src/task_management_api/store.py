from collections.abc import Mapping
from threading import Lock
from typing import Any, Protocol
from uuid import UUID

from task_management_api.models import Task, TaskPage, TaskStatus, utc_now


class TaskRepository(Protocol):
    """Storage contract used by the HTTP layer.

    Every method is a single atomic operation, so a database-backed
    implementation can map each one to one statement or transaction.
    """

    def create(self, title: str, description: str) -> Task: ...

    def get(self, task_id: UUID) -> Task | None: ...

    def list(
        self, *, status: TaskStatus | None = None, limit: int = 20, offset: int = 0
    ) -> TaskPage: ...

    def update(self, task_id: UUID, changes: Mapping[str, Any]) -> Task | None: ...

    def delete(self, task_id: UUID) -> bool: ...


class TaskStore:
    """Thread-safe in-memory implementation of ``TaskRepository``.

    FastAPI runs sync endpoints in a thread pool, so concurrent requests can
    touch the store at the same time. A lock makes each operation atomic; in
    particular ``update`` reads and writes under the same lock, so a PATCH can
    never re-insert a task that a concurrent DELETE has just removed.
    """

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}
        self._lock = Lock()

    def create(self, title: str, description: str) -> Task:
        now = utc_now()
        task = Task(title=title, description=description, created_at=now, updated_at=now)
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: UUID) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(
        self, *, status: TaskStatus | None = None, limit: int = 20, offset: int = 0
    ) -> TaskPage:
        with self._lock:
            # dict preserves insertion order, which is creation order: listings are stable.
            tasks = list(self._tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return TaskPage(items=tasks[offset : offset + limit], total=len(tasks))

    def update(self, task_id: UUID, changes: Mapping[str, Any]) -> Task | None:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                return None
            # model_validate (not model_copy) so the new state is checked against Task's rules.
            updated = Task.model_validate(
                {**current.model_dump(), **changes, "updated_at": utc_now()}
            )
            self._tasks[task_id] = updated
            return updated

    def delete(self, task_id: UUID) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None
