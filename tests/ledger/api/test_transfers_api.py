"""POST /api/v1/transfers: the transfer action end to end (ROADMAP 6.4).

Approved contract (step 6.4 brief; Q1-Q7 were left unanswered, so the brief's
labelled suggestions stand, same pattern as D-062/D-064/D-066/D-070/D-076/D-079):
exactly two envelopes per request, a POSITIVE whole-BDT ``amount``, a required
non-blank ``note`` (db/schema.sql:259; blank names follow the same app-level
``validation_failed`` pattern, D-066 Q7=a), optional ``tag``/``cost_center_id``
and the same envelope on both sides refused by the domain. The response is
``201 {"id": n, "kind": "transfer", "from_balance": x, "to_balance": y}``.
The adapter writes the two lines that a transfer needs (sum zero,
db/schema.sql:353-354); unknown envelopes are named by an app pre-check
(D-083/D-084), because ``line_guard`` is a BEFORE INSERT trigger.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb, idempotent

POOL, EVENTS, ADMIN = 1, 2, 3


def transfer(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "amount": 200,
        "occurred_on": "2026-02-02",
        "from_envelope_id": POOL,
        "to_envelope_id": EVENTS,
        "note": "for workshop",
    }
    body.update(overrides)
    return body


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


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
        headers=idempotent(auth, "fund-1-1"),
    )
    assert response.status_code == 201


async def test_a_transfer_moves_money_from_one_envelope_to_another(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await client.post("/api/v1/transfers", json=transfer(), headers=auth)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "kind", "from_balance", "to_balance"}
    assert (body["kind"], body["from_balance"], body["to_balance"]) == ("transfer", 300, 200)
    row = await lab.owner.fetchrow("SELECT * FROM ledger_transactions WHERE id = $1", body["id"])
    assert row is not None
    assert (row["kind"], row["recorded_by"], row["note"]) == ("transfer", USERNAME, "for workshop")
    lines = await lab.owner.fetch(
        "SELECT envelope_id, amount FROM ledger_lines"
        " WHERE transaction_id = $1 ORDER BY envelope_id",
        body["id"],
    )
    assert [(r["envelope_id"], r["amount"]) for r in lines] == [(POOL, -200), (EVENTS, 200)]
    assert await balances(lab) == {POOL: 300, EVENTS: 200, ADMIN: 0}


async def test_a_transfer_may_move_money_back_to_the_pool(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)
    first = await client.post("/api/v1/transfers", json=transfer(), headers=auth)
    assert first.status_code == 201

    response = await client.post(
        "/api/v1/transfers",
        json=transfer(amount=50, from_envelope_id=EVENTS, to_envelope_id=POOL),
        headers=auth,
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["from_balance"], body["to_balance"]) == (150, 350)
    assert await balances(lab) == {POOL: 350, EVENTS: 150, ADMIN: 0}


async def test_a_transfer_keeps_its_note_tag_and_cost_center(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)
    cost_center = await lab.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Workshop 1', 'event') RETURNING id"
    )

    response = await client.post(
        "/api/v1/transfers",
        json=transfer(note="workshop budget", tag="workshop", cost_center_id=cost_center),
        headers=auth,
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert (row["note"], row["tag"], row["cost_center_id"]) == (
        "workshop budget",
        "workshop",
        cost_center,
    )
    open_tenure = await lab.owner.fetchval("SELECT id FROM tenures WHERE closed_on IS NULL")
    assert row["tenure_id"] == open_tenure
    assert (response.json()["from_balance"], response.json()["to_balance"]) == (300, 200)


async def test_an_overdrawing_transfer_is_a_409_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=100)

    response = await client.post(
        "/api/v1/transfers",
        json=transfer(amount=150, from_envelope_id=EVENTS, to_envelope_id=POOL),
        headers=auth,
    )

    assert_problem(response, 409, "rule_violation")
    assert "below zero" in response.json()["detail"].lower()
    assert await entry_count(lab) == 1  # only the funding deposit
    assert await balances(lab) == {POOL: 0, EVENTS: 100, ADMIN: 0}


async def test_a_transfer_from_an_inactive_envelope_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await lab.app.execute("UPDATE envelopes SET active = false WHERE id = $1", ADMIN)

    response = await client.post(
        "/api/v1/transfers",
        json=transfer(amount=10, from_envelope_id=ADMIN, to_envelope_id=POOL),
        headers=auth,
    )

    assert_problem(response, 409, "rule_violation")
    assert "inactive" in response.json()["detail"].lower()
    assert await entry_count(lab) == 0


async def test_a_transfer_to_an_inactive_envelope_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)
    await lab.app.execute("UPDATE envelopes SET active = false WHERE id = $1", ADMIN)

    response = await client.post(
        "/api/v1/transfers",
        json=transfer(amount=10, from_envelope_id=POOL, to_envelope_id=ADMIN),
        headers=auth,
    )

    assert_problem(response, 409, "rule_violation")
    assert "inactive" in response.json()["detail"].lower()
    assert await entry_count(lab) == 1
    assert await balances(lab) == {POOL: 500, EVENTS: 0, ADMIN: 0}


@pytest.mark.parametrize("side", ["from_envelope_id", "to_envelope_id"])
async def test_an_unknown_envelope_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], side: str
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await client.post("/api/v1/transfers", json=transfer(**{side: 999}), headers=auth)

    assert_problem(response, 422, "unknown_reference")
    assert await entry_count(lab) == 1
    assert await balances(lab) == {POOL: 500, EVENTS: 0, ADMIN: 0}


async def test_the_same_envelope_twice_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await client.post(
        "/api/v1/transfers", json=transfer(to_envelope_id=POOL), headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert await entry_count(lab) == 1
    assert await balances(lab) == {POOL: 500, EVENTS: 0, ADMIN: 0}


@pytest.mark.parametrize("note", ["", "   "])
async def test_a_blank_note_is_a_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], note: str
) -> None:
    response = await client.post("/api/v1/transfers", json=transfer(note=note), headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await entry_count(lab) == 0


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
async def test_a_bad_amount_is_a_422_problem(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    response = await client.post("/api/v1/transfers", json=transfer(amount=amount), headers=auth)

    assert_problem(response, 422, "validation_error")
    assert await entry_count(lab) == 0


async def test_a_date_before_the_tenure_opened_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await client.post(
        "/api/v1/transfers", json=transfer(occurred_on="2025-12-31"), headers=auth
    )

    assert_problem(response, 409, "date_before_tenure")
    assert await entry_count(lab) == 1


async def test_without_an_open_tenure_the_answer_is_a_409(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/transfers", json=transfer(), headers=auth)

    assert_problem(response, 409, "no_open_tenure")
    assert await entry_count(db) == 0


async def test_the_transfer_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/transfers", json=transfer())

    assert_problem(response, 401, "invalid_token")
    assert await entry_count(lab) == 0


@pytest.mark.parametrize("extra", [{"member_id": 1}, {"source": "other"}])
async def test_member_and_source_are_not_part_of_the_transfer_contract(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], extra: dict[str, Any]
) -> None:
    """Q6=a: only tag/cost_center are optional; deposits own source and member."""
    response = await client.post("/api/v1/transfers", json=transfer(**extra), headers=auth)

    assert_problem(response, 422, "validation_error")
    assert await entry_count(lab) == 0
