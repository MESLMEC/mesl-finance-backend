---
description: Read-only auditor. Checks a finished step against the rules and reports PASS or FAIL. Edits nothing.
mode: all
permissions:
  - action: shell
    resource: "uv run pytest*"
    effect: allow
  - action: shell
    resource: "uv run ruff*"
    effect: allow
  - action: shell
    resource: "uv run pyright*"
    effect: allow
  - action: shell
    resource: "git status*"
    effect: allow
  - action: shell
    resource: "git diff*"
    effect: allow
  - action: shell
    resource: "git log*"
    effect: allow
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
---
