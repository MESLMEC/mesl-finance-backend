# Decisions and open questions

**Append-only.** Never edit or delete an entry; add a new one that supersedes it.
`confirmed` = the user said it (quoted in Evidence). `proposed` = suggested by an agent or found in
a generated document; NOT authority until the user confirms. Dates are YYYY-MM-DD.

## Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Supersedes |
|---|---|---|---|---|
| D-001 | 2026-10-20 | Backend is FastAPI now; Go later. | "we will use fastapi. later we will move on to golang." | |
| D-002 | 2026-10-20 | Strict clean architecture and modern standards. | "we must follow strict clean architecture. and modern standards." | |
| D-003 | 2026-10-20 | SQLAlchemy (not SQLModel) with the asyncpg driver. | "i think sqlalchemy will be better." / "4. asyncpg" | |
| D-004 | 2026-10-20 | Python 3.15, managed with uv. | "python 3.15 is latest stable." | |
| D-005 | 2026-10-20 | Dev PostgreSQL is 18.0 in Docker. Database timezone is Asia/Dhaka. | "i am running postgres via docker . v18.0" / "6. asia/dhaka" | |
| D-006 | 2026-10-20 | Auth: one treasurer login. Username and argon2 hash come from environment settings (no users table). JWT access token only (no refresh), valid 72 hours for now. | "8. jwt" / "defaults, 72hours (for now)" | |
| D-007 | 2026-10-20 | Backend only. Frontend is built by another team in parallel. One repo, not a monorepo, no CI. | "frontend isnt there yet, and it will be build parallel by another team, not you, not me." / "only one repo" / "not monorepo. i dont want ci." | |
| D-008 | 2026-10-20 | Docker is out of scope for now (this does not change that PostgreSQL runs in Docker for dev). | "forget docker at this level" | |
| D-009 | 2026-10-20 | Test-driven development at every step. | "also i want test driven development every step." | |
| D-010 | 2026-10-20 | Builder is OpenCode v2.0.29 with minimax m3.1 flash. The user makes all git commits. No MCP servers; use the official FastAPI skill. | "opencode v2.0.29" / "2. minimax m3.1 flash" / "3. me" / "drop mcp, i was confusing with skills. there is official fastapi skill for agents." | |
| D-011 | 2026-10-20 | The first tenure and the dev database are created by hand with db/examples/00_go_live.sql. | "8. by hand" | |
| D-012 | 2026-10-20 | Printable PDFs and reports come later. | "3. later" | |
| D-013 | 2026-10-20 | Build order: ledger, fees, assets, allocation, reconciliation, tenure close. Errors are RFC 9457 problem JSON. Layout is feature folders with domain, application, infrastructure, api. Quality gates are ruff and strict pyright, run locally. | "9. deault" (the user's reply accepting the listed defaults) | |
| D-014 | 2026-10-20 | Schema changes: none by default; any DDL need is reported first and needs explicit approval. | "currently i dont plan changing sql. but if if necessary we can consider maybe" | |
| D-015 | 2026-10-20 | Three-agent flow (tester, coder, reviewer); agents may fetch official docs only after asking; business context is drafted for line-by-line approval; the first OpenCode task is a read-only plan. | "4. ok" / "5. yes." / "6. ok" / "7. draft" | |
| D-016 | 2026-10-20 | Every roadmap step is its own session. Nothing is carried between sessions in memory: all shared knowledge, decisions and instructions live in repo files so any session can start from `/start`. | "all slices should be standalone to their seperate session ... that should be handled in a persistent manner" | |
| D-017 | 2026-10-20 | OpenCode must never assume: when context is missing it asks. | "remember context asking, never assuming. -> this instruction that opencode must follow." | |

## Proposed (NOT authority; found in the generated ROADMAP.md; user must confirm or reject)

| ID | Proposal | Conflict or concern |
|---|---|---|
| P-001 | Alembic migration chain with db/schema.sql executed in place as migration 0001, plus a sha256 guard. | Zero DDL means Alembic only wraps one script; heavy for the current phase. |
| P-002 | API prefix `/api/v1`. | none known |
| P-003 | Publish `docs/openapi.json` and a handwritten `docs/api-contract.md` per feature. | A handwritten contract can drift; a generated openapi.json export may be enough. |
| P-004 | Owner bootstrap CLI that runs migrations, sets the labapp password and opens the first tenure (roadmap 11.3). | Conflicts with D-011 (by hand). |
| P-005 | Dockerfile and compose for app plus PostgreSQL 18 (roadmap 11.4). | Conflicts with D-008. |
| P-006 | Port all worked examples to pytest (Phase 1) before any feature work. | Delays the first running endpoint; per-feature just-in-time porting is an alternative. |

## Open questions

| ID | Question |
|---|---|
| Q-001 | Which of P-001 to P-006 does the user accept, change or reject? |
| Q-002 | Capacity-fill priority for the allocation waterfall: the earlier notes say it was not set and a recommendation was requested. |
| Q-003 | Protection against a double-submitted deposit (the schema has no idempotency key). |
| Q-004 | Frontend origin for CORS. |
| Q-005 | How and when the labapp password (schema default `change-me`) is changed. |

---
## Added 2026-10-20 (second batch). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-018 | 2026-10-20 | Accepts P-001: an Alembic migration chain. The existing db/schema.sql is used first and kept untouched. The database structure should not change in future; if a migration is ever needed, consult the user first. (How migration 0001 executes the script is still to be decided by experiment at that step.) | "alembic proposal i discussed with opencode, first use the schema, try to keep it untouched, and even in future our database structure shouldnt change, if any migration needed, we consult first." | P-001, D-014 |
| D-019 | 2026-10-20 | Accepts P-004: a bootstrap CLI is built so the first start-up things exist. Until it exists, D-011 (by hand) still applies. What exactly it creates is decided at its `/start` brief. | "bootstrap cli, he said i need to start up first things." | P-004, D-011 |
| D-020 | 2026-10-20 | Deployment is barebone (no Docker, no compose). Rejects P-005. The agent's concern is development, not deployment. | "we run build deploy barebone, you have any problem? you concern with development, not deployment." | P-005, D-008 |
| D-021 | 2026-10-20 | The allocation waterfall priority is not set. Cap/priority values in the examples are suggestions only. Code must not hard-code any cap or priority; they are data entered by the treasurer. | "not set, its just suggesstion." | Q-002 |
| D-022 | 2026-10-20 | Models available in OpenCode: minimax m3.1 flash, nemotron 3.5 super vl, beam, longcat 2.5 preview, mimo 2.6 flash, deepseek v4.1 flash, glm 5.3 flash, nemotron 3.5 lightning, nemotron 3 ultra, big pickle. Which model serves which role is NOT decided (Q-006). | the user's numbered list of ten models | D-010 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-001 | accepted -> D-018 |
| P-004 | accepted -> D-019 |
| P-005 | rejected -> D-020 |
| Q-002 | answered -> D-021 |
| Q-003, Q-004, Q-005 | user replied "maybe?": still open; kept as unconfirmed backlog in ROADMAP.md |
| P-002, P-003, P-006 | not yet answered: still proposed |

### Proposed (NOT authority; roadmap changes suggested by Claude, user must accept or reject)

| ID | Proposal |
|---|---|
| P-007 | Contract tests are ported just in time, one example before its feature (steps x.0), instead of porting all examples first; the raw db/examples run on PG18 first (step 0.6). Refines P-006. |
| P-008 | The first ledger step is only the deposit action, built end to end (domain, use case, SQL adapter, route, tests) as a vertical slice; the other ledger actions are separate steps. |
| P-009 | Envelope and cost-center APIs come before the ledger, because every ledger entry needs an envelope. |
| P-010 | No separate "write tests" steps. Under TDD every step writes its own tests first. |
| P-011 | The bootstrap CLI is placed right after the Alembic phase (before the kernel and features), since nothing can run without a tenure. |
| P-012 | No separate "row mappers" step; mappers are written inside the first feature that needs them (no speculative code). |

### Open questions (added)

| ID | Question |
|---|---|
| Q-006 | Which model for which role (/start, /review, /tests, /code)? To be decided after the bake-off (see the chat). Record the exact provider/model strings as OpenCode shows them. |
| Q-007 | Does the bootstrap CLI also create the pool envelope and the envelope list (B-15)? Decide at that step's `/start`. |

---

## Added 2026-10-20 (third batch). Earlier rows above are unchanged.

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-023 (proposed) | 2026-10-20 | The user's initial "0.1" commit (edde64e) already carried a full working tree: Phase 0 tooling deps (incl. `asyncpg-stubs` in the dev group and lockfile), Phase 2/3 shared kernel + error translator, settings (part of 0.5), full auth with JWT/argon2 (Phase 4), and a deposit slice with unit/API tests (6.2 territory). Roadmap ticks lagged the tree. The user instructed: tick 0.1; after verification tick 0.2, 0.3, 0.4; leave `.env.example` in place. | Session `/start` 2026-10-20: `git log` shows only `edde64e` + `c70ea9c` with 78 files / 5,399 insertions in `edde64e`; gates run this session: `uv run pytest` 40 passed, `uv run ruff check .` passed, `uv run ruff format --check .` 61 files formatted, `uv run pyright` 0 errors; `uv sync` clean; pyright probe on an asyncpg.Connection/Record snippet (outside repo) 0 errors. |

## Added 2026-10-20 (fourth batch). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-024 | 2026-10-20 | Step 0.5 settings shape: `Settings` gains a required `admin_database_url: SecretStr` (env key `MESL_ADMIN_DATABASE_URL`, the owner/superuser DSN used only by migrations, bootstrap and tests, never the app runtime); `.env.example` documents it; the plain-`str` app DSN is unchanged. Step type CODE-WITH-TESTS. | "The user approved the step brief for: 1. a 2. b 3. a 4. a go" (a = required admin field; b = SecretStr; a = admin block documented in .env.example; a = CODE-WITH-TESTS) | ROADMAP 0.5, D-006 |

---

## Added 2026-10-20 (fifth batch). Earlier rows above are unchanged.

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-025 (proposed) | 2026-10-20 | Step 0.6 verification run, approved as VERIFY-ONLY (user answered 1.a P-007 confirmed; 2.a verify-only; 3.a throwaway DBs dropped; 4.a report here; 5.a real current date, "go"). All 8 raw `db/examples/*.sql` scripts ran against PostgreSQL 18.0 (docker `postgres:18.0`, D-005) with local psql 18.6 over `TEST_ADMIN_DSN`, into 7 scratch databases created fresh from `db/schema.sql` (`mesl_06_00`; `mesl_06_0102` holds 01+02 because script 02 says "SAME database right after example 1"; `mesl_06_03`…`mesl_06_07`), scripts piped through `psql -f` with a leading `\c <db>` after `-v ON_ERROR_STOP=1` schema load. RESULT: zero differences. Every `EXPECT FAIL` errored and every `EXPECT` row matched the script's stated values: **00** healthy (`verify_all()` empty; balances/suggestion/standing/assets as scripted); **01** all 13 sections (overdraw guard, append-only, entry shapes raised at COMMIT as DEFERRABLE, double-reverse/missing-mirror, closed-tenure guards, tenure close); **02** label edits + history, labapp permission wall, checksum tamper detection (2 problems, then 0 after restore); **03** all 5 standing rows exact, rate change, fix-amount, shutdown undo, close + arrears carry-over (A 190/100/-90/od3), dues tamper detection (3 problems); **04** 2wk/40 billing start, backdated-rate reject, latest-row-wins 22+25=47; **05** both EXPECT asset counts, replacement queue, correction, all 16 rejected mistakes, close + handover register, post-close tamper detection; **06** header 2560/50/2510, suggestion math, priority fill, voided-session ignore, cap override, 9 bad-allocation rejects, envelope guards, sweep lifecycle, sessions survive close; **07** matched/mismatched checks, timer review rows, all 6 suspect heuristics + the +77 no-match + late cross-tenure entry, per-envelope mismatch (matched=f, diff=0), bad-`reconcile` rejects, screen-total tamper (1 problem). One nuance for future porting (steps x.0): in **01 §8** the third rejected case ("wrong mirror") errors via the *balance guard* before any mirror-specific check — it does error as the script requires, but the 6.x test-porter should assert the intended reason, not just an error. Scratch DBs all dropped (count of `mesl_06_%` databases now 0). Gates still green after (pytest 49 passed, ruff clean, format clean, pyright 0 errors). No repo or schema file was changed by the run itself. | Raw psql outputs kept session-only under `/tmp/opencode/ex06/` (`out_00.txt`, `mesl_06_0102.out`, `mesl_06_03.out`…`mesl_06_07.out`); the fact table above is the durable record and the session transcript shows the full outputs. |

---

## Added 2026-10-20 (sixth batch, step 1.1). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-026 | 2026-10-20 | Step 1.1 is NO-TEST type; `alembic/env.py` reads the owner DSN from the raw env var `MESL_ADMIN_DATABASE_URL` (not via `Settings`); `alembic.ini` + `alembic/` at the repo root. | "The user reviewed and approved the tests for: 1. a 2. a 3. confirm  go" (per the brief: a = NO-TEST; a = raw env var; confirmed root layout) | ROADMAP 1.1 |
| D-027 | 2026-10-20 | Standing rule accepted: on ANY permission denial (edit or shell) the agent must STOP, report the exact denial to the user, and take no probing/workaround steps until the user decides. | "so this literally says ask, but you didnt ask. you assumed denied and tried to bypass the barrier!" (user's rebuke after the agent probed `whoami`/`id`/`touch` files following an edit denial); explicit "no" to further attempts | AGENTS.md section 0 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-028 (proposed) | 2026-10-20 | OpenCode v2.0.29 agent permission lists behave against the docs: an `allow` rule placed AFTER a matching catch-all `deny`/`ask` rule does NOT rescue the request (silent deny, no prompt shown to the user) — observed for both `edit` and `shell` on `.opencode/agents/coder.md` and `reviewer.md`. Working order (verified green after the reorder): specific allow rules FIRST, catch-all deny LAST. Steps that verified: `uv run pytest` 49 passed, ruff check/format clean, pyright 0 errors re-run under the reviewer agent after the reorder. | Session log + tool denials this session; docs page opencode.ai/docs/permissions claims "last matching rule wins" |
| D-029 (proposed) | 2026-10-20 | In v2.0.29, permission prompts for `edit` with `effect: ask` never reached the user (auto-rejected); the user worked around it by flipping the affected rules to `allow`. Worth retesting after an OpenCode upgrade (latest: 2.0.32). | write attempts on `alembic.ini` 2026-10-20: three deny events with no visible prompt; success only after rules changed to `allow` |

---

## Added 2026-10-20 (seventh batch, step 1.2). Earlier rows above are unchanged.

### Discovered facts (proposed; verified from tool output this session; CONFIRMATION REQUESTED at review)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-030 (proposed) | 2026-10-20 | Roadmap 1.2 outcome: **option (a) confirmed by experiment — revision 0001 executes `db/schema.sql` whole on the raw asyncpg connection Alembic owns — WITH one non-negotiable correction: the revision must own a server-side transaction itself** (`async with raw.transaction():` around the whole-file execute), because the raw simple-protocol writes do NOT reliably join Alembic's per-migration transaction. Facts behind it: (1) a prepared statement is one statement, and SQLAlchemy's asyncpg dialect cursor path always prepares (`AsyncAdapt_asyncpg_cursor._prepare_and_execute` -> `_prepare` -> `connection.prepare`), so the whole file CANNOT go through `Connection.execute(text(...))` — splitter (b) is unnecessary, raw access (a) is required. (2) Whole-file raw execute works: throwaway revision `9999_0001_experiment` ran `alembic upgrade head` on a fresh scratch DB -> alembic_version stamped, `verify_all()` empty (healthy), all 20 public tables of db/schema.sql present. (3) UNWRAPPED raw execute runs in AUTOCOMMIT: probe C (second revision in a chain after a successful one, table created then Python raise) -> `raw.is_in_transaction()` was False before and after the CREATE, and `probe_should_not_exist` SURVIVED the failing migration (0001 + stamp survived; per-migration rollback unaffected). Alembic's per-migration transaction is real on the ADAPTER (cursor) path — probe A as the FIRST migration rolled back correctly — but the unwrapped raw path escaped it. (4) WRAPPED execute (the correction): probe D (same chain, same failing revision, but `async with raw.transaction():` around the execute, one `await_` from the greenlet and plain awaits inside — nested `await_` raises `MissingGreenlet`) -> probe table GONE after the failure, tenures + 0001 stamp intact: full per-migration atomicity. (5) The adapter is bypassed (`op.get_bind().connection` is a `_ConnectionFairy`; `.driver_connection` -> `PGDialect_asyncpg.get_driver_connection` -> the real asyncpg Connection). (6) db/schema.sql has no psql metacommands and no top-level BEGIN/COMMIT (conftest has run it raw all along; step 0.6 verified its behavior on PG18). Verified APIs: sqlalchemy 2.1.5 `Connection.connection` (base.py:581), `_ConnectionFairy.driver_connection` (pool/base.py:1295) -> `get_driver_connection` (dialects/postgresql/asyncpg.py:1318); `sqlalchemy.util.await_` requires greenlet_spawn context, no nesting (util/concurrency.py:143-167); asyncpg 0.32.0 `Connection.execute` runs many statements with no args (asyncpg/connection.py:326-378), `Connection.transaction()` context manager (asyncpg/transaction.py:63-75: `__aexit__` rolls back on exception); alembic 1.20.0 `begin_transaction` per-migration real-transaction path (alembic/runtime/migration.py:405-460, `alembic/util/sqla_compat.py:176-183`). All experiment revisions and scratch DBs (mesl_12_*) were thrown away; working tree left with only this entry. | Session `/code` 2026-10-20: probe outputs pasted in the session; gates after cleanup: `uv run pytest` 49 passed, `uv run ruff check .` passed, `uv run ruff format --check .` 63 files formatted, `uv run pyright` 0 errors |

### Worth recording for the reviewer (proposed)

| Row | Note |
|---|---|
| Runner mishaps this session (no repo impact) | The experiment runner had two self-inflicted bugs (mangled re-restore of `*.hidden`, `isolate()` revealing two probe files at once -> "Multiple head revisions" refused by alembic with nothing executed), plus one probe-code bug (nested `await_` -> `MissingGreenlet` before any SQL ran), which produced VACUOUS passes twice before probe C/D ran for real. Every probe verdict above comes from a run where the probe traceback proves the probe executed. Lesson for the reviewer: absence-based asserts on a DB that the probe never ran are not evidence. |

## Added 2026-10-20 (eighth batch, step 1.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-031 | 2026-10-20 | Confirms D-030 as THE step 1.2 decision: revision 0001 executes db/schema.sql whole on the raw asyncpg connection Alembic owns, and the revision must own a server-side transaction itself (`async with raw.transaction():` around the whole-file execute); a statement splitter is unnecessary. | Asked directly ("Do you confirm this as the decision for step 1.2?") the user answered "Confirm (Recommended)"; after the review had presented D-030 for confirmation the user also said "i reran uv run pytest and all passed. continue" | D-030, ROADMAP 1.2 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-032 (proposed) | 2026-10-20 | Gate runs from agent subshells can be red for ENVIRONMENTAL reasons only: the dev PostgreSQL 18.0 container (postgres-db-1, D-005) publishes host port 5434, nothing listens on 5432, and `TEST_ADMIN_DSN` is NOT set inside an agent subshell (unset env) — conftest's connect attempt then goes to localhost:5432 and fails. In the user's own shell, where the variable is set, `uv run pytest` passes (49 tests). A subshell pytest ending in `OSError: [Errno 111] Connect call failed ... 5432` is an env gap, not a code/test failure; ask the user to run that gate in their shell. | This session: `docker ps` (postgres:18.0 Up, 5434->5432), `ss -ltn` (nothing on 5432), env probe (TEST_ADMIN_DSN set: False), subshell `uv run pytest` -> 49 setup errors all refusing 5432 while the user's run of the same suite passed the same day. |

## Added 2026-10-20 (ninth batch, step 1.5 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-033 | 2026-10-20 | Step 1.5 is TEST-ONLY (no `/code`): the sha256 guard is a pure unit test at `tests/test_schema_hash.py`, loading `SCHEMA_SHA256` from `alembic/versions/0001_initial.py` by path; the stale `alembic.ini` comment ("guard tests live beside them") is left untouched; coverage proof is the single roadmap assertion, since no `db/examples` script covers this step. | "1. a 2. a 3. a 4. a 5. a" and "go, all default / your suggestion accepted." | ROADMAP 1.5 |
| D-034 | 2026-10-20 | Step 1.4 (`tests/conftest.py` builds the template via `alembic upgrade head`) is complete in commit `f7a88ee` but was never ticked; the user confirms completion and chose a separate docs commit to tick it. | "1.4 is done, forgot to tick" | ROADMAP 1.4 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-035 (proposed) | 2026-10-20 | D-032 did not reproduce during step 1.5: `TEST_ADMIN_DSN` was set in the agent subshell and host port 5434 was listening, so the agent ran the full suite (51 passed). Later the harness removed the `shell` tool from the agent catalog mid-session, so the closing gates were run by the user (51 passed in 4.77s; ruff/format/pyright green). A missing tool in the agent catalog is a harness gap to report, not a code failure. | `ss`/env probe this session; user-pasted gate run; `No tool named "shell" is currently available` |

## Added 2026-10-20 (tenth batch, step 1.6). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-036 | 2026-10-20 | Step 1.6 convention approved as drafted in the step brief: the Alembic chain is the migration history; `db/schema.sql` is revision 0001's payload and is never edited; after 0001 each approved schema change is one hand-written payload `db/sql/NNN_<slug>.sql` plus one thin revision `alembic/versions/NNN_<slug>.py` (same NNN and slug, starting at 0002) that executes the payload whole on the raw asyncpg connection inside `async with raw.transaction():` (D-031); payloads and revisions are append-only; no autogenerate. `db/sql/` is created now with a `.gitkeep`; per-payload sha256 guards are deferred to the first real migration. The exact AGENTS.md wording was approved as drafted (section 0, section 1 table and authority order, section 3, new section 5 subsection). | "6b, 7b, rest as you suggested. go." (Q1=a, Q2=a, Q3=a, Q4=a, Q5=a) | D-018, D-031, ROADMAP 1.6 |
| D-037 | 2026-10-20 | Step 1.6 also repoints the two stale SQL-source lines in `.opencode/commands/code.md` and `.opencode/commands/review.md`, and grants the coder agent edit permission for `AGENTS.md` and `DECISIONS.md` in `.opencode/agents/coder.md` so the approved wording can be applied; specific allow rules stay before the catch-all deny (D-028). The stale `alembic.ini` comment and the `alembic/env.py` docstring stay untouched (D-033). | "6b, 7b, rest as you suggested. go." | D-028, D-033, ROADMAP 1.6 |

## Added 2026-10-20 (eleventh batch, step 1.6 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-038 | 2026-10-20 | Step 1.6 closes with the reviewer permission fix: `.opencode/agents/reviewer.md` keeps `shell "*"` allowed (needed to run the four gates) and restores `edit "*"` to `deny`, so the reviewer stays read-only as its description and AGENTS.md section 2 require. D-036/D-037 stand unchanged. The tool-name rule requested this session is now AGENTS.md section 3 ("`shell` (never `bash`) ... If a tool is missing or a call is refused: STOP and report the exact error. Do not probe."). | "i allowed shell for you" and "add those permission fixes too in this commit" | D-027, D-037, ROADMAP 1.6 |

## Added 2026-10-20 (twelfth batch, step 1.7 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-039 | 2026-10-20 | Step 1.7 brief approved as drafted: P-011 confirmed (bootstrap directly after the Alembic chain); the CLI takes required `--tenure-name` / `--opened-on` CLI options (Q4=a, no invented defaults); is idempotent — if an open tenure exists it skips and exits 0 (Q5=a); documented invocation `PYTHONPATH=src uv run python -m mesl_finance.bootstrap` (Q7=a); the CLI reads config through Settings (full `.env`). | "The user approved the step brief for: 1.7. all suggestions accepted (if empty, the step briefed earlier in this session)." (the brief's labelled suggestions 1a/2b/3a/4a/5a/6 moot/7a) | ROADMAP 1.7, P-011 |
| D-040 | 2026-10-20 | Resolves Q-005: the bootstrap CLI sets the password of the login ROLE NAMED IN MESL_DATABASE_URL to that DSN's password (parsed with sqlalchemy.make_url); no new setting is added, so the role password can never drift from the app DSN. | "all suggestions accepted" (Q3=a was the labelled suggestion) | D-039, Q-005, D-024 |
| D-041 | 2026-10-20 | Resolves Q-007: the bootstrap CLI creates exactly the pool envelope (`name='Unallocated General'`, `is_pool=true`) and the first tenure; the other envelope names, caps and priorities are treasurer-entered data (D-021), not hard-coded by the CLI. | "all suggestions accepted" (Q2=b was the labelled suggestion) | D-039, Q-007, D-021 |
| D-042 | 2026-10-20 | The tester-phase test defect (direct logins in `tests/test_bootstrap.py` passed a `postgresql+asyncpg://` DSN straight to `asyncpg.connect`, which asyncpg rejects) was fixed by the approved option 1: a `_login_dsn` helper strips `+asyncpg` for the two direct logins; the env-var value keeps `+asyncpg`, so the CLI is proven to normalize the DSN itself. | "The user approved the step brief for: go with 1" | AGENTS.md section 0 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-043 (proposed) | 2026-10-20 | alembic.ini records `script_location` AND `version_locations` relative to the cwd (lines 6 and 10); run from any other cwd, `ScriptDirectory.walk_revisions()` returns an EMPTY list (probe: `revisions: []`) and `alembic upgrade head` exits 0 as a silent NO-OP — no "Running upgrade" log line, no error, nothing migrated. `Config.set_main_option("script_location", ...)` alone is NOT enough; the bootstrap CLI overrides BOTH with absolute paths derived from `__file__` (`src/mesl_finance/bootstrap.py::_run_migrations`). conftest/pytest are unaffected (repo-root cwd). | Child probe output `cwd: /tmp/..., revisions: []`; failing CLI runs this session (`UndefinedTableError: relation "tenures" does not exist`, rc=1, no Running-upgrade line); all 7 tests green after the absolute-path override |
| D-044 (proposed) | 2026-10-20 | `ALTER ROLE ... PASSWORD` accepts a string constant only; a bind parameter is not accepted there, so secret values are quoted SERVER-SIDE: `SELECT format('ALTER ROLE %I PASSWORD %L', $1::text, $2::text)` executed over bound params, the returned statement carries PostgreSQL's own quoting. Separately, `asyncpg.connect` refuses the `postgresql+asyncpg` scheme (`asyncpg/connect_utils.py:324`: scheme must be `postgresql` or `postgres`); any asyncpg DSN built from Settings must strip `+asyncpg` first. | connect_utils.py:324 read this session; step 1.7 tests: 7 passed (both facts exercised live) |

## Added 2026-10-20 (thirteenth batch, step 1.8). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-045 | 2026-10-20 | Step 1.8 brief approved as drafted: tests use the CURRENT Sunday (`sunday_on_or_before(current_date)`), not a pinned date, with all expected numbers derived from the schema functions (1b); the two checks the script implies in comments are included as tests — a second 'opening' entry rejected and `labapp` denied an INSERT on `tenures` (2a); step type TEST-ONLY, tests expected to pass at once (3a). | "The user approved the step brief for: 1b 2a 3a go (if empty, the step briefed earlier in this session)." | ROADMAP 1.8, P-007 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-046 (proposed) | 2026-10-20 | `db/examples/00_go_live.sql` contains no machine-readable `EXPECT`/`EXPECT FAIL` lines (64 lines read in full); for just-in-time ports of such scripts the coverage proof is a numbered-section table (kept in the new test file's module docstring) instead of EXPECT-line mapping. Also: — after `allocate`, `allocation_context.pool_balance` sits at the POST-allocation value (2600 in the script scenario), so a faithful port must read the context/suggestion BEFORE calling `allocate`, mirroring the script's §§7 order. | audit finding re-checked this session; 13 go-live tests + full suite 71 passed with gates green |

## Added 2026-10-20 (fourteenth batch, step 2.1). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-047 | 2026-10-20 | Step 2.1 shape of `Money`: non-negative with zero allowed ("1. a"); no arithmetic operators — PostgreSQL owns the sums, an operator is added later only together with its test ("3. it should be b, as much as i understand from sql, do we need arithmetic?"); construction accepts ONLY a real `int` (bool rejected even though it subclasses int; float/Decimal/str refused) ("4. a"); the value property is named `amount` ("5. n/a" on the naming question). | "1. no sql change, do what code needs. this codes was just as guide, so it doesnt matter that it exist" / "2. a" / "3. it should be b, as much as i understand from sql, do we need arithmetic?" / "4. a" / "The user approved the step brief for: 1. a go" | ROADMAP 2.1, B-02 |
| D-048 | 2026-10-20 | `shared/errors.py` (which already existed in the pre-roadmap guide tree, D-023) is accepted AS-IS and is FROZEN: step 2.1 adds only guard tests; a later step may add a new error only together with its test (same rule as the error translator). | "a a a(ask me in details, no migration, cant we change code term? or will that be catastrophic?)" (brief Q1/Q2 answered a/a) and "2. a" | ROADMAP 2.1, D-023 |
| D-049 | 2026-10-20 | Approved exception to "the coder cannot edit tests/": a mechanical FORMATTER fix (E501 line-wrap of two test signatures, zero behaviour change, proven by pytest green) inside `tests/shared/test_errors.py` done by the coder with explicit user approval. Other test edits stay tester-domain. | "1" (option 1 = "approve me making that mechanical reformat ... no logic touched") | AGENTS.md section 2, D-042 |
| D-050 | 2026-10-20 | In this session's harness catalog there is NO `edit`/`write`/`patch` tool. Files were written through `shell` heredocs (reported at the time, never probed). If a future session's catalog regains an edit tool, prefer it. | Tool-catalog listing at session start (no edit tool); D-027-style stop not triggered because `shell` was available and no permission refusal occurred | AGENTS.md section 3 |

## Added 2026-10-21 (fifteenth batch, step 2.2). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-051 | 2026-10-21 | Step 2.2 shape approved: CODE-WITH-TESTS with four guard tests in `tests/shared/test_ports.py`; both ports `@runtime_checkable`; `Clock` has a single method `now() -> datetime` returning a timezone-aware UTC instant (Q4=a); the shared `UnitOfWork` Protocol holds transaction scope (`__aenter__`/`__aexit__`, `commit`) plus an `actor` property ONLY — repository accessors are declared by each feature's own protocol (Q3=a); the ledger's `LedgerUnitOfWork` is refactored to extend the shared protocol and any pre-existing duplication is removed (Q2=a); the `SqlUnitOfWork` vs ROADMAP 3.2 naming question is deferred to 3.2's `/start` (Q5=a). Tests were separately reviewed and approved. | "The user approved the step brief for: all suggestions accepted. go (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for: (if empty, the step in this session)." | ROADMAP 2.2, D-002, D-009 |

### Discovered facts / proposals (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-052 (proposed) | 2026-10-21 | Naming mismatch parked per D-051 Q5=a: ROADMAP 3.2 names the future concrete unit of work `SqlAlchemyUnitOfWork`, but the existing concrete class is `SqlUnitOfWork` (`src/mesl_finance/shared/infrastructure/database.py:21`), now exposing a read-only `actor` property (added step 2.2, +5 lines, so `SqlLedgerUnitOfWork` structurally satisfies the shared port that `main.py`'s factory lambda must conform to). Resolve at 3.2's `/start`: adopt the roadmap name in a rename commit, or amend the roadmap wording. | Step 2.2 review finding (reviewer item 7, FAIL then fixed by this entry); `git diff --stat` showed database.py +5/-0; tester/coder reports this session |

## Added 2026-10-21 (sixteenth batch, step 3.1). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-053 | 2026-10-21 | Step 3.1 brief and shape approved with the agent's suggestions: (Q1=a) TEST-ONLY — the async engine already existed in the pre-roadmap tree (D-023) and is accepted as-is, guard tests pin it; (Q2=a) the "session factory" is the existing shape — `create_engine(settings)` plus constructing `SqlUnitOfWork(engine, actor)`, no separate factory; (Q3=a) the engine's `server_settings: {"timezone": "Asia/Dhaka"}` is accepted as-is (D-005); (Q4=a) nothing to do about the unpushed commits. | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for: (if empty, the step in this session)." | ROADMAP 3.1, D-003, D-005, D-023 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-054 (proposed) | 2026-10-21 | Pyright strict DOES have `reportPrivateUsage` active here: accessing `Pool._pre_ping` in `tests/shared/test_database_engine.py:86` produced `error: "_pre_ping" is protected ... (reportPrivateUsage)` and is suppressed with `# pyright: ignore[reportPrivateUsage]` plus a source citation. SQLAlchemy exposes pre-ping only through that private attribute (sqlalchemy/engine/create.py:649-667 pops `pool_pre_ping` and passes `pre_ping` to the Pool; sqlalchemy/pool/base.py:282 stores `pool._pre_ping`; `AsyncEngine.pool` is the public path, ext/asyncio/engine.py:1251). | gate run this session: pyright 1 error before the suppression, 0 errors after; other calls verified in the same installed source (AsyncConnection.scalar ext/asyncio/engine.py:705; StartableContext __aenter__ ext/asyncio/base.py:151; engine.dispose engine.py:1145) |

### Evidence for the step close

Gates this session: `uv run pytest` 120 passed (115 pre-existing + 5 new, all green throughout); `uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "75 files already formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit found no defect (reviewer PASS with the wait-for-notes note below now written: D-053/D-054 above and the ROADMAP 3.1 tick).

## Added 2026-10-21 (seventeenth batch, step 3.2). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-055 | 2026-10-21 | Step 3.2 brief approved with all labelled suggestions: (Q1=b) the concrete class keeps the name `SqlUnitOfWork`; ROADMAP 3.2's wording is amended at wrapup instead of renaming code (resolves D-052); (Q2=a) step type TEST-ONLY — the UoW already exists in the pre-roadmap tree (D-023) and is accepted as-is, no `/code`; (Q3=a) error mapping inside `execute`/`commit` is excluded from 3.2's guard tests and stays step 3.3 territory. The six guard tests in `tests/shared/test_unit_of_work.py` (protocol conformance, actor set transaction-local, no actor leak outside the transaction, rollback discards, commit persists, writes invisible to others before commit) were reviewed and approved. | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." | ROADMAP 3.2, D-052, D-051, D-053 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| D-052 (proposed) | answered -> D-055: keep `SqlUnitOfWork`; the ROADMAP 3.2 wording now says `SqlUnitOfWork` (amended in the step's commit) |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-057 (proposed) | 2026-10-21 | `runtime_checkable` Protocol isinstance checks pass for `SqlUnitOfWork` against `shared/ports.UnitOfWork` because the check is structural member presence (property `actor` + `__aenter__`/`__aexit__`/`commit`); no behaviour is proven by that test — the five DB-backed tests prove behaviour. Guard-test evidence this session: 6 passed; full suite 126 passed; ruff check/format clean; pyright 0 errors. | gates run 2026-10-21 (pytest 126 passed; reviewer re-run same result); stdlib `typing.runtime_checkable` source read this session |

### Evidence for the step close

Gates this session: `uv run pytest` 126 passed (120 pre-existing + 6 new, all green throughout — final re-run also 126 passed); `uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "76 files already formatted"; `uv run pyright` "0 errors, 0 informations". Audit found no defect (reviewer PASS; the wrapup notes this batch records are: the ROADMAP 3.2 tick + wording amendment, D-055, D-052 resolution, D-057).

## Added 2026-10-21 (eighteenth batch, step 3.3 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-058 | 2026-10-21 | Step 3.3 shape approved: Q1=b - a NEW domain error `Unique` (subclass of `RuleViolation`: `code="unique"`, `title="Already exists"`), added to `shared/errors.py` together with its tests in `tests/shared/test_error_translator.py`; Q2 and Q3 were left unanswered, so the brief's recorded suggestions stand: the translator carries the constraint name inside the server's 23505 message text with NO per-constraint-name rule table until a consumer needs one; step type CODE-WITH-TESTS (the P0001/23503/commit-time rules predated the step and the green tests pin them; /code added only the 23505 branch). | "The user approved the step brief for: q1=b go (if empty, the step briefed earlier in this session)." + "The user reviewed and approved the tests for:" (generic test approval, no override) | ROADMAP 3.3, D-048, D-055 Q3 |
| D-059 | 2026-10-21 | `Unique` exists in the translator's detail as the SERVER's message (which names the constraint, e.g. `envelopes_name_key`), NOT as a separate annotated field or a new project-side error class - the detail is exactly the driver message; tests 4/7 fail loudly if the server's 23505 text ever stops naming the constraint. | Step 3.3 /code + /review session run (test passed as-is with the minimal mapping; constraint verified from `pg_constraint` output the same session) | ROADMAP 3.3 Q2 |


## Added 2026-10-21 (nineteenth batch, step 4.1 close). Earlier rows above are unchanged.

**Note on step numbering:** ROADMAP Phase 3 ends at the ticked 3.3, so the session's fallback
("first unticked step whose prerequisites are all ticked") selected 4.1; there is no step 3.4.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-060 | 2026-10-21 | Step 4.1 brief approved: questions Q1-Q3 were left unanswered, so the brief's labelled suggestions stand — (Q1=a) TEST-ONLY, the pre-existing `Argon2CredentialChecker` accepted as-is with no `/code`; (Q2=a) the settings-hash wiring test kept; (Q3=a) the pre-existing Phase-4 checker confirmed as accepted as-is (extending the D-023 pattern used for phases 2-3). Five guard tests in `tests/auth/test_credentials.py`: correct credentials verify, wrong password rejected, garbage hash rejected without a raise, wrong username rejected, and verification against the `Settings.auth_password_hash` value itself. | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." | ROADMAP 4.1, D-006, D-023 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-061 (proposed) | 2026-10-21 | argon2-cffi 25.1.0: `PasswordHasher.verify(hash, password)` returns `Literal[True]` or raises `VerifyMismatchError` (a `VerificationError` subclass) on a mismatch and `InvalidHashError` (a `ValueError`) when the hash's 9-character header is unknown, so `Argon2CredentialChecker`'s `except (VerificationError, InvalidHashError)` covers every documented failure. Test hashes are built with a local low-cost hasher (`time_cost=1, memory_cost=8, parallelism=1`), the same parameters the `settings` fixture uses. | installed source `.venv/lib/python3.15/site-packages/argon2/_password_hasher.py:215-260` and `argon2/exceptions.py:14,40`; `uv run python -c` -> argon2-cffi 25.1.0, Python 3.15.0 |

### Evidence for the step close

Gates this session: `uv run pytest` 138 passed (133 pre-existing + 5 new); `uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "78 files already formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit PASS on all eight items (scope, library args, SQL names, layering, SQL safety, no stubs, unwritten facts, gates).

## Added 2026-10-21 (twentieth batch, step 4.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-062 | 2026-10-21 | Step 4.2 shape: Q1-Q3 were left unanswered, so the brief's labelled suggestions stand — (Q1=a) rename the route dependency `current_user` -> `current_actor` (the roadmap's name; 2 lines in `auth/api/dependencies.py` and `ledger/api/router.py`), (Q2=a) the seven guard tests as listed in the brief, (Q3=a) the dependency tests in a NEW file `tests/auth/test_current_actor.py`. Because the approved tests passed at once (the JWT service, dependency and their earlier tests pre-existed per D-023), option 1 of the `/code` brief stands: they are accepted as green guard tests and `/code` performs only the rename. | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." then "Write the smallest code that makes the approved tests pass." | ROADMAP 4.2, D-023, D-006, D-060 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-063 (proposed) | 2026-10-21 | PyJWT 2.15.1 details behind the 4.2 guards: `jwt.encode` converts `exp`/`iat`/`nbf` `datetime` values to intDate, so `JwtTokenService` may pass datetimes; `options={"require": ["exp","sub"]}` makes a token missing either claim raise `MissingRequiredClaimError`; an HS512 token decoded with `algorithms=["HS256"]` raises `InvalidAlgorithmError`; every one of these is a `PyJWTError` subclass, so `tokens.py`'s single `except jwt.PyJWTError` maps them all to `InvalidToken`. HMAC keys shorter than the SHA-512 digest size (64 bytes) trigger `InsecureKeyLengthWarning`, so the HS512 guard signs and verifies with an 81-byte secret. Full suite 145 passed (138 + 7). | `.venv/lib/python3.15/site-packages/jwt/api_jwt.py:92-100,126-141,176-196,384-433`; `jwt/exceptions.py:1-12,65,71`; gates run 2026-10-21 |

### Evidence for the step close

Gates this session: `uv run pytest` 145 passed (138 pre-existing + 7 new); `uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "79 files already formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit result: item 7 FAIL until this batch was appended; all other seven items PASS.

## Added 2026-10-21 (twenty-first batch, step 4.3 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-064 | 2026-10-21 | Step 4.3 shape: (Q1=a) P-002 confirmed - one top-level `/api/v1` prefix in `main.py` wrapping the auth and ledger routers (`API_PREFIX`, `include_router(prefix=...)`), while `/docs` and `/openapi.json` stay at the root; (Q2=a) the framework's own HTTP errors (404/405) are translated to problem JSON with `code` from a small status map (404 `not_found`, 405 `method_not_allowed`, fallback `http_error`), `title` from `http.client.responses`, `detail` from the exception and its headers (e.g. `Allow`) forwarded; (Q3=a) new test package `tests/api/`; (Q4=a) the pre-existing login-API tests stay in `tests/auth/test_login_api.py`, only their paths updated; (Q5=a) a test pins that the unprefixed `/auth/login` is gone (404); (Q6=a) `create_app(settings: Settings | None = None)` and the `app.state` wiring stay unchanged. Q1-Q6 were answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062). | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for: (if empty, the step in this session)." | ROADMAP 4.3, P-002, D-006, D-013 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-002 | accepted -> D-064: the API lives under `/api/v1` |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-065 (proposed) | 2026-10-21 | Problem-JSON details behind 4.3: FastAPI 0.150.0's default `HTTPException` handler returns `{"detail": ...}` with `application/json` (`fastapi/exception_handlers.py`), so framework 404/405 were not problem JSON before this step; Starlette dispatches exception handlers by walking `type(exc).__mro__` (`starlette/_exception_handler.py:16-20`), so ONE `StarletteHTTPException` handler also catches `fastapi.HTTPException`; a 405 is raised with `headers={"Allow": "POST"}` (`starlette/routing.py:278-279`), which the handler must forward; `http.client.responses` gives the standard phrases ("Not Found", "Method Not Allowed"). `shared/api/problems.py::problem()` now takes `headers: Mapping[str, str] | None` and only applies its `WWW-Authenticate: Bearer` default when status is 401 AND no headers were supplied. Tests: `tests/api/test_app_factory.py` (3) + `tests/api/test_problem_json.py` (5); full suite 153 passed (145 pre-existing files + 8 new guards), ruff/format/pyright green. | installed-source reads listed above; gates run 2026-10-21 |

## Added 2026-10-21 (twenty-second batch, step 5.1 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-066 | 2026-10-21 | Step 5.1 shape: (Q3=b) cap and priority are set on create AND through a separate `POST /api/v1/envelopes/{id}/settings` action; Q1-Q2 and Q4-Q9 were left unanswered, so the brief's labelled suggestions stand: Q1=a P-009 confirmed (envelopes before cost centers), Q2=a action-style routes (`POST /envelopes`, `GET /envelopes`, `POST /envelopes/{id}/rename`, `POST /envelopes/{id}/settings`, `POST /envelopes/{id}/deactivate`), Q4=a the list is every envelope in id order with no balance, Q5=a an unknown id is 404 `not_found` (the router raises `HTTPException(404)` and the existing handler formats it), Q6=a a CHECK violation is 409 `rule_violation` through the shared translator, Q7=a blank names are refused by the app (422 `validation_failed`), Q8=a the pool may be renamed (the schema forbids changing `is_pool`, not `name`), Q9=a all operations in one session. | "The user approved the step brief for: q3=b go (if empty, the step briefed earlier in this session)." | ROADMAP 5.1, P-009, D-021, D-064 |
| D-067 | 2026-10-21 | The `settings` action's semantics, as pinned by the approved tests: the body replaces BOTH `target_cap` and `alloc_priority`, both fields required and nullable (null clears; an omitted field is 422 `validation_error`). This detail was not in the brief, so it is recorded from the approved test `test_settings_without_both_fields_is_422`. | "The user reviewed and approved the tests for:  (if empty, the step in this session)." | D-066, ROADMAP 5.1 |
| D-068 | 2026-10-21 | The shared error translator gained exactly ONE rule in this step: SQLSTATE 23514 (table CHECK violation) -> `RuleViolation` (409 `rule_violation`), so PostgreSQL keeps owning `envelopes.target_cap >= 0` (db/schema.sql:69) instead of the app duplicating it. Pinned end to end by the two negative-cap API tests. | "q3=b go" plus the generic test approval (D-066/D-067); Q6=a was the brief's labelled suggestion | ROADMAP 5.1, AGENTS.md section 5, D-059 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-009 | accepted -> D-066: envelope actions come before cost centers (5.2 is now the next eligible step) |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-069 (proposed) | 2026-10-21 | Two gate facts for later test/code sessions. (1) ruff's isort classifies an import of a module that does not exist yet as THIRD-party, so a test that pins a not-yet-created package must import it lazily or its import block has to be re-sorted the moment the package appears; `tests/envelopes/unit/test_envelope_domain.py:34-42` does this via `import_module` + `vars(module)["Envelope"]` (B009 forbids a constant-name `getattr`). (2) ruff `S608` flags f-string SQL even when the interpolated part is a module-level constant column list, so `src/mesl_finance/envelopes/infrastructure/repository.py` inlines its column list in every statement instead of sharing a constant. | `/tmp/isort-probe` runs (module absent -> I001 wants third-party grouping; module present -> first-party grouping) and the red `ruff check .` run before the repository rewrite, then green gates |

### Evidence for the step close

Gates this session: `uv run pytest` 188 passed (153 pre-existing + 35 new: 9 domain, 26 API);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "103 files already formatted";
`uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS, item 7 FAIL
until this batch and the ROADMAP tick were written.

## Added 2026-10-21 (twenty-third batch, step 5.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-070 | 2026-10-21 | Step 5.2 shape: (Q8=b) the cost-center list also filters on `kind` and `status`. Q1-Q7 and Q9 were left unanswered, so the brief's labelled suggestions stand: Q1=a four action routes (`POST /cost-centers`, `GET /cost-centers`, `POST /cost-centers/{id}/rename`, `POST /cost-centers/{id}/status`); Q2=a the status action is `POST .../status` with body `{"status": ...}`; Q3=a create takes `name` + `kind` only and the database default makes it `active`; Q4=a blank names are refused by the app (422 `validation_failed`) although `db/schema.sql:79` only says NOT NULL; Q5=a PostgreSQL's CHECKs own the four kinds and four statuses (23514 -> 409 `rule_violation`, no Python duplication); Q6=a `kind` is fixed at create; Q7=a any status may be set at any time (no transition rules invented); Q9=a the 23505 test pins the constraint name. | "The user approved the step brief for: q8=b go (if empty, the step briefed earlier in this session)." | ROADMAP 5.2, D-066, D-068, D-059 |
| D-071 | 2026-10-21 | The step 5.2 tests were approved as written, including the three deviations forced by the answers: the "explicit status at create" domain test was dropped (Q3=a), the "app refuses an unknown kind" domain test was dropped (Q5=a), and the "no filters" list test was replaced by unfiltered + `?kind=` + `?status=` tests (Q8=b). The filters are optional, combinable in one query, and the app validates no filter value; no test pins an invalid filter value because no rule defines one (the SQL equality simply matches nothing). | "The user reviewed and approved the tests for:  (if empty, the step in this session)." | D-070 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-072 (proposed) | 2026-10-21 | Step 5.2 facts for later sessions. (1) The cost-center constraint names, read live from `pg_constraint` on the session template: `cost_centers_kind_name_key` (UNIQUE (kind, name)), `cost_centers_kind_check`, `cost_centers_status_check`; the API tests assert those names. (2) `TEST_ADMIN_DSN` here points at database `decentdeath`, not `postgres`, and the same server holds 14 leftover `mesl_dbg_*` databases (left untouched). `psql "$TEST_ADMIN_DSN" -c ... mesl_test_template` reported 0 public tables while `asyncpg` on the same DSN reported 21: for auditing the template, connect with an explicit database in the DSN (asyncpg/python), not a psql positional argument. (3) The cost-center domain exposes a public `require_name()` helper (`cost_centers/domain/cost_center.py`) that the rename use case calls, so the blank-name rule exists once, in the domain. | `pg_constraint` and `pg_tables` queries this session; `uv run pytest` gate output |

## Added 2026-10-21 (twenty-fourth batch, step 6.0 close). Earlier rows above are unchanged.

**Note on step numbering:** the session asked for 5.3, which does not exist (Phase 5 ends at the
ticked 5.2), so the fallback ("first unticked step whose prerequisites are all ticked") selected
6.0, as in the 4.1 session (see the note before D-060).

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-073 | 2026-10-21 | Step 6.0 shape, as drafted in the step brief: Q1=a the step is 6.0; Q2=a P-007 confirmed (contract tests ported just in time); Q3=a a local `example_01()` helper inside the new test file replays example 1 (no shared conftest scenario); Q4=a the six blocked statements assert `asyncpg.InsufficientPrivilegeError` exactly; Q5=a the file is `tests/db/test_ledger_edits_and_roles.py`; Q6=a expectations are the exact integers derived from the script's amounts (500/200/150/150/60/60/80). | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." | ROADMAP 6.0, P-007, AGENTS.md section 2 |
| D-074 | 2026-10-21 | The step 6.0 tests are accepted after one audit cycle: the audit's only defect was item 5 (SQL safety), fixed by binding the entry ids as `$1` in the six refused statements instead of `str.format`; items 1-4, 6 and 8 were PASS and item 7 is this batch. No explicit "tests approved" sentence was given; the user's audit request, the fix order and the instruction to close the step served as the approval. | "Audit the current working tree for the step" then "fix point 5" then "check if we can proceed for wrapup" then "Close the step:  (if empty, the step in this session)." | D-073, AGENTS.md section 2 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-007 | accepted -> D-073: porting one `db/examples` script just in time before its feature; 6.0 is its first use after 0.6 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-075 (proposed) | 2026-10-21 | Facts for later sessions. (1) In example 02 the "labapp may not" wall is PRIVILEGE-level, not trigger-level: `recorded_by`/`kind` fail through the column-level grant (`db/schema.sql:1196`), `ledger_lines` amount/delete through the missing table grant, `DISABLE TRIGGER` through ownership, `session_replication_role` through superuser — all SQLSTATE 42501 (`InsufficientPrivilegeError`); the closed-tenure relabel instead reaches `tx_label_edit` and raises P0001 (`RaiseError`, 'tenure "2026" is closed'). The future 6.6 label-edit API and the error translator must expect that split. (2) The owner tamper (disable `no_change_ln`, amount +1 on a closed-tenure line) yields exactly 2 `verify_integrity()` rows: the tenure checksum mismatch and the next tenure's opening mismatch (300 vs 301), matching D-025. (3) Example 1's tenure-2 deposit carries note '' (its step-13 INSERT sets none), so 02's first `ledger_label_edits` row has `old_value = ''`; the example's psql output hides that. (4) 02's lines 34-35 ("app role may close tenure via function") execute nothing — no statement, just an `\echo` + `RESET ROLE`; the actual app-role close is lines 47-48, mapped to `test_tamper_restore_and_close_as_app_role`. | `uv run pytest tests/db/test_ledger_edits_and_roles.py -v` (13 passed); `asyncpg/exceptions/__init__.py:639`; `db/schema.sql:287,376-410,1193-1202`; file read of `db/examples/02_ledger_edits_and_roles.sql:34-35,47-48` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 236 passed (223 pre-existing + 13 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "124 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-4, 6, 8 PASS;
item 5 FAIL, fixed and re-verified by the user's order; item 7 closed by this batch and the
ROADMAP tick.


## Added 2026-10-21 (twenty-fifth batch, step 6.1 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-076 | 2026-10-21 | Step 6.1 shape: Q1-Q5 were left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070): (Q1=a) exactly three value objects `EntryKind`, `IncomeSource`, `LedgerLine` and no header/aggregate yet; (Q2=a) `IncomeSource` replaces the pre-existing `DepositSource` as the one enum, with `ledger/domain/deposit.py`, `ledger/application/record_deposit.py`, `ledger/api/schemas.py` and the two ledger unit-test files updated mechanically (no assertion weakened); (Q3=a) `LedgerLine` validates ONLY that `envelope_id` and `amount` are real `int`s (D-047 strictness applied to a signed amount), while `amount <> 0` (db/schema.sql:270) and every per-kind shape (db/schema.sql:340-369) stay PostgreSQL's and are not duplicated in Python (AGENTS.md section 5); (Q4=a) one new module `src/mesl_finance/ledger/domain/entry.py`; (Q5=a) one new test file `tests/ledger/unit/test_entry_domain.py` using the D-069 lazy import. Step type CODE-WITH-TESTS (10 new tests; the 8 existing ledger tests moved to `IncomeSource`). | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 6.1, D-047, D-062, D-069 |
| D-077 | 2026-10-21 | The step 6.1 tests are approved as written (10 tests: both enum member name+value lists, a positive and a negative line, and the non-`int` amount/envelope refusals pinned by message text "whole" / "envelope"). The audit's only FAIL was item 7 (this batch plus the roadmap tick); items 1-6 and 8 were PASS. | "The user reviewed and approved the tests for:  (if empty, the step in this session)." then "Audit the current working tree for the step" and "Close the step:  (if empty, the step in this session)." | D-076, ROADMAP 6.1 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-078 (proposed) | 2026-10-21 | Pyright strict flags `vars(x)` as `reportUnknownVariableType` when `x` is typed `Any`, so a lazy-import helper must be annotated `-> ModuleType` (`tests/ledger/unit/test_entry_domain.py:62`); `vars(<ModuleType>)[name]` then yields `Any` and is accepted. The same file documents that requiring `type(value) is int` (not `isinstance`) is what refuses `bool`, matching `shared/money.py`. Gate evidence this session: `uv run pytest` 246 passed, `ruff check` all passed, `ruff format --check` 126 files, `pyright` 0 errors. | pyright run this session: 3 `reportUnknownVariableType` errors at `test_entry_domain.py:69,73,77` before the annotation, 0 after; full test run 246 passed (236 pre-existing + 10 new) |


## Added 2026-10-21 (twenty-sixth batch, step 6.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-079 | 2026-10-21 | Step 6.2 shape: Q1-Q6 were left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076): (Q1=a) P-008 confirmed - the first ledger step is only the deposit action, built end to end; (Q2=a) TEST-ONLY - the deposit slice pre-exists from the pre-roadmap tree (D-023) and is accepted as-is, no `/code`; (Q3=a) the existing contract is confirmed: `POST /api/v1/deposits`, body `{amount, occurred_on, source, note="", tag, cost_center_id, member_id, envelope_id}` (`envelope_id=None` means the pool; naming another envelope is allowed), response `201 {"id": n}`; (Q4=a) the pre-DB guards stay (see D-080); (Q5=a) the ten approved test cases; (Q6=a) test setup uses the `labapp` role directly for the cost-center INSERT and the envelope deactivation, and asserts the error `code` plus a loose "inactive" detail match. | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." | ROADMAP 6.2, P-008, D-023, D-064, D-076 |
| D-080 | 2026-10-21 | The three pre-DB guards in `src/mesl_finance/ledger/domain/deposit.py` (`amount > 0`; `weekly_fee` needs `member_id` and forbids `envelope_id`; only `weekly_fee` may carry `member_id`) are kept ON PURPOSE, although AGENTS.md section 5 says schema rules are not re-implemented in Python and D-076 Q3=a ruled that way for 6.1's `LedgerLine`. Reasons: they predate the roadmap (D-023); their two unit tests and three API tests already pin 422 `validation_failed` before any SQL; PostgreSQL still owns the same rules as a backstop (`fee_needs_member` at db/schema.sql:261, `check_shape` at 340-369). A later session must NOT silently delete them: removing them is a new step with new tests and its own decision. | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." (Q4=a was the brief's labelled suggestion) | AGENTS.md section 5, D-076, ROADMAP 6.2 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-008 | accepted -> D-079: the first ledger step is the deposit action only, built end to end |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-081 (proposed) | 2026-10-21 | Facts for later sessions. (1) pydantic 2.14.1 with `Field(strict=True)` refuses `True`, `10.5` and `'100'` for an `int` field and accepts `5`, so the API's 422 `validation_error` catches booleans too; the six quota test now pins `[0, -5, 10.5, "100", True]`. (2) The 401 guard needs no extra code: `HTTPBearer(auto_error=False)` returns `None` when the header is missing (`fastapi/security/http.py:305-320`), and `current_actor` turns that into `InvalidToken` -> 401 `invalid_token`. (3) No `db/examples` script covers the app-level deposit slice, so 6.2 is TEST-ONLY without an EXPECT table; example 01's DB-level deposit contract remains ported at `tests/db/test_ledger_contract.py::test_deposit_lands_in_the_pool`. (4) BUSINESS.md B-14 ("All income lands first in the Unallocated General pool") is still UNTICKED and would conflict with the confirmed 6.2 contract (deposits may name another envelope); if the user ever ticks B-14, a new decision and a new step are needed. (5) Gate evidence: `uv run pytest` 256 passed (246 + 9 new tests + 1 new parametrize case); ruff check "All checks passed!"; ruff format --check "126 files already formatted"; pyright "0 errors, 0 warnings, 0 informations". | pydantic probe this session; `.venv/lib/python3.15/site-packages/fastapi/security/http.py:305-320`; `.venv/lib/python3.15/site-packages/asyncpg/connection.py:320,725,746`; `.venv/lib/python3.15/site-packages/httpx/_client.py:1485,1838`; gate runs 2026-10-21 |

### Evidence for the step close

Gates this session: `uv run pytest` 256 passed; `uv run ruff check .` "All checks passed!";
`uv run ruff format --check .` "126 files already formatted"; `uv run pyright` "0 errors, 0 warnings,
0 informations". Audit: items 1-6 and 8 PASS; item 7 FAIL until this batch and the ROADMAP tick were
written.

## Added 2026-10-21 (twenty-seventh batch, step 6.3 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-082 | 2026-10-21 | Step 6.3 shape: (Q5=b) the expense response is a richer body than the deposit's `{"id"}`, carrying the entry `id`, `kind` and the envelope `balance` after the write; Q1-Q4 and Q6 were left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079): Q1=a `POST /api/v1/expenses`; Q2=a the body takes a POSITIVE whole-BDT `amount` and the adapter writes the one negative line the schema demands (db/schema.sql:351-352); Q3=a `envelope_id` is required (the pool is a valid envelope); Q4=a no `member_id` (member-linked refunds are ROADMAP 7.4); Q6=a the 18 approved test definitions (25 cases) as listed in the brief. | "q5=b go (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 6.3, D-079, D-076, D-064 |
| D-083 | 2026-10-21 | Approved option (a) for the unknown-envelope case found during /code: the expense adapter checks the envelope before writing and raises `UnknownReference` when it is missing, so `POST /api/v1/expenses` with an unknown envelope answers 422 `unknown_reference` like the deposit action does. The rejected options were (b) changing the approved test to expect 409 `rule_violation` and (c) a schema change to `line_guard`. This is an accepted, deliberate exception to "do not re-implement schema rules in Python": the pre-check exists to name the error correctly, not to enforce the FK. | "a" (answering the audit question "Tell me (a), (b) or (c)") | D-082, D-084, AGENTS.md section 5 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-084 (proposed) | 2026-10-21 | `line_guard` is a BEFORE INSERT row trigger (db/schema.sql:319-337) and therefore runs before the `ledger_lines_envelope_id_fkey` check. For a MISSING envelope its `SELECT active ... FOR UPDATE` yields NULL, so `IF NOT is_active` does not fire; a negative line then raises P0001 `envelope % would drop below zero (balance 0, change %)`, while a positive line falls through to the FK (23503). Consequence: an expense (one negative line) can never surface an unknown envelope as `unknown_reference` from the database alone — hence D-083's pre-check. This also means a future transfer/sweep/reversal with a negative line on an unknown envelope will answer 409 `rule_violation`, not 422. | Throwaway-DB probe this session: `envelope 999, expense line -150 -> RaiseError sqlstate=P0001 ... "would drop below zero"`; `envelope 999, deposit line 150 -> ForeignKeyViolationError sqlstate=23503`; `db/schema.sql:319-337` |
| D-085 (proposed) | 2026-10-21 | Adding `add_expense` to the shared `LedgerRepository` protocol breaks the pre-existing fake in `tests/ledger/unit/test_record_deposit.py` under pyright strict (`reportArgumentType`: "FakeLedger is incompatible with protocol LedgerRepository"), and tests may not be edited by the coder. The expense slice therefore declares its own `ExpenseRepository`/`ExpenseUnitOfWork` in `ledger/application/ports.py`; `SqlLedgerUnitOfWork` structurally satisfies both ports, so there is still one adapter and one transaction class. Future slices that extend the ledger should either add their own port or plan a test-fake change with the tester. | pyright run this session: 3 errors in `tests/ledger/unit/test_record_deposit.py:75,93,106` before the split, "0 errors, 0 warnings, 0 informations" after; `src/mesl_finance/ledger/application/ports.py:24-43` |

### Evidence for the step close

Gates this session: `uv run pytest` 281 passed (256 pre-existing + 25 new); `uv run ruff check .`
"All checks passed!"; `uv run ruff format --check .` "131 files already formatted"; `uv run pyright`
"0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS; item 7 FAIL until this batch and
the ROADMAP tick were written.

## Added 2026-10-21 (twenty-eighth batch, step 6.4 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-086 | 2026-10-21 | Step 6.4 shape: Q1-Q7 were left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079): (Q1=a) exactly two envelopes per request (`from_envelope_id`, `to_envelope_id`); (Q2=a) response `201 {"id", "kind", "from_balance", "to_balance"}`; (Q3=a) `note` required and non-blank, refused by the domain as 422 `validation_failed` (the schema CHECK at db/schema.sql:259 stays the backstop, same pattern as blank envelope names in D-066 Q7=a); (Q4=a) BOTH envelopes pre-checked in the adapter -> 422 `unknown_reference` (D-083 pattern); (Q5=a) the same envelope on both sides refused by the domain -> 422 `validation_failed`; (Q6=a) optional `tag` / `cost_center_id`; (Q7=a) the slice declares its own `TransferRepository` / `TransferUnitOfWork` (D-085). 37 approved test cases (13 domain, 3 use case, 21 API). | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 6.4, D-082, D-083, D-085, D-066 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-087 (proposed) | 2026-10-21 | The transfer adapter pre-checks both envelopes before inserting the header (`ledger/infrastructure/repository.py:100-105`), so a transfer to OR from a missing envelope answers 422 `unknown_reference`. This narrows D-084's prediction to sweeps/reversals only: a future `sweep_leftover` (8.3) or reversal (6.5) whose negative line names a missing envelope still reaches `line_guard` first and answers 409 `rule_violation`. Related: PostgreSQL fires a BEFORE INSERT row trigger per row in `VALUES` order, so the adapter writes the negative (source) line first (`repository.py:127-134`); for sweeps/reversals the first negative line is therefore the one that decides which guard/error appears. | `tests/ledger/api/test_transfers_api.py:189-204` (both sides parametrized, 422 `unknown_reference`); file reads of `repository.py`; gates this session: `uv run pytest` 318 passed, `uv run ruff check .` all passed, `uv run ruff format --check .` 136 files, `uv run pyright` 0 errors |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 318 passed (281 pre-existing + 37 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "136 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch and the ROADMAP tick were written.

## Added 2026-10-21 (twenty-ninth batch, step 6.5 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-088 | 2026-10-21 | Step 6.5 shape: (Q2=a) `POST /api/v1/entries/{entry_id}/fix-amount`, use case `FixAmount`, domain `AmountFix`, response model `FixAmountCreated`; (Q1=a) only `deposit` and `expense` entries are fixable — the app refuses any other kind as 422 `validation_failed`, so a multi-line fix (transfer/sweep) needs its own step; (Q4=c) the response is `201 {"id", "kind", "reversal_id", "corrected_from", "balance"}` (ids/kind plus the envelope balance after the write); (Q5=a) an unknown entry id is 422 `unknown_reference` (adapter pre-check), an already-fixed entry reaches `reverses_id` UNIQUE and answers 409 `unique`, and everything PostgreSQL itself refuses (tenure, mirror, overdraw) is 409 `rule_violation`; (Q6=a) the replacement copies the original's tag, cost center, source and member. Q3 was answered "all": the approved tests pin the resulting contract — `occurred_on` is written on BOTH headers (no date copied from the original), the request `note` goes on the reversal, and the replacement keeps the original's note; a blank note is refused by the domain as 422 `validation_failed` while `db/schema.sql:259` stays the backstop. | "The user approved the step brief for: q3=all, q4=c, go (if empty, the step briefed earlier in this session)." then, after the brief flagged the Q3 reading, "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 6.5, D-083, D-085, D-086 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-089 (proposed) | 2026-10-21 | Facts for later sessions. (1) SQLAlchemy 2.1.5 `Row` refuses string keys (`TypeError: tuple indices must be integers`), so a string-keyed read must go through `Result.mappings().first()` (`sqlalchemy/engine/result.py:774`; `MappingResult.first` :1693; `_KeyType` includes `str` :65-67). (2) The 6.5 reversal copies the original's `tag`/`cost_center_id` onto its own header (`ledger/infrastructure/repository.py:208-210`); no test pins this and `cost_center_summary` already reads the original's cost center for reversals (`db/schema.sql:539-541`), so either choice is safe — a later session must not change it silently. (3) Step 6.5 tests are 27 cases (11 domain, 3 use case, 13 API), all red before `/code` (module absent / 404) and green after. | pyright/pytest runs this session; the `/code` defect and its fix; file reads above |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 345 passed (318 pre-existing + 27 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "141 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch and the ROADMAP tick were written.

## Added 2026-10-22 (thirtieth batch, step 6.6 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-090 | 2026-10-22 | Step 6.6 shape: (Q7=b) a blank note on a kind the schema requires one for (transfer/sweep/reversal, db/schema.sql:259) is refused by the APP as 422 `validation_failed` before any SQL, after the adapter reads the entry's kind; PostgreSQL's CHECK stays the backstop. Q1-Q6, Q8 and Q9 were left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088): (Q1=a) `POST /api/v1/entries/{entry_id}/edit-labels`; (Q2=a) any non-opening kind may be relabelled, including a voided original and a reversal, with `tx_label_edit` owning the rest; (Q3=a) a partial body - only the supplied fields change, an explicit null clears `tag`/`cost_center_id`/`source`, while `note` and `occurred_on` may never be null; (Q4=a) an empty body is 422 `validation_failed`; (Q5=a) 200 `{"id","kind","note","tag","cost_center_id","occurred_on","source"}` after the write; (Q6=a) a `source` on a non-deposit reaches the server CHECK and answers 409 `rule_violation`; (Q8=a) an unknown `cost_center_id` is the foreign key -> 422 `unknown_reference`; (Q9=a) 6.6 adds no history read route. | "The user approved the step brief for: q7=b, why pass to database when we know it will be an error, let db rest. (if empty, the step briefed earlier in this session)." | ROADMAP 6.6, D-083, D-085, D-088 |
| D-091 | 2026-10-22 | The step 6.6 tests are approved as written: 35 cases (15 domain, 3 use case, 17 API), including the two `LabelEdit.validate_for(kind)` tests that replace the briefed "blank note is not the domain's business" test, because Q7=b makes the judgement depend on the entry's kind. | "The user reviewed and approved the tests for:  (if empty, the step in this session)." | D-090, ROADMAP 6.6 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-092 (proposed) | 2026-10-22 | Facts for later sessions. (1) The app-side blank-note rule is `LabelEdit.validate_for(kind)` (`ledger/domain/label_edit.py:70-73`), called by the adapter after the `SELECT ... FOR UPDATE` that also names an unknown entry (`ledger/infrastructure/repository.py:279-293`): only the database knows the kind, so the rule cannot live in the value object's `create()`. (2) A partial label edit carries `frozenset(model_fields_set)` from `ledger/api/router.py:107`; the adapter merges the supplied fields onto the row it locked and writes all five columns in one UPDATE, so `tx_label_edit` logs only the values that really changed. (3) A label edit asks for no open tenure: the entry's own tenure is what `tx_label_edit` checks, so a closed-tenure edit is a 409 `rule_violation` without an `open_tenure_id()` call. (4) The response is 200, not 201, because the action changes a row; Q2=a makes voided originals and reversal rows editable, which the approved test pins. (5) Test-seeding fact: `check_shape` is a DEFERRABLE constraint trigger, so an opening entry must be inserted (header + line) inside one explicit transaction or the first commit raises "entry N has no amounts"; the 6.6 opening test does this. (6) Gate evidence: `uv run pytest` 380 passed (345 pre-existing + 35 new), ruff check/format clean, pyright 0 errors. | gate runs and file reads this session; pydantic probe (`model_fields_set` includes explicit nulls; `Field(strict=True)` on `int | None` refuses `bool`, accepts `None` and a real int); `.venv/lib/python3.15/site-packages/sqlalchemy/engine/result.py:774,1589,1693` |


## Added 2026-10-22 (thirty-first batch, step 6.7 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-093 | 2026-10-22 | Step 6.7 shape: every question was left unanswered, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090): (Q1=a) `GET /api/v1/entries`; (Q2=a) an item is exactly `{id, tenure_id, kind, occurred_on, recorded_at, recorded_by, note, tag, cost_center_id, member_id, source, corrected_from}` (the view's `reverses_id`/`replaces_id` stay private; `corrected_from` is `replaces_id`); (Q3=a) NO amounts, because `entries_current` has none; (Q4=a) every tenure by default with optional `?tenure_id=`, no open-tenure call; (Q5=a) no other filter; (Q6=a) `id` ascending; (Q7=a) no pagination; (Q8=a) a bare JSON array; (Q9=a) no single-entry route in this step; (Q10=a) an unknown `tenure_id` is 200 `[]`; (Q11=a) the slice declares its own `EntryListRepository`/`EntryListUnitOfWork` (D-085); (Q12=a) a read does not commit, mirroring `ListCostCenters`. | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." | ROADMAP 6.7, D-064, D-085, D-089 |
| D-094 | 2026-10-22 | The step 6.7 tests are approved as written: 13 cases - 3 use-case unit tests (`tests/ledger/unit/test_list_entries.py`: one transaction, the tenure filter reaches the repository, the actor is the transaction actor) and 10 API tests (`tests/ledger/api/test_entry_list_api.py`: 401, empty list, id order, the 12-key item, a fixed amount collapsing to one line, a label edit visible, tenure filter, unknown tenure, non-numeric tenure 422, an opening entry listed). | "The user reviewed and approved the tests for:  (if empty, the step in this session)." | D-093, ROADMAP 6.7 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-095 (proposed) | 2026-10-22 | Facts for later sessions. (1) ONLY ONE tenure may be open at a time (`one_open_tenure`, db/schema.sql:40), so a cross-tenure read test cannot just insert a second tenure: it must hand over with `close_tenure(p_close_on, p_by, p_next_name)` (db/schema.sql:910-938), which closes the open tenure and writes a carry-over `opening` entry into the new one whenever the closing tenure has lines. The 6.7 tenure-filter test therefore expects `[opening, deposit]` in tenure 2 (`tests/ledger/api/test_entry_list_api.py:242-269`); any later cross-tenure read (6.8, 11.x) must expect the same opening row. (2) The optional filter is one bound parameter cast twice: `WHERE CAST(:tenure_id AS bigint) IS NULL OR tenure_id = CAST(:tenure_id AS bigint)` (`ledger/infrastructure/repository.py:337-352`), with the value passed in the params dict, never formatted into SQL; rows are read with `Result.mappings()` (D-089). (3) The read model pair `ListEntriesQuery`/`EntryView` lives in `ledger/domain/entry_list.py` (pure) so that `application/ports.py` can import the port's input type at runtime while `application/list_entries.py` imports the port; putting the query in the use-case module would need a `TYPE_CHECKING`-only cycle, which this repo does not use. (4) `EntryOut` (`ledger/api/schemas.py:101-114`) mirrors `EntryView` field for field and the router maps one to the other explicitly (`ledger/api/router.py:137-152`), so a new list field is a three-file change plus its test. (5) Gate evidence: `uv run pytest` 393 passed (380 pre-existing + 13 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "150 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | gate runs and installed-source reads this session; `db/schema.sql:40,426-430,910-938`; `tests/ledger/api/test_entry_list_api.py:242-269` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 393 passed; `uv run ruff check .` "All checks passed!";
`uv run ruff format --check .` "150 files already formatted"; `uv run pyright` "0 errors, 0 warnings,
0 informations". Audit: items 1-6 and 8 PASS; item 7 FAIL until this batch and the ROADMAP tick were
written.

## Added 2026-10-22 (thirty-second batch, step 6.8 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-096 | 2026-10-22 | Step 6.8 shape: every question was answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093): (Q1=a) P-003 confirmed in its NARROWED form - publish only the generated `docs/openapi.json`; no handwritten `docs/api-contract.md`, because ROADMAP 6.8 says "no handwritten contract"; (Q2=a) CODE-WITH-TESTS with three tests, and the check that the committed file still matches a fresh export stays ROADMAP 12.2's; (Q3=a) the generator is `src/mesl_finance/export_openapi.py`, run as `PYTHONPATH=src uv run python -m mesl_finance.export_openapi`, writing `<repo>/docs/openapi.json`; (Q4=a) it builds the app from documented schema-only placeholder `Settings` values and opens no database connection, so exporting needs neither a server nor the app's secrets; (Q5=a) output is UTF-8 JSON with `indent=2`, `sort_keys=True` and exactly one trailing newline, and `info.version` stays FastAPI's default "0.1.0" (no step defines an app version). | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 6.8, P-003, D-064 |
| D-097 | 2026-10-22 | The step 6.8 tests are approved as written (3 cases in `tests/api/test_export_openapi.py`): exported document equals `create_app(...).openapi()`, OpenAPI "3.1.0", `info {"title": "MESL Finance", "version": "0.1.0"}`, the exact 16-operation inventory; byte-stable output with `components` first and two-space indent; a missing destination directory is created. Test file unchanged between approval and close. | "The user reviewed and approved the tests for:  (if empty, the step in this session)." | D-096, ROADMAP 6.8 |

### Resolutions of earlier rows (nothing above was edited)

| Row | Resolution |
|---|---|
| P-003 | accepted -> D-096, narrowed to the generated `docs/openapi.json` only; the handwritten `docs/api-contract.md` half is rejected |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-098 (proposed) | 2026-10-22 | Facts for later sessions. (1) `docs/openapi.json` at this step: sha256 `a52b20f5f1d006ec13f652d82dafbdd946ff8ff5838cdfd037a141bf639aaf09`, 41,574 bytes, 16 operations, root keys `components/info/openapi/paths`, `securitySchemes: HTTPBearer`, 25 component schemas. (2) Exporting is settings-independent and env-independent: the document was regenerated with `PYTHONPATH=src` only (no `.env`, no `MESL_*` variables) and the bytes were identical, which is why Q4=a's placeholders are safe. (3) The generated document carries only what FastAPI knows - success responses plus its own `422 HTTPValidationError` - so the RFC 9457 problem-JSON bodies (D-013, D-064) are absent; no step authorises `responses=` metadata, so a future contract step that wants them needs its own decision. (4) The hardcoded inventory in `tests/api/test_export_openapi.py:58-75` is the only assertion that catches a router silently disappearing from `create_app`, and every API step must extend it. (5) `export_openapi()` builds the app and never disposes the engine; no connection is ever checked out and the process exits, so nothing leaks - a later long-running caller would need `await engine.dispose()`. (6) Gate evidence: `uv run pytest` 396 passed (393 pre-existing + 3 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "152 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | independent regeneration and byte comparison this session; gate runs 2026-10-22 |

## Added 2026-10-22 (thirty-third batch, step 7.0 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-099 | 2026-10-22 | Step 7.0 shape: every question was answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096): (Q1=a) two new files, one per worked example - `tests/db/test_fees.py` (03, 27 cases) and `tests/db/test_fees_existing_members.py` (04, 3 cases); (Q2=a) small composable phase helpers replaying the script prefix (`start`, `add_adjustments`, `change_rate`, `fix_b_payment`, `script_prefix`), as 6.0's `example_01()` did; (Q3=a) each rejected line asserts the exact asyncpg exception class it really raises; (Q4=a) dates come from `sunday_on_or_before(current_date)` per run (D-045); (Q5=a) in 03 line 96 the `INSERT INTO members('F')` SUCCEEDS (members has no guard; `db/schema.sql:87-93,1193-1194`) and only the line-97 period insert is rejected; (Q6=a) the tamper test asserts exactly 3 `verify_integrity()` rows, one per affected member (A, B, E); (Q7=a) 04 asserts only the numbers its script states (`weeks_owed`, `owed`), not the balance; (Q8=a) one session, no roadmap split. The tests are accepted as written: the user asked for the audit and then to close the step, with no change requested (D-074 pattern). | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." then "Audit the current working tree for the step:" then "Close the step:" | ROADMAP 7.0, D-045, D-073, D-025 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-100 (proposed) | 2026-10-22 | Facts for later fee sessions (7.1-7.5). (1) In example 03, five "rejected mistakes" never reach their trigger: the app role has INSERT only on `fee_rates`, `membership_periods` and `member_adjustments`, UPDATE only on `membership_periods.end_date` and on the label columns of `ledger_transactions` (`db/schema.sql:1191-1202`), so lines 65 (start-date edit), 67 (delete period), 70-71 (edit/delete adjustment) and 81 (member edit on a payment) are SQLSTATE 42501 `InsufficientPrivilegeError`, not the `forbid_change()`/`period_guard`/`tx_label_edit` P0001. Lines 66 and 94 (end_date update) DO reach `period_guard` and raise P0001; 62/76/78/92/93/95/97 raise P0001; 63/68/69/72/73 raise 23514; 64 raises 23P01; 74-75 raise P0001 at COMMIT. A future error translator for the fee APIs must keep that split (same lesson as D-075). (2) Example 03 line 96's `INSERT INTO members(name) VALUES ('F')` succeeds by design: `members` carries only the blank-name CHECK and no tenure guard; the old-tenure period at line 97 is the rejected statement. (3) Disabling `shutdown_guard` as owner and inserting a shutdown for the closed week s0+21 yields exactly 3 `verify_integrity()` rows, all "dues of ..." (A, B, E); the ledger is untouched, so no checksum or opening mismatch appears. (4) Test mechanics: all ids (tenures 1, envelopes 1-2, members 1-6) come from the fresh template clone, which the schema leaves empty; `sunday_on_or_before(current_date)` is read from the database, so no test pins a calendar date; `enter()` repeats the 6.0 helper pattern (bound values, column list from literal kwargs). (5) Coverage proof lives in the two module docstrings; the audit noted that `03_fees.sql:1` (file header) and `:61` (`\echo` group header) contain the words "EXPECT FAIL" but are prose, not expectation lines, and are therefore not table rows. (6) Gate evidence: `uv run pytest` 426 passed (396 pre-existing + 30 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "154 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | gate runs and script reads this session; `db/schema.sql:87-93,240-262,1191-1202`; `db/examples/03_fees.sql:61-109`; audit tool output |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 426 passed (396 pre-existing + 30 new: 27 + 3);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "154 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch and the ROADMAP tick were written.

## Added 2026-10-22 (thirty-fourth batch, step 7.1 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-101 | 2026-10-22 | Step 7.1 shape: (Q6=b) a blank member name is refused by the APP as 422 `validation_failed` on create and on edit, like cost centers (D-070 Q4), although `db/schema.sql:89` also carries `CHECK (length(btrim(name)) > 0)`. Every other question took the brief's labelled suggestion: (Q1=a) member edit is part of the step; (Q2=a) the period read is part of it; (Q3=a) an unknown member addressed in the URL is 404 `not_found` via an adapter pre-check (D-083 pattern); (Q4=a) ending with nothing open is 404; (Q5=a) `end` picks the member's single open period; (Q7=a) `MemberOut` is `{id,name,batch,note}`; (Q8=a) the six routes - `POST /api/v1/members` (201), `GET /api/v1/members` (200, id order), `POST /api/v1/members/{id}/edit` (200, partial body, explicit null clears `batch` only, empty body 422 `validation_failed`), `POST /api/v1/members/{id}/periods/start` (201), `POST /api/v1/members/{id}/periods/end` (200), `GET /api/v1/members/{id}/periods` (200, id order) - with `PeriodOut = {id,member_id,start_date,end_date}`; (Q9=a) the shared translator gains exactly one rule, SQLSTATE 23P01 -> `RuleViolation`; (Q10=a) only the supplied edit fields change; (Q11=a) create takes `name` plus optional `batch`/`note`. 41 new cases (8 domain, 32 API, 1 translator). | This session's `/start` answer: Q6=b, everything else as the brief's labelled suggestions; then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 7.1, D-070, D-083, D-088, D-100 |
| D-102 | 2026-10-22 | The user authorised the coder to fix two defective ALREADY-APPROVED test files (other test edits stay tester-domain). Defects found during `/code`: (1) `tests/members/api/test_membership_periods_api.py::test_non_numeric_member_id_is_422` sent no auth header, so `current_actor` answered 401 before path parsing - no production change can yield 422 for an unauthenticated request; fixed by adding `headers=auth`. (2) `tests/api/test_export_openapi.py::EXPECTED_OPERATIONS` was not sorted although the assertion compares against `sorted(_operations(document))`; the four `POST /api/v1/members*` tuples sat before `POST /api/v1/expenses`; fixed by moving them below it. No assertion was weakened, deleted or skipped. | "fixthose two test-file" | D-049, AGENTS.md section 2, ROADMAP 7.1 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-103 (proposed) | 2026-10-22 | Facts for later sessions. (1) The `end` adapter (`members/infrastructure/repository.py:86-109`) reads the member's latest period by id (`ORDER BY id DESC LIMIT 1`) and then UPDATEs that row by id; an `UPDATE ... WHERE member_id = :id AND end_date IS NULL` was tried first and turned the approved "a second end is 409" into 404 because the closed row no longer matched. PostgreSQL's `period_guard` (db/schema.sql:210-212) owns "ended once"; a member with no period row at all is 404. Do NOT narrow this adapter. The 404 detail for `end` names both possibilities on purpose ("does not exist or has no open membership period") because the adapter cannot tell them apart without a second query. (2) `start` and `periods_for` pre-check member existence (`SELECT 1 FROM members WHERE id = :id`) to answer 404 `not_found` instead of letting the FK answer 422 `unknown_reference` (D-083's pattern of naming the error). (3) The translator's fifth branch is 23P01 -> `RuleViolation` (`shared/infrastructure/error_mapping.py:19,49-51`), pinned by the DB-backed `tests/shared/test_error_translator.py::test_exclusion_violation_maps_to_a_rule_violation`. (4) `period_guard`'s INSERT check only bites once `fee_rates` has at least one row (db/schema.sql:200-205), so the closed-tenure start test seeds a rate at `sunday_on_or_before(current_date)` (7.2 owns fee rates); `rate_guard` itself refuses a rate backdated before the current week's Sunday (db/schema.sql:166-175). (5) The period views carry `date` objects; the API serialises them as ISO strings like `EntryOut` (`ledger/api/schemas.py:12`). (6) Gate evidence: `uv run pytest` 467 passed (426 pre-existing + 41 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "177 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | gate runs, audit and file reads this session; `db/schema.sql:89,95-102,166-175,193-218,1193-1198`; `tests/members/api/test_membership_periods_api.py:167-243` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 467 passed (426 pre-existing + 41 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "177 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch and the ROADMAP tick were written.

## Added 2026-10-24 (thirty-fifth batch, step 7.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-104 | 2026-10-24 | Step 7.2 shape, all eight questions as the brief's labelled suggestions: (Q1=a) a new `fees` feature with ONE `FeeRepository`; (Q2=a) the step carries both writes and reads; (Q3=a) one `POST /api/v1/shutdown-weeks` action with body `{from_week, to_week, is_shutdown=true, reason=""}` answering 201 `{"weeks": n}`, and undo is the same action with `is_shutdown=false`; (Q4=a) `POST /api/v1/fee-rates` takes `{effective_from, amount}` and a second rate for the same Sunday is accepted (the DB's `current_rate` keeps the latest id, db/schema.sql:113-115); (Q5=a) `amount` is strict `int` only - `10.5`, `true` and `"20"` are 422, while `0` and `-5` reach the table CHECK and answer 409; (Q6=a) `GET /api/v1/shutdown-weeks` returns the raw `shutdown_events` rows, the per-week latest-wins view belongs to 7.5; (Q7=a) the rate is global only, per-batch rates need DDL and stay unbuilt; (Q8=a) domain and API tests only, no DB-test port. Routes: `POST`/`GET /api/v1/fee-rates` and `POST`/`GET /api/v1/shutdown-weeks`; `GET /api/v1/fee-rates` in `(effective_from, id)` order and `GET /api/v1/shutdown-weeks` in `(week_start, id)` order; `recorded_by` is always the JWT actor. 28 new cases (6 domain, 13 rates API, 9 shutdown API) and the operation inventory grew 22 -> 26. | "The user approved the step brief for:  (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 7.2, D-005, D-099, D-105 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-105 (proposed) | 2026-10-24 | Facts for later sessions. (1) The CHECK constraints are named `fee_rates_amount_check` (`CHECK ((amount > 0))`), `fee_rates_effective_from_check` (`CHECK ((EXTRACT(dow FROM effective_from) = (0)::numeric))`) and `shutdown_events_week_start_check` (same Sunday test on `week_start`); the API tests assert the 409 bodies by those names. (2) `set_shutdown(date,date,boolean,text,text)` exists with `proacl` NULL, i.e. the default PUBLIC EXECUTE, so `labapp` may call it; it is not SECURITY DEFINER (same class as `allocate()` and `sweep_leftover()`), returns the number of weeks written, and `SELECT set_shutdown(:from_week, :to_week, :is_shutdown, :recorded_by, :reason)` works with bound parameters inside the app transaction (`fees/infrastructure/repository.py:56-73`). (3) No translator change was needed: the table CHECK answers 23514 -> `RuleViolation` (`shared/infrastructure/error_mapping.py:45-48`), the trigger and function messages ("weeks start on Sunday", "to-week is before from-week", "cannot be backdated", "belongs to a closed tenure") fall through P0001 -> `RuleViolation` (`:30-35`), and "before this tenure opened" already maps to `DateBeforeTenure` (`:21-24`). (4) Intentional shapes not to silently change: the two read use cases do NOT commit; each write commits once in its own use case; the adapter inserts and reads with RETURNING and no existence pre-checks, because PostgreSQL owns every rule. `docs/openapi.json` was deliberately not regenerated (22 -> 26 operations is 7.6's job). (5) Gate evidence: `uv run pytest` 495 passed (467 pre-existing + 28 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "199 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". (6) Environment: at `/code` start nothing listened on `localhost:5434` and no PostgreSQL container existed (only exited adminer/velxio), so every test errored with `OSError ... Connect call failed ('127.0.0.1', 5434)`; the user started the dev DB, after which all gates ran. Same class as D-032. | `pg_constraint` query on `mesl_test_template`; `pg_proc` for `set_shutdown`; `db/schema.sql:106-125,220-233,1193-1194`; `error_mapping.py` read; gate runs and `ss -ltn` output this session |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 495 passed (467 pre-existing + 28 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "199 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch and the ROADMAP tick were written.

## Added 2026-10-24 (thirty-sixth batch, step 7.3 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-106 | 2026-10-24 | Step 7.3 shape: all nine questions took the brief's labelled suggestions (same pattern as D-101/D-104). (Q1=a) `POST /api/v1/members/{member_id}/adjustments` with `kind` in the body. (Q2=a) the read is part of the step: `GET /api/v1/members/{member_id}/adjustments`, id order, no filters, `[]` when none. (Q3=a) `amount` is SIGNED and the direction rules stay the table CHECKs. (Q4=c) the app refuses a blank note for `waiver`/`correction` as 422 `validation_failed`; a wrong sign reaches PostgreSQL as 409 `rule_violation`. (Q5=a) `occurred_on` is required, no invented default. (Q6=a) 201 answers the full stored row `{id, member_id, kind, amount, occurred_on, note, recorded_at, recorded_by}`. (Q7=a) an unknown member is 404 `not_found` naming the id (adapter pre-check). (Q8=a) no open tenure is answered by `adj_guard`/`open_tenure_start()` as 409 `rule_violation`. (Q9=a) `members/domain/adjustment.py` with `AdjustmentKind`, `MemberAdjustment`, `AdjustmentView`, plus a new `AdjustmentRepository`/`AdjustmentUnitOfWork` and `SqlMemberUnitOfWork.adjustments` (D-085). | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." | ROADMAP 7.3, D-101, D-104, D-085 |
| D-107 | 2026-10-24 | One approved test was self-contradictory (a waiver with no note expected `note == ""` while another test required that same construction to raise), so the user authorised option (a): `test_an_adjustment_keeps_its_values_and_defaults_the_note_to_empty` uses `AdjustmentKind.OPENING`, a kind that may omit the note; every other assertion unchanged and no production change. 29 new cases (12 domain, 17 API) plus the OpenAPI inventory growth 26 -> 28; suite 495 -> 524. | "you are now tester, fix with 'a'" | D-106, ROADMAP 7.3 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-108 (proposed) | 2026-10-24 | Facts for later sessions (7.4 onward). (1) A route that does not exist yet answers 404 `not_found` through the app's own handler, indistinguishable by status/code from a real "unknown member" 404; a test for the latter must also assert the detail names its subject, otherwise it passes vacuously (this happened on the first red run: two of 29 tests passed). The 7.3 tests assert `"9999" in response.json()["detail"]`. (2) No translator rule was needed: SQLSTATE 23514 (zero amount, wrong waiver/donation sign) and P0001 (`adj_guard` closed-tenure date, `open_tenure_start()` "no open tenure") already map to `RuleViolation`; the member pre-check keeps an unknown member away from the FK so it answers 404 `not_found`, not 422 `unknown_reference`. (3) The app-side blank-note rule lives in `MemberAdjustment.__post_init__` (`members/domain/adjustment.py:40-43`) and applies to `waiver` and `correction` only; the kind signs and the date rule stay PostgreSQL's (Q4=c). (4) `SqlMemberUnitOfWork` now exposes both `members` and `adjustments`; one adapter satisfies both ports (D-085), so no existing member fake had to change. (5) `docs/openapi.json` was deliberately NOT regenerated (26 -> 28 only in the test inventory); the file refresh is ROADMAP 7.6's. (6) Gate evidence: `uv run pytest` 524 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "204 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | test red/green runs, audit and file reads this session; `db/schema.sql:128-141,185-191,1194`; `src/mesl_finance/shared/api/problems.py:28,60-69` |

## Added 2026-10-25 (thirty-seventh batch, step 7.4 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-109 | 2026-10-25 | Step 7.4 shape: every question was answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106): (Q1=a) 7.4 adds ONLY the refund - the member-linked fee payment already exists at `POST /api/v1/deposits` with `source="weekly_fee"` + `member_id`; (Q2=a) `POST /api/v1/refunds` in the ledger router, `member_id` in the body, an unknown member answers 422 `unknown_reference` through the foreign key; (Q3=a) the body has NO `envelope_id` - the adapter resolves the pool; (Q4=a) 201 `{"id","kind":"expense","balance"}`; (Q5=a) `note` optional, default `""`; (Q6=a) no member-credit cap, only `line_guard`'s pool overdraw wall; (Q7=a) `tag` and `cost_center_id` optional; (Q8=a) no read in this step (7.5 owns `member_standing`/dues/allocation reads); (Q9=a) CODE-WITH-TESTS. 21 new cases (6 domain, 3 use case, 12 API) and the operation inventory grew 28 -> 29. | "The user approved the step brief for: go with suggestions (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 7.4, D-082, D-083, D-085, D-096 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-110 (proposed) | 2026-10-25 | Facts for later sessions. (1) A refund is a normal `expense` header carrying `member_id` plus one negative line on the pool (`ledger/infrastructure/repository.py:106-148`): `member_link_kinds` (db/schema.sql:260) allows the member on an expense and `check_shape` (:364-367) forces it through the pool, so no schema change and no translator rule were needed (23503 -> `unknown_reference`, P0001 -> `rule_violation`, "before this tenure opened" -> `date_before_tenure` all pre-existed). (2) The pool id is resolved at execution time (`FROM envelopes e WHERE e.is_pool`), never hard-coded; a missing pool raises an untranslated `NoResultFound`, the same pre-existing gap the deposit adapter has, and the bootstrap always creates the pool (D-041). (3) `RefundRequest.member_id` is a lax `int` exactly like the pre-existing `DepositRequest.member_id`, so a JSON `true` would coerce to member 1 - not changed in this step. (4) `docs/openapi.json` was deliberately NOT regenerated (28 -> 29 only in the test inventory); the file refresh stays ROADMAP 7.6's, same as 7.2/7.3. (5) Gate evidence: `uv run pytest` 545 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "209 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | audit and gate runs this session; `db/schema.sql:260,293-315,319-337,364-367`; `src/mesl_finance/ledger/infrastructure/repository.py:106-148`; `src/mesl_finance/ledger/api/schemas.py:46-60` |

## Added 2026-10-26 (thirty-eighth batch, step 7.5 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-111 | 2026-10-26 | Step 7.5 shape: every question was answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109): (Q1=b) TWO reads only, `GET /api/v1/dues` and `GET /api/v1/allocation-context`; (Q2=a) no `as_of` parameter - the views use `current_date`; (Q3=a) the dues row exposes `member_id`/`member_name` (from the function's `who_id`/`who_name`) plus the other seven schema names; (Q4=a) every member, in `dues_overview`'s own order, no filter; (Q5=a) the context row carries all three ints; (Q6=a) a missing pool row stays out of scope; (Q8=a) the dues read lives in `fees`, the context read in `envelopes`; (Q9=a) one transaction, no commit, no `open_tenure` call; (Q10=a) one session. 15 new cases (2 fees unit, 1 envelopes unit, 8 dues API, 4 context API) and the operation inventory grew 29 -> 31. | "go with your suggestions" (this session's step-brief approval) then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 7.5, D-041, D-093, D-105, D-109 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-112 (proposed) | 2026-10-26 | Facts for later sessions. (1) `dues_overview` (db/schema.sql:627-628) carries its ORDER BY inside the view, so a column-subset SELECT keeps `weeks_overdue DESC, who_name`; the adapter adds no ORDER BY of its own (fees/infrastructure/repository.py:109-118). (2) `allocation_context` (:630-634) is a single-row view; with no pool envelope its `pool_balance` is NULL and `int(None)` raises TypeError, i.e. a 500 - the same pre-existing gap as D-110 (2), out of scope here (Q6=a), and the bootstrap always creates the pool (D-041) (envelopes/infrastructure/repository.py:100-104). (3) `SqlFeeUnitOfWork.dues` (fees/infrastructure/unit_of_work.py:11) and `SqlEnvelopeUnitOfWork.allocation_context` (envelopes/infrastructure/unit_of_work.py:14) are the new ports' adapters; both reads reuse the existing units of work, so `main.py` only gained the two use cases (:96, :123). (4) Every `dues_overview` field is non-NULL except `oldest_unpaid_week`: the other eight are `count(*)`, coalesced sums, `EXISTS` and `members.name` (db/schema.sql:89,620-624), so only that one column is typed `date | None`. (5) The operation inventory grew 29 -> 31 (tests/api/test_export_openapi.py:59,61) and `docs/openapi.json` was deliberately NOT regenerated; the file refresh stays ROADMAP 7.6's, same as 7.2/7.3/7.4. (6) Gate evidence: `uv run pytest` 560 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "217 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | audit and gate runs this session; `db/schema.sql:89,582-634`; `src/mesl_finance/fees/infrastructure/repository.py:109-118`; `src/mesl_finance/envelopes/infrastructure/repository.py:100-104`; `src/mesl_finance/main.py:96,123` |

## Added 2026-10-26 (thirty-ninth batch, step 7.6 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-113 | 2026-10-26 | Step 7.6 shape: (Q1=a) NO-TEST - an artifact refresh has no behaviour to assert, and D-096 Q2=a keeps the committed-file freshness test for ROADMAP 12.2; (Q2=a) `/code` changes ONLY `docs/openapi.json`, by re-running the documented generator, with `ROADMAP.md`/`DECISIONS.md` edits at wrapup; (Q3=a) the refresh is verified by a read-only comparison and its new facts are recorded in DECISIONS.md; (Q4=a) the generated document still carries no RFC 9457 problem-JSON bodies (D-098 (3) unchanged). | "The user reviewed and approved the tests for: go (if empty, the step in this session)." then the `/code` directive "Write the smallest code that makes the approved tests pass." | ROADMAP 7.6, D-096, D-098 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-114 (proposed) | 2026-10-26 | `docs/openapi.json` at step 7.6: sha256 `29b20da764381d5193bebda88080d44f6d22ca8fdc5fe54e8f69986b6a313e27`, 71,614 bytes, 31 operations, 43 component schemas (supersedes D-098 (1)'s 41,574 bytes / 16 operations / 25 schemas, which stay as the 6.8 snapshot; D-098 is NOT edited). Regenerated with `PYTHONPATH=src uv run python -m mesl_finance.export_openapi`; the working-tree file equals a fresh export BYTE FOR BYTE, `openapi`/`info`/`securitySchemes` and all 16 pre-6.8 paths plus all 25 pre-6.8 schemas are semantically unchanged, and nothing was removed - the 15 new operations and 18 new schemas are exactly the 7.1-7.5 additions. Regeneration stays env-independent (no `.env`, no `MESL_*` variables, no DB connection). Every later API step (8.4, 9.5, 10.3, 12.2) reruns the same command; the "committed file matches the app" assertion remains 12.2's. Gate evidence: `uv run pytest` 560 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "217 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | independent fresh export + byte comparison, `git diff` inspection and gate runs this session |

## Added 2026-10-28 (fortieth batch, step 8.0 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-115 | 2026-10-28 | Step 8.0 shape: (Q1=a) TEST-ONLY, no `/code`, because the behaviour already exists in `db/schema.sql`; (Q2=a) line 57's unmarked `DELETE FROM allocation_sessions` gets a dedicated `InsufficientPrivilegeError` test and line 107 asserts exactly 3 sessions survive; (Q3=a) every rejected line pins the exact asyncpg class plus its message fragment; (Q4=a) the post-close balances derived from the script are asserted (pool 1760 / Admin 500 / Components 500 / Projects 445 / Events 297 / Research 148) plus the 3-session count; (Q5=a) the blank-note CHECK is matched by the `ledger_transactions_check` prefix, not a guessed suffix. One new file `tests/db/test_allocation_and_sweeps.py`, 28 cases (20 test functions, one parametrized 9 ways), local prefix helpers (`start`, `allocation_prefix`, `event_prefix`, `script_prefix`), coverage table T1-T20. | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." | ROADMAP 8.0, D-045, D-073, D-099, D-100 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-116 (proposed) | 2026-10-28 | Facts for later sessions. (1) Line 57's `DELETE FROM allocation_sessions` as `labapp` is SQLSTATE 42501 (`InsufficientPrivilegeError`), NOT the append-only trigger's P0001, because the role has INSERT only on that table (`db/schema.sql:1193-1194`); the sessions therefore survive. Line 59's echo says "delete" but the example has no envelope DELETE statement: its three refusal labels map to lines 60-62, and the only DELETE is line 57. (2) Line 90's sweep header with no cost center fails as 23514 `sweep_needs_cc` at INSERT (`db/schema.sql:262`), never reaching the deferred shape trigger. (3) The bad-allocation block (lines 48-56) is 8 x P0001 `RaiseError` plus 1 x 23514 for the blank note; the latter is the unnamed CHECK at `db/schema.sql:259`, whose generated name is matched by the prefix `ledger_transactions_check`. (4) The script's final state after close is pool 1760, Admin 500, Components 500, Projects 445, Events 297, Research 148, `Old idea` 0, with 3 `allocation_sessions` rows and an empty `verify_all()`; the pool figure is 1760 (not the 1660 first estimated in the brief: the reversed sweep is followed by a second sweep). (5) Test mechanics: the fresh template clone supplies ids 1-6; rejected lines replay the script prefix; two wrong-reason fixes were made during `/tests` (the blank-note parametrize row had note/amounts swapped, and the sweep tests first skipped the allocation prefix) with no assertion weakened. (6) Gate evidence: `uv run pytest` 588 passed (560 pre-existing + 28 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "218 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | red/green runs, audit and installed-source reads this session; `db/examples/06_allocation_and_sweeps.sql:57,59,90`; `db/schema.sql:259,262,1193-1194`; `tests/db/test_allocation_and_sweeps.py` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 588 passed; `uv run ruff check .` "All checks passed!";
`uv run ruff format --check .` "218 files already formatted"; `uv run pyright` "0 errors, 0 warnings,
0 informations". Audit: items 1-6 and 8 PASS; item 7 FAIL until this batch and the ROADMAP tick were
written.

## Added 2026-10-28 (forty-first batch, step 8.1 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-117 | 2026-10-28 | Step 8.1 shape: every question Q1-Q7 was answered by the generic approval, so the brief's labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109/D-111): (Q1=a) `POST /api/v1/allocation-suggestion` with body `{amount: int, shares: {"<envelope_id>": int} | null}` - a READ that writes nothing, chosen because `p_shares` is a JSON object; (Q2=a) every row the function returns, in its own order, field names `envelope_id, envelope_name, balance, target_cap, alloc_priority, gap, phase, suggested`; (Q3=a) `amount` strict whole number with `amount <= 0` refused by the app as 422 `validation_failed` while a non-integer is FastAPI's 422 `validation_error` (D-081 (1)); (Q4=a) `shares` accepted as-is, string keys + strict-int values, no key/sign rule invented (PostgreSQL ignores keys naming no eligible envelope); (Q5=a) the slice lives in `envelopes` (own `DraftAllocationRepository`/`DraftAllocationUnitOfWork`, D-085); (Q6=a) no open-tenure call (7.5's Q9=a); (Q7=a) raw rows only, no total/remainder field. 18 new cases (2 use-case unit, 16 API) and the operation inventory grew 31 -> 32. | "The user approved the step brief for: go (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 8.1, D-085, D-111, D-081 |
| D-118 | 2026-10-28 | The user authorised the coder to fix ONE defective approved test file (other test edits stay tester-domain): `tests/envelopes/api/test_allocation_suggestion_api.py::test_the_draft_reuses_the_last_session_proportions` seeded the confirming session with only the three uncapped amounts (445/297/148 = 890), leaving both cap gaps pending, so `allocation_suggestion(600)` filled 110 of caps first and split the remaining 490 -> 245/163/82 instead of the asserted 300/200/100. Options were (a) add the cap fills to the seed like example 06 line 28, (b) change the expectations, (c) redesign the test. Option (a) was chosen; ONLY the seed gained `{ADMIN: 60, COMPONENTS: 50}` (full 1000, mirroring example lines 28-29). No assertion was weakened, deleted or skipped, and no production code was changed to satisfy it. | "a. fix the seeding" (after the coder's STOP report showing `assert 245 == 300`) | D-049, D-102, AGENTS.md section 2, ROADMAP 8.1 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-119 (proposed) | 2026-10-28 | Facts for later sessions. (1) Passing an explicit `NULL` for `p_shares` is equivalent to omitting it: the function's shares CTE branches on `p_shares IS NOT NULL` (db/schema.sql:480-483), so the adapter's single statement `allocation_suggestion(CAST(:amount AS integer), CAST(:shares AS jsonb))` serves both modes, with `json.dumps` in the bound parameter (never in the SQL text). (2) The last-session reuse reads the positive lines of the newest non-voided `allocation_sessions` transfer, but CAP GAPS ARE STILL FILLED FIRST: a confirming session must include the cap fills (example 06 line 28's `WHERE suggested > 0`), otherwise the next draft spends the remainder on the gaps and the proportions differ (D-118). (3) The API response returns `phase` as a plain `str` (`cap_fill`/`share`/`none`); the schema has no enum type for it. (4) `allocation_suggestion` is callable by `labapp` through the default PUBLIC EXECUTE (no REVOKE; only `close_tenure` is revoked, db/schema.sql:1202-1203). (5) The read is one transaction with no commit (`envelopes/application/draft_allocation.py:23-24`), and the tests prove no ledger/allocation rows are written. (6) Inventory 31 -> 32 in `tests/api/test_export_openapi.py`; `docs/openapi.json` was deliberately NOT regenerated (8.4 owns it, D-113/D-114). (7) Gate evidence: `uv run pytest` 606 passed (588 pre-existing + 18 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "222 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | gate runs, red/green runs, audit and installed-source reads this session; db/schema.sql:457-503,1202-1203; test reproduction `assert 245 == 300` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 606 passed (588 pre-existing + 18 new);
`uv run ruff check .` "All checks passed!"; `uv run ruff format --check .` "222 files already
formatted"; `uv run pyright` "0 errors, 0 warnings, 0 informations". Audit: items 1-6 and 8 PASS;
item 7 FAIL until this batch, D-118 and the ROADMAP tick were written.

## Added 2026-10-28 (forty-second batch, step 8.2 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-120 | 2026-10-28 | Step 8.2 shape: every question Q1-Q8 was answered by the generic approval, so the brief's labelled suggestions stand (the D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109/D-111/D-117 pattern): (Q1=a) `POST /api/v1/allocations`, 201; (Q2=a) body `{occurred_on: date, note: str, amounts: {"<envelope_id>": int}}`, all three required, `p_by` from the JWT; (Q3=b) `201 {"id", "kind": "transfer", "pool_balance"}`; (Q4=a) a THIN app - pydantic strict whole numbers only, so zero, a negative entry, a non-digit key, an empty map, a blank note and an unknown or inactive envelope all reach `allocate` and answer 409 `rule_violation` with its own message (AGENTS.md section 5), while a non-integer value or a non-object `amounts` is FastAPI's 422 `validation_error`; (Q5=a) the adapter pre-checks `open_tenure_id()` so no open tenure answers 409 `no_open_tenure`, with `allocate`'s own check as the backstop; (Q6=a) the slice lives in `envelopes` with its own `ConfirmAllocationRepository`/`ConfirmAllocationUnitOfWork` (D-085); (Q7=a) the confirm write only, no allocation-session read route; (Q8=a) an unknown or inactive envelope answers 409 `rule_violation` naming the id, exactly as the function raises it. 32 new cases (9 unit, 22 API, 1 operation-inventory) and the inventory grew 32 -> 33. | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 8.2, D-083, D-084, D-085, D-117, D-119, AGENTS.md section 5 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-121 (proposed) | 2026-10-28 | Facts for later sessions. (1) `allocate`'s rejections split exactly as the 8.0 port predicted, and NO translator rule was needed: zero -> P0001 "zero amount for envelope %"; negative and a non-digit key/value -> P0001 "bad entry ..."; pool target, unknown envelope and inactive envelope -> P0001 "the pool cannot be allocated to itself" / "envelope % does not exist or is inactive"; empty map -> P0001 "nothing to allocate"; all become 409 `rule_violation` (`shared/infrastructure/error_mapping.py:34-38`). A blank note reaches the unnamed :259 CHECK -> 23514, whose message names `ledger_transactions_check` (D-115 (3)); over-allocation reaches `line_guard`, P0001 "would drop below zero" (:325-333); a pre-tenure date reaches `tx_guard`, mapped to `date_before_tenure` (:302-303). (2) The adapter passes only `p_by`, `p_date`, `p_note` and `p_amounts` (`envelopes/infrastructure/repository.py:172-186`): `allocate` finds the open tenure itself, so the `open_tenure_id()` pre-check exists only to name `no_open_tenure`; the response's `pool_balance` is read after the call from `envelope_balances`, and the returned id equals the new `allocation_sessions.ledger_transaction_id`. (3) The function hard-codes the header's `tag='allocation'` and `kind='transfer'`; the router's `kind="transfer"` literal mirrors it and is not read back from the row. (4) 8.2 test seeding fact: in the `lab` fixture's id order (pool 1, Events 2, Admin 3, Components 4, Projects 5, Research 6) the example's 3:2:1 shares map to Projects/Events/Research and the confirmed 1000 must include both cap fills, so the next draft of 600 answers 300/200/100 (same cap-fill rule as D-119 (2)). (5) Operation inventory 32 -> 33 in `tests/api/test_export_openapi.py`; `docs/openapi.json` was deliberately NOT regenerated (8.4 owns it, D-113/D-114). (6) Gate evidence: `uv run pytest` 637 passed (605 pre-existing + 32 new), `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "226 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | red/green runs, audit and installed-source reads this session; `db/schema.sql:259,302-303,325-333,444-448,507-534,1193-1194`; `src/mesl_finance/envelopes/infrastructure/repository.py:155-194`; `tests/envelopes/api/test_confirm_allocation_api.py` |

### Evidence for the step close

Gates this session (final run): `uv run pytest` 637 passed; `uv run ruff check .` "All checks passed!";
`uv run ruff format --check .` "226 files already formatted"; `uv run pyright` "0 errors, 0 warnings,
0 informations". Audit: items 1-6 and 8 PASS; item 7 FAIL until this batch and the ROADMAP tick were
written.

## Added 2026-10-28 (forty-third batch, step 8.3 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-122 | 2026-10-28 | Step 8.3 shape: every question Q1-Q6 was answered by the generic approval, so the brief's labelled suggestions stand (the D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109/D-111/D-117/D-120 pattern): (Q1=a) the slice lives in `cost_centers` - both operations are keyed by cost center; (Q2=a) `GET /api/v1/cost-centers/{cost_center_id}/summary`, ONE row, the view's own 8 columns; (Q3=a) `POST /api/v1/sweeps` with body `{cost_center_id, from_envelope_id, occurred_on, note}`, `note` required and non-blank, `p_by` from the JWT; (Q4=a) 201 `{"id", "kind": "sweep", "from_balance", "pool_balance"}`; (Q5=a) a THIN app - the leftover rules reach `sweep_leftover` and answer 409 `rule_violation` with its own message, only a non-whole id is 422 `validation_error` and only a blank note is the app's 422 `validation_failed`; (Q6=a) the sweep's reversal and second sweep stay DB-level (8.0's), no API test. 32 new cases (10 unit, 22 API), inventory 33 -> 35. | "The user approved the step brief for: go with your suggestions (if empty, the step briefed earlier in this session)." then "The user reviewed and approved the tests for:  (if empty, the step in this session)." | ROADMAP 8.3, D-083, D-084, D-085, D-087, D-116, D-120, AGENTS.md section 5 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-123 (proposed) | 2026-10-28 | Facts for later sessions. (1) NO translator rule was needed for 8.3: `sweep_leftover`'s own raises - 'nothing to sweep (leftover is 0)' (second sweep AND unknown cost center), 'sweep from an envelope other than the pool', and `line_guard`'s 'would drop below zero' on an unknown from-envelope (D-084/D-087: the negative line preempts the FK) - all reach the pre-existing P0001 -> `rule_violation` branch (`shared/infrastructure/error_mapping.py`); a pre-tenure date reaches `tx_guard` -> `date_before_tenure`; the adapter's `open_tenure_id()` pre-check names `no_open_tenure` (the 8.2 Q5=a pattern, D-121 (2)). (2) The adapter passes only the function's five parameters and reads BOTH balances back from `envelope_balances` (db/schema.sql:413-420) with ONE string-keyed `mappings()` query (D-089); `sweep_leftover` is NOT SECURITY DEFINER and `labapp` calls it through the default PUBLIC EXECUTE (D-119 (4)). (3) Intentional shapes not to silently change: the summary read never commits and never asks for an open tenure; the summary's 404 detail names the id (D-108 (1)); `SweepRequest.note` is a required field, so the blank-note 422 `validation_failed` is the domain's `Sweep.__post_init__`, not pydantic's. (4) Operation inventory 33 -> 35 in `tests/api/test_export_openapi.py`; `docs/openapi.json` was deliberately NOT regenerated (8.4 owns it, D-113/D-114). (5) Gate evidence: `uv run pytest` 669 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "235 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations". | gate runs, red/green runs, audit and installed-source reads this session; `db/schema.sql:33,71,240,413-420,537-557,560-574`; db/examples/06 lines 67-97 |

## Added 2026-10-28 (forty-fourth batch, step 8.4 close). Earlier rows above are unchanged.

### Confirmed by the user

| ID | Date | Decision | Evidence (the user's words) | Relates to |
|---|---|---|---|---|
| D-124 | 2026-10-28 | Step 8.4 shape, as briefed: NO-TEST, same shape as 7.6 (D-113) — `/code` regenerated `docs/openapi.json` ONLY with the documented command, and the refresh was verified read-only at the brief's suggested depth (structured diff vs the 7.6 file + byte-equality re-export + four gates). One mid-run stop: the agent's old-file snapshot attempt via `git stash` was permission-denied; with the user's approval ("go with your suggestion = a") the read-only alternative `git show HEAD:docs/openapi.json > /tmp/...` was used instead — no git state was ever changed. | "The user reviewed and approved the tests for: go with suggestions" then "go with your suggestion = a" | ROADMAP 8.4, D-113, D-114, D-027 |

### Discovered facts (proposed; verified from tool output this session)

| ID | Date | Fact | Evidence |
|---|---|---|---|
| D-125 (proposed) | 2026-10-28 | `docs/openapi.json` at step 8.4: sha256 `b67981c5ae7afc992acc65a62c57a8bd049f5bc65212d121f24f5f18c6bad2f8`, 83,127 bytes, 35 operations, 50 component schemas (supersedes D-114's 7.6 snapshot `29b20da…` / 71,614 bytes / 31 operations / 43 schemas, which stays as the 7.6 record; D-114 is NOT edited). The diff vs 7.6 is 450 insertions / 0 deletions: exactly the four 8.1-8.3 paths (`POST /api/v1/allocation-suggestion`, `POST /api/v1/allocations`, `GET /api/v1/cost-centers/{cost_center_id}/summary`, `POST /api/v1/sweeps`) and the seven new schemas (`AllocationConfirmedOut`, `AllocationSuggestionOut`, `AllocationSuggestionRequest`, `ConfirmAllocationRequest`, `CostCenterSummaryOut`, `SweepCreated`, `SweepRequest`); no path removed, no pre-existing path changed, `openapi` 3.1.0 / `info` / `securitySchemes` unchanged. A second fresh export is byte-identical (same sha). Regeneration stays env-independent (no `.env`, no `MESL_*`, no DB connection). Every later API step (9.5, 10.3, 12.2) reruns the same command; the "committed file matches the app" assertion remains 12.2's. Read-only old-file snapshots for future refresh audits: `git show HEAD:<path> > /tmp/...` (git plumbing, no tree mutation) — a stash is forbidden (git state). | byte comparison, structured diff and gate runs 2026-10-28: `uv run pytest` 669 passed, `uv run ruff check .` "All checks passed!", `uv run ruff format --check .` "235 files already formatted", `uv run pyright` "0 errors, 0 warnings, 0 informations" |
