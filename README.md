# TaskHub API

TaskHub is a FastAPI task-management API. Task 1 implements the application core and a complete `Label` resource: versioned routing, validation, CRUD endpoints, dependency injection, tests, and interactive OpenAPI documentation.

## Current scope

- FastAPI application factory, ASGI entry point, lifespan, health check, Swagger UI, and ReDoc.
- Versioned API under `/api/v1`.
- Project-scoped label CRUD with UUID path parameters.
- Pydantic v2 validation: non-empty names up to 50 characters and normalized `#RRGGBB` colors.
- Application-scoped in-memory storage.

Authentication, database persistence, migrations, workspaces, projects, tasks, Redis, and Docker are intentionally outside Task 1.

`project_id` currently namespaces labels only: there is no `Project` resource, parent lookup, or foreign-key validation yet. Any syntactically valid UUID can be used as a project namespace until database-backed project handling is added.

## Requirements

- Python 3.12 (pinned in `.python-version`).
- [uv](https://docs.astral.sh/uv/).

No database, Redis instance, environment variables, or Docker setup is required for the current implementation.

## Run locally

```bash
uv sync
uv run uvicorn taskhub.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/docs` | Swagger UI; use this to call the API interactively. |
| `http://127.0.0.1:8000/redoc` | ReDoc API reference. |
| `http://127.0.0.1:8000/openapi.json` | Generated OpenAPI document. |
| `http://127.0.0.1:8000/health` | Health check; returns `{"status":"ok"}`. |

`/` is not an application route, so opening it returns `404` by design. Stop the development server with `Ctrl+C`.

## Verify quality

Run the same mandatory checks used by Task 1:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## API endpoints

All label endpoints are tagged `labels` in Swagger. `project_id` and `label_id` must be UUIDs.

| Method | Path | Success | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | 200 | Confirm the API is reachable. |
| `POST` | `/api/v1/projects/{project_id}/labels` | 201 | Create a label. |
| `GET` | `/api/v1/projects/{project_id}/labels` | 200 | List labels for a project. |
| `GET` | `/api/v1/projects/{project_id}/labels/{label_id}` | 200 | Get one label. |
| `PATCH` | `/api/v1/projects/{project_id}/labels/{label_id}` | 200 | Partially update a label. |
| `DELETE` | `/api/v1/projects/{project_id}/labels/{label_id}` | 204 | Delete a label. |

`GET`, `PATCH`, and `DELETE` return `404` when the label does not exist or does not belong to the supplied project. Invalid UUIDs and invalid request bodies return FastAPI's `422` validation response.

### Label payloads

Create request:

```json
{
  "name": "Backend",
  "color": "#1a73e8"
}
```

The response normalizes `color` to uppercase:

```json
{
  "id": "d2b15e83-df9d-4c53-bf4a-b55e86f8ac90",
  "project_id": "bc2a70bb-0bb7-4496-82a8-1832d59a9c5f",
  "name": "Backend",
  "color": "#1A73E8"
}
```

For `PATCH`, send at least one concrete field. Omitted fields remain unchanged; `{}` and explicit `null` values are rejected. For example:

```json
{
  "name": "Platform"
}
```

### Swagger smoke-test flow

1. Open `/docs`, expand **labels**, then choose `POST /api/v1/projects/{project_id}/labels`.
2. Click **Try it out**, enter a generated UUID for `project_id`, and submit the create payload above. Copy the returned `id`.
3. Call list and get with the same `project_id` and `id`.
4. Patch the label using the example partial payload.
5. Delete it, then call get again to confirm the `404` response.

## Architecture

```text
src/taskhub/
├── application.py                 # create_app(), lifespan, application composition root
├── main.py                        # ASGI object: taskhub.main:app
├── api/
│   ├── system.py                  # /health
│   └── v1/router.py               # /api/v1 composition
└── modules/labels/
    ├── entities.py                # Framework-free Label dataclass
    ├── schemas.py                 # Pydantic request/response models
    ├── repository.py              # LabelRepository contract + in-memory adapter
    ├── service.py                 # Label use cases and domain exception
    ├── dependencies.py            # FastAPI DI providers
    └── router.py                  # HTTP request/response handling
```

The request and dependency flow is:

```text
HTTP request
  → Label router
  → LabelService (Depends)
  → LabelRepository (Depends)
  → app.state.label_repository
  → InMemoryLabelRepository
```

Responsibilities are intentionally separated:

- **Router** parses HTTP input, declares OpenAPI metadata, converts `LabelNotFoundError` to HTTP 404, and serializes `LabelResponse`.
- **Service** owns use cases: UUID creation, project ownership checks, partial update semantics, and domain errors. It does not import FastAPI.
- **Repository** stores and retrieves `Label` entities. It does not import FastAPI, return HTTP status codes, or raise `HTTPException`.
- **Entity** is a frozen Python dataclass without HTTP, Pydantic, or persistence dependencies.

The composition root creates the concrete in-memory repository once for each FastAPI application instance. A future SQLAlchemy implementation can satisfy `LabelRepository`; router signatures and service use cases remain unchanged.

The decision and trade-offs are recorded in [ADR-001](docs/architecture/adr-001-modular-layered-architecture.md).

## In-memory storage limitations

The current repository is deliberately a teaching and development adapter, not production persistence:

- Data is lost whenever the process restarts or the development reloader recreates the app.
- Data is local to one application process; multiple workers do not share it.
- There are no database transactions, uniqueness constraints, migrations, backups, or cross-process concurrency guarantees.
- Labels do not currently verify that a parent project exists; `project_id` is only an in-memory grouping key.
- Any labels created in Swagger exist only while that app process remains alive.

Task 2 will introduce a database-backed repository and migrations. Do not use the in-memory adapter for persistent or multi-instance deployments.

## Tests

Tests are split by boundary:

- `tests/test_label_service.py` and `tests/test_label_repository.py`: unit behavior without HTTP.
- `tests/test_label_api.py`: integration flow from HTTP router through DI, service, repository, and response.
- `tests/test_application.py`: lifespan, health, router composition, OpenAPI, Swagger, and ReDoc.

The integration suite covers the CRUD happy path, validation failures, project boundaries, 404 after deletion, application-instance isolation, and dependency overrides.
