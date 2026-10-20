---
description: Implement the approved step until the approved tests pass and all four gates are green.
agent: coder
---
The user reviewed and approved the tests for: $ARGUMENTS (if empty, the step in this session).

1. You cannot edit tests/. If a test looks wrong or impossible, STOP and explain; never work around it.
2. Write the smallest code that makes the approved tests pass. No extra features, endpoints, fields or dependencies.
3. Before using any library API, verify it in installed source or official docs (AGENTS.md section 3). SQL names come only from db/schema.sql.
4. Refactor with tests green.
5. Run all four gates and paste each output: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`. If any is red, fix it. Do not say "done" until all four are green.
6. STOP. Tell the user to run /review.
