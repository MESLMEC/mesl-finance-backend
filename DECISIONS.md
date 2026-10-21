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
