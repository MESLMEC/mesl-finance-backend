---
description: Read-only audit of the finished step. Reports PASS or FAIL with file:line. Edits nothing.
agent: reviewer
---
Audit the current working tree for the step: $ARGUMENTS (if empty, the step in this session). Read ROADMAP.md, DECISIONS.md, BUSINESS.md, AGENTS.md first, then `git status` and `git diff`.

Check each item and answer PASS or FAIL with file:line evidence:
1. Scope: any change outside the step's goal and listed files?
2. Library calls: grep installed source in .venv for every non-obvious call; does each exist with those arguments?
3. SQL: does every table, column, function, constraint and enum value used appear in db/schema.sql or a later db/sql/ payload?
4. Layering: any forbidden import (domain or application importing fastapi/sqlalchemy/asyncpg/pydantic or infrastructure)?
5. SQL safety: any value put into SQL by string formatting?
6. Any TODO, placeholder, stub, commented-out code, or silent assumption?
7. Any decision or fact a future session needs that is not yet written in DECISIONS.md or ROADMAP.md?
8. Run the four gates and report the results.
9. Bug fix: does a regression test exist that fails without the fix?
End with one line: PASS or FAIL. Edit nothing.
