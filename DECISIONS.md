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
