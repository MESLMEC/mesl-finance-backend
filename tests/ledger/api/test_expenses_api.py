"""POST /api/v1/expenses: the expense action end to end (ROADMAP 6.3).

Contract (step 6.3 brief, Q1-Q6): the body carries a POSITIVE whole-BDT
``amount`` and a REQUIRED ``envelope_id`` (the pool is a valid envelope), no
``member_id`` (ROADMAP 7.4 owns member-linked refunds); the adapter writes the
one negative line that db/schema.sql:351-352 demands. The response is
``201 {"id": n, "kind": "expense", "balance": <envelope balance after>}``
(Q5=b).
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS = 1, 2


def expense(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"amount": 150, "occurred_on": "2026-02-03", "envelope_id": EVENTS}
    body.update(overrides)
    return body


async def balances(db: TestDb) -> dict[int, int]:
    rows = await db.owner.fetch("SELECT id, balance FROM envelope_balances")
    return {r["id"]: int(r["balance"]) for r in rows}


async def entry_count(db: TestDb) -> int:
    return int(await db.app.fetchval("SELECT count(*) FROM ledger_transactions"))


async def fund(client: AsyncClient, auth: dict[str, str], *, envelope_id: int, amount: int) -> None:
    """Put money into an envelope through the deposit action (step 6.2)."""
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "envelope_id": envelope_id,
        },
        headers=auth,
    )
    assert response.status_code == 201


async def test_an_expense_spends_from_the_named_envelope(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=500)

    response = await client.post("/api/v1/expenses", json=expense(), headers=auth)

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["balance"]) == ("expense", 350)
    row = await lab.owner.fetchrow("SELECT * FROM ledger_transactions WHERE id = $1", body["id"])
    assert row is not None
    assert (row["kind"], row["recorded_by"]) == ("expense", USERNAME)
    line = await lab.owner.fetchrow(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1", body["id"]
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (EVENTS, -150)
    assert (await balances(lab))[EVENTS] == 350


async def test_an_expense_may_spend_from_the_pool(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await client.post(
        "/api/v1/expenses", json=expense(envelope_id=POOL, amount=100), headers=auth
    )

    assert response.status_code == 201
    assert response.json()["balance"] == 400
    line = await lab.owner.fetchrow(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1",
        response.json()["id"],
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (POOL, -100)
    assert (await balances(lab))[POOL] == 400


async def test_an_expense_keeps_its_note_tag_and_cost_center(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=500)
    cost_center = await lab.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Annual Fest', 'event') RETURNING id"
    )

    response = await client.post(
        "/api/v1/expenses",
        json=expense(note="lunch for volunteers", tag="catering", cost_center_id=cost_center),
        headers=auth,
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert (row["note"], row["tag"], row["cost_center_id"]) == (
        "lunch for volunteers",
        "catering",
        cost_center,
    )
    open_tenure = await lab.owner.fetchval("SELECT id FROM tenures WHERE closed_on IS NULL")
    assert row["tenure_id"] == open_tenure
    assert response.json()["balance"] == 350


async def test_an_overdraw_is_a_409_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=100)

    response = await client.post("/api/v1/expenses", json=expense(amount=150), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "rule_violation"
    assert "below zero" in response.json()["detail"].lower()
    assert await entry_count(lab) == 1  # only the funding deposit
    assert (await balances(lab))[EVENTS] == 100


async def test_an_expense_from_an_inactive_envelope_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await lab.app.execute("UPDATE envelopes SET active = false WHERE id = $1", EVENTS)

    response = await client.post("/api/v1/expenses", json=expense(), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "rule_violation"
    assert "inactive" in response.json()["detail"].lower()
    assert await entry_count(lab) == 0


async def test_an_unknown_envelope_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/expenses", json=expense(envelope_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await entry_count(lab) == 0


async def test_an_expense_with_an_unknown_cost_center_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=500)

    response = await client.post("/api/v1/expenses", json=expense(cost_center_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await entry_count(lab) == 1  # only the funding deposit


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
async def test_a_bad_amount_is_a_422_problem(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    response = await client.post("/api/v1/expenses", json=expense(amount=amount), headers=auth)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert await entry_count(lab) == 0


async def test_a_date_before_the_tenure_opened_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=500)

    response = await client.post(
        "/api/v1/expenses", json=expense(occurred_on="2025-12-31"), headers=auth
    )

    assert response.status_code == 409
    assert response.json()["code"] == "date_before_tenure"
    assert await entry_count(lab) == 1


async def test_without_an_open_tenure_the_answer_is_a_409(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/expenses", json=expense(), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "no_open_tenure"
    assert await entry_count(db) == 0


async def test_the_expense_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/expenses", json=expense())

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"
    assert await entry_count(lab) == 0


async def test_a_member_is_not_part_of_the_expense_contract(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q4=a: member-linked refunds are ROADMAP 7.4; the body forbids extra fields."""
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('A') RETURNING id")

    response = await client.post("/api/v1/expenses", json=expense(member_id=member), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await entry_count(lab) == 0
