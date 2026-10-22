"""API tests for membership periods: start once, end once (roadmap step 7.1).

Approved brief answers this session: Q6=b (blank names, see
tests/members/api/test_members_api.py) and every other question as the brief's
labelled suggestion: Q2=a the period read is part of the step, Q3=a an unknown
member is 404 `not_found` (adapter pre-check, D-083's pattern of naming the
error), Q4=a ending when nothing is open is 404 `not_found`, Q5=a the end
action picks the member's single open period (the EXCLUDE constraint makes
more than one impossible, db/schema.sql:101-102), Q8=a the routes below, Q9=a
the shared translator gains one 23P01 -> `RuleViolation` rule.

Contract this file pins:
    POST /api/v1/members/{id}/periods/start   201  PeriodOut  {"start_date"}
    POST /api/v1/members/{id}/periods/end     200  PeriodOut  {"end_date"}
    GET  /api/v1/members/{id}/periods         200  [PeriodOut] id order

PeriodOut = {"id","member_id","start_date","end_date"} with ISO dates.

Database rules these tests rely on (db/schema.sql, read this session):
- `CHECK (end_date IS NULL OR end_date >= start_date)` (:100) -> 23514;
- `EXCLUDE USING gist (... daterange(...) WITH &&)` (:101-102) -> 23P01, the
  overlap rule (the translator rule this step adds);
- `period_guard` (:193-218): an INSERT whose first billable week falls inside
  a closed tenure, and an UPDATE ending inside a closed tenure, both raise
  P0001; a second end (or a start-date edit) raises P0001;
- `labapp` may INSERT membership_periods and UPDATE (end_date) only (:1193,
  :1198), so the start date can never be changed through the app.

Only ONE tenure may be open at a time (db/schema.sql:40), so the closed-tenure
tests hand over with the schema's own `close_tenure` as the owner, exactly as
tests/ledger/api/test_entry_list_api.py does (D-095).

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get/post/request` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1485,1751,1838);
- `asyncpg.Connection.fetchrow/fetchval/execute` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,236-266);
- `pytest.mark.parametrize` (pytest 9.1.1,
  .venv/lib/python3.15/site-packages/_pytest/python.py:1231);
- pydantic 2.14.1 parses an ISO `"YYYY-MM-DD"` string into `date` and rejects
  a bad string with `ValidationError` (verified live this session);
- `datetime.date` / `datetime.timedelta` are stdlib;
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

PERIOD_FIELDS = {"id", "member_id", "start_date", "end_date"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def member(client: AsyncClient, auth: dict[str, str], name: str = "Ayesha") -> dict[str, Any]:
    response = await client.post("/api/v1/members", json={"name": name}, headers=auth)
    assert response.status_code == 201
    return response.json()


async def start(client: AsyncClient, auth: dict[str, str], member_id: int, **overrides: Any) -> Any:
    body: dict[str, Any] = {"start_date": "2026-02-01"}
    body.update(overrides)
    return await client.post(f"/api/v1/members/{member_id}/periods/start", json=body, headers=auth)


async def end(client: AsyncClient, auth: dict[str, str], member_id: int, **overrides: Any) -> Any:
    body: dict[str, Any] = {"end_date": "2026-06-30"}
    body.update(overrides)
    return await client.post(f"/api/v1/members/{member_id}/periods/end", json=body, headers=auth)


async def stored_period(db: TestDb, period_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, member_id, start_date, end_date FROM membership_periods WHERE id = $1",
        period_id,
    )
    assert row is not None
    return {
        "id": row["id"],
        "member_id": row["member_id"],
        "start_date": row["start_date"].isoformat(),
        "end_date": None if row["end_date"] is None else row["end_date"].isoformat(),
    }


async def period_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM membership_periods")


# ---- start ------------------------------------------------------------------


async def test_start_period_returns_201_and_stores_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)

    response = await start(client, auth, person["id"], start_date="2026-02-01")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == PERIOD_FIELDS
    assert (body["member_id"], body["start_date"], body["end_date"]) == (
        person["id"],
        "2026-02-01",
        None,
    )
    assert await stored_period(lab, body["id"]) == body


async def test_start_period_for_unknown_member_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    person = await member(client, auth)
    known = await start(client, auth, person["id"])
    assert known.status_code == 201

    response = await start(client, auth, 999)

    assert_problem(response, 404, "not_found")
    assert await period_count(lab) == 1


async def test_second_open_period_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q9=a: the EXCLUDE constraint's SQLSTATE is 23P01; it becomes 409."""
    person = await member(client, auth)
    first = await start(client, auth, person["id"], start_date="2026-02-01")
    assert first.status_code == 201

    response = await start(client, auth, person["id"], start_date="2026-03-01")

    assert_problem(response, 409, "rule_violation")
    assert "exclusion" in response.json()["detail"].lower()
    assert await period_count(lab) == 1


