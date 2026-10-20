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
