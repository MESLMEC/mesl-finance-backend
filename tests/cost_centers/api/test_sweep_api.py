"""POST /api/v1/sweeps: sweep an event's leftover back to the pool (ROADMAP 8.3).

Approved brief this session ("go with your suggestions", so every labelled
suggestion stands):

- Q3=a body ``{"cost_center_id": int, "from_envelope_id": int, "occurred_on":
  date, "note": str}`` - every field required; ``p_by``/``recorded_by`` is the
  JWT actor, never the client.
- Q4=a response ``201 {"id", "kind": "sweep", "from_balance", "pool_balance"}``.
- Q5=a a THIN app: the leftover rules reach ``sweep_leftover``
  (db/schema.sql:560-574) and answer 409 ``rule_violation`` with that
  function's own message - a second sweep ("nothing to sweep"), the pool as
  the source ("other than the pool"), an unknown cost center ("nothing to
  sweep (leftover is 0)"), an unknown from-envelope (D-084/D-087: the negative
  line reaches ``line_guard`` first, "would drop below zero", never the FK).
  Only a non-whole id is FastAPI's 422 ``validation_error`` and only a blank
  note is the app's 422 ``validation_failed`` (D-090 Q7=b).
- The adapter pre-checks the open tenure, so no open tenure answers 409
  ``no_open_tenure`` (the 8.2 Q5=a pattern); ``sweep_leftover``'s own check
  stays the backstop.
- Q1=a the slice lives in ``cost_centers`` with its own port (D-085).

The expected numbers are the worked example's
(db/examples/06_allocation_and_sweeps.sql lines 82-86: sweep 600, Events 0,
pool +600), seeded through the app's own deposit and expense actions in the
``lab`` fixture's id order. The sweep's reversal and the second sweep are NOT
pinned here (the approved brief dropped them): example lines 92-97 are already
ported at the database level by step 8.0 (D-115).

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.post`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1838);
- ``pydantic`` 2.14.1 strict ``int`` (a live probe this session: ``True``,
  ``10.5`` and ``"5"`` raise ValidationError, ``3`` is accepted);
- ``asyncpg.Connection.fetch/fetchrow/fetchval`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:213,236,244);
- pytest-asyncio auto mode (pyproject.toml:25) and the real ``client`` / ``lab``
  / ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS = 1, 2


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def create_event(client: AsyncClient, auth: dict[str, str], name: str) -> int:
    response = await client.post(
        "/api/v1/cost-centers", json={"name": name, "kind": "event"}, headers=auth
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


async def seed_event_spending(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], cost_center_id: int
) -> date:
    """Example lines 69-76: in 1000, out 400, both on the Events envelope."""
    s0 = await sunday(lab)
    deposit = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 1000,
            "occurred_on": (s0 + timedelta(days=4)).isoformat(),
            "source": "admin_grant",
            "envelope_id": EVENTS,
            "cost_center_id": cost_center_id,
        },
        headers=auth,
    )
    assert deposit.status_code == 201, deposit.text
    expense = await client.post(
        "/api/v1/expenses",
        json={
            "amount": 400,
            "occurred_on": (s0 + timedelta(days=5)).isoformat(),
            "envelope_id": EVENTS,
            "tag": "catering",
            "cost_center_id": cost_center_id,
        },
        headers=auth,
    )
    assert expense.status_code == 201, expense.text
    return s0


async def sweep(
    client: AsyncClient,
    auth: dict[str, str],
    cost_center_id: int,
    occurred_on: date,
    *,
    from_envelope_id: int = EVENTS,
    note: str = "event over; leftover back to pool",
) -> Any:
    return await client.post(
        "/api/v1/sweeps",
        json={
            "cost_center_id": cost_center_id,
            "from_envelope_id": from_envelope_id,
            "occurred_on": occurred_on.isoformat(),
            "note": note,
        },
        headers=auth,
    )


async def swept(
    client: AsyncClient,
    auth: dict[str, str],
    cost_center_id: int,
    occurred_on: date,
    *,
    from_envelope_id: int = EVENTS,
    note: str = "event over; leftover back to pool",
) -> dict[str, Any]:
    response = await sweep(
        client,
        auth,
        cost_center_id,
        occurred_on,
        from_envelope_id=from_envelope_id,
        note=note,
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def balances(db: TestDb) -> dict[str, int]:
    rows = await db.owner.fetch("SELECT name, balance FROM envelope_balances")
    return {str(row["name"]): int(row["balance"]) for row in rows}


async def counts(db: TestDb) -> dict[str, int]:
    row = await db.owner.fetchrow(
        """
        SELECT (SELECT count(*) FROM ledger_transactions) AS tx,
               (SELECT count(*) FROM ledger_lines) AS lines,
               (SELECT count(*) FROM allocation_sessions) AS sessions
        """
    )
    assert row is not None
    return {"tx": int(row["tx"]), "lines": int(row["lines"]), "sessions": int(row["sessions"])}


async def test_the_sweep_requires_a_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/sweeps",
        json={
            "cost_center_id": 1,
            "from_envelope_id": EVENTS,
            "occurred_on": "2026-02-08",
            "note": "x",
        },
    )

    assert_problem(response, 401, "invalid_token")


async def test_the_sweep_moves_the_leftover_to_the_pool(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 82-86: sweep 600; Events 1000-400-600=0; pool +600."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    body = await swept(client, auth, cost_center_id, s0 + timedelta(days=7))

    assert set(body) == {"id", "kind", "from_balance", "pool_balance"}
    assert type(body["id"]) is int
    assert body["kind"] == "sweep"
    assert body["from_balance"] == 0
    assert body["pool_balance"] == 600
    assert await balances(lab) == {
        "Unallocated General": 600,
        "Events and Workshops": 0,
        "Admin and Misc": 0,
    }


async def test_the_sweep_writes_a_sweep_header_two_lines_and_no_session_row(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)
    occurred_on = s0 + timedelta(days=7)

    body = await swept(client, auth, cost_center_id, occurred_on)

    header = await lab.owner.fetchrow(
        """
        SELECT kind, occurred_on, recorded_by, note, tag, cost_center_id
        FROM ledger_transactions WHERE id = $1
        """,
        body["id"],
    )
    assert header is not None
    assert dict(header) == {
        "kind": "sweep",
        "occurred_on": occurred_on,
        "recorded_by": USERNAME,
        "note": "event over; leftover back to pool",
        "tag": None,
        "cost_center_id": cost_center_id,
    }
    lines = await lab.owner.fetch(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1", body["id"]
    )
    assert {int(row["envelope_id"]): int(row["amount"]) for row in lines} == {
        EVENTS: -600,
        POOL: 600,
    }
    sessions = await lab.owner.fetchval("SELECT count(*) FROM allocation_sessions")
    assert int(sessions) == 0


async def test_a_second_sweep_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example line 89: nothing left to sweep."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)
    await swept(client, auth, cost_center_id, s0 + timedelta(days=7))

    response = await sweep(client, auth, cost_center_id, s0 + timedelta(days=7))

    assert_problem(response, 409, "rule_violation")
    assert "nothing to sweep" in response.json()["detail"]


async def test_sweeping_from_the_pool_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example line 91: sweep from an envelope other than the pool."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    response = await sweep(
        client, auth, cost_center_id, s0 + timedelta(days=7), from_envelope_id=POOL
    )

    assert_problem(response, 409, "rule_violation")
    assert "other than the pool" in response.json()["detail"]


async def test_an_unknown_from_envelope_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """D-084/D-087: the negative line reaches line_guard first, never the FK."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    response = await sweep(
        client, auth, cost_center_id, s0 + timedelta(days=7), from_envelope_id=9999
    )

    assert_problem(response, 409, "rule_violation")
    assert "would drop below zero" in response.json()["detail"]


