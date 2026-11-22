"""GET /api/v1/allocation-context: the allocation screen header (ROADMAP 7.5).

Approved brief this session (the user answered "go with your suggestions", so every
labelled suggestion stands):
- Q1=b the second of the TWO routes; this file pins
  ``GET /api/v1/allocation-context``.
- Q5=a the payload is exactly the view's three columns:
  ``{"pool_balance", "member_credit_held", "pool_after_member_credit"}``.
- Q8=a the read lives in the ``envelopes`` feature (the pool is an envelope).
- Q9=a a read: one transaction, no commit, no open-tenure call; a missing token is
  401 ``invalid_token``.

The view (db/schema.sql:630-634) is the single source:
``pool_balance`` is the OPEN tenure's balance of the pool envelope
(``envelope_balances``, :413-420), ``member_credit_held`` is the sum of the
POSITIVE ``member_standing()`` balances, and ``pool_after_member_credit`` is the
difference. The schema computes all three; the API invents no rule.

Q6=a: a missing pool envelope is OUT OF SCOPE. The bootstrap always creates the
pool (D-041), so these tests always run on the ``lab`` fixture, which makes one.
With no pool row the view's two pool columns are NULL and the response model would
refuse them; that gap is the same pre-existing one D-110 (2) records for the
deposit adapter, and it is not repaired by inventing a zero.

Rows are seeded through the owner connection where a row is only context (members,
periods, rates, as in 7.0/7.2/7.3); the ledger writes go through their endpoints,
because those are the numbers this read must see.

No ``db/examples`` script is ported here: example 06's ``allocation_context``
header is already covered at the database level by step 6.0's ports and 8.1 owns
``allocation_suggestion``.

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.get/post`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838);
- ``asyncpg.Connection.fetch/fetchrow/fetchval/execute`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,213,236,244);
- ``pytest`` auto asyncio mode (pyproject.toml:25);
- the real ``client`` / ``lab`` / ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb, idempotent

CONTEXT_FIELDS = {"pool_balance", "member_credit_held", "pool_after_member_credit"}
POOL = 1
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


async def context(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    response = await client.get("/api/v1/allocation-context", headers=auth)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


async def deposit(client: AsyncClient, auth: dict[str, str], amount: int, occurred_on: date) -> int:
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "source": "sponsorship",
        },
        headers=idempotent(auth, "deposit-1-1"),
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def spend(client: AsyncClient, auth: dict[str, str], amount: int, occurred_on: date) -> None:
    response = await client.post(
        "/api/v1/expenses",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "envelope_id": POOL,
        },
        headers=auth,
    )
    assert response.status_code == 201


async def pay(
    client: AsyncClient, auth: dict[str, str], member_id: int, amount: int, occurred_on: date
) -> None:
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


async def test_the_context_requires_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/allocation-context")

    assert_problem(response, 401, "invalid_token")


async def test_the_context_matches_the_view(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    member = await seed_member(lab, "Ayesha")
    await start_period(lab, member, s0)
    await pay(client, auth, member, 50, s0)
    await deposit(client, auth, 25, s0)

    body = await context(client, auth)

    row = await lab.owner.fetchrow(
        """
        SELECT pool_balance, member_credit_held, pool_after_member_credit
        FROM allocation_context
        """
    )
    assert row is not None
    assert set(body) == CONTEXT_FIELDS
    assert body == {
        "pool_balance": row["pool_balance"],
        "member_credit_held": row["member_credit_held"],
        "pool_after_member_credit": row["pool_after_member_credit"],
    }


async def test_member_credit_held_counts_only_positive_balances(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await seed_rate(lab, s0)
    ahead = await seed_member(lab, "Ahead")
    behind = await seed_member(lab, "Behind")
    await start_period(lab, ahead, s0)
    await start_period(lab, behind, s0)
    await pay(client, auth, ahead, 50, s0)

    body = await context(client, auth)

    assert body == {
        "pool_balance": 50,
        "member_credit_held": 30,
        "pool_after_member_credit": 20,
    }


async def test_the_pool_balance_follows_the_ledger(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    await deposit(client, auth, 100, s0)
    await spend(client, auth, 40, s0)

    body = await context(client, auth)

    assert body == {
        "pool_balance": 60,
        "member_credit_held": 0,
        "pool_after_member_credit": 60,
    }
