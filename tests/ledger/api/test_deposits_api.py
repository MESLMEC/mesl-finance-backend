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


async def entry_count(db: TestDb) -> int:
    return int(await db.app.fetchval("SELECT count(*) FROM ledger_transactions"))


async def test_a_deposit_lands_in_the_pool_by_default(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/deposits", json=deposit(note="sponsor", tag="sponsorship"), headers=auth
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
        "/api/v1/deposits",
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
        "/api/v1/deposits",
        json=deposit(source="weekly_fee", member_id=member, amount=100),
        headers=auth,
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT member_id FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert row["member_id"] == member
    assert (await balances(lab))[POOL] == 100


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
async def test_a_bad_amount_is_a_422_problem(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    response = await client.post("/api/v1/deposits", json=deposit(amount=amount), headers=auth)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert (await balances(lab))[POOL] == 0


async def test_a_weekly_fee_without_a_member_is_rejected_before_touching_the_database(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/deposits", json=deposit(source="weekly_fee"), headers=auth
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_a_weekly_fee_naming_an_envelope_is_a_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('B') RETURNING id")

    response = await client.post(
        "/api/v1/deposits",
        json=deposit(source="weekly_fee", member_id=member, envelope_id=EVENTS),
        headers=auth,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert await entry_count(lab) == 0


async def test_a_non_weekly_source_with_a_member_is_a_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('C') RETURNING id")

    response = await client.post("/api/v1/deposits", json=deposit(member_id=member), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert await entry_count(lab) == 0


async def test_an_unknown_source_is_a_422_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/deposits", json=deposit(source="gift"), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await entry_count(lab) == 0


async def test_an_unknown_member_is_a_422_not_a_500(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/deposits", json=deposit(source="weekly_fee", member_id=999), headers=auth
    )

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert (await balances(lab))[POOL] == 0  # nothing half-written


async def test_an_unknown_envelope_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/deposits", json=deposit(envelope_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await lab.owner.fetchval("SELECT count(*) FROM ledger_transactions") == 0


async def test_a_deposit_with_an_unknown_cost_center_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/deposits", json=deposit(cost_center_id=999), headers=auth)

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_reference"
    assert await entry_count(lab) == 0


async def test_a_deposit_into_an_inactive_envelope_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await lab.app.execute("UPDATE envelopes SET active = false WHERE id = $1", EVENTS)

    response = await client.post(
        "/api/v1/deposits",
        json=deposit(source="registration", envelope_id=EVENTS),
        headers=auth,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "rule_violation"
    assert "inactive" in response.json()["detail"].lower()
    assert await entry_count(lab) == 0


async def test_a_deposit_keeps_its_tag_and_cost_center(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await lab.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Annual Fest', 'event') RETURNING id"
    )

    response = await client.post(
        "/api/v1/deposits",
        json=deposit(amount=700, note="gate takings", tag="fest", cost_center_id=cost_center),
        headers=auth,
    )

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", response.json()["id"]
    )
    assert row is not None
    assert (row["tag"], row["cost_center_id"]) == ("fest", cost_center)
    open_tenure = await lab.owner.fetchval("SELECT id FROM tenures WHERE closed_on IS NULL")
    assert row["tenure_id"] == open_tenure
    assert (await balances(lab))[POOL] == 700
    line = await lab.owner.fetchrow(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1",
        response.json()["id"],
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (POOL, 700)


async def test_the_deposit_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/deposits", json=deposit())

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"
    assert await entry_count(lab) == 0


async def test_a_date_before_the_tenure_opened_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/deposits", json=deposit(occurred_on="2025-12-31"), headers=auth
    )

    assert response.status_code == 409
    assert response.json()["code"] == "date_before_tenure"


async def test_without_an_open_tenure_the_answer_is_a_409(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/deposits", json=deposit(), headers=auth)

    assert response.status_code == 409
    assert response.json()["code"] == "no_open_tenure"
