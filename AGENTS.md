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
- a business rule that is not in db/schema.sql, a ticked BUSINESS.md line, or a confirmed DECISIONS.md entry
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
| `db/schema.sql`, `db/examples/` | database truth and its acceptance spec | never edited |

Authority when sources conflict (highest first): the user's words in this session; confirmed
DECISIONS.md entries; db/schema.sql and db/examples; ticked BUSINESS.md lines; ROADMAP.md; this
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
`/wrapup` (tick roadmap, log decisions, print commit message). The USER commits. You never run
`git add`, `git commit`, `git push`, or anything that changes git state.
Do only the step in hand. Never start the next step.

## 3. Verify before you use

- **Library APIs:** read the installed source under `.venv/lib/python*/site-packages/<package>/`
  or the official docs (webfetch, which asks the user first) BEFORE writing the call. Do not use a
  function, argument or behaviour you have not seen this session. Versions come from `pyproject.toml`
  and `uv.lock`, never from memory.
- **SQL names** (tables, columns, functions, constraints, enum values): only from `db/schema.sql`.
  Search it. Real-database tests are the final check.
- **OpenCode v2.0.29 here has no LSP and does not run formatters.** You run `uv run pyright` and
  `uv run ruff` yourself after changes.

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

## 7. Never

- Never invent endpoints, fields, columns, rules, versions or API calls.
- Never weaken, skip or delete a test to get green.
- Never add features, dependencies or files beyond the current step.
- Never read or print `.env` files; never commit secrets.
- Never claim something works without showing the command output from this session.
