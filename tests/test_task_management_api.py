from fastapi.testclient import TestClient

from task_management_api.main import create_app
from task_management_api.store import TaskStore


def client() -> TestClient:
    return TestClient(create_app(TaskStore()))


def test_create_and_read_task() -> None:
    api = client()
    created = api.post("/tasks", json={"title": "Ship API", "description": "First version"})

    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Ship API"
    assert task["status"] == "pending"
    assert api.get(f"/tasks/{task['id']}").json()["id"] == task["id"]


def test_validation_and_missing_task_errors() -> None:
    api = client()

    assert api.post("/tasks", json={"title": "   "}).status_code == 422
    assert api.get("/tasks/not-a-uuid").status_code == 422
    assert api.get("/tasks/00000000-0000-0000-0000-000000000000").status_code == 404


def test_filter_update_delete_and_pagination() -> None:
    api = client()
    ids = [api.post("/tasks", json={"title": f"Task {n}"}).json()["id"] for n in range(3)]

    updated = api.patch(f"/tasks/{ids[0]}", json={"status": "done"})
    assert updated.status_code == 200
    assert [task["id"] for task in api.get("/tasks", params={"status": "done"}).json()] == [ids[0]]
    assert len(api.get("/tasks", params={"limit": 1, "offset": 1}).json()) == 1
    assert api.delete(f"/tasks/{ids[0]}").status_code == 204
    assert api.delete(f"/tasks/{ids[0]}").status_code == 404


def test_health_endpoint() -> None:
    assert client().get("/health").json() == {"status": "ok"}
