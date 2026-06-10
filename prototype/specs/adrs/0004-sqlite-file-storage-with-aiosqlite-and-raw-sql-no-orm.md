---
adr_id: ADR-0004
status: accepted
date: 2026-05-31
tags: [storage, database, persistence]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md (CAP-009)]
---

# ADR-0004: SQLite file storage with aiosqlite and raw SQL (no ORM)

## Status

Accepted.

## Context

The product must be self-contained with no external database server (PRD constraint), store all state in a single backup-able volume, and support a single-user, single-instance workload where a background scheduler writes while the UI reads. A storage engine and data-access approach must be chosen.

## Decision Drivers

- No external database server (hard PRD constraint)
- Single-file persistence for trivial backup (copy one file)
- Adequate concurrency for one user + background scheduler
- Zero-config startup
- Async compatibility with the FastAPI event loop

## Considered Options

### Option A: SQLite single file via `aiosqlite` with raw SQL (no ORM)

SQLite single file accessed via `aiosqlite` with raw SQL and Pydantic models for (de)serialization; a lightweight numbered-migration runner with a `schema_version` table applied on startup.

- **Pros**: zero external infra; single-file backup; WAL allows concurrent reads during writes; async driver fits FastAPI; full SQL control; tiny footprint.
- **Cons**: hand-written SQL and migrations; limited write concurrency (fine for single user).

### Option B: SQLite via an ORM (e.g., SQLAlchemy)

- **Pros**: less hand-written SQL; declarative models/migrations (Alembic).
- **Cons**: heavier dependency and abstraction for a tiny schema; async ORM ergonomics add complexity disproportionate to the few tables (DeviceType, Device, AppConfig, logs).

### Option C: Embedded document store or flat JSON files

- **Pros**: schema-less simplicity.
- **Cons**: no relational integrity for device-type/device relationships; no transactional guarantees; harder querying for grouped views.

## Decision Outcome

Chosen option: **Option A: SQLite with aiosqlite + raw SQL, no ORM** — SQLite uniquely satisfies the "no external DB server" and single-file-backup constraints with zero configuration. Given the small relational schema, raw SQL via the async `aiosqlite` driver plus Pydantic models and a repository-per-entity pattern is simpler and lighter than an ORM, while WAL journaling provides sufficient read/write concurrency for the single-user + scheduler workload.

## Consequences

### Positive

- Zero external infrastructure; backup = copy `binocular.db`; async-native; full SQL control; minimal dependencies.
- WAL mode + `busy_timeout` + `foreign_keys=ON` set per connection handle concurrency and integrity.

### Negative

- Hand-maintained numbered SQL migrations and a custom lightweight runner; raw SQL requires discipline to avoid injection (parameterized queries mandatory).

### Neutral

- Repository pattern, one Pydantic model per entity; `BINOCULAR_DB_PATH` env var (default `/app/data/binocular.db` in Docker).

## Links

- [specs/prd.md](../prd.md) — CAP-009 (Self-Hosted Operability)
- [ADR-0002](0002-python-311-and-fastapi-for-the-backend.md) — FastAPI/async backend
