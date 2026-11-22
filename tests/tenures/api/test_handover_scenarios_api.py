"""Carry-over opening and arrears-across-tenure scenarios end to end (ROADMAP 11.2).

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a TEST-ONLY - the behaviour already exists in
``db/schema.sql`` and is surfaced by the existing endpoints ``GET /api/v1/entries``
(6.7), ``GET /api/v1/dues`` (7.5) and ``GET /api/v1/tenures/{id}/member-snapshots``
(11.1), so these are scenario tests, no production code; Q2=a the carry-over
``opening`` is pinned by existence + note + fields, not by amounts (the amounts
stay database-verified by ``verify_integrity`` and the 7.0/8.0 example ports);
Q3=a include the negative case - a tenure with no ledger lines writes no
``opening``; Q4=a a new file.

Database rules these tests rely on (db/schema.sql, read this session):
- ``close_tenure(p_close_on, p_by, p_next_name)`` (:910-938) closes the open
  tenure, snapshots members/assets/holdings, ALWAYS inserts the next tenure with
  ``opened_on = p_close_on + 1``, and writes a carry-over ``opening`` entry into
  the new tenure ONLY when the closing tenure has ledger lines. The ``opening``
  header is ``kind='opening'``, ``occurred_on = p_close_on + 1``, ``note =
  'Carry-over from ' || t.name``, no ``source``/``member_id``/``tag``/
  ``cost_center_id`` (:926-936); ``one_opening_per_tenure`` (:264).
- ``entries_current`` (:426-430) is the treasurer's list with NO amounts
  (6.7 Q3=a), so the ``opening`` is asserted by its fields, not its carried sums.
- ``member_standing(p_as_of DEFAULT current_date)`` (:582-625) computes dues
  globally - it never references tenures - so a member's arrears naturally span a
  handover; ``dues_overview`` (:627-628) is ``SELECT * FROM member_standing()``.
- ``tenure_member_snapshots`` (:863-872) records each member's ``balance`` /
  ``owed`` at close, read back by the 11.1 ``member-snapshots`` route.

Seeding follows the existing API-test pattern (tests/fees/api/test_dues_api.py):
the fee rate, member and membership period are written through the OWNER
connection (setup), while every scenario step - deposit, close, and the reads -
goes through the API. The rate sits on ``sunday_on_or_before(current_date)``
(``s0``) so the member owes exactly one week, and the tenure closes on ``s0 + 2``
so the snapshot and ``/dues`` both bill that week.

Library APIs used, all verified in installed source this session:
- httpx ``AsyncClient.get`` (0.28.1, .venv/lib/python3.15/site-packages/httpx/
  _client.py:1751) and ``.post`` (:1838);
- asyncpg 0.32.0 ``Connection.execute`` / ``fetchval`` (asyncpg-stubs,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,236);
- pytest auto asyncio mode (pyproject.toml:25);
- the real ``client`` / ``lab`` / ``auth`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb, idempotent

RATE = 20


async def close_tenure(
    client: AsyncClient, auth: dict[str, str], *, close_on: date, next_name: str
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/tenures/close",
        json={"close_on": close_on.isoformat(), "next_name": next_name},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()


async def deposit(
    client: AsyncClient, auth: dict[str, str], *, amount: int, occurred_on: date
) -> int:
    response = await client.post(
        "/api/v1/deposits",
        json={"amount": amount, "occurred_on": occurred_on.isoformat(), "source": "other"},
        headers=idempotent(auth, "deposit-1-1"),
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def pay(
    client: AsyncClient, auth: dict[str, str], *, member_id: int, amount: int, occurred_on: date
) -> int:
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "source": "weekly_fee",
            "member_id": member_id,
        },
        headers=idempotent(auth, "deposit-1-2"),
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def entries(
    client: AsyncClient, auth: dict[str, str], *, tenure_id: int
) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/entries", params={"tenure_id": tenure_id}, headers=auth)
    assert response.status_code == 200
    return response.json()


async def dues(client: AsyncClient, auth: dict[str, str]) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/dues", headers=auth)
    assert response.status_code == 200
    return response.json()


async def member_snapshots(
    client: AsyncClient, auth: dict[str, str], *, tenure_id: int
) -> list[dict[str, Any]]:
    response = await client.get(f"/api/v1/tenures/{tenure_id}/member-snapshots", headers=auth)
    assert response.status_code == 200
    return response.json()


def by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["member_name"]: row for row in rows}


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def seed_rate(db: TestDb, effective_from: date, amount: int = RATE) -> None:
    await db.owner.execute(
        "INSERT INTO fee_rates (effective_from, amount, recorded_by) VALUES ($1, $2, 'treasurer')",
        effective_from,
        amount,
    )


async def seed_member(db: TestDb, name: str) -> int:
    member_id: int = await db.owner.fetchval(
        "INSERT INTO members (name) VALUES ($1) RETURNING id", name
    )
    return member_id


async def start_period(db: TestDb, member_id: int, start_date: date) -> None:
    await db.owner.execute(
        "INSERT INTO membership_periods (member_id, start_date) VALUES ($1, $2)",
        member_id,
        start_date,
    )


# ---- carry-over opening ------------------------------------------------------


async def test_close_after_a_deposit_writes_one_carry_over_opening(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await deposit(client, auth, amount=500, occurred_on=date(2026, 1, 15))
    closed = await close_tenure(client, auth, close_on=date(2026, 1, 31), next_name="2026B")

    # the next tenure opens on close_on + 1
    assert closed == {"id": 2, "name": "2026B", "opened_on": "2026-02-01"}

    tenure_one = await entries(client, auth, tenure_id=1)
    assert [(item["id"], item["kind"]) for item in tenure_one] == [(deposit_id, "deposit")]

    tenure_two = await entries(client, auth, tenure_id=2)
    assert len(tenure_two) == 1
    opening = tenure_two[0]
    assert opening["kind"] == "opening"
    assert opening["note"] == "Carry-over from 2026"
    assert opening["occurred_on"] == "2026-02-01"
    assert opening["recorded_by"] == "treasurer"
    assert opening["source"] is None
    assert opening["member_id"] is None
    assert opening["tag"] is None
    assert opening["cost_center_id"] is None
    assert opening["corrected_from"] is None


async def test_close_an_empty_tenure_writes_no_opening(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await close_tenure(client, auth, close_on=date(2026, 1, 31), next_name="2026B")

    assert await entries(client, auth, tenure_id=2) == []


# ---- arrears across tenure ---------------------------------------------------


async def test_arrears_survive_the_handover(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member_id = await seed_member(lab, "Ayesha")
    await start_period(lab, member_id, s0)

    await close_tenure(client, auth, close_on=s0 + timedelta(days=2), next_name="2027")

    ayesha = by_name(await dues(client, auth))["Ayesha"]
    assert ayesha["owed"] == RATE
    assert ayesha["credits"] == 0
    assert ayesha["balance"] == -RATE
    assert ayesha["weeks_overdue"] == 1

    snapshots = await member_snapshots(client, auth, tenure_id=1)
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert (snap["member_id"], snap["owed"], snap["balance"]) == (member_id, RATE, -RATE)


async def test_a_settled_member_stays_settled_across_the_handover(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member_id = await seed_member(lab, "Bashir")
    await start_period(lab, member_id, s0)
    await pay(client, auth, member_id=member_id, amount=RATE, occurred_on=s0)

    await close_tenure(client, auth, close_on=s0 + timedelta(days=2), next_name="2027")

    bashir = by_name(await dues(client, auth))["Bashir"]
    assert (bashir["owed"], bashir["credits"], bashir["balance"]) == (RATE, RATE, 0)
    assert bashir["weeks_overdue"] == 0

    snapshots = await member_snapshots(client, auth, tenure_id=1)
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert (snap["member_id"], snap["owed"], snap["balance"]) == (member_id, RATE, 0)
