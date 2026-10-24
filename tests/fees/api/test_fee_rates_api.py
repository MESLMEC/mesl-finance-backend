"""API tests for fee rates (roadmap step 7.2).

Approved brief this session: every question was left unanswered, so the brief's
labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/
D-082/D-086/D-088/D-090/D-093/D-096/D-099/D-101): Q2=a writes AND reads; Q4=a the
body is `{effective_from, amount}`, a second rate on the same Sunday is ACCEPTED
(the schema has no UNIQUE on `effective_from`), and the answer is the stored row;
Q5=a the request schema only enforces a strict `int`, so zero and negative amounts
reach the database CHECK and answer 409 `rule_violation`.

Contract this file pins:
    POST /api/v1/fee-rates   201  FeeRateOut  {"effective_from","amount"}
    GET  /api/v1/fee-rates   200  [FeeRateOut] in effective_from, id order

FeeRateOut = {"id","effective_from","amount","recorded_at","recorded_by"};
`recorded_by` is the JWT actor, never a body field (AGENTS.md section 5).

Database rules these tests rely on (db/schema.sql, read this session):
- `fee_rates_effective_from_check` (`CHECK extract(dow)=0`, :108) -> 23514;
- `fee_rates_amount_check` (`CHECK amount > 0`, :109) -> 23514;
- `rate_guard` (:166-175): a rate before `open_tenure_start()` raises P0001
  "a rate cannot start before this tenure opened on ..." (the translator's
  existing "before this tenure opened" -> `DateBeforeTenure` rule); a rate
  backdated before the current week's Sunday raises P0001 -> `RuleViolation`;
- `rate_on()` (:113-115) prefers the highest `effective_from`, then the highest id,
  so example 04's latest-row-wins holds: `db/examples/04_fees_existing_members.sql:15-17`;
- `labapp` has INSERT on `fee_rates` (:1193) and the tables are append-only (:159).

Library APIs used, all verified in installed source or by probe this session:
- pydantic 2.14.1 `Field(strict=True)` refuses `True`, `10.5` and `"20"`, accepts
  `0`, `-5` and a real `int` (live probe this session);
- `httpx.AsyncClient.post/get` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838);
- `asyncpg.Connection.fetchval/fetchrow/execute` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,236,244);
- `pytest.mark.parametrize` (pytest, .venv/lib/python3.15/site-packages/_pytest/python.py);
- `datetime.date/timedelta/datetime.fromisoformat` are stdlib;
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

RATE_FIELDS = {"id", "effective_from", "amount", "recorded_at", "recorded_by"}
SUNDAY_CONSTRAINT = "fee_rates_effective_from_check"


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def create_rate(
    client: AsyncClient, auth: dict[str, str], effective_from: date, amount: Any
) -> Any:
    return await client.post(
        "/api/v1/fee-rates",
        json={"effective_from": effective_from.isoformat(), "amount": amount},
        headers=auth,
    )


async def stored_rate(db: TestDb, rate_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        """
        SELECT id, effective_from, amount, recorded_at, recorded_by
        FROM fee_rates
        WHERE id = $1
        """,
        rate_id,
    )
    assert row is not None
    return {
        "id": row["id"],
        "effective_from": row["effective_from"],
        "amount": row["amount"],
        "recorded_at": row["recorded_at"],
        "recorded_by": row["recorded_by"],
    }


async def rate_count(db: TestDb) -> int:
    count: int = await db.owner.fetchval("SELECT count(*) FROM fee_rates")
    return count


# ---- create -----------------------------------------------------------------


async def test_create_rate_returns_201_and_stores_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    response = await create_rate(client, auth, s0, 20)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == RATE_FIELDS
    assert (body["effective_from"], body["amount"], body["recorded_by"]) == (
        s0.isoformat(),
        20,
        USERNAME,
    )
    stored = await stored_rate(lab, body["id"])
    assert (stored["effective_from"], stored["amount"], stored["recorded_by"]) == (
        s0,
        20,
        USERNAME,
    )
    assert datetime.fromisoformat(body["recorded_at"]) == stored["recorded_at"]


async def test_create_rate_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    s0 = await sunday(lab)

    response = await client.post(
        "/api/v1/fee-rates", json={"effective_from": s0.isoformat(), "amount": 20}
    )

    assert_problem(response, 401, "invalid_token")


async def test_rate_not_on_a_sunday_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    response = await create_rate(client, auth, s0 + timedelta(days=1), 20)

    assert_problem(response, 409, "rule_violation")
    assert SUNDAY_CONSTRAINT in response.json()["detail"]
    assert await rate_count(lab) == 0


async def test_backdated_rate_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    response = await create_rate(client, auth, s0 - timedelta(days=7), 25)

    assert_problem(response, 409, "rule_violation")
    assert "cannot be backdated" in response.json()["detail"]
    assert await rate_count(lab) == 0


async def test_rate_before_the_tenure_opened_is_409_date_before_tenure(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # `lab` opens the first tenure on 2026-01-01; this is the Sunday before it.
    before_the_tenure = date(2025, 12, 28)

    response = await create_rate(client, auth, before_the_tenure, 20)

    assert_problem(response, 409, "date_before_tenure")
    assert "before this tenure opened" in response.json()["detail"]
    assert await rate_count(lab) == 0


@pytest.mark.parametrize("amount", [0, -5])
async def test_rate_amount_must_be_positive_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: int
) -> None:
    s0 = await sunday(lab)

    response = await create_rate(client, auth, s0, amount)

    assert_problem(response, 409, "rule_violation")
    assert "fee_rates_amount_check" in response.json()["detail"]


@pytest.mark.parametrize("amount", [10.5, True, "20"])
async def test_rate_amount_must_be_a_whole_number_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    s0 = await sunday(lab)

    response = await create_rate(client, auth, s0, amount)

    assert_problem(response, 422, "validation_error")


async def test_two_rates_on_the_same_sunday_are_kept_and_the_latest_wins(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    first = await create_rate(client, auth, s0, 20)
    second = await create_rate(client, auth, s0, 25)

    assert (first.status_code, second.status_code) == (201, 201)
    assert await rate_count(lab) == 2
    assert await lab.owner.fetchval("SELECT rate_on($1)", s0) == 25


# ---- list -------------------------------------------------------------------


async def test_list_rates_returns_them_in_effective_from_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    next_week = s0 + timedelta(days=7)
    assert (await create_rate(client, auth, next_week, 25)).status_code == 201
    assert (await create_rate(client, auth, s0, 20)).status_code == 201

    response = await client.get("/api/v1/fee-rates", headers=auth)

    assert response.status_code == 200
    items = response.json()
    assert [(item["effective_from"], item["amount"]) for item in items] == [
        (s0.isoformat(), 20),
        (next_week.isoformat(), 25),
    ]
    assert all(set(item) == RATE_FIELDS for item in items)


async def test_list_rates_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    response = await client.get("/api/v1/fee-rates")

    assert_problem(response, 401, "invalid_token")
