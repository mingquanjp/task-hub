# ADR-001: Use a modular layered architecture for TaskHub features

## Status

Accepted — 2026-07-31

## Context

TaskHub starts as a FastAPI API with one `Label` resource, but the target system will later add database persistence and more task-management domains. The first slice needs a design that is easy to test and lets the persistence implementation change without coupling use cases to HTTP or SQLAlchemy.

The initial delivery has no database. It needs an in-memory adapter scoped to a FastAPI application instance while keeping the future SQLAlchemy migration local to the persistence boundary.

There is also no Project module yet. A label's `project_id` is therefore a UUID namespace rather than a verified parent relationship until a database-backed Project feature exists.

## Options considered

| Option | Advantages | Drawbacks |
| --- | --- | --- |
| Put CRUD directly in the FastAPI router | Least initial code. | Mixes HTTP, use cases, and persistence; makes unit tests and a persistence swap harder. |
| Generic repository and shared base service now | May reduce repetition later. | Adds unproven abstraction before a second resource exists. |
| Feature module with entity, repository contract, service, schemas, DI, and router | Keeps each concern replaceable and testable; preserves simple per-feature navigation. | More files than a single router. |

## Decision

Use a modular layered architecture inside `src/taskhub/modules/<feature>/`. For labels, the module contains:

- a framework-free frozen `Label` entity;
- a `LabelRepository` protocol and `InMemoryLabelRepository` adapter;
- `LabelService` application use cases and domain exception;
- Pydantic schemas for the HTTP contract;
- FastAPI dependencies and an `APIRouter` delivery adapter.

The application factory is the composition root. It creates `InMemoryLabelRepository` on `app.state`; FastAPI dependency functions provide it to `LabelService`, which is then injected into the router.

## Rationale

1. The service can be tested with the in-memory adapter without starting an HTTP server.
2. The router is responsible only for HTTP concerns, including translating a domain not-found error to 404.
3. A future `SQLAlchemyLabelRepository` can implement the existing contract while keeping router and service interfaces stable.
4. This adds only feature-local boundaries needed by the current requirements; it does not introduce a generic base repository before Task 2 has multiple persistence adapters.

## Trade-offs

- The Label feature has more files and explicit mapping than a router-only implementation.
- The in-memory adapter is application-scoped but volatile and unsuitable for production persistence.
- The service currently accepts validated Pydantic schemas. This avoids duplicate command DTOs while no non-HTTP caller exists; introduce framework-free commands only if a CLI, queue worker, or another delivery mechanism needs the same use cases.

## Consequences

- **Positive:** HTTP, domain behavior, and persistence can be verified independently; dependency overrides make integration tests deterministic.
- **Negative:** Feature authors must preserve the boundaries instead of placing convenience logic in routers.
- **Mitigation:** Tests and code review check that routers contain no business rules, services do not import FastAPI, repositories do not know HTTP, and state is app-scoped rather than module-global.

## Revisit triggers

Revisit this decision when TaskHub introduces a second persistence-backed feature, transaction boundaries across multiple repositories, a background worker/CLI caller, or shared cross-feature business rules.
