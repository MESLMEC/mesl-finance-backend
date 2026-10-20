---
description: Implements one approved roadmap step so the approved tests pass. Cannot edit tests/.
mode: primary
permissions:
  - action: edit
    resource: "src/**"
    effect: allow
  - action: edit
    resource: "pyproject.toml"
    effect: ask
  - action: edit
    resource: ".env.example"
    effect: ask
  - action: edit
    resource: "alembic/**"
    effect: ask
  - action: edit
    resource: "alembic.ini"
    effect: ask
  - action: edit
    resource: ".gitignore"
    effect: ask
  - action: edit
    resource: "docs/**"
    effect: ask
  - action: edit
    resource: "db/sql/*"
    effect: ask
  - action: edit
    resource: "ROADMAP.md"
    effect: ask
  - action: edit
    resource: "AGENTS.md"
    effect: allow
  - action: edit
    resource: "DECISIONS.md"
    effect: allow
  - action: edit
    resource: "*"
    effect: deny
---
