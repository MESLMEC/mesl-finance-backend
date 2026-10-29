"""GET /api/v1/health: the database's own verify_all() surfaced as one read
(roadmap step 12.1).

Approved step brief this session (the brief's labelled suggestions, since the
user answered "go"): Q1=a the route is `GET /api/v1/health`; Q2=a it requires
the bearer JWT like every other read; Q3=a the body is a bare JSON array of
problem strings, `[]` = healthy; Q4=a 200 when the report is empty, 503 with
the SAME body shape when it has problems; Q5=a a new `health` feature package;
Q6=a a normal documented route (operation inventory 52 -> 53); Q7=a one real
tamper API test on top of the unit fake.

Database rules these tests rely on (db/schema.sql:1180-1183, read this
session): `verify_all()` is `verify_integrity() UNION ALL verify_assets()
UNION ALL verify_reconciliations()`, one `problem text` column, empty result =
healthy; it is NOT SECURITY DEFINER and is not REVOKEd, so `labapp` reaches it
through the default PUBLIC EXECUTE plus its own SELECT grants (:1189-1203).

The one-problem tamper is the reconciliation drift already pinned at
tests/db/test_reconciliation.py:537-553 (D-146 (6)): disable `no_change_rec`,
bump `system_total` by 5, and `verify_reconciliations` reports exactly one
problem naming the reconciliation. The tamper must start from a MISMATCH
(matched=false): the row's two table CHECKs are `difference = counted_total -
system_total` and `NOT matched OR difference = 0`, so a matched row cannot be
bumped without violating one of them (the same seed tests/db/test_reconciliation.py
uses). The tenure in the `lab` fixture opened on 2026-01-01; envelopes pool=1.

Library APIs used, all verified in installed source this session:
- httpx AsyncClient.get/post with `headers=` (0.28.1);
- asyncpg Connection.transaction()/fetchval/execute for the seed, and
  `ALTER TABLE ... DISABLE/ENABLE TRIGGER` as owner (tests/db/test_reconciliation.py);
- the real `client` / `lab` / `auth` fixtures from tests/conftest.py.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb

POOL = 1


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def entry(
    db: TestDb, kind: str, lines: list[tuple[int, int]], *, source: str | None = None
) -> None:
    """One ledger entry (header + lines) as `labapp`, in one transaction."""
    async with db.app.transaction():
        tx: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " source, note) VALUES (1, $1, current_date, 'treasurer', $2, '') RETURNING id",
            kind,
            source,
        )
        for envelope_id, amount in lines:
            await db.app.execute(
                "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
                tx,
                envelope_id,
                amount,
            )


async def test_health_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.get("/api/v1/health")

    assert_problem(response, 401, "invalid_token")


async def test_a_healthy_database_reports_no_problems(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # the lab fixture opens a tenure and envelopes but writes no ledger entries

    response = await client.get("/api/v1/health", headers=auth)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == []


async def test_a_tampered_reconciliation_is_reported(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # a deposit of 100, then a MISMATCH (counted 80): system_total 100, matched=false
    await entry(lab, "deposit", [(POOL, 100)], source="other")
    response = await client.post(
        "/api/v1/reconciliations", json={"counted_total": 80}, headers=auth
    )
    assert response.status_code == 201

    await lab.owner.execute("ALTER TABLE reconciliations DISABLE TRIGGER no_change_rec")
    await lab.owner.execute(
        "UPDATE reconciliations SET system_total = system_total + 5,"
        " difference = difference - 5 WHERE id = 1"
    )
    await lab.owner.execute("ALTER TABLE reconciliations ENABLE TRIGGER no_change_rec")

    response = await client.get("/api/v1/health", headers=auth)

    assert response.status_code == 503
    # a bare array of problem strings (Q3=a), not a wrapped object
    problems: list[str] = [str(p) for p in response.json()]
    assert len(problems) == 1
    assert "reconciliation #1" in problems[0]
