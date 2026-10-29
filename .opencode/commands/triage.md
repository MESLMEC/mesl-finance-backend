---
description: Triage a live issue. Classify, check intent, recommend. Read-only; writes nothing.
agent: plan
---
Issue: $ARGUMENTS

You remember nothing from earlier sessions. Read MAINTENANCE.md, DECISIONS.md and BUSINESS.md completely, and sections 0 to 3 of AGENTS.md. Then, READ-ONLY:

1. Restate the issue in one sentence. List what you could not confirm; if reproduction details are missing, ask for them.
2. Reproduce or trace it: find the endpoint, use case and SQL involved (names from db/schema.sql only). Show evidence with file:line or output you ran this session.
3. Classify it per MAINTENANCE.md section 2 and name the sources that prove intent (section 3). Never treat the code alone as proof.
4. If it is a change or feature, answer every item of section 4.
5. Give your recommended outcome, acceptance tests, step type, files likely touched, DDL needed, severity.
6. Ask numbered questions, each with options and your labelled suggestion.
7. Print a short comment the user can post on the issue: type, outcome, acceptance tests, decisions to record.
8. STOP. Write no files. The user decides, posts the comment, then runs `/start #N`.
