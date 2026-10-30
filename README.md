# MESL Finance Backend

Backend for the MESL lab's finance, member-fee and asset tracking. Replaces a Google Sheet.

FastAPI + PostgreSQL. PostgreSQL owns the business rules; the app calls the right SQL in the right
transaction and translates server errors into typed domain errors (RFC 9457 problem JSON). Money is
whole-BDT `int` everywhere — never floats.

Status: all roadmap phases (Phase 0–12) are complete; [`ROADMAP.md`](ROADMAP.md) is now history.
Changes are issue-driven (see [Making changes](#making-changes)). Backlog items that are not yet confirmed stay listed in [`ROADMAP.md`](ROADMAP.md#backlog-unconfirmed-the-user-said-maybe-not-part-of-any-step-until-confirmed) until someone opens them as issues. A frontend is built in parallel by another team; this repo is backend only, with no CI.

## Tech stack

- Python 3.14+ (developed on 3.15), managed with [uv](https://docs.astral.sh/uv/)
- FastAPI, SQLAlchemy 2.x (Core only, asyncpg driver), Alembic, PostgreSQL 18 (dev)
- Auth: argon2 password verification, PyJWT access tokens (72 h)

## Architecture

Strict clean architecture, feature folders. Dependencies point inward only:

```
src/mesl_finance/
  shared/                         # kernel: errors, Money, ports, settings, engine, error translator
  <feature>/
    domain/                       # pure Python (no fastapi/sqlalchemy/asyncpg/pydantic)
    application/                  # use cases + Protocol ports
    infrastructure/               # adapters and ALL SQL
    api/                          # routers, request/response schemas
  main.py                         # composition root — the only module that knows every layer
```

Features: `assets`, `auth`, `cost_centers`, `envelopes`, `fees`, `health`, `ledger`, `members`,
`reconciliation`, `tenures`.

The database schema (`db/schema.sql`) is migration 0001's payload and is never edited; later
migrations follow the append-only convention in [`AGENTS.md`](AGENTS.md#5-database-rules)
(hand-written `db/sql/NNN_<slug>.sql` + one thin Alembic revision each).

## Getting started

```bash
uv sync
```

### 1. Configure the environment

Copy `.env.example` to `.env` (never commit `.env`) and fill in the values:

| Variable | Purpose |
|---|---|
| `MESL_DATABASE_URL` | App DSN. The app connects as the limited `labapp` role, never as the owner. |
| `MESL_ADMIN_DATABASE_URL` | Owner/superuser DSN, used only by migrations, bootstrap and tests — never the running app. |
| `MESL_JWT_SECRET` | HMAC secret for JWT signing. |
| `MESL_JWT_TTL_HOURS` | Access-token lifetime in hours (default 72). |
| `MESL_AUTH_USERNAME` | The treasurer's username (the only login). |
| `MESL_AUTH_PASSWORD_HASH` | argon2 hash of the treasurer's password. Generate one with `uv run python -m mesl_finance.auth.infrastructure.hash_cli`. |
| `MESL_TIMEZONE` | Database timezone (default `Asia/Dhaka`). |

### 2. Migrate and bootstrap

Apply the migration chain as the owner. `alembic` does **not** read `.env` (by design: the owner
DSN must come from the raw `MESL_ADMIN_DATABASE_URL` process variable only, never from a file),
so export it in your shell first — copy the values from `.env`, never commit credentials:

```bash
export MESL_ADMIN_DATABASE_URL=postgresql://postgres:<password>@localhost:<port>/mesl
uv run alembic upgrade head
```

Open the first tenure (idempotent: skips and exits 0 if an open tenure already exists). It creates
exactly the pool envelope (`Unallocated General`) and the first tenure, and sets the login role's
password to the password embedded in `MESL_DATABASE_URL`:

```bash
PYTHONPATH=src uv run python -m mesl_finance.bootstrap --tenure-name "2026" --opened-on YYYY-MM-DD
```

### 3. Run the app

```bash
uv run uvicorn --app-dir src mesl_finance.main:create_app --factory
```

## API

- Everything lives under the `/api/v1` prefix; `/docs` and `/openapi.json` stay at the root.
- One public login route (`POST /api/v1/auth/login`). There are no users in the database — the
  single treasurer's credentials come from the environment.
- Errors are RFC 9457 problem JSON (`problem+json`), produced by one shared error translator.
- The API contract is the generated [`docs/openapi.json`](docs/openapi.json); there is no handwritten
  contract file. Regenerate it after any route change with:

  ```bash
  PYTHONPATH=src uv run python -m mesl_finance.export_openapi
  ```

## Tests and quality gates

Tests run against a real PostgreSQL — no mocked databases. `tests/conftest.py` builds a template
database and clones one per test; it needs a superuser DSN for the dev server, in `TEST_ADMIN_DSN`.
Point it at the server root (the `/postgres` database), not the app database:

```bash
export TEST_ADMIN_DSN=postgresql://postgres:<password>@localhost:<port>/postgres
```

Tests ignore `.env` by design (`Settings` is built inside the fixtures, with `_env_file=None`),
so sourcing or exporting the `MESL_*` variables does not substitute for `TEST_ADMIN_DSN`.

A test database change is never made by editing `db/schema.sql` — see the schema policy in
[`AGENTS.md`](AGENTS.md#schema-changes-and-the-migration-convention-d-018-d-031).

All four gates must be green, in this order:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

## Making changes

Every change starts as a Github issue (bug, quesion, change request or feature). The agent workflow, run inside opencode, one session per phrase:
1. `/triage #N` (or `/triage` plus the pasted issue text): read-only. Classifies the issue, checks - whether the behavior is intended, and recommends accept, defer, decline or workaround.
2. Post the report as a comment on the issue. Declined or deferred issue end here.
3. Accepted issues: `/start #N`, then `/tests`, `/code`, `/review`, `/wrapup`. Commit with - `Fixes #N` in the message

How to judge a change (intent, money history, schema, API contract) is in [`MAINTENANCE.md`](MAINTENANCE.md). The repo records only decisions, business rules and tests, never issues themselves.

## Repo documentation

| File | Holds |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Standing rules for the building agent (architecture, database, TDD gates) |
| [`DECISIONS.md`](DECISIONS.md) | Append-only log of confirmed decisions and discovered facts (D-xxx) |
| [`BUSINESS.md`](BUSINESS.md) | The lab's business rules (ticked lines are authoritative) |
| [`MAINTENANCE.md`](MAINTENANCE.md) | How to triage and judge live issues, bugs and change requests |
| [`ROADMAP.md`](ROADMAP.md) | History: the original build plan and its progress (one step = one session = one commit) |
| [`.opencode/`](.opencode/) | Agents (tester, coder, reviewer) and commands (/triage, /start, /tests, /code, /review, /wrapup) |
## License

TBD.
