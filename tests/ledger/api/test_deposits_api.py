from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS = 1, 2


def deposit(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"amount": 500, "occurred_on": "2026-02-01", "source": "sponsorship"}
    body.update(overrides)
    return body


async def balances(db: TestDb) -> dict[int, int]:
    rows = await db.owner.fetch("SELECT id, balance FROM envelope_balances")
    return {r["id"]: int(r["balance"]) for r in rows}


async def test_a_deposit_lands_in_the_pool_by_default(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/deposits", json=deposit(note="sponsor", tag="sponsorship"), headers=auth
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert (row["kind"], row["source"], row["recorded_by"], row["note"]) == (
        "deposit",
        "sponsorship",
        USERNAME,
        "sponsor",
    )
    assert (await balances(lab))[POOL] == 500


async def test_a_deposit_can_target_another_envelope(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/deposits",
        json=deposit(source="registration", envelope_id=EVENTS, amount=300),
        headers=auth,
    )

    assert response.status_code == 201
    assert await balances(lab) == {1: 0, EVENTS: 300, 3: 0}


async def test_a_weekly_fee_is_linked_to_its_member_and_goes_to_the_pool(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('A') RETURNING id")

    response = await client.post(
        "/deposits", json=deposit(source="weekly_fee", member_id=member, amount=100), headers=auth
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT member_id FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert row["member_id"] == member
    assert (await balances(lab))[POOL] == 100


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100"])
async def test_a_bad_amount_is_a_422_problem(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    response = await client.post("/deposits", json=deposit(amount=amount), headers=auth)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert (await balances(lab))[POOL] == 0


async def test_a_weekly_fee_without_a_member_is_rejected_before_touching_the_database(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/deposits", json=deposit(source="weekly_fee"), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_an_unknown_member_is_a_422_not_a_500(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/deposits", json=deposit(source="weekly_fee", member_id=999), headers=auth
    )

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert (await balances(lab))[POOL] == 0  # nothing half-written


async def test_an_unknown_envelope_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/deposits", json=deposit(envelope_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await lab.owner.fetchval("SELECT count(*) FROM ledger_transactions") == 0


async def test_a_date_before_the_tenure_opened_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/deposits", json=deposit(occurred_on="2025-12-31"), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "date_before_tenure"


async def test_without_an_open_tenure_the_answer_is_a_409(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/deposits", json=deposit(), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "no_open_tenure"