async def test_an_unknown_cost_center_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q5=a: sweep_leftover answers "nothing to sweep (leftover is 0)" itself."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    response = await sweep(client, auth, 9999, s0 + timedelta(days=7))

    assert_problem(response, 409, "rule_violation")
    assert "nothing to sweep" in response.json()["detail"]


async def test_a_blank_note_is_422_validation_failed(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """D-090 Q7=b: the app refuses the blank note before any SQL."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    response = await sweep(client, auth, cost_center_id, s0 + timedelta(days=7), note="")

    assert_problem(response, 422, "validation_failed")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost_center_id", True),
        ("cost_center_id", 10.5),
        ("cost_center_id", "5"),
        ("from_envelope_id", True),
        ("from_envelope_id", 10.5),
        ("from_envelope_id", "5"),
    ],
)
async def test_a_non_whole_id_is_422_validation_error(
    client: AsyncClient,
    lab: TestDb,
    auth: dict[str, str],
    field: str,
    value: Any,
) -> None:
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    body: dict[str, Any] = {
        "cost_center_id": cost_center_id,
        "from_envelope_id": EVENTS,
        "occurred_on": (s0 + timedelta(days=7)).isoformat(),
        "note": "event over",
    }
    body[field] = value
    response = await client.post("/api/v1/sweeps", json=body, headers=auth)

    assert_problem(response, 422, "validation_error")


async def test_no_open_tenure_is_409(client: AsyncClient, db: TestDb, auth: dict[str, str]) -> None:
    response = await sweep(client, auth, 1, date(2026, 2, 8))

    assert_problem(response, 409, "no_open_tenure")


async def test_a_date_before_the_tenure_opened_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    await seed_event_spending(client, lab, auth, cost_center_id)

    response = await sweep(client, auth, cost_center_id, date(2025, 12, 31))

    assert_problem(response, 409, "date_before_tenure")
    assert "before this tenure opened" in response.json()["detail"]


async def test_a_failed_sweep_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)
    before = await counts(lab)

    response = await sweep(client, auth, 9999, s0 + timedelta(days=7))

    assert_problem(response, 409, "rule_violation")
    assert await counts(lab) == before
