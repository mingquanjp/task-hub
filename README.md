# TaskHub API

TaskHub is a FastAPI task-management API. It currently provides a database-backed `Label` resource with versioned routing, validation, CRUD endpoints, dependency injection, Alembic migrations, and interactive OpenAPI documentation.

## Current scope

- FastAPI application factory, ASGI entry point, lifespan, health check, Swagger UI, and ReDoc.
- Versioned API under `/api/v1`.
- Project-scoped label CRUD with UUID path parameters.
- Workspaces and Workspace Members with Role-Based Access Control (OWNER, EDITOR, VIEWER).
- Project management within workspaces.
- Task management within projects (Status, Priority, Assignee, Filters, Pagination).
- Pydantic v2 validation: non-empty names up to 50 characters and normalized `#RRGGBB` colors.
- PostgreSQL persistence with SQLAlchemy 2.x async, psycopg, and Alembic.
- Authentication: user persistence, Argon2 password hashing, JWT access/refresh tokens, and register/login/refresh/logout flows.

User profile, Comments, Notification, and Background Task are intentionally outside the current scope. Authentication, Workspaces, Projects, and Task Management APIs are now available.

## Requirements

- Python 3.12 (pinned in `.python-version`).
- [uv](https://docs.astral.sh/uv/).
- A Neon PostgreSQL database.

Copy `.env.example` to `.env` and add the Neon direct connection string. Keep its `sslmode=require` and `channel_binding=require` parameters unchanged.

JWT authentication requires `JWT_SECRET_KEY` (at least 32 characters), `JWT_ALGORITHM=HS256`, and access/refresh expiry settings. Secrets are represented with `SecretStr`, are not logged, and must be replaced with deployment-specific values.

## Run locally

```bash
uv sync
uv run alembic upgrade head
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
uv run alembic current --check-heads
```

## API endpoints

All label endpoints are tagged `labels` in Swagger. `project_id` and `label_id` must be UUIDs.

| Method | Path | Success | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | 200 | Confirm the API is reachable. |
| `POST` | `/api/v1/auth/register` | 201 | Register a member account. |
| `POST` | `/api/v1/auth/login` | 200 | Issue access and refresh tokens. |
| `POST` | `/api/v1/auth/refresh` | 200 | Rotate a refresh token. |
| `POST` | `/api/v1/auth/logout` | 204 | Revoke a refresh token. |
| `GET` | `/api/v1/users/me` | 200 | Get current user profile. |
| `PATCH` | `/api/v1/users/me` | 200 | Partially update current user profile. |
| `POST` | `/api/v1/users/me/change-password` | 204 | Change password and revoke refresh tokens. |
| `POST` | `/api/v1/projects/{project_id}/labels` | 201 | Create a label. |
| `GET` | `/api/v1/projects/{project_id}/labels` | 200 | List labels for a project. |
| `GET` | `/api/v1/projects/{project_id}/labels/{label_id}` | 200 | Get one label. |
| `PATCH` | `/api/v1/projects/{project_id}/labels/{label_id}` | 200 | Partially update a label. |
| `DELETE` | `/api/v1/projects/{project_id}/labels/{label_id}` | 204 | Delete a label. |
| `POST` | `/api/v1/workspaces` | 201 | Create a workspace. |
| `GET` | `/api/v1/workspaces/{workspace_id}` | 200 | Get a workspace. |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects` | 201 | Create a project. |
| `GET` | `/api/v1/projects/{project_id}` | 200 | Get a project. |
| `POST` | `/api/v1/projects/{project_id}/tasks` | 201 | Create a task. |
| `GET` | `/api/v1/projects/{project_id}/tasks` | 200 | List paginated tasks with filters. |
| `GET` | `/api/v1/tasks/{task_id}` | 200 | Get a task. |
| `PATCH` | `/api/v1/tasks/{task_id}` | 200 | Partially update a task. |
| `DELETE` | `/api/v1/tasks/{task_id}` | 204 | Delete a task. |

`POST` returns `404` when the parent project does not exist. `GET`, `PATCH`, and `DELETE` return `404` when the resource does not exist. Invalid UUIDs and invalid request bodies return FastAPI's `422` validation response. Workspace mutation actions (like creating/updating tasks) require appropriate workspace roles.

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

```

### Task Management

The `Task` API provides full CRUD capabilities with strong RBAC constraints.

**Properties:**
- **Status**: `TODO` (default), `IN_PROGRESS`, `IN_REVIEW`, `DONE`.
- **Priority**: `LOW`, `MEDIUM` (default), `HIGH`, `URGENT`.

**Permission Matrix:**
| Action | ADMIN | OWNER | EDITOR | VIEWER |
| :--- | :--- | :--- | :--- | :--- |
| View tasks | Yes | Yes | Yes | Yes |
| Create tasks | Yes | Yes | Yes | No |
| Edit/Assign tasks | Yes | Yes | Yes | No |
| Delete tasks | Yes | Yes | Yes | No |

**Assignee Rule**: Tasks can only be assigned to valid members of the workspace that owns the project. An invalid assignee ID will result in a `403` or `404`.

**Filter & Pagination Example:**
```bash
# List tasks on page 2, limit 10, filtering by HIGH priority and TODO status
GET /api/v1/projects/{project_id}/tasks?page=2&limit=10&status=TODO&priority=HIGH
```

### Swagger smoke-test flow

1. In the Neon SQL Editor, seed one minimal parent row and copy the UUID you used:

   ```sql
   INSERT INTO projects (id) VALUES ('bc2a70bb-0bb7-4496-82a8-1832d59a9c5f');
   ```

2. Open `/docs`, expand **labels**, then choose `POST /api/v1/projects/{project_id}/labels`.
3. Click **Try it out**, enter the seeded `project_id`, and submit the create payload above. Copy the returned `id`.
4. Call list and get with the same `project_id` and `id`.
5. Patch the label using the example partial payload.
6. Delete it, then call get again to confirm the `404` response.

### Swagger auth and token flow

TaskHub uses JWT access and refresh tokens. Follow these steps to test protected endpoints in Swagger:

1. **Register**: Expand `POST /api/v1/auth/register` and submit a new user payload (email, full_name, password).
2. **Login**: Expand `POST /api/v1/auth/login` and submit the credentials. Copy the `access_token` and `refresh_token` from the response.
3. **Authorize**: Scroll to the top of `/docs`, click the **Authorize** button. Paste ONLY the `access_token` into the value field and click Authorize.
4. **Access Protected Routes**: Expand `GET /api/v1/users/me` and click Try it out. It will automatically use your Bearer token.
5. **Update Profile**: Use `PATCH /api/v1/users/me` to update your details.
6. **Refresh Token**: Expand `POST /api/v1/auth/refresh`. Do NOT put the refresh token in the Authorize button. Put the `refresh_token` in the request body. You will receive a new access/refresh pair. The old refresh token is now revoked.
7. **Change Password**: Use `POST /api/v1/users/me/change-password`. Note: changing password revokes ALL active refresh tokens for the user.
8. **Login Again**: Use `POST /api/v1/auth/login` with your new password to get a new pair of tokens.
9. **Authorize Again**: Update the **Authorize** button with the new `access_token`.
10. **Logout**: Use `POST /api/v1/auth/logout`. Submit the NEW `refresh_token` in the body. Ensure your new `access_token` is still in the Authorize button.
11. **Verify Revocation**: Try to use `POST /api/v1/auth/refresh` with the OLD `refresh_token` and confirm it returns a `401 Unauthorized`.

*Note: The `access_token` is verified against the database on each request to ensure the user is still active. There is no access-token blacklist; tokens expire naturally after their configured lifespan (default 15 mins).*

## Architecture

```text
src/taskhub/
├── application.py                 # create_app(), lifespan, application composition root
├── main.py                        # ASGI object: taskhub.main:app
├── core/config.py                  # Environment-backed database configuration
├── infrastructure/
│   ├── database/                   # Async engine, session factory, ORM models
│   └── repositories/base.py         # Generic ORM persistence operations
├── api/
│   ├── system.py                  # /health
│   └── v1/router.py               # /api/v1 composition
└── modules/labels/
    ├── entities.py                # Framework-free Label dataclass
    ├── schemas.py                 # Pydantic request/response models
    ├── repository.py              # LabelRepository contract + in-memory unit-test adapter
    ├── sqlalchemy_repository.py   # SQLAlchemy implementation of the contract
    ├── service.py                 # Label use cases and domain exception
    ├── dependencies.py            # FastAPI DI providers
    └── router.py                  # HTTP request/response handling
```

The request and dependency flow is:

```text
FastAPI lifespan
  → app.state.engine + app.state.session_factory

HTTP request
  → Label router
  → LabelService (Depends)
  → get_db_session (Depends)
  → AsyncSession
  → SQLAlchemyLabelRepository (Depends)
  → PostgreSQL
```

Responsibilities are intentionally separated:

- **Router** parses HTTP input, declares OpenAPI metadata, converts `LabelNotFoundError` to HTTP 404, and serializes `LabelResponse`.
- **Service** owns use cases: UUID creation, parent-project existence checks, partial update semantics, and domain errors. It does not import FastAPI.
- **Repository** maps between `Label` entities and SQLAlchemy models. It does not import FastAPI, return HTTP status codes, or raise `HTTPException`.
- **Entity** is a frozen Python dataclass without HTTP, Pydantic, or persistence dependencies.

The application lifespan owns an async engine and session factory. Each request receives one `AsyncSession`; it commits after a successful response, rolls back on an unhandled exception, and closes the session. Router signatures and service use cases remain independent of the concrete database adapter.

The decision and trade-offs are recorded in [ADR-001](docs/architecture/adr-001-modular-layered-architecture.md).

## Database and migration notes

Run migrations before starting the API:

```bash
uv run alembic upgrade head
uv run alembic current --check-heads
```

The migrations create `projects`, `labels`, `users`, and `refresh_tokens`, including their foreign keys, cascade rules, role check, and indexes. Refresh tokens are represented by persisted hashes; raw token values are not stored. Alembic autogenerate is a starting point only: every revision must be reviewed manually before it is applied. `InMemoryLabelRepository` remains only as a fast fake for unit tests and dependency-override tests; it is not used by the running application.

To verify rollback locally, run `uv run alembic downgrade -1`, then `uv run alembic upgrade head` again.

The automated database suite uses a temporary SQLite file to remain self-contained; it validates migrations, foreign keys, persistence, and the full HTTP dependency chain. Before release, also run the Neon migration commands above and the Swagger smoke-test flow to validate PostgreSQL, psycopg, and TLS behavior.

## Tests

Tests are split by boundary:

- `tests/test_label_service.py` and `tests/test_label_repository.py`: unit behavior without HTTP.
- `tests/test_label_database.py` and `tests/test_migrations.py`: a temporary SQLite database receives the real Alembic revision; these tests cover repository CRUD, FK enforcement, rollback, pagination, and migration round-trip.
- `tests/test_sqlalchemy_label_repository.py`: SQLAlchemy mapping and persistence-adapter behavior without HTTP.
- `tests/test_label_api.py`: HTTP → router → DI → service → SQLAlchemy repository → temporary migrated database → response.
- `tests/test_application.py`: lifespan, health, router composition, OpenAPI, Swagger, and ReDoc.

The integration suite covers the CRUD happy path, validation failures, project boundaries, 404 after deletion, application-instance isolation, and dependency overrides.
