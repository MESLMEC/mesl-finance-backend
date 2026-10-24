# MESL Finance Backend: Development Roadmap

Backend for the MESL lab's finance, member-fee and asset tracking. Replaces a Google Sheet.
FastAPI + PostgreSQL. PostgreSQL owns the business rules; the app calls the right SQL in the right
transaction and translates errors.

**This file is the plan and the progress tracker, nothing else.** Decisions live in `DECISIONS.md`,
standing rules in `AGENTS.md`, business rules in `BUSINESS.md`. Do not duplicate them here.

## How to use

- One step = one session = one commit. Start every session with `/start` (or `/start 6.2`).
- `/start` picks the first unticked step whose `needs:` steps are ALL ticked.
- Tests are part of every step (written first). There are no separate "write tests" steps.
- A step marked `[P-xxx]` depends on a `proposed` entry in DECISIONS.md. `/start` must ask the
  user to confirm it before work begins.
- If a step is too big for one session, `/start` proposes a split; the roadmap is updated BEFORE work.

## Definition of Done (every step)

1. Failing tests first, seen failing for the right reason. 2. Smallest code that passes. 3. Refactor green.
4. All four gates green: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`.
5. No TODO, placeholder or silent assumption. Decisions and facts later sessions need are written down.
6. The user reviews and commits; the step is ticked in the same commit.

## Schema policy (D-014, D-018)

`db/schema.sql` is used first and kept untouched. The structure should not change; if a migration is
ever needed, stop and consult the user (`DB change needed: X; alternative: Y`), write nothing.

How the app needs are met with ZERO schema changes:

| Need | Existing mechanism |
|---|---|
| Treasurer login | argon2 hash in settings; JWT issued by the app (D-006) |
| "Who edited this label" | `set_config('app.actor', <jwt subject>, true)` inside the transaction |
| First tenure | bootstrap CLI as owner (D-019); `labapp` has no INSERT on `tenures` |
| Dues / standing | `member_standing()` |
| Allocation, sweep, reconciliation, tenure close | `allocate`, `sweep_leftover`, `reconcile`, `close_tenure` |
| Reads | views and functions: `envelope_balances`, `entries_current`, `cost_center_summary`, `asset_state`, `asset_holdings`, `asset_activity`, `allocation_suggestion`, ... |
| Error detail | exception message text and constraint names, translated in ONE infrastructure place |

---

## Phase 0: Repo and tooling baseline

- [x] **0.1** `git init`; extend `.gitignore` (`.env`, `dist/`, `*.orig`); the user commits the current tree. needs: none
- [x] **0.2** Add dev dependency `asyncpg-stubs`. needs: 0.1
- [x] **0.3** Fix the ruff findings in `tests/db/test_ledger_contract.py`; format the unformatted files. needs: 0.1
- [x] **0.4** Pyright strict-clean, including `tests/conftest.py`. needs: 0.2, 0.3
- [x] **0.5** `src/mesl_finance/shared/settings.py` (pydantic-settings): app DSN, admin DSN, JWT secret, JWT TTL (72h), treasurer username, argon2 hash, timezone (Asia/Dhaka); plus `.env.example`. needs: 0.4
  Notes: the admin/owner DSN is Settings' required `MESL_ADMIN_DATABASE_URL` (SecretStr); its spelling differs from the tests' raw `TEST_ADMIN_DSN` env var. Local `.env` must add the key.
- [x] **0.6** Run every raw `db/examples/*.sql` against PostgreSQL 18: every `EXPECT FAIL` still errors, every expectation still holds. Report differences; change nothing. needs: 0.1 [P-007]
  Notes: verified 2026-10-20 (D-025, verify-only step approved by the user): 7 fresh scratch DBs (00; 01+02 share one DB; 03–07), PG 18.0 docker, psql 18.6. Zero differences; nuance for step 6.x: 01 §8 "wrong mirror" errors via the balance guard before any mirror-specific rejection.

## Phase 1: Alembic chain and bootstrap (D-018, D-019)

- [x] **1.1** Add `alembic` to the MAIN dependency group; `alembic.ini` and `alembic/env.py` (async, owner DSN from env only, one transaction per migration). needs: 0.4, 0.6
  Notes: NO-TEST step (user-approved). alembic 1.20.0 in the main group; `alembic/env.py` reads the owner DSN from the env var `MESL_ADMIN_DATABASE_URL` only (accepts `postgresql://`, normalizes to `postgresql+asyncpg://`, hard-fails otherwise) and sets `transaction_per_migration=True`. `alembic/versions/.gitkeep` holds the versions dir until 1.3.
- [x] **1.2** Decide, by experiment, how revision 0001 executes the script: (a) the raw asyncpg connection runs the whole file (this is how `tests/conftest.py` loads it today) or (b) a statement splitter. Prefer (a) if it works under Alembic. Build a splitter only if (a) is impossible. Record the outcome in DECISIONS.md. needs: 1.1
  Notes: outcome is D-030 — option (a): revision 0001 executes `db/schema.sql` whole on the raw asyncpg connection Alembic owns, wrapped in the revision's own server-side transaction (`async with raw.transaction():`); a splitter is unnecessary.
- [x] **1.3** `alembic/versions/0001_initial.py`: executes `db/schema.sql` in place (never copied); records the file's sha256. needs: 1.2
  Notes: the revision owns a server-side transaction around the whole-file execute (D-030/D-031); if db/schema.sql ever legitimately changes, the recorded sha256 in `0001_initial.py` must be updated too (the 1.5 guard test will catch a mismatch).
- [x] **1.4** `tests/conftest.py` builds the template DB with `alembic upgrade head` (owner DSN). needs: 1.3
- [x] **1.5** Guard test: sha256 of `db/schema.sql` equals the hash recorded in 0001. needs: 1.3
  Notes: pure unit test at `tests/test_schema_hash.py` (no DB); loads `SCHEMA_SHA256` from the revision by path.
- [x] **1.6** AGENTS.md repointed (the Alembic chain is the migration history; `db/schema.sql` is 0001's payload and is never edited) and the future-change convention written down (`db/sql/NNN_*.sql` + thin revision; consult the user first). needs: 1.4, 1.5
- [x] **1.7** Bootstrap CLI `src/mesl_finance/bootstrap.py` (owner credentials): `alembic upgrade head`, set the `labapp` password from env, open the first tenure. Exact scope (for example the pool envelope) is decided at its `/start` (Q-007). needs: 0.5, 1.4 [P-011]
  Notes: P-011 confirmed; scope decided per Q-007 -> D-041 (tenure + pool envelope only) and Q-005 -> D-040 (role and password both derived from MESL_DATABASE_URL). Required CLI options `--tenure-name`/`--opened-on`; idempotent (open tenure exists -> skip, exit 0); documented run `PYTHONPATH=src uv run python -m mesl_finance.bootstrap`. CLI overrides alembic.ini's cwd-relative script_location/version_locations with absolute paths (D-043), so it works from any cwd; ALTER ROLE can only take a constant, quoted server-side with format('%I','%L') over bound params (D-044).
- [x] **1.8** Port `00_go_live.sql` to `tests/db/test_go_live.py`. needs: 1.7
  Notes: 13 tests, TEST-ONLY (all passed at once). Dates run from
  `sunday_on_or_before(current_date)` as in the script; every expected number derives from the
  schema functions, so the suite keeps passing on any later date. Coverage table in the
  module docstring. 00_go_live.sql has no EXPECT lines; sections map by number.


## Phase 2: Shared kernel (pure Python: no fastapi, sqlalchemy, asyncpg or pydantic)

- [x] **2.1** `shared/errors.py` (domain error taxonomy) and `shared/money.py` (whole-BDT `int` value object; never floats). needs: 0.4
  Notes: `shared/errors.py` already existed in the pre-roadmap guide tree (D-023): user accepted it as-is and it is FROZEN; step 2.1 only adds its guard tests. `Money` is construct-only (no arithmetic operators — PostgreSQL owns the sums; an operator may be added later only together with its test). It accepts only a real `int` (bool/float/Decimal/str refused), is non-negative with zero valid, and exposes the read-only `amount: int` property for any future SQL adapter. The deposit slice keeps its plain `int` amount for now.
- [x] **2.2** `shared/ports.py`: `Clock` and the `UnitOfWork` Protocol (transaction scope, actor, repository accessors). needs: 2.1

## Phase 3: Infrastructure

- [x] **3.1** Async engine and session factory (SQLAlchemy 2.x Core + asyncpg, `labapp` DSN, pool pre-ping, no ORM models for the ledger). needs: 0.5, 1.4
  Notes: TEST-ONLY guard tests at `tests/shared/test_database_engine.py`; the engine was already in the pre-roadmap tree (D-023) and was accepted as-is (D-053). The "session factory" is `create_engine` + `SqlUnitOfWork(engine, actor)`, no separate factory; the engine pins Asia/Dhaka via asyncpg `server_settings` (D-053). The `SqlUnitOfWork` vs `SqlAlchemyUnitOfWork` name question (D-052) stays parked for 3.2's `/start`.
- [x] **3.2** `SqlUnitOfWork` (brief Q1=b amended the wording; was formerly named `SqlAlchemyUnitOfWork`):
  one transaction per use case; sets `app.actor` with `set_config` inside it. needs: 2.2, 3.1
  Notes: TEST-ONLY (D-055): the UoW already existed in the pre-roadmap tree (D-023) and is
  accepted as-is; guard tests at `tests/shared/test_unit_of_work.py` (6 tests). The name stays
  `SqlUnitOfWork` (D-055 Q1=b resolves D-052). Error mapping inside execute/commit stays step
  3.3 territory (brief Q3=a). No db/examples script covers this step (no P-007 port).
- [x] **3.3** The single error translator (infrastructure only): `RaiseError`, unique and foreign-key violations, constraint names, and commit-time raises to typed domain errors. Each rule is added with the test that needs it. needs: 2.1, 3.2
  Notes: CODE-WITH-TESTS; /code added only the 23505 branch + the new `Unique` error (brief Q1=b);
  the P0001/23503/commit-time/event-bypass rules predated this step (D-023) and the 5 green tests pin
  them (tests/shared/test_error_translator.py). The constraint name reaches the detail inside the
  server's own 23505 message text (confirmed live: `envelopes_name_key`); no per-constraint-name
  table (Q2 standing suggestion).

## Phase 4: Auth (D-006)

- [x] **4.1** Argon2 verification against the settings hash. needs: 0.5, 2.1
  Notes: TEST-ONLY (D-060): the checker already existed in the pre-roadmap tree (D-023) and is
  accepted as-is; guard tests at `tests/auth/test_credentials.py` (5). No `db/examples` script
  covers this step.
- [x] **4.2** JWT issue and verify (PyJWT, 72h, access token only) and the FastAPI `current_actor` dependency. needs: 4.1
  Notes: CODE-WITH-TESTS (D-062): the token service, route dependency and most tests pre-existed (D-023) and the 7 new guards were green at once, so /code only applied the approved `current_user` -> `current_actor` rename (auth/api/dependencies.py, ledger/api/router.py); guards: missing `sub`, missing `exp`, HS512 algorithm pinning, claim set `{sub,iat,exp}`, expired/forged/non-bearer 401s (tests/auth/test_tokens.py, tests/auth/test_current_actor.py). No `db/examples` script covers this step.
- [x] **4.3** App factory, RFC 9457 problem-JSON error handlers, `POST /api/v1/auth/login` and API tests. needs: 4.2 [P-002]
  Notes: P-002 confirmed (D-064). `main.py` mounts both routers under `API_PREFIX = "/api/v1"` via
  `include_router(..., prefix=...)`; `/docs` and `/openapi.json` stay at the root. The framework's own
  404/405 are problem JSON (`not_found` / `method_not_allowed`, fallback `http_error`; `title` from
  `http.client.responses`, exception headers e.g. `Allow` forwarded). Guard tests live in `tests/api/`;
  every pre-existing API test path moved to `/api/v1` (D-065).

## Phase 5: Envelopes and cost centers [P-009]

- [x] **5.1** Envelopes: create, list, rename, deactivate (only at zero balance); optional cap and priority, no defaults (D-021). needs: 3.3, 4.3
  Notes: the list carries no balance on purpose (balances are ledger reads, 6.7/8.1); the cap/priority `settings` action comes from Q3=b (D-067) and the shared translator gained 23514 -> RuleViolation (D-068).
- [x] **5.2** Cost centers (event, member_project, lab_project, competition). needs: 5.1
  Notes: Q8=b - the list filters on optional `kind` and `status`; kind is fixed at create
  (Q6=a); the four kinds/statuses and per-kind name uniqueness stay PostgreSQL's (D-070).

## Phase 6: Ledger (first vertical slice)

- [x] **6.0** Port `02_ledger_edits_and_roles.sql` to `tests/db/` (label edits and history, limited role, tamper detection). needs: 1.4 [P-007]
  Notes: 13 cases in `tests/db/test_ledger_edits_and_roles.py`; the module docstring holds the
  coverage table. `example_01()` lives INSIDE that file (not in conftest) and replays example 1,
  because 02 must run "in the SAME database right after example 1". The six "labapp may not"
  lines are SQLSTATE 42501 (privilege wall), the closed-tenure edit is P0001 (D-073/D-075).
- [x] **6.1** Ledger domain objects (entry kinds, lines, income sources). needs: 2.1
- [x] **6.2** Deposit action, built end to end: domain, use case, SQL adapter, route, unit and API tests. needs: 3.3, 4.3, 5.1, 6.1 [P-008]
  Notes: TEST-ONLY (D-079): the slice pre-existed (D-023) and is accepted as-is; P-008 confirmed;
  nine guard tests plus one new parametrize case (246 -> 256). `ledger/domain/deposit.py` keeps its
  pre-DB amount/member/pool guards on purpose (D-080), not by accident.
- [x] **6.3** Expense action. needs: 6.2
  Notes: CODE-WITH-TESTS (25 tests). Response is `201 {"id", "kind", "balance"}` (Q5=b,
  D-082). An unknown envelope is named by an app pre-check because `line_guard` is a BEFORE
  INSERT trigger that preempts the FK (D-084). The expense action has its own port (D-085).
- [x] **6.4** Transfer action. needs: 6.2
  Notes: CODE-WITH-TESTS (37 tests); two-envelope request, response {id,kind,from_balance,to_balance}
  (D-086), blank note/same envelope -> 422 validation_failed, both envelopes pre-checked -> 422
  unknown_reference (so D-084's 409 prediction no longer holds for transfers; sweeps/reversals still),
  own port (D-085).
- [x] **6.5** Fix amount (reversal and replacement in ONE transaction). needs: 6.2, 6.3
  Notes: Q1=a scope: `deposit` and `expense` only; the app refuses any other kind as 422
  `validation_failed` (multi-line fixes, e.g. a transfer, need their own step). ONE
  transaction writes the mirroring reversal and the replacement; PostgreSQL keeps the
  once-only (`reverses_id`/`replaces_id`), tenure and overdraw walls (D-088).
- [x] **6.6** Label edit (note, tag, cost center, date, source). needs: 6.0, 6.2
  Notes: Q7=b - a blank note on transfer/sweep/reversal is refused by the app (422) after the
  row read, not by the CHECK; 200 `{id,kind,note,tag,cost_center_id,occurred_on,source}`; any
  non-opening kind is editable; own port (D-085); 35 tests (D-090/D-091).
- [x] **6.7** Entry list (`entries_current`). needs: 6.2
  Notes: CODE-WITH-TESTS, 13 tests (D-093/D-094). `GET /api/v1/entries` returns the
  12-key `EntryOut` read straight from `entries_current`, deliberately WITHOUT amounts
  (Q3=a); `?tenure_id=` is the only filter and an unknown id is an empty list, and a read
  never asks for an open tenure or commits. Only one tenure may be open at a time
  (db/schema.sql:40), so a cross-tenure read test must hand over via `close_tenure`, which
  leaves a carry-over `opening` in the next tenure's list (D-095).
- [x] **6.8** Export `docs/openapi.json` for the features so far, generated, no handwritten contract. needs: 6.7 [P-003]
  Notes: the artifact is produced by `PYTHONPATH=src uv run python -m mesl_finance.export_openapi`
  from schema-only placeholder settings (no connection, no secrets); the test's
  hardcoded operation inventory must grow with every API step, and the
  committed-file freshness test stays 12.2's (D-096).

## Phase 7: Fees and members

- [x] **7.0** Port `03_fees.sql` and `04_fees_existing_members.sql` to `tests/db/`. needs: 1.4 [P-007]
  Notes: TEST-ONLY (D-099); 30 cases (27 in `tests/db/test_fees.py`, 3 in
  `tests/db/test_fees_existing_members.py`). In 03, the five statements the app role's grants
  stop (start-date edit, delete period, edit/delete adjustment, member edit) raise 42501,
  not the append-only trigger's P0001 (D-100).
- [x] **7.1** Members and membership periods (start once, end once). needs: 6.2, 7.0
  Notes: CODE-WITH-TESTS, 41 new cases (D-101/D-102); `end` targets the member's LATEST period row so `period_guard` answers a second end with 409 and a member with no period with 404 - do not narrow it to `WHERE end_date IS NULL` (D-103).
- [x] **7.2** Fee rates and shutdown weeks (week and Sunday rules enforced by the database). needs: 7.1
  Notes: CODE-WITH-TESTS, 28 new cases (D-104/D-105); the adapter calls `set_shutdown()` itself, so
  the Sunday/order/closed-tenure rules stay in PostgreSQL, no translator rule was needed, and a
  second rate for the same Sunday is accepted (latest id wins) - do not add pre-checks.
- [ ] **7.3** Member adjustments (waiver, credit_donation, opening, correction). needs: 7.1
- [ ] **7.4** Fee payments and refunds (member-linked deposit and expense through the pool). needs: 6.3, 7.1
- [ ] **7.5** Reads: `member_standing`, dues overview, `allocation_context`. needs: 7.2, 7.3, 7.4
- [ ] **7.6** Refresh `docs/openapi.json`. needs: 7.5 [P-003]

## Phase 8: Allocation and sweeps

- [ ] **8.0** Port `06_allocation_and_sweeps.sql` to `tests/db/`. needs: 1.4 [P-007]
- [ ] **8.1** Allocation draft (`allocation_suggestion`, read-only). needs: 5.1, 8.0
- [ ] **8.2** Confirm allocation (`allocate`, one transaction). needs: 8.1, 6.2
- [ ] **8.3** Event leftover (`cost_center_summary`) and sweep to the pool (`sweep_leftover`). needs: 5.2, 6.2, 8.0
- [ ] **8.4** Refresh `docs/openapi.json`. needs: 8.3 [P-003]

## Phase 9: Assets

- [ ] **9.0** Port `05_assets.sql` to `tests/db/`. needs: 1.4 [P-007]
- [ ] **9.1** Asset records and events: acquired, lent, returned, damaged, lost, repaired, scrapped, exchanged, correction. needs: 7.1, 9.0
- [ ] **9.2** Fix an asset event (reversal and replacement, one transaction). needs: 9.1
- [ ] **9.3** Reads: asset state, who-has-what, admin replacement queue. needs: 9.1
- [ ] **9.4** Activity numbers for the admin report (`asset_activity`, CSV-ready). needs: 9.1
- [ ] **9.5** Refresh `docs/openapi.json`. needs: 9.4 [P-003]

## Phase 10: Reconciliation

- [ ] **10.0** Port `07_reconciliation.sql` to `tests/db/`. needs: 1.4 [P-007]
- [ ] **10.1** `reconcile` action (counted total, optional per-envelope counts). needs: 6.2, 10.0
- [ ] **10.2** Reads: reconciliation status, unverified entries, difference suspects. needs: 10.1
- [ ] **10.3** Refresh `docs/openapi.json`. needs: 10.2 [P-003]

## Phase 11: Tenure handover

- [ ] **11.1** Close tenure action (`close_tenure`) and the snapshot reads (member, asset, holding). needs: 7.5, 9.3, 10.1
- [ ] **11.2** Carry-over opening and arrears-across-tenure scenarios through the API. needs: 11.1

## Phase 12: Contract

- [ ] **12.1** `verify_all` health endpoint. needs: 4.3, 1.4
- [ ] **12.2** Final generated `docs/openapi.json` plus a test that it matches the running app. needs: 11.2, 12.1 [P-003]

---

## Backlog (unconfirmed; the user said "maybe?"; NOT part of any step until confirmed)

- Protection against a double-submitted deposit (Q-003). The schema has no idempotency key, so a database fix would need a schema change; consult first.
- CORS: the allowed frontend origin(s) from settings (Q-004).
- Changing the `labapp` password from the schema default `change-me` (Q-005); step 1.7 may cover it.

## Change log

| Date | Change |
|---|---|
| 2026-10-20 | Revised from the first generated roadmap. Decisions moved to DECISIONS.md; tests folded into steps; contract tests ported just in time (proposed); envelopes before ledger and deposit-first slice (proposed); Docker dropped (D-020); bootstrap CLI kept (D-019) and moved early (proposed). |
