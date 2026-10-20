---
description: Close the step. Tick the roadmap, log decisions, print the commit message. Never commits.
agent: coder
---
Close the step: $ARGUMENTS (if empty, the step in this session).

1. Run the four gates. If any is red, STOP and report.
2. Tick this step in ROADMAP.md. Add a one-line `Notes:` under it ONLY if a later session needs a fact that is not obvious from the code.
3. Append to DECISIONS.md any decision made this session. Status `confirmed` only where the user said it in this session (quote their words); otherwise `proposed`. Never edit old entries.
4. List anything a future session must know that is not yet in a file. Write it, or ask the user where it belongs.
5. Run `git status`. Print the changed files and ONE suggested commit message. Do not commit.
