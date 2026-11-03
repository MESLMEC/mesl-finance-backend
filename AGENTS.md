# MESL Finance Backend: rules for the building agent

You are the builder. **Sessions are stateless: you remember nothing from earlier sessions.**
Everything that must outlive a session lives in the files listed in section 1.
If it is not written in a file, it does not exist.

## 0. Prime directive: never assume, ask

An **assumption** is any fact that does not come from: (a) the user's messages in THIS session,
(b) files in this repo, (c) tool output you produced in THIS session, (d) installed library source
or official docs you read in THIS session. Your training memory is NOT a source.

When anything is missing, ambiguous or in conflict: **STOP.** Write numbered questions (for each:
the options you see, plus your suggestion labelled as a suggestion), end your turn, and do nothing
but read-only exploration until the user answers. Never fill a gap with a "reasonable default".
Never write placeholder / TODO / stub code to get past a gap.

Mandatory stop triggers:
- a business rule that is not in the database schema (`db/schema.sql` / later `db/sql/` payloads),
  a ticked BUSINESS.md line, or a confirmed DECISIONS.md entry
- a library function or option you have not seen in installed source/official docs this session
- a need to change the database schema (report: `DB change needed: X; alternative: Y`; write nothing)
- two sources disagree (user vs file, file vs file, test vs schema)
- an endpoint, field or name that no roadmap step or decision defines
- a test that looks wrong or impossible (you may not edit tests; report it)
- the roadmap step is unclear, too big for one session, or its prerequisites are not ticked
- anything destructive or outside the current step

## 1. Where persistent knowledge lives

| File | Holds | Who may change it |
|---|---|---|
| `AGENTS.md` | these rules | only with the user's explicit approval |
| `DECISIONS.md` | decisions, their status, open questions | append only (see below) |
| `BUSINESS.md` | the lab's business rules; only TICKED lines are authoritative | the user ticks; you propose |
| `ROADMAP.md` | the plan and progress, one step = one session = one commit | you tick a step after all gates pass |
| `db/schema.sql` | revision 0001's payload: the initial schema, executed in place | never edited (guarded by `tests/test_schema_hash.py`) |
| `db/sql/NNN_*.sql`, `alembic/versions/NNN_*.py` | the migration history after 0001: one hand-written payload + one thin revision per approved change | append only: new files; committed migrations never edited |
| `db/examples/` | the database's acceptance spec, ported into `tests/` just in time | never edited |

ROADMAP.md is history now. In this repo "step" means the current work item: a roadmap step OR an issue.
Live changes follow MAINTENANCE.md. The issue tracker holds issues; the repo holds only decisions, rules and tests.
Authority when sources conflict (highest first): the user's words in this session; confirmed
DECISIONS.md entries; the migration chain (`db/schema.sql` is its 0001 payload; `db/sql/` and
`alembic/versions/` are its history) and db/examples; ticked BUSINESS.md lines; ROADMAP.md; this
file. Entries marked `proposed` are NOT authority: ask the user to confirm or reject them.

Writing rules:
- Anything a later session needs (a decision, a convention, a discovered fact) MUST be written to
  a file before the session ends. Decisions go to DECISIONS.md. A new standing rule goes to
  AGENTS.md, but only after the user approves the exact wording.
- DECISIONS.md is append-only. Never edit or delete an old entry: add a new one that supersedes it.
  Mark an entry `confirmed` only if the user said it in this session, and quote their words.
  Otherwise mark it `proposed`.
- Never record your own preference as the user's decision.

## 2. Session routine (one roadmap step per session)

`/start` (read-only brief, questions) -> user answers and says "go" -> `/tests` (failing tests
only) -> user reviews the tests -> `/code` (implement) -> `/review` (read-only audit) ->
`/wrapup` (tick roadmap, log decisions, print commit message).
Two different agents do the two middle stages: `tester` writes tests and can edit only `tests/`;
`coder` writes code and can never edit `tests/`. Neither can do the other's job.
Every step has a type, stated in the `/start` brief and confirmed by the user:
- CODE-WITH-TESTS (most steps): the full routine above.
- TEST-ONLY (porting an example, fixing lint/type findings inside `tests/`): `/tests`, then
  `/review`, then `/wrapup`. Skip `/code`. For lint/type fixes the "failing test" is the red gate.
  For porting a worked example the behaviour already exists in the database, so the new tests are
  expected to PASS at once; proof of coverage is a table mapping EVERY `EXPECT` / `EXPECT FAIL`
  line of the example to a test assertion. An unmapped line is a defect.
- NO-TEST (pure configuration, no behaviour to assert): skip `/tests`; `/code`, `/review`, `/wrapup`.
If a step needs to edit both tests and source in a way that does not fit one type, STOP and ask:
the step should be split. The USER commits. You never run
`git add`, `git commit`, `git push`, or anything that changes git state.
Do only the step in hand. Never start the next step.

## 3. Verify before you use

- **Library APIs:** read the installed source under `.venv/lib/python*/site-packages/<package>/`
  or the official docs (webfetch, which asks the user first) BEFORE writing the call. Do not use a
  function, argument or behaviour you have not seen this session. Versions come from `pyproject.toml`
  and `uv.lock`, never from memory.
