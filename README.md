# Task Management API

A REST API for managing tasks, built as a backend portfolio project with Python and FastAPI. It demonstrates endpoint design, input validation, automated tests, consistent error handling, and API documentation.

> This is a demonstration project. Data is stored in memory and is lost when the server restarts. It is not intended for production use without persistence, authentication, and operational safeguards.

## Requirements

- Python 3.11 or later

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
uvicorn task_management_api.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive OpenAPI documentation.

## Run tests

```bash
pytest
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | /health | Health check |
| POST | /tasks | Create a task |
| GET | /tasks | List tasks with filters and pagination |
| GET | /tasks/{id} | Retrieve a task |
| PATCH | /tasks/{id} | Partially update a task |
| DELETE | /tasks/{id} | Delete a task |

List filters: status (pending, in_progress, done), limit (1–100), and offset.

## Example

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Document the API","description":"Add usage examples"}'

curl 'http://127.0.0.1:8000/tasks?status=pending&limit=10&offset=0'
```

## Technical decisions

- Boundary validation: Pydantic models reject invalid input before it reaches application logic.
- Explicit HTTP semantics: creation returns 201, deletion returns 204, missing items return 404, and invalid input returns 422.
- Bounded pagination: the maximum page size is 100.
- Simple separation of concerns: models, storage, and routes are in separate modules, making it straightforward to replace the in-memory store with a persistent repository.
- Isolated tests: each test creates a fresh application and store, so test outcomes do not depend on execution order.

## Possible next steps

1. Replace the in-memory store with PostgreSQL and migrations.
2. Add authentication and per-user authorization.
3. Measure latency and query profiles under a documented workload before optimizing.
4. Add observability, request limits, and container deployment.

## Portfolio walkthrough

Be ready to explain the problem, HTTP contracts, validation rules, and test coverage. To demonstrate performance optimization with evidence, add persistence and compare before-and-after measurements under a documented workload. Do not claim performance gains without measuring them.
