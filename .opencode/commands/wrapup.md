---
description: Close the step. Tick the roadmap, log decisions, print the commit message. Never commits.
agent: coder
---
Close the step: $ARGUMENTS (if empty, the step in this session).

1. Run the four gates. If any is red, STOP and report.
2. Roadmap step: tick it in ROADMAP.md (Notes line only if needed). Issue: do NOT edit ROADMAP.md; print a closing comment for the issue (root cause, fix, tests added) and a commit message ending in `Fixes #N`.
3. Append to DECISIONS.md any decision made this session. Status `confirmed` only where the user said it in this session (quote their words); otherwise `proposed`. Never edit old entries.
4. List anything a future session must know that is not yet in a file. Write it, or ask the user where it belongs.
5. Run `git status`. Print the changed files and ONE suggested commit message. Do not commit.
