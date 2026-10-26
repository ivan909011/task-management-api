from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from task_management_api.main import create_app
from task_management_api.store import TaskStore

CreateTask = Callable[..., dict[str, Any]]


@pytest.fixture
def store() -> TaskStore:
    return TaskStore()


@pytest.fixture
def client(store: TaskStore) -> TestClient:
    # A fresh app and store per test keeps tests independent of execution order.
    return TestClient(create_app(store))


@pytest.fixture
def create_task(client: TestClient) -> CreateTask:
    def _create(title: str = "Task", **fields: Any) -> dict[str, Any]:
        response = client.post("/tasks", json={"title": title, **fields})
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    return _create
