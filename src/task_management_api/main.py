from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status

from task_management_api.models import Task, TaskCreate, TaskStatus, TaskUpdate
from task_management_api.store import TaskStore


def create_app(store: TaskStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Task Management API",
        description="REST API for managing tasks.",
        version="0.1.0",
    )
    app.state.task_store = store or TaskStore()

    def get_store() -> TaskStore:
        return app.state.task_store

    Store = Annotated[TaskStore, Depends(get_store)]

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, tags=["tasks"])
    def create_task(payload: TaskCreate, store: Store) -> Task:
        return store.add(Task(title=payload.title, description=payload.description))

    @app.get("/tasks", response_model=list[Task], tags=["tasks"])
    def list_tasks(
        store: Store,
        task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Task]:
        tasks = store.list()
        if task_status is not None:
            tasks = [task for task in tasks if task.status == task_status]
        return tasks[offset : offset + limit]

    @app.get("/tasks/{task_id}", response_model=Task, tags=["tasks"])
    def get_task(task_id: UUID, store: Store) -> Task:
        task = store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.patch("/tasks/{task_id}", response_model=Task, tags=["tasks"])
    def update_task(task_id: UUID, payload: TaskUpdate, store: Store) -> Task:
        task = store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=422, detail="At least one field must be provided")
        updated = task.model_copy(update=changes)
        store.add(updated)
        return updated

    @app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
    def delete_task(task_id: UUID, store: Store) -> Response:
        if not store.delete(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
