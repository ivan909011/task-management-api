from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from task_management_api.models import TaskStatus
from task_management_api.store import TaskStore


def test_create_sets_matching_timestamps(store: TaskStore) -> None:
    task = store.create(title="a", description="")

    assert task.created_at == task.updated_at
    assert store.get(task.id) == task


def test_update_missing_task_returns_none_and_does_not_insert(store: TaskStore) -> None:
    assert store.update(uuid4(), {"title": "ghost"}) is None
    assert store.list().total == 0


def test_update_validates_the_new_state(store: TaskStore) -> None:
    task = store.create(title="a", description="")

    with pytest.raises(ValidationError):
        store.update(task.id, {"title": None})

    assert store.get(task.id) == task


def test_update_after_delete_does_not_resurrect_task(store: TaskStore) -> None:
    # Regression: PATCH used to read the task, then write it back unconditionally,
    # so a DELETE landing in between was silently undone.
    task = store.create(title="a", description="")
    store.delete(task.id)

    assert store.update(task.id, {"status": TaskStatus.DONE}) is None
    assert store.get(task.id) is None


def test_list_total_counts_all_matches_not_just_the_page(store: TaskStore) -> None:
    for n in range(5):
        store.create(title=f"t{n}", description="")

    page = store.list(limit=2, offset=1)

    assert [task.title for task in page.items] == ["t1", "t2"]
    assert page.total == 5


def test_concurrent_updates_and_deletes_leave_store_consistent(store: TaskStore) -> None:
    tasks = [store.create(title=f"t{n}", description="") for n in range(200)]

    def update(task_id: UUID) -> None:
        store.update(task_id, {"status": TaskStatus.DONE})

    with ThreadPoolExecutor(max_workers=16) as pool:
        for task in tasks:
            pool.submit(update, task.id)
            pool.submit(store.delete, task.id)

    # Whatever the interleaving, every task was deleted exactly once and none came back.
    assert store.list(limit=1000).total == 0
