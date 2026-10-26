from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from task_management_api.models import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH

CreateTask = Callable[..., dict[str, Any]]

MISSING_ID = "00000000-0000-0000-0000-000000000000"


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestCreate:
    def test_returns_created_task_with_defaults(self, client: TestClient) -> None:
        response = client.post("/tasks", json={"title": "  Ship API  ", "description": "v1"})

        assert response.status_code == 201
        task = response.json()
        assert task["title"] == "Ship API"  # surrounding whitespace is stripped
        assert task["description"] == "v1"
        assert task["status"] == "pending"
        assert task["created_at"] == task["updated_at"]
        assert response.headers["Location"] == f"/tasks/{task['id']}"

    def test_created_task_can_be_read_back(
        self, client: TestClient, create_task: CreateTask
    ) -> None:
        task = create_task("Read me")

        assert client.get(f"/tasks/{task['id']}").json() == task

    def test_status_cannot_be_set_on_create(self, client: TestClient) -> None:
        response = client.post("/tasks", json={"title": "x", "status": "done"})

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({}, id="missing-title"),
            pytest.param({"title": ""}, id="empty-title"),
            pytest.param({"title": "   "}, id="blank-title"),
            pytest.param({"title": None}, id="null-title"),
            pytest.param({"title": 123}, id="non-string-title"),
            pytest.param({"title": "x" * (TITLE_MAX_LENGTH + 1)}, id="title-too-long"),
            pytest.param(
                {"title": "x", "description": "d" * (DESCRIPTION_MAX_LENGTH + 1)},
                id="description-too-long",
            ),
            pytest.param({"title": "x", "priority": "high"}, id="unknown-field"),
        ],
    )
    def test_rejects_invalid_body(self, client: TestClient, body: dict[str, Any]) -> None:
        assert client.post("/tasks", json=body).status_code == 422

    def test_accepts_boundary_lengths(self, client: TestClient) -> None:
        body = {"title": "x" * TITLE_MAX_LENGTH, "description": "d" * DESCRIPTION_MAX_LENGTH}

        assert client.post("/tasks", json=body).status_code == 201


class TestRead:
    def test_missing_task_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/tasks/{MISSING_ID}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Task not found"}

    def test_malformed_id_returns_422(self, client: TestClient) -> None:
        assert client.get("/tasks/not-a-uuid").status_code == 422


class TestList:
    def test_empty(self, client: TestClient) -> None:
        response = client.get("/tasks")

        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"

    def test_returns_tasks_in_creation_order(
        self, client: TestClient, create_task: CreateTask
    ) -> None:
        ids = [create_task(f"Task {n}")["id"] for n in range(3)]

        assert [task["id"] for task in client.get("/tasks").json()] == ids

    def test_filters_by_status(self, client: TestClient, create_task: CreateTask) -> None:
        first, _, third = (create_task(f"Task {n}")["id"] for n in range(3))
        client.patch(f"/tasks/{first}", json={"status": "done"})
        client.patch(f"/tasks/{third}", json={"status": "done"})

        response = client.get("/tasks", params={"status": "done"})

        assert [task["id"] for task in response.json()] == [first, third]
        assert response.headers["X-Total-Count"] == "2"

    @pytest.mark.parametrize(
        ("limit", "offset", "expected_slice"),
        [
            (2, 0, slice(0, 2)),
            (2, 2, slice(2, 4)),
            (2, 4, slice(4, 5)),  # last, partial page
            (2, 10, slice(0, 0)),  # past the end
            (100, 0, slice(0, 5)),
        ],
    )
    def test_paginates(
        self,
        client: TestClient,
        create_task: CreateTask,
        limit: int,
        offset: int,
        expected_slice: slice,
    ) -> None:
        ids = [create_task(f"Task {n}")["id"] for n in range(5)]

        response = client.get("/tasks", params={"limit": limit, "offset": offset})

        assert [task["id"] for task in response.json()] == ids[expected_slice]
        # The total reflects every match, not just the current page.
        assert response.headers["X-Total-Count"] == "5"

    @pytest.mark.parametrize(
        "params",
        [
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"status": "archived"},
        ],
    )
    def test_rejects_invalid_query(self, client: TestClient, params: dict[str, Any]) -> None:
        assert client.get("/tasks", params=params).status_code == 422


class TestUpdate:
    def test_updates_only_given_fields(self, client: TestClient, create_task: CreateTask) -> None:
        task = create_task("Original", description="Keep me")

        response = client.patch(f"/tasks/{task['id']}", json={"status": "in_progress"})

        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "in_progress"
        assert updated["title"] == "Original"
        assert updated["description"] == "Keep me"
        assert updated["created_at"] == task["created_at"]
        assert parse_time(updated["updated_at"]) > parse_time(task["updated_at"])
        assert client.get(f"/tasks/{task['id']}").json() == updated

    def test_description_can_be_cleared_with_empty_string(
        self, client: TestClient, create_task: CreateTask
    ) -> None:
        task = create_task("x", description="old")

        response = client.patch(f"/tasks/{task['id']}", json={"description": ""})

        assert response.json()["description"] == ""

    @pytest.mark.parametrize("field", ["title", "description", "status"])
    def test_rejects_explicit_null_without_changing_the_task(
        self, client: TestClient, create_task: CreateTask, field: str
    ) -> None:
        # Regression: null used to pass validation and was written into the task.
        task = create_task("Keep me")

        response = client.patch(f"/tasks/{task['id']}", json={field: None})

        assert response.status_code == 422
        assert client.get(f"/tasks/{task['id']}").json() == task

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({}, id="no-fields"),
            pytest.param({"title": "  "}, id="blank-title"),
            pytest.param({"status": "archived"}, id="unknown-status"),
            pytest.param({"id": str(uuid4())}, id="read-only-field"),
            pytest.param({"created_at": "2020-01-01T00:00:00Z"}, id="read-only-timestamp"),
        ],
    )
    def test_rejects_invalid_body(
        self, client: TestClient, create_task: CreateTask, body: dict[str, Any]
    ) -> None:
        task = create_task()

        assert client.patch(f"/tasks/{task['id']}", json=body).status_code == 422

    def test_rejects_non_object_body(self, client: TestClient, create_task: CreateTask) -> None:
        task = create_task()

        assert client.patch(f"/tasks/{task['id']}", json=["status", "done"]).status_code == 422

    def test_missing_task_returns_404(self, client: TestClient) -> None:
        response = client.patch(f"/tasks/{MISSING_ID}", json={"status": "done"})

        assert response.status_code == 404


class TestDelete:
    def test_deletes_task(self, client: TestClient, create_task: CreateTask) -> None:
        task = create_task()

        response = client.delete(f"/tasks/{task['id']}")

        assert response.status_code == 204
        assert response.content == b""
        assert client.get(f"/tasks/{task['id']}").status_code == 404

    def test_second_delete_returns_404(self, client: TestClient, create_task: CreateTask) -> None:
        task = create_task()
        client.delete(f"/tasks/{task['id']}")

        assert client.delete(f"/tasks/{task['id']}").status_code == 404
