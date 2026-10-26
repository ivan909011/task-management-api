# Task Management API

[![CI](https://github.com/ivan909011/task-management-api/actions/workflows/ci.yml/badge.svg)](https://github.com/ivan909011/task-management-api/actions/workflows/ci.yml)

A REST API for managing tasks, built with Python and FastAPI. The focus is on a precise HTTP contract, strict input validation, correctness under concurrent requests, and a test suite that pins down each of those behaviours.

> Data is stored in memory and is lost when the server restarts. Storage sits behind a small repository interface so it can be swapped for a database without touching the HTTP layer.

## Quick start

Requires Python 3.11 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
uvicorn task_management_api.main:app --reload
```

Interactive OpenAPI docs: http://127.0.0.1:8000/docs

## API

| Method | Path | Success | Errors |
| --- | --- | --- | --- |
| GET | `/health` | 200 | |
| POST | `/tasks` | 201 + `Location` header | 422 |
| GET | `/tasks` | 200 + `X-Total-Count` header | 422 |
| GET | `/tasks/{id}` | 200 | 404, 422 |
| PATCH | `/tasks/{id}` | 200 | 404, 422 |
| DELETE | `/tasks/{id}` | 204 | 404, 422 |

A task:

```json
{
  "id": "6f1c2b9e-1a7e-4a53-9a51-1f6f1e0c2b7d",
  "title": "Document the API",
  "description": "Add usage examples",
  "status": "pending",
  "created_at": "2026-10-26T12:00:00Z",
  "updated_at": "2026-10-26T12:00:00Z"
}
```

Validation rules:

- `title`: required on create, 1 to 120 characters after trimming whitespace.
- `description`: optional, up to 2000 characters, may be an empty string.
- `status`: `pending`, `in_progress` or `done`. New tasks always start as `pending`.
- Unknown fields are rejected, so a typo such as `"titel"` or an attempt to set `id` returns 422 instead of being silently ignored.
- `PATCH` needs at least one field, and fields may be omitted but not set to `null`.

Listing: `GET /tasks?status=pending&limit=20&offset=0`. Results are in creation order, `limit` is 1 to 100 (default 20), and `X-Total-Count` holds the number of matching tasks across all pages.

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Document the API","description":"Add usage examples"}'

curl -i 'http://127.0.0.1:8000/tasks?status=pending&limit=10'

curl -X PATCH http://127.0.0.1:8000/tasks/<id> \
  -H 'Content-Type: application/json' \
  -d '{"status":"done"}'
```

## Development

```bash
pytest --cov          # tests with branch coverage (fails under 95%)
ruff check .          # lint
ruff format .         # format
mypy src tests        # strict type checking
```

CI runs all of these on every push and pull request, with tests on Python 3.11, 3.12 and 3.13.

## Project layout

```
src/task_management_api/
  main.py     HTTP layer: routes, status codes, headers
  models.py   Pydantic schemas and validation rules
  store.py    TaskRepository protocol and its thread-safe in-memory implementation
tests/
  test_api.py     HTTP contract tests, one class per endpoint
  test_store.py   repository unit tests, including concurrency
```

## Design decisions

**Partial updates reject `null`.** `PATCH` fields are optional so they can be omitted, but none of the stored fields is nullable. Earlier, `{"title": null}` passed validation and was written into the task with a 200 response, leaving it in an invalid state. The update model now rejects explicit nulls, and the store rebuilds the task with `model_validate` rather than `model_copy`, which skips validation. Both layers have regression tests.

**Each repository operation is atomic.** FastAPI runs sync endpoints in a thread pool, so requests really do run concurrently. `PATCH` used to read a task and then write it back as two separate steps; a `DELETE` landing between them was silently undone and the task reappeared. `update` is now a single operation that reads and writes under one lock, and returns `None` if the task no longer exists. A database implementation would map it to one `UPDATE ... RETURNING` statement.

**Storage is behind a `Protocol`.** Routes depend on `TaskRepository`, not on the in-memory class, and the app factory takes a repository argument. Tests use this for isolation (a fresh store per test), and a PostgreSQL implementation could be added without changing a route.

**Filtering and pagination happen in the repository.** Pushing them down means a database implementation can use `WHERE` and `LIMIT/OFFSET` (and an index on `status`) instead of loading every row into Python. The repository also returns the total match count, which the API exposes as `X-Total-Count` so clients can paginate without guessing.

**Tasks are immutable.** `Task` is a frozen model, so a task can only change through the repository's `update`, which also refreshes `updated_at`.

## Possible next steps

1. A PostgreSQL repository with migrations, and the same test suite run against it.
2. Authentication and per-user ownership of tasks.
3. Cursor-based pagination, which stays stable while tasks are inserted or deleted.
4. Load testing against the database implementation, with before and after numbers for any optimisation.
