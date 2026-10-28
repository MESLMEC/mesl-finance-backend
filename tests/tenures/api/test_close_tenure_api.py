"""POST /api/v1/tenures/close: close the open tenure, save the snapshots and
open the next tenure (roadmap step 11.1).

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a `POST /api/v1/tenures/close`; Q2=a body `{close_on,
next_name}`, response `201 {"id","name","opened_on"}` read back from the new
tenure; Q5=a a THIN app - the close-date and no-open-tenure rules stay in
PostgreSQL's `close_tenure` (db/schema.sql:910-938), which raises them as
P0001 and the shared translator maps them to 409 `rule_violation`.

The tenure in the `lab` fixture opened on 2026-01-01 (tests/conftest.py).

Library APIs used, all verified in installed source this session:
- asyncpg 0.32.0 `Connection.execute` / `fetchval` / `fetch` / `transaction`
  (connection.py:285,320,689,725);
- httpx `AsyncClient.post` (0.28.1, _client.py:1838);
- pydantic 2.14.1 date parsing - a malformed date answers 422
  `validation_error` (the FastAPI 422 pattern);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

CLOSE_FIELDS = {"id", "name", "opened_on"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def close(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> Any:
    body: dict[str, Any] = {"close_on": "2026-01-31", "next_name": "2026"}
    body.update(overrides)
    return await client.post("/api/v1/tenures/close", json=body, headers=auth)


async def seed_entry(db: TestDb, occurred_on: date) -> None:
    """One deposit entry on a later date, to pin the close-date wall."""
    async with db.app.transaction():
        tx: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source)"
            " VALUES (1, 'deposit', $1, 'treasurer', 'other') RETURNING id",
            occurred_on,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1, 1, 100)", tx
        )


# ---- 201 ---------------------------------------------------------------------


async def test_close_closes_current_tenure_and_creates_the_next_one(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await close(client, auth, close_on="2026-01-31", next_name="2026B")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == CLOSE_FIELDS
    assert body == {"id": 2, "name": "2026B", "opened_on": "2026-02-01"}

    rows = await lab.app.fetch("SELECT id, name, opened_on, closed_on FROM tenures ORDER BY id")
    assert [(int(r["id"]), r["name"], r["opened_on"], r["closed_on"]) for r in rows] == [
        (1, "2026", date(2026, 1, 1), date(2026, 1, 31)),
        (2, "2026B", date(2026, 2, 1), None),
    ]


# ---- 401 / 422 ---------------------------------------------------------------


async def test_close_requires_authentication(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post(
        "/api/v1/tenures/close", json={"close_on": "2026-01-31", "next_name": "2026"}
    )

    assert_problem(response, 401, "invalid_token")


@pytest.mark.parametrize(
    "body",
    [
        {"next_name": "2026"},
        {"close_on": "2026-01-31"},
        {"close_on": "2026-13-99", "next_name": "2026"},
    ],
)
async def test_close_rejects_a_malformed_body(
    body: dict[str, Any], client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/tenures/close", json=body, headers=auth)

    assert_problem(response, 422, "validation_error")


# ---- 409: PostgreSQL owns the rules ------------------------------------------


async def test_close_date_before_the_last_entry_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_entry(lab, date(2026, 3, 1))

    response = await close(client, auth, close_on="2026-01-31")

    assert_problem(response, 409, "rule_violation")
    assert "before the last recorded entry" in response.json()["detail"]


async def test_close_without_an_open_tenure_is_409(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await close(client, auth)

    assert_problem(response, 409, "rule_violation")
    assert "no open tenure" in response.json()["detail"]
