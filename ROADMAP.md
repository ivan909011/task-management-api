# Roadmap

Planned work for the next versions, roughly in order. Estimates are in hours of development, including tests and docs.

## 1. Persistent storage with PostgreSQL (~15 h)

- [ ] `PostgresTaskRepository` implementing the existing `TaskRepository` protocol
- [ ] Schema migrations (Alembic)
- [ ] `update` as a single `UPDATE ... RETURNING` statement, keeping the atomicity guarantee
- [ ] Index on `status` for filtered listings
- [ ] Run the same repository test suite against both the in-memory store and PostgreSQL
- [ ] `docker-compose.yml` for a local database, and a PostgreSQL service in CI

## 2. Authentication and task ownership (~12 h)

- [ ] User registration and login with hashed passwords and JWT access tokens
- [ ] Each task belongs to a user, and users can only see and change their own tasks
- [ ] Return 404 rather than 403 for other users' tasks, so task IDs don't leak
- [ ] Tests for every endpoint covering the unauthenticated, wrong-user and owner cases

Only made-up sample data is used in development and tests.

## 3. Cursor-based pagination (~5 h)

- [ ] Opaque cursor based on `(created_at, id)`, stable while tasks are inserted or deleted
- [ ] Keep `limit`/`offset` working for existing clients, and document the deprecation

## 4. Performance measurement (~6 h)

- [ ] Load test with a documented workload (Locust)
- [ ] Record baseline latency and throughput for the PostgreSQL version
- [ ] Optimise only where the measurements point, and report the before and after numbers

## 5. Packaging and docs (~2 h)

- [ ] Dockerfile for the API
- [ ] Changelog and tagged releases
