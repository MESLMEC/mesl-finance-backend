# Live-system maintenance guide

The roadmap is finished; it is history now. Every change starts as an ISSUE: a bug, a question
about behaviour, a change request or a feature. Judgement comes before code. The user decides;
the agent investigates, cites evidence and recommends.

## 1. Intake: `/triage <description>`
Read-only. It produces a triage report (section 7). The user decides and posts the report on
the issue (as a comment), then `/start #N` runs the normal tests -> code -> review -> wrapup routine.

## 2. Classify (first match wins)
| Type | Meaning | Default outcome |
|---|---|---|
| Data-entry mistake | The app did what it should; a wrong value was typed | No code. Fix with reversal + replacement, label edit or adjustment through the app. Check reconciliation. |
| Works as designed | A source in section 3 states this behaviour | Explain with the citation. If it is only confusing, tell the frontend team. |
| Bug | Behaviour violates a source in section 3, or a 500/crash | Regression test first, then minimal fix. |
| Gap | No source says what should happen | ASK the user. Record the answer as a decision. Then it is a bug or a change. |
| Change request | Works as designed, but the lab wants it different | Judge it (section 4). Needs a new decision that supersedes the old one. |
| New feature | New capability | Judge it (section 4), then build in small slices. |
| Not backend | Frontend, deployment, hardware, people | Say so and stop. |

## 3. Is it intended? Evidence, highest first
The user's words in this session; confirmed DECISIONS.md entries; db/schema.sql and db/examples;
ticked BUSINESS.md lines; existing tests; code. **Code alone never proves intent**: "the code does
X" is not "X is intended". Cite IDs and file:line. To answer "why is it intended", read the
Evidence column of the decision; if no reason is recorded, ask the user and record it.

## 4. Judging a change or feature: answer every item in writing
1. Problem: what real lab problem, how often, who is hurt (today only the treasurer)?
2. Money history: does it alter past numbers? History is immutable (B-18), a fee-rate change affects
   only future weeks (B-05), a closed tenure is locked. Usually decline, or do it with new entries.
3. Schema: does it need DDL? D-018: stop and consult; first find a no-DDL alternative.
4. API contract: additive (safe) or breaking? A breaking change must be announced to the frontend team.
5. Conflict: does it contradict a confirmed decision or ticked business line? Then a new decision
   must explicitly supersede it, quoting the user.
6. Smallest useful version; is it reversible; what can go wrong (list the edge cases).
7. Outcome: ACCEPT, ACCEPT-MODIFIED, DEFER (with the trigger that revives it), DECLINE (with the
   reason, so it is not argued again), or WORKAROUND (no code).
The agent recommends. The user decides. The decision is written to DECISIONS.md.

## 5. Executing
- Bug: reproduce first. Cannot reproduce: ask for the data, never guess-fix. Find the root cause
  and write it in the issue entry. Tester writes the failing regression test, coder fixes minimally.
  Same fix failing twice: stop and report; do not try a third guess.
- Change or feature: the triage report's acceptance tests become the step brief; the issue
  replaces the roadmap step. Too big for one session: split into several issues first.
- Severity S1 (money wrong or data at risk): stop adding entries (the user decides), preserve
  evidence, never edit rows in the database directly. Correct only through app actions
  (reversal + replacement, label edit, adjustment), then reconcile.
- Schema change on live data: only after consulting the user (D-018); the user takes a `pg_dump`
  first; try the Alembic revision on a copy before the real database.

## 6. Record
The issue tracker is the ONLY record of an issue and its progress; do not duplicate it in the repo.
The repo keeps only what future sessions need: decisions (DECISIONS.md), business rules
(BUSINESS.md, the user ticks), regression tests, and a commit message that says `Fixes #N`.
A new standing rule needs the user's approval of the exact wording.

## 7. Triage report format
a. Issue in one sentence; what could NOT be confirmed. b. Evidence from reproduction (file:line,
output). c. Type and the sources that prove intent. d. Section 4 answers, if a change/feature.
e. Recommended outcome, acceptance tests (name + one-line behaviour), step type, files likely
touched, DDL needed?, severity. f. Numbered questions with options and a labelled suggestion.
g. A short comment the user can post on the issue: type, outcome, acceptance tests, decisions to record.

## 8. Pitfalls
Fixing the number instead of the cause. Calling a typing mistake a bug. Adding a setting for a
one-off. Touching past-week fee behaviour. "While I am here" extras. Fixing two issues in one
session. Declining without recording why. A recurring issue means a regression test, and maybe a
BUSINESS.md line.
