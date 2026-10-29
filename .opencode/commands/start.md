---
description: Begin a roadmap step. Reads state, writes the step brief, asks questions, then stops.
agent: plan
---
Session start. Work item: $ARGUMENTS. Either a roadmap step id (e.g. 6.2) or an issue: a number like #12, or pasted issue text with its triage comment. If empty: the first unticked ROADMAP.md step whose prerequisites are ticked; if there is none, STOP and ask which issue.

You remember nothing from earlier sessions. Do exactly this, in order, READ-ONLY:

1. Read ROADMAP.md, DECISIONS.md and BUSINESS.md completely. Re-read sections 0 to 3 of AGENTS.md.
2. Run `git status` and `git log --oneline -10`. Report whether the working tree is clean and whether the last commit matches the last ticked step. If not, STOP and say so.
3. Roadmap step: check that every prerequisite is ticked, else STOP. Issue: no prerequisites; the issue text plus its approved triage outcome are the brief. If the triage outcome is missing, STOP and tell the user to run /triage first.
4. Write the STEP BRIEF with these headings:
   a. Goal: one sentence, quoting the roadmap line or the issue.
   b. Authority: the decision IDs and ticked BUSINESS.md lines that apply. Flag any that are only `proposed` or unticked.
   c. Files you expect to create or change (exact paths).
   d. Tests you propose: name + one-line behaviour each. The user reviews these before any code exists.
   e. Library APIs you will need: for each, the .venv file or doc URL where you will verify it.
   f. Assumptions: this must say "none". Anything unknown goes in (g).
   g. Questions for the user, numbered, each with options and your labelled suggestion.
   h. DDL needed? If yes: "DB change needed: X; alternative: Y".
   i. Is the step small enough for one session? If not, propose how to split it.
   j. Step type (AGENTS.md section 2): CODE-WITH-TESTS, TEST-ONLY or NO-TEST, with one line why. Name which of /tests and /code will run.
5. STOP. Write no files. Wait for the user's answers and an explicit "go".
