# ADR 0002, DuckDB for local dev, Postgres as the production target

**Status:** Accepted

## Context

The OMOP store needs a SQL warehouse dbt can build into. The original plan was
Dockerized Postgres. On the dev machine there is no Docker daemon and no JDK,
and standing up Docker Desktop just to hold a 140-row `person` table is
disproportionate. We still want the production story to be Postgres (the OHDSI
/ OMOP ecosystem standard).

## Decision

Use **DuckDB** as the local development warehouse (via `dbt-duckdb`), and keep
**Postgres** as the documented production target (`docker-compose.yml` +
`dbt-postgres`). dbt's adapter abstraction makes the target a profile-level
concern, so the models are written once and run against either.

## Rationale

- **Zero infra, fully reproducible.** DuckDB is an in-process single file, no
  server, no container, no daemon. `make all` reproduces the entire OMOP build
  from raw data in seconds.
- **The SQL is portable.** The models use standard SQL; the only
  DuckDB-specific touches (`read_csv_auto`, `try_strptime`) live in the staging
  layer and have direct Postgres equivalents (`COPY`/`to_timestamp`).
- **dbt is the whole point of this choice.** Swapping `type: duckdb` for
  `type: postgres` in `profiles.yml` retargets the build; that portability is
  itself a thing worth demonstrating.

## Consequences

- Local dev and CI run on DuckDB (fast, no services).
- A production deployment points the same dbt project at Postgres; the
  DuckDB-only functions in staging would need their Postgres equivalents (small,
  contained surface).
- PySpark streaming ingestion (also JVM-dependent) is deferred to the scale
  story; for the dev cohort, pandas is the correct tool.

## Alternatives rejected

- **Dockerized Postgres now**, real infra cost for no benefit at this data size.
- **SQLite**, weaker analytical SQL, no columnar engine, clumsier CSV/columnar
  ingest than DuckDB.
