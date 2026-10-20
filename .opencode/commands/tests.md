---
description: Write ONLY the failing tests for the approved step, then stop for review.
agent: tester
---
The user approved the step brief for: $ARGUMENTS (if empty, the step briefed earlier in this session).

1. Re-read the roadmap line and the approved brief. Write the tests that were approved, nothing more. Only tests/ may be edited; no production code and no stubs in src/.
2. Before using any library API in a test, verify it in installed source or official docs (AGENTS.md section 3).
3. Run the new tests and paste the output.
   - CODE-WITH-TESTS step: each test must fail because the behaviour or module under test does not exist yet, not because of a mistake in the test itself. Fix the test if it fails for a wrong reason.
   - TEST-ONLY step that ports a worked example: the behaviour already exists, so the tests are expected to PASS. Instead, print a table that maps EVERY `EXPECT` and `EXPECT FAIL` line of the example to the test and assertion that covers it. Any unmapped line is a defect; fix it.
4. Run the whole suite and report that earlier tests still pass.
5. STOP. Ask the user to review the tests. Do not implement anything.
