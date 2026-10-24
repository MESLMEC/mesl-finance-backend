"""API tests for shutdown weeks (roadmap step 7.2).

Approved brief this session: every question was left unanswered, so the brief's
labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/
D-082/D-086/D-088/D-090/D-093/D-096/D-099/D-101): Q2=a writes AND reads; Q3=a ONE
range action `POST /api/v1/shutdown-weeks` calling the schema's `set_shutdown()`
and answering `201 {"weeks": n}`, with the undo as the same route and
`is_shutdown=false`; Q6=a the read returns the raw event rows ordered
`week_start, id` (the per-week "latest wins" view is a dues read, 7.5).

Contract this file pins:
    POST /api/v1/shutdown-weeks  201  {"weeks": n}
         body {"from_week", "to_week", "is_shutdown"=true, "reason"=""}
    GET  /api/v1/shutdown-weeks  200  [ShutdownEventOut] in week_start, id order

ShutdownEventOut = {"id","week_start","is_shutdown","reason","recorded_at",
"recorded_by"}; `recorded_by` is the JWT actor, never a body field.

Database rules these tests rely on (db/schema.sql, read this session):
- `set_shutdown(from,to,is_shutdown,by,reason='')` (:220-233) refuses a non-Sunday
  end with P0001 "weeks start on Sunday", refuses `to < from` with P0001
  "to-week is before from-week", inserts ONE row per week and returns the count;
- `shutdown_guard` (:177-183) refuses a week inside a closed tenure with P0001
  "week ... belongs to a closed tenure";
- the comment on the table says the latest event per week wins (:117), which is
  why the undo is a new `is_shutdown=false` row, never an UPDATE (append-only,
  :160);
- `labapp` has INSERT on `shutdown_events` (:1194); `set_shutdown` is default
  PUBLIC EXECUTE (verified live from `pg_proc` this session).

Library APIs used, all verified in installed source or by probe this session:
- `httpx.AsyncClient.post/get` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838);
- `asyncpg.Connection.fetch/fetchval/execute` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,213,236);
- pydantic 2.14.1 parses an ISO `"YYYY-MM-DD"` into `date` and rejects a bad
  string with `ValidationError` (live probe this session);
- `datetime.date/timedelta` are stdlib;
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

EVENT_FIELDS = {"id", "week_start", "is_shutdown", "reason", "recorded_at", "recorded_by"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def shut(
    client: AsyncClient,
    auth: dict[str, str],
    from_week: date,
    to_week: date,
    **overrides: Any,
) -> Any:
    body: dict[str, Any] = {
        "from_week": from_week.isoformat(),
        "to_week": to_week.isoformat(),
    }
    body.update(overrides)
    return await client.post("/api/v1/shutdown-weeks", json=body, headers=auth)


async def events(db: TestDb) -> list[dict[str, Any]]:
    rows = await db.owner.fetch(
        """
        SELECT id, week_start, is_shutdown, reason, recorded_at, recorded_by
        FROM shutdown_events
        ORDER BY week_start, id
        """
    )
    return [
        {
            "id": row["id"],
            "week_start": row["week_start"],
            "is_shutdown": row["is_shutdown"],
            "reason": row["reason"],
            "recorded_at": row["recorded_at"],
            "recorded_by": row["recorded_by"],
        }
        for row in rows
    ]


async def event_count(db: TestDb) -> int:
    count: int = await db.owner.fetchval("SELECT count(*) FROM shutdown_events")
    return count


# ---- write ------------------------------------------------------------------


async def test_set_shutdown_returns_201_and_writes_one_row_per_week(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second, third = (s0 + timedelta(days=days) for days in (14, 21, 28))

    response = await shut(client, auth, first, third, reason="campus incident")

    assert response.status_code == 201
    assert response.json() == {"weeks": 3}
    stored = await events(lab)
    assert [row["week_start"] for row in stored] == [first, second, third]
    assert all(row["is_shutdown"] is True for row in stored)
    assert all(row["reason"] == "campus incident" for row in stored)
    assert all(row["recorded_by"] == USERNAME for row in stored)


async def test_set_shutdown_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    s0 = await sunday(lab)

    response = await client.post(
        "/api/v1/shutdown-weeks",
        json={"from_week": s0.isoformat(), "to_week": s0.isoformat()},
    )

    assert_problem(response, 401, "invalid_token")


async def test_shutdown_range_not_on_sunday_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    monday = s0 + timedelta(days=1)

    response = await shut(client, auth, monday, monday)

    assert_problem(response, 409, "rule_violation")
    assert "weeks start on Sunday" in response.json()["detail"]
    assert await event_count(lab) == 0


async def test_shutdown_to_week_before_from_week_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    response = await shut(client, auth, s0 + timedelta(days=7), s0)

    assert_problem(response, 409, "rule_violation")
    assert "to-week is before from-week" in response.json()["detail"]
    assert await event_count(lab) == 0


async def test_single_week_shutdown(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)

    response = await shut(client, auth, week, week)

    assert response.status_code == 201
    assert response.json() == {"weeks": 1}
    assert [row["week_start"] for row in await events(lab)] == [week]


async def test_reopening_a_week_writes_a_false_row_that_wins(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)

    closed = await shut(client, auth, week, week, reason="campus incident")
    reopened = await shut(client, auth, week, week, is_shutdown=False, reason="was a mistake")

    assert (closed.status_code, reopened.status_code) == (201, 201)
    assert len(await events(lab)) == 2
    latest = await lab.owner.fetchval(
        "SELECT is_shutdown FROM shutdown_events ORDER BY id DESC LIMIT 1"
    )
    assert latest is False


async def test_closed_tenure_rejects_a_shutdown(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    # Hand over: tenure 2 opens on s0+3, so last week's Sunday belongs to tenure 1.
    await lab.owner.execute("SELECT close_tenure($1::date + 2, $2, 'T2')", s0, USERNAME)
    in_the_closed_tenure = s0 - timedelta(days=7)

    response = await shut(client, auth, in_the_closed_tenure, in_the_closed_tenure)

    assert_problem(response, 409, "rule_violation")
    assert "belongs to a closed tenure" in response.json()["detail"]
    assert await event_count(lab) == 0


# ---- read -------------------------------------------------------------------


async def test_list_shutdown_events_returns_the_rows_in_week_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second = s0 + timedelta(days=7), s0 + timedelta(days=14)
    assert (await shut(client, auth, first, second)).status_code == 201
    assert (await shut(client, auth, first, first, is_shutdown=False)).status_code == 201

    response = await client.get("/api/v1/shutdown-weeks", headers=auth)

    assert response.status_code == 200
    items = response.json()
    assert [(item["week_start"], item["is_shutdown"]) for item in items] == [
        (first.isoformat(), True),
        (first.isoformat(), False),
        (second.isoformat(), True),
    ]
    assert all(set(item) == EVENT_FIELDS for item in items)
    assert all(item["recorded_by"] == USERNAME for item in items)


async def test_list_shutdown_events_without_a_token_is_401(
    client: AsyncClient, lab: TestDb
) -> None:
    response = await client.get("/api/v1/shutdown-weeks")

    assert_problem(response, 401, "invalid_token")