- **SQL names** (tables, columns, functions, constraints, enum values): only from `db/schema.sql`
  and later `db/sql/` payloads. Search them. Real-database tests are the final check.
- **OpenCode v2.0.29 here has no LSP and does not run formatters.** You run `uv run pyright` and
  `uv run ruff` yourself after changes.
- Tool names in OpenCode v2 are `shell` (never `bash`), `edit`/`write`/`patch`, `read`, `grep`, `glob`.
  If a tool is missing or a call is refused: STOP and report the exact error. Do not probe.
- Permission lists in `.opencode/agents/*.md` and OpenCode config: order broad
  `resource: "*"` deny rules BEFORE specific allows/asks. Two evaluations decide different
  things: the LAST rule matching a tool's action (resource ignored) decides whether the tool
  appears in the session's tool catalog at all — a final `*` deny strips `edit`/`write`/`shell`
  etc. entirely (OpenCode `packages/core/src/tool.ts::whollyDisabled`, v2.1.4) — while the last
  matching action+resource rule decides allow/ask/deny at call time. A `*`-deny placed after
  specific allows removed the edit tools from tester/coder sessions (D-050's wrong explanation).

## 4. Architecture (strict clean architecture, feature folders)

```
src/mesl_finance/
  shared/                # kernel: errors, settings, unit-of-work base, error translator
  <feature>/{domain,application,infrastructure,api}/
  main.py                # composition root: the only module that knows every layer
```
- domain: pure Python (no fastapi/sqlalchemy/asyncpg/pydantic imports). application: use cases +
  Protocol ports, depends on domain only. infrastructure: adapters and ALL SQL. api: routers,
  request/response schemas. Dependencies point inward only.
- API = business actions, one database transaction each, not generic CRUD.
- Money is a whole-BDT `int` everywhere. Never floats.

## 5. Database rules

- PostgreSQL owns the business rules. The app calls the right SQL in the right transaction and
  translates errors. Do not re-implement schema rules in Python.
- Connect as the limited `labapp` role, never as owner/superuser.
- Zero schema changes by default. Any DDL need: stop and report (section 0).
- Never put values into SQL by string formatting. Use bound parameters. Set the actor with
  `SELECT set_config('app.actor', :actor, true)` inside the transaction (`SET LOCAL` cannot take
  bound parameters, and `recorded_by`/label history must name the treasurer, not `labapp`).
- Entry-shape checks are DEFERRABLE triggers: they raise at COMMIT. Translate errors at both
  execute and commit time, in ONE infrastructure translator. Add a translation rule only together
  with the test that needs it.
- `allocate()` and `sweep_leftover()` run with the caller's rights (not SECURITY DEFINER).
  `reconcile()` and `close_tenure()` are SECURITY DEFINER. `close_tenure` is granted to `labapp` only.
- Ledger rows are never updated or deleted. Corrections are reversal + replacement in ONE transaction.

### Schema changes and the migration convention (D-018, D-031)

- The Alembic chain in `alembic/versions/` is the migration history. `alembic upgrade head` applies it
  in revision order as the owner (`MESL_ADMIN_DATABASE_URL`); tests build their template with it.
- `db/schema.sql` is revision 0001's payload. It is executed in place and never edited; the sha256 guard
  (`tests/test_schema_hash.py`) catches any change. 0001 has no downgrade.
- Zero schema changes by default. A change needs explicit user approval FIRST: report
  `DB change needed: X; alternative: Y`, write nothing until the user agrees and a roadmap step exists.
- Once approved, one change = two new files, one migration:
  1. `db/sql/NNN_<slug>.sql`: the SQL payload, written by hand.
  2. `alembic/versions/NNN_<slug>.py`: a thin revision with the same `NNN` and slug; `down_revision`
     is the previous revision; it reads the payload by path and executes it whole on the raw asyncpg
     connection inside `async with raw.transaction():`, exactly like `0001_initial.py` (D-031). No
     statement splitter.
- Payloads and revisions are append-only: never edit a committed migration; correct it with a new revision.
- No `autogenerate` and no model metadata: the SQL is the truth.

## 6. Test-driven development and gates

Failing test first, seen failing for the right reason. Smallest code. Refactor green. Tests run
against a real PostgreSQL (`tests/conftest.py`: template DB + one clone per test; needs
`TEST_ADMIN_DSN`, a superuser DSN). No mocked databases.
All four gates green before a step counts as done:
```
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Commit messages follow Conventional Commits v1.0.0 exactly (https://www.conventionalcommits.org/en/v1.0.0/#specification). Include EVERY applicable part, never omit one:
- header `<type>(<scope>)!: <imperative subject>`; subject <= 50 characters; `!` before the colon marks a breaking change;
- a body when the "why" is not obvious;
- every applicable footer, including `BREAKING CHANGE: <what breaks>` for any backward-incompatible change
  (for a schema change, say what old input now fails) and `Fixes #N` for the issue.
`/wrapup` prints the message; the user commits.

## 7. Never

- Never invent endpoints, fields, columns, rules, versions or API calls.
- Never weaken, skip or delete a test to get green.
- Never add features, dependencies or files beyond the current step.
- Never read or print `.env` files; never commit secrets.
- Never claim something works without showing the command output from this session.