async def test_new_period_after_a_closed_one_is_allowed(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)
    first = await start(client, auth, person["id"], start_date="2026-02-01")
    assert first.status_code == 201
    closed = await end(client, auth, person["id"], end_date="2026-03-01")
    assert closed.status_code == 200

    response = await start(client, auth, person["id"], start_date="2026-04-01")

    assert response.status_code == 201
    body = response.json()
    assert body["end_date"] is None
    assert body["id"] != first.json()["id"]
    assert await period_count(lab) == 2


async def test_start_inside_a_closed_tenure_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`period_guard` (:199-205) only bites once a rate exists, and
    `rate_guard` (:170) allows no rate before the current week's Sunday."""
    s0: date = await lab.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    person = await member(client, auth)
    await lab.app.execute(
        "INSERT INTO fee_rates (effective_from, amount, recorded_by) VALUES ($1, 20, $2)",
        s0,
        USERNAME,
    )
    # Hand over: tenure 2 opens on s0+3, so a period whose first billable week
    # is s0 would owe weeks inside a closed tenure.
    await lab.owner.execute("SELECT close_tenure($1::date + 2, $2, 'T2')", s0, USERNAME)

    response = await start(
        client, auth, person["id"], start_date=(s0 - timedelta(days=7)).isoformat()
    )

    assert_problem(response, 409, "rule_violation")
    assert "closed tenure" in response.json()["detail"]
    assert await period_count(lab) == 0


# ---- end (Q5=a: the single open period is the target) ------------------------


async def test_end_period_sets_the_end_date(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)
    started = await start(client, auth, person["id"], start_date="2026-02-01")
    assert started.status_code == 201

    response = await end(client, auth, person["id"], end_date="2026-06-30")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PERIOD_FIELDS
    assert (body["member_id"], body["start_date"], body["end_date"]) == (
        person["id"],
        "2026-02-01",
        "2026-06-30",
    )
    assert await stored_period(lab, body["id"]) == body


async def test_end_when_nothing_is_open_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: end one real period, then ask for another.
    person = await member(client, auth)
    started = await start(client, auth, person["id"])
    assert started.status_code == 201
    closed = await end(client, auth, person["id"])
    assert closed.status_code == 200

    other = await member(client, auth, name="Bashir")
    response = await end(client, auth, other["id"])

    assert_problem(response, 404, "not_found")


async def test_second_end_is_409(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    """`period_guard` :210-212: "a membership can only be ended once"."""
    person = await member(client, auth)
    started = await start(client, auth, person["id"], start_date="2026-02-01")
    assert started.status_code == 201
    closed = await end(client, auth, person["id"], end_date="2026-03-01")
    assert closed.status_code == 200

    response = await end(client, auth, person["id"], end_date="2026-04-01")

    assert_problem(response, 409, "rule_violation")
    assert "ended once" in response.json()["detail"]
    assert (await stored_period(lab, closed.json()["id"]))["end_date"] == "2026-03-01"


async def test_end_before_start_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)
    started = await start(client, auth, person["id"], start_date="2026-02-01")
    assert started.status_code == 201

    response = await end(client, auth, person["id"], end_date="2026-01-15")

    assert_problem(response, 409, "rule_violation")
    assert "membership_periods" in response.json()["detail"]
    assert (await stored_period(lab, started.json()["id"]))["end_date"] is None


async def test_end_inside_a_closed_tenure_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)
    started = await start(client, auth, person["id"], start_date="2026-09-01")
    assert started.status_code == 201
    await lab.owner.execute("SELECT close_tenure('2026-10-01', $1, 'T2')", USERNAME)

    response = await end(client, auth, person["id"], end_date="2026-09-15")

    assert_problem(response, 409, "rule_violation")
    assert "closed tenure" in response.json()["detail"]
    assert (await stored_period(lab, started.json()["id"]))["end_date"] is None


# ---- read -------------------------------------------------------------------


async def test_periods_list_is_id_ordered(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    person = await member(client, auth)
    first = await start(client, auth, person["id"], start_date="2026-02-01")
    assert first.status_code == 201
    closed = await end(client, auth, person["id"], end_date="2026-03-01")
    assert closed.status_code == 200
    second = await start(client, auth, person["id"], start_date="2026-04-01")
    assert second.status_code == 201

    response = await client.get(f"/api/v1/members/{person['id']}/periods", headers=auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [first.json()["id"], second.json()["id"]]
    assert all(set(row) == PERIOD_FIELDS for row in rows)
    assert (rows[0]["start_date"], rows[0]["end_date"]) == ("2026-02-01", "2026-03-01")


# ---- path ids ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/members/abc/edit", {"note": "x"}),
        ("POST", "/api/v1/members/abc/periods/start", {"start_date": "2026-02-01"}),
        ("POST", "/api/v1/members/abc/periods/end", {"end_date": "2026-06-30"}),
        ("GET", "/api/v1/members/abc/periods", None),
    ],
)
async def test_non_numeric_member_id_is_422(
    client: AsyncClient,
    lab: TestDb,
    auth: dict[str, str],
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    request: dict[str, Any] = {"json": body} if body is not None else {}
    response = await client.request(method, path, headers=auth, **request)

    assert_problem(response, 422, "validation_error")
