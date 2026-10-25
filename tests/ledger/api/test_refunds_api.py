"""POST /api/v1/refunds: the refund action end to end (ROADMAP 7.4).

Approved contract (step 7.4 brief, Q1-Q8 = a): the body is
``{amount, occurred_on, member_id, note="", tag, cost_center_id}`` with NO
envelope field, because `check_shape` (db/schema.sql:364-367) forces every
member-linked deposit/expense through the Unallocated General pool, so the
adapter resolves the pool itself. The response is
``201 {"id", "kind": "expense", "balance": <pool balance after>}``. PostgreSQL
owns the pool rule, the member link (`member_link_kinds`, :260), the overdraw
guard (`line_guard`, :319-337) and the tenure/date guard (`tx_guard`, :293-315);
there is no member-credit cap (Q6=a).

The payment half of the roadmap line already exists at ``POST /api/v1/deposits``
with ``source="weekly_fee"`` + ``member_id`` (pinned by
``tests/ledger/api/test_deposits_api.py``); this file covers only the refund.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL = 1


def refund(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"amount": 60, "occurred_on": "2026-02-03", "member_id": 1}
    body.update(overrides)
    return body


async def balances(db: TestDb) -> dict[int, int]:
    rows = await db.owner.fetch("SELECT id, balance FROM envelope_balances")
    return {r["id"]: int(r["balance"]) for r in rows}


async def entry_count(db: TestDb) -> int:
    return int(await db.app.fetchval("SELECT count(*) FROM ledger_transactions"))


async def fund(client: AsyncClient, auth: dict[str, str], amount: int) -> None:
    """Put money into the pool through the deposit action (step 6.2)."""
    response = await client.post(
        "/api/v1/deposits",
        json={"amount": amount, "occurred_on": "2026-02-01", "source": "sponsorship"},
        headers=auth,
    )
    assert response.status_code == 201


async def test_a_refund_is_a_member_linked_expense_out_of_the_pool(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('D') RETURNING id")
    await fund(client, auth, amount=500)

    response = await client.post("/api/v1/refunds", json=refund(member_id=member), headers=auth)

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["balance"]) == ("expense", 440)
    row = await lab.owner.fetchrow("SELECT * FROM ledger_transactions WHERE id = $1", body["id"])
    assert row is not None
    assert (row["kind"], row["member_id"], row["source"], row["recorded_by"]) == (
        "expense",
        member,
        None,
        USERNAME,
    )
    line = await lab.owner.fetchrow(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1", body["id"]
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (POOL, -60)
    assert (await balances(lab))[POOL] == 440


async def test_the_refund_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/refunds", json=refund())

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"
    assert await entry_count(lab) == 0


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
async def test_a_bad_refund_amount_is_a_422_problem(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    response = await client.post("/api/v1/refunds", json=refund(amount=amount), headers=auth)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert await entry_count(lab) == 0


async def test_a_refund_with_an_unknown_member_is_a_422_unknown_reference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/refunds", json=refund(member_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert "999" in response.json()["detail"]
    assert await entry_count(lab) == 0


async def test_a_refund_bigger_than_the_pool_is_a_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('E') RETURNING id")
    await fund(client, auth, amount=100)

    response = await client.post(
        "/api/v1/refunds", json=refund(member_id=member, amount=150), headers=auth
    )

    assert response.status_code == 409
    assert response.json()["code"] == "rule_violation"
    assert "below zero" in response.json()["detail"].lower()
    assert await entry_count(lab) == 1  # only the funding deposit
    assert (await balances(lab))[POOL] == 100


async def test_a_refund_dated_before_the_tenure_is_a_409_date_before_tenure(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('F') RETURNING id")
    await fund(client, auth, amount=500)

    response = await client.post(
        "/api/v1/refunds", json=refund(member_id=member, occurred_on="2025-12-31"), headers=auth
    )

    assert response.status_code == 409
    assert response.json()["code"] == "date_before_tenure"
    assert await entry_count(lab) == 1


async def test_a_refund_keeps_its_note_tag_and_cost_center(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('G') RETURNING id")
    await fund(client, auth, amount=500)
    cost_center = await lab.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Annual Fest', 'event') RETURNING id"
    )

    response = await client.post(
        "/api/v1/refunds",
        json=refund(
            member_id=member, note="refund of credit", tag="refund", cost_center_id=cost_center
        ),
        headers=auth,
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert (row["note"], row["tag"], row["cost_center_id"]) == (
        "refund of credit",
        "refund",
        cost_center,
    )
    assert response.json()["balance"] == 440


async def test_a_refund_with_an_unknown_cost_center_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('H') RETURNING id")
    await fund(client, auth, amount=500)

    response = await client.post(
        "/api/v1/refunds", json=refund(member_id=member, cost_center_id=999), headers=auth
    )

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await entry_count(lab) == 1  # only the funding deposit
