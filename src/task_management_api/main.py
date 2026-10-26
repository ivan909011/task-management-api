from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from task_management_api import __version__
from task_management_api.models import Task, TaskCreate, TaskStatus, TaskUpdate
from task_management_api.store import TaskRepository, TaskStore

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
TOTAL_COUNT_HEADER = "X-Total-Count"

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "Task not found"}
}


def get_repository(request: Request) -> TaskRepository:
    repository: TaskRepository = request.app.state.task_repository
    return repository


Repository = Annotated[TaskRepository, Depends(get_repository)]


def task_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


def create_app(repository: TaskRepository | None = None) -> FastAPI:
    """Build the application. Tests pass their own repository for isolation."""
    app = FastAPI(
        title="Task Management API",
        description="REST API for managing tasks.",
        version=__version__,
    )
    app.state.task_repository = repository if repository is not None else TaskStore()

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/tasks", status_code=status.HTTP_201_CREATED, tags=["tasks"])
    def create_task(payload: TaskCreate, repo: Repository, response: Response) -> Task:
        task = repo.create(title=payload.title, description=payload.description)
        response.headers["Location"] = f"/tasks/{task.id}"
        return task

    @app.get("/tasks", tags=["tasks"])
    def list_tasks(
        repo: Repository,
        response: Response,
        task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Task]:
        """List tasks in creation order. The total number of matches is in `X-Total-Count`."""
        page = repo.list(status=task_status, limit=limit, offset=offset)
        response.headers[TOTAL_COUNT_HEADER] = str(page.total)
        return page.items

    @app.get("/tasks/{task_id}", tags=["tasks"], responses=NOT_FOUND)
    def get_task(task_id: UUID, repo: Repository) -> Task:
        task = repo.get(task_id)
        if task is None:
            raise task_not_found()
        return task

    @app.patch("/tasks/{task_id}", tags=["tasks"], responses=NOT_FOUND)
    def update_task(task_id: UUID, payload: TaskUpdate, repo: Repository) -> Task:
        task = repo.update(task_id, payload.changes())
        if task is None:
            raise task_not_found()
        return task

    @app.delete(
        "/tasks/{task_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["tasks"],
        responses=NOT_FOUND,
    )
    def delete_task(task_id: UUID, repo: Repository) -> None:
        if not repo.delete(task_id):
            raise task_not_found()

    return app


app = create_app()
