"""GET /api/v1/dues: the dues overview end to end (ROADMAP 7.5).

Approved brief this session: the user answered "go with your suggestions", so every
labelled suggestion stands (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/
D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109):
- Q1=b TWO routes only; this file pins ``GET /api/v1/dues``. The read is
  ``dues_overview``, which is ``SELECT * FROM member_standing() ORDER BY
  weeks_overdue DESC, who_name`` (db/schema.sql:627-628); there is no per-member
  route and no other filter in this step.
- Q2=a no ``as_of`` query parameter: the database's own ``current_date`` is used
  (the view calls ``member_standing()`` with its default, :582).
- Q3=a an item is ``{"member_id", "member_name", "is_member_now", "weeks_owed",
  "owed", "credits", "balance", "weeks_overdue", "oldest_unpaid_week"}``: the
  function's ``who_id``/``who_name`` are exposed as ``member_id``/``member_name``
  and the other seven columns keep the schema's names.
- Q4=a every member is listed exactly as the view returns it, including a member
  with no period and a settled member, in the view's order.
- Q6=a a missing pool envelope is out of scope (the bootstrap always creates one,
  D-041); it does not affect this read.
- Q9=a a read: one transaction, no commit, no open-tenure call; a missing token is
  401 ``invalid_token``.

Database rules these tests rely on (db/schema.sql, read this session):
- ``member_standing(p_as_of date DEFAULT current_date)`` (:582-625) computes every
  number: ``owed`` is the sum of the weekly rates the period covers, ``credits``
  is fee payments minus refunds plus adjustments, ``balance = credits - owed``,
  ``weeks_overdue`` counts the weeks whose running owed exceeds the credits, and
  ``oldest_unpaid_week`` is the first of them (:600-624);
- billing runs from ``min(fee_rates.effective_from)`` to
  ``sunday_on_or_before(p_as_of)`` (:587-591), so seeding ONE rate on the current
  Sunday makes a period that starts that Sunday owe exactly one week;
- ``rate_guard`` (:166-175) accepts a rate on the current week's Sunday;
- ``period_guard`` (:193-218) accepts a period starting on it once the tenure
  opened (the ``lab`` fixture opens 2026-01-01);
- ``member_adjustments`` waiver/credit rows feed ``credits`` through ``adj``
  (:607-609) and ``set_shutdown`` (:220-233) forgives a whole week;
- a fixed amount is one reversal plus one replacement (:243-256), and both carry
  the member (:212, :259), so ``credits`` shows the corrected amount once.

Rows are seeded through the owner connection (the 7.0/7.2/7.3 pattern): the
behaviour under test is the read, so a dues test must not depend on the write
endpoints answering first. The payment, refund, waiver, shutdown and fix-amount
actions are exercised through their own endpoints, because those are the links
this read must see.

No ``db/examples`` script is ported here: examples 03/04 already cover
``member_standing`` at the database level (step 7.0).

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.get/post`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838);
- ``asyncpg.Connection.fetch/fetchval/execute`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,213,236);
- ``pytest`` auto asyncio mode (pyproject.toml:25);
- the real ``client`` / ``lab`` / ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb, idempotent

STANDING_FIELDS = {
    "member_id",
    "member_name",
    "is_member_now",
    "weeks_owed",
    "owed",
    "credits",
    "balance",
    "weeks_overdue",
    "oldest_unpaid_week",
}
RATE = 20


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def seed_rate(db: TestDb, effective_from: date, amount: int = RATE) -> None:
    await db.owner.execute(
        "INSERT INTO fee_rates (effective_from, amount, recorded_by) VALUES ($1, $2, $3)",
        effective_from,
        amount,
        "treasurer",
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


async def dues(client: AsyncClient, auth: dict[str, str]) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/dues", headers=auth)
    assert response.status_code == 200
    body: list[dict[str, Any]] = response.json()
    return body


def by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["member_name"]: row for row in rows}


async def pay(
    client: AsyncClient, auth: dict[str, str], member_id: int, amount: int, occurred_on: date
) -> int:
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "source": "weekly_fee",
            "member_id": member_id,
        },
        headers=idempotent(auth, "pay-1-1"),
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def refund(
    client: AsyncClient, auth: dict[str, str], member_id: int, amount: int, occurred_on: date
) -> None:
    response = await client.post(
        "/api/v1/refunds",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "member_id": member_id,
        },
        headers=auth,
    )
    assert response.status_code == 201


async def waive(
    client: AsyncClient, auth: dict[str, str], member_id: int, amount: int, occurred_on: date
) -> None:
    response = await client.post(
        f"/api/v1/members/{member_id}/adjustments",
        json={
            "kind": "waiver",
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "note": "forgiven",
        },
        headers=auth,
    )
    assert response.status_code == 201


async def shut_down(client: AsyncClient, auth: dict[str, str], week: date) -> None:
    response = await client.post(
        "/api/v1/shutdown-weeks",
        json={"weeks": [week.isoformat()], "reason": "vacation"},
        headers=auth,
    )
    assert response.status_code == 201


async def fix_amount(
    client: AsyncClient, auth: dict[str, str], entry_id: int, amount: int, occurred_on: date
) -> None:
    response = await client.post(
        f"/api/v1/entries/{entry_id}/fix-amount",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "note": "amount typo",
        },
        headers=auth,
    )
    assert response.status_code == 201


async def test_the_dues_require_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dues")

    assert_problem(response, 401, "invalid_token")


async def test_the_dues_list_every_member_with_the_nine_fields(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    ayesha = await seed_member(lab, "Ayesha")
    bashir = await seed_member(lab, "Bashir")
    chitra = await seed_member(lab, "Chitra")
    await start_period(lab, ayesha, s0)
    await start_period(lab, bashir, s0)
    await pay(client, auth, bashir, RATE, s0)

    rows = await dues(client, auth)

    assert len(rows) == 3
    for row in rows:
        assert set(row) == STANDING_FIELDS
    assert by_name(rows)["Ayesha"] == {
        "member_id": ayesha,
        "member_name": "Ayesha",
        "is_member_now": True,
        "weeks_owed": 1,
        "owed": RATE,
        "credits": 0,
        "balance": -RATE,
        "weeks_overdue": 1,
        "oldest_unpaid_week": s0.isoformat(),
    }
    assert by_name(rows)["Bashir"] == {
        "member_id": bashir,
        "member_name": "Bashir",
        "is_member_now": True,
        "weeks_owed": 1,
        "owed": RATE,
        "credits": RATE,
        "balance": 0,
        "weeks_overdue": 0,
        "oldest_unpaid_week": None,
    }
    assert by_name(rows)["Chitra"] == {
        "member_id": chitra,
        "member_name": "Chitra",
        "is_member_now": False,
        "weeks_owed": 0,
        "owed": 0,
        "credits": 0,
        "balance": 0,
        "weeks_overdue": 0,
        "oldest_unpaid_week": None,
    }


async def test_the_dues_are_ordered_by_weeks_overdue_then_name(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    ayesha = await seed_member(lab, "Ayesha")
    bashir = await seed_member(lab, "Bashir")
    await seed_member(lab, "Chitra")
    await start_period(lab, ayesha, s0)
    await start_period(lab, bashir, s0)
    await pay(client, auth, bashir, RATE, s0)

    rows = await dues(client, auth)

    assert [row["member_name"] for row in rows] == ["Ayesha", "Bashir", "Chitra"]
    assert [row["weeks_overdue"] for row in rows] == [1, 0, 0]


async def test_the_dues_agree_with_the_view(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    ayesha = await seed_member(lab, "Ayesha")
    bashir = await seed_member(lab, "Bashir")
    await seed_member(lab, "Chitra")
    await start_period(lab, ayesha, s0)
    await start_period(lab, bashir, s0)
    await pay(client, auth, bashir, 50, s0)
    await refund(client, auth, bashir, 10, s0)
    await waive(client, auth, ayesha, 5, s0)

    rows = await dues(client, auth)

    view = await lab.owner.fetch("SELECT * FROM dues_overview")
    expected = [
        {
            "member_id": row["who_id"],
            "member_name": row["who_name"],
            "is_member_now": row["is_member_now"],
            "weeks_owed": row["weeks_owed"],
            "owed": row["owed"],
            "credits": row["credits"],
            "balance": row["balance"],
            "weeks_overdue": row["weeks_overdue"],
            "oldest_unpaid_week": (
                None if row["oldest_unpaid_week"] is None else row["oldest_unpaid_week"].isoformat()
            ),
        }
        for row in view
    ]
    assert len(rows) == 3
    assert rows == expected


async def test_a_member_with_no_period_owes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member = await seed_member(lab, "Later")

    rows = await dues(client, auth)

    assert rows == [
        {
            "member_id": member,
            "member_name": "Later",
            "is_member_now": False,
            "weeks_owed": 0,
            "owed": 0,
            "credits": 0,
            "balance": 0,
            "weeks_overdue": 0,
            "oldest_unpaid_week": None,
        }
    ]


async def test_a_fee_payment_and_a_refund_move_the_balance(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member = await seed_member(lab, "Ayesha")
    await start_period(lab, member, s0)
    await pay(client, auth, member, 50, s0)
    await refund(client, auth, member, 30, s0)

    row = by_name(await dues(client, auth))["Ayesha"]

    assert row["owed"] == RATE
    assert row["credits"] == 20
    assert row["balance"] == 0
    assert row["weeks_overdue"] == 0
    assert row["oldest_unpaid_week"] is None


async def test_a_waiver_and_a_shutdown_week_move_the_standing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member = await seed_member(lab, "Ayesha")
    await start_period(lab, member, s0)

    before = by_name(await dues(client, auth))["Ayesha"]
    assert (before["owed"], before["credits"], before["balance"]) == (RATE, 0, -RATE)

    await waive(client, auth, member, RATE, s0)

    waived = by_name(await dues(client, auth))["Ayesha"]
    assert (waived["owed"], waived["credits"], waived["balance"]) == (RATE, RATE, 0)
    assert waived["weeks_overdue"] == 0

    await shut_down(client, auth, s0)

    forgiven = by_name(await dues(client, auth))["Ayesha"]
    assert (forgiven["weeks_owed"], forgiven["owed"]) == (0, 0)
    assert (forgiven["credits"], forgiven["balance"]) == (RATE, RATE)
    assert forgiven["weeks_overdue"] == 0


async def test_a_fixed_amount_leaves_one_standing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member = await seed_member(lab, "Ayesha")
    await start_period(lab, member, s0)
    entry = await pay(client, auth, member, 30, s0)

    await fix_amount(client, auth, entry, 40, s0)

    row = by_name(await dues(client, auth))["Ayesha"]

    assert row["owed"] == RATE
    assert row["credits"] == 40
    assert row["balance"] == 20
    assert row["weeks_overdue"] == 0
