# ADR-001: Use a modular layered architecture for TaskHub features

## Status

Accepted — 2026-07-31

## Context

TaskHub starts as a FastAPI API with one `Label` resource, but the target system will later add database persistence and more task-management domains. The first slice needs a design that is easy to test and lets the persistence implementation change without coupling use cases to HTTP or SQLAlchemy.

The initial delivery used an in-memory adapter. Task 2 now needs durable PostgreSQL persistence, schema migration, request-scoped transactions, and test isolation without making unit tests depend on Neon.

There is still no Project API. A minimal `ProjectModel` is therefore a persistence anchor only; labels validate that the parent row exists when created.

## Options considered

| Option | Advantages | Drawbacks |
| --- | --- | --- |
| Put CRUD directly in the FastAPI router | Least initial code. | Mixes HTTP, use cases, and persistence; makes unit tests and a persistence swap harder. |
| Generic repository and shared base service now | May reduce repetition later. | Adds unproven abstraction before a second resource exists. |
| Feature module with entity, repository contract, service, schemas, DI, and router | Keeps each concern replaceable and testable; preserves simple per-feature navigation. | More files than a single router. |

## Decision

Use a modular layered architecture inside `src/taskhub/modules/<feature>/`. For labels, the module contains:

- a framework-free frozen `Label` entity;
- a `LabelRepository` protocol, an in-memory test adapter, and a SQLAlchemy adapter;
- `LabelService` application use cases and domain exception;
- Pydantic schemas for the HTTP contract;
- FastAPI dependencies and an `APIRouter` delivery adapter.

The application factory is the composition root. Its lifespan creates an async SQLAlchemy engine and session factory on `app.state`. FastAPI dependencies yield one transaction-scoped session per request, compose `SQLAlchemyLabelRepository`, then provide it to `LabelService`.

## Rationale

1. The service can be tested with the in-memory adapter without starting an HTTP server, while database and HTTP integration tests run against a temporary migrated SQLite file.
2. The router is responsible only for HTTP concerns, including translating a domain not-found error to 404.
3. `SQLAlchemyLabelRepository` implements the existing contract while keeping router and service interfaces stable.
4. A generic repository provides only shared ORM persistence primitives; Label-specific mapping and parent lookup remain in the feature adapter.

## Trade-offs

- The Label feature has more files and explicit mapping than a router-only implementation.
- SQLAlchemy mapping introduces explicit domain/ORM conversion and migration maintenance.
- The in-memory adapter is test-only and must not be selected by application runtime composition.
- The service currently accepts validated Pydantic schemas. This avoids duplicate command DTOs while no non-HTTP caller exists; introduce framework-free commands only if a CLI, queue worker, or another delivery mechanism needs the same use cases.

## Consequences

- **Positive:** HTTP, domain behavior, persistence, and migration behavior can be verified independently; dependency overrides and temporary migrated databases keep tests deterministic.
- **Negative:** Feature authors must preserve the boundaries instead of placing convenience logic in routers, and must manually review generated migrations.
- **Mitigation:** Tests and code review check that routers contain no business rules, services do not import FastAPI or SQLAlchemy, repositories do not know HTTP, migrations stay aligned with models, and state is app-scoped rather than module-global.

## Revisit triggers

Revisit this decision when TaskHub introduces a second persistence-backed feature, transaction boundaries across multiple repositories, a background worker/CLI caller, or shared cross-feature business rules.
