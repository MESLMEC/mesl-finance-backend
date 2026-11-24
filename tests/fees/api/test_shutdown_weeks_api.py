"""API tests for shutdown weeks (issue #15, steps 1 and 2).

Step 1 (D-188) reshaped the write so the caller NAMES the Sundays instead of
sending a range: D-104 Q3=a ("body {from_week, to_week, ...}") is superseded.
Approved answers: (Q1=a) empty/duplicate refusals are pydantic's 422
`validation_error`; (Q3=a) the `to-week is before from-week` test is deleted because
that input no longer exists; (Q4=a) the domain value object is renamed
`ShutdownWeeks`; (Q5=a) the commit says `Refs #15`.

Step 2 (approved this session: "go with your suggestions") adds the authoritative
state read, an ADDITIVE route (D-104 Q6=a's deferred per-week view):

    GET  /api/v1/shutdown-weeks/state  200  [ShutdownStateOut] in week_start order
         ShutdownStateOut = {"week_start","event_id","reason","recorded_at",
         "recorded_by"}
         - the LATEST `shutdown_events` row per week decides (max id, the schema's
           own latest-wins rule, db/schema.sql:117,594-595);
         - a week whose latest row is `is_shutdown=false` is absent (reopened);
         - OPEN TENURE ONLY (`week_start >= open_tenure_start()`,
           db/schema.sql:54-60,177-183): a closed tenure's weeks never appear;
         - `[]` when nothing in the open tenure is shut.
         Brief suggestions used: Q1=a `event_id`; Q2=a open tenure only; Q3=a the
         SQL calls `open_tenure_start()`; Q4=a own port `.shutdown_state`.

Contract this file pins:
    POST /api/v1/shutdown-weeks  201  {"weeks": n}
         body {"weeks": ["YYYY-MM-DD", ...], "is_shutdown"=true, "reason"=""}
         - `n` is the number of named Sundays, one row each, in the order supplied;
         - `weeks: []` and a repeated Sunday are 422 `validation_error`, and the
           errors must blame `weeks` and nothing else, so an old `{from_week,
           to_week}` body cannot satisfy them by accident;
         - the old `{"from_week", "to_week"}` body is 422 (extra fields forbidden);
         - UNDO is the same action with `is_shutdown=false` (newest row wins);
         - the whole list is ONE transaction: a bad Sunday anywhere leaves NOTHING
           written, so a half-applied list can never exist.
    GET  /api/v1/shutdown-weeks  200  [ShutdownEventOut] in week_start, id order
         (history, NOT state: a reopened week still lists its `is_shutdown=true` row;
         the state read below answers the current state)

ShutdownEventOut = {"id","week_start","is_shutdown","reason","recorded_at",
"recorded_by"}; `recorded_by` is the JWT actor, never a body field.

Database rules these tests rely on (db/schema.sql, read in the step-7.2 session and
re-read this session):
- `set_shutdown(from,to,is_shutdown,by,reason='')` (:220-233) refuses a non-Sunday
  end with P0001 "weeks start on Sunday", inserts ONE row per week and returns the
  count; the adapter calls it once per named week as `set_shutdown(w, w, ...)`, so
  its "to-week is before from-week" branch is unreachable from the API;
- `shutdown_guard` (:177-183) refuses a week inside a closed tenure with P0001
  "week ... belongs to a closed tenure";
- the latest event per week wins (:117, :594-595), which is why the undo is a new
  `is_shutdown=false` row, never an UPDATE (append-only, :160);
- `labapp` has INSERT on `shutdown_events` (:1194); `set_shutdown` is default
  PUBLIC EXECUTE (verified live from `pg_proc` in the 7.2 session).

Library APIs used, verified in installed source or by probe:
- `httpx.AsyncClient.post/get` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838);
- `asyncpg.Connection.fetch/fetchval/execute` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:145,213,236);
- pydantic 2.14.1 parses an ISO `"YYYY-MM-DD"` into `date` and rejects a bad string
  with `ValidationError` (probe in the step-brief session); the new refusals were
  probed there too: `Field(min_length=1)` on a `list` -> `too_short`, a
  `field_validator` raising `ValueError` -> `value_error`, `extra="forbid"` ->
  `extra_forbidden`, and FastAPI turns all three into 422 `validation_error`
  (src/mesl_finance/shared/api/problems.py:71-80);
- `datetime.date/timedelta` are stdlib;
- the real `client` / `lab` / `auth` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

EVENT_FIELDS = {"id", "week_start", "is_shutdown", "reason", "recorded_at", "recorded_by"}
STATE_FIELDS = {"week_start", "event_id", "reason", "recorded_at", "recorded_by"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


def assert_weeks_error(response: Any) -> None:
    """A 422 that blames `weeks` and nothing else.

    The old `{from_week, to_week}` schema answers a `weeks` body with 422 too, but its
    errors also name `from_week`/`to_week`, so this exact-loc check keeps it red.
    """
    assert_problem(response, 422, "validation_error")
    assert [error["loc"] for error in response.json()["errors"]] == [["body", "weeks"]]


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def shut(
    client: AsyncClient,
    auth: dict[str, str],
    *weeks: date,
    **overrides: Any,
) -> Any:
    body: dict[str, Any] = {"weeks": [week.isoformat() for week in weeks]}
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


async def state(client: AsyncClient, auth: dict[str, str]) -> Any:
    return await client.get("/api/v1/shutdown-weeks/state", headers=auth)


# ---- write ------------------------------------------------------------------


async def test_set_shutdown_writes_one_row_per_named_week(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second, third = (s0 + timedelta(days=days) for days in (14, 21, 28))
    supplied = [third, first, second]

    response = await shut(client, auth, *supplied, reason="campus incident")

    assert response.status_code == 201
    assert response.json() == {"weeks": 3}
    rows = await lab.owner.fetch(
        """
        SELECT week_start, is_shutdown, reason, recorded_by
        FROM shutdown_events
        ORDER BY id
        """
    )
    assert [row["week_start"] for row in rows] == supplied
    assert all(row["is_shutdown"] is True for row in rows)
    assert all(row["reason"] == "campus incident" for row in rows)
    assert all(row["recorded_by"] == USERNAME for row in rows)


async def test_two_named_sundays_shut_exactly_two_weeks(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, between, third = (s0 + timedelta(days=days) for days in (7, 14, 21))

    response = await shut(client, auth, first, third)

    assert response.status_code == 201
    assert response.json() == {"weeks": 2}
    stored = await events(lab)
    assert [row["week_start"] for row in stored] == [first, third]
    assert between not in {row["week_start"] for row in stored}


async def test_an_empty_weeks_list_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await shut(client, auth)

    assert_weeks_error(response)
    assert await event_count(lab) == 0


async def test_a_duplicate_sunday_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)

    response = await shut(client, auth, week, week)

    assert_weeks_error(response)
    assert await event_count(lab) == 0


async def test_a_non_sunday_week_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    monday = s0 + timedelta(days=1)

    response = await shut(client, auth, monday)

    assert_problem(response, 409, "rule_violation")
    assert "weeks start on Sunday" in response.json()["detail"]
    assert await event_count(lab) == 0


async def test_a_sunday_and_a_monday_write_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    good_week, monday = s0 + timedelta(days=14), s0 + timedelta(days=15)

    response = await shut(client, auth, good_week, monday)

    assert_problem(response, 409, "rule_violation")
    assert "weeks start on Sunday" in response.json()["detail"]
    assert await event_count(lab) == 0


async def test_a_single_named_week_is_shut(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)

    response = await shut(client, auth, week)

    assert response.status_code == 201
    assert response.json() == {"weeks": 1}
    assert [row["week_start"] for row in await events(lab)] == [week]


async def test_reopening_a_week_writes_a_false_row_that_wins(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)

    closed = await shut(client, auth, week, reason="campus incident")
    reopened = await shut(client, auth, week, is_shutdown=False, reason="was a mistake")

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

    response = await shut(client, auth, in_the_closed_tenure)

    assert_problem(response, 409, "rule_violation")
    assert "belongs to a closed tenure" in response.json()["detail"]
    assert await event_count(lab) == 0


async def test_the_old_range_body_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)

    response = await client.post(
        "/api/v1/shutdown-weeks",
        json={"from_week": s0.isoformat(), "to_week": (s0 + timedelta(days=7)).isoformat()},
        headers=auth,
    )

    assert_problem(response, 422, "validation_error")
    assert await event_count(lab) == 0


async def test_set_shutdown_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    s0 = await sunday(lab)

    response = await client.post(
        "/api/v1/shutdown-weeks",
        json={"weeks": [s0.isoformat()]},
    )

    assert_problem(response, 401, "invalid_token")


# ---- read -------------------------------------------------------------------


async def test_list_shutdown_events_returns_the_rows_in_week_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second = s0 + timedelta(days=7), s0 + timedelta(days=14)
    assert (await shut(client, auth, first, second)).status_code == 201
    assert (await shut(client, auth, first, is_shutdown=False)).status_code == 201

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


# ---- state (step 2) ---------------------------------------------------------


async def test_state_lists_only_currently_shut_weeks(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second = s0 + timedelta(days=7), s0 + timedelta(days=14)
    assert (await shut(client, auth, first, second)).status_code == 201
    assert (await shut(client, auth, first, is_shutdown=False)).status_code == 201

    response = await state(client, auth)

    assert response.status_code == 200
    assert [item["week_start"] for item in response.json()] == [second.isoformat()]


async def test_state_returns_the_latest_event_per_week(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    week = s0 + timedelta(days=14)
    assert (await shut(client, auth, week, reason="durga puja")).status_code == 201
    reopened = await shut(client, auth, week, is_shutdown=False, reason="was a mistake")
    assert reopened.status_code == 201
    assert (await shut(client, auth, week, reason="durga puja again")).status_code == 201
    stored = await lab.owner.fetchrow(
        """
        SELECT id, recorded_at FROM shutdown_events
        WHERE week_start = $1 ORDER BY id DESC LIMIT 1
        """,
        week,
    )
    assert stored is not None

    response = await state(client, auth)

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    item = items[0]
    assert set(item) == STATE_FIELDS
    assert item["week_start"] == week.isoformat()
    assert item["event_id"] == stored["id"]
    assert item["reason"] == "durga puja again"
    assert item["recorded_by"] == USERNAME
    assert datetime.fromisoformat(item["recorded_at"]) == stored["recorded_at"]


async def test_state_is_ordered_by_week_start(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    first, second, third = (s0 + timedelta(days=days) for days in (7, 21, 35))
    assert (await shut(client, auth, third, first, second)).status_code == 201

    response = await state(client, auth)

    assert response.status_code == 200
    assert [item["week_start"] for item in response.json()] == [
        first.isoformat(),
        second.isoformat(),
        third.isoformat(),
    ]


async def test_state_excludes_closed_tenure_weeks(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0 = await sunday(lab)
    old_week = s0 - timedelta(days=7)
    assert (await shut(client, auth, old_week)).status_code == 201
    # Hand over: tenure 2 opens on s0+3, so old_week belongs to the closed tenure.
    await lab.owner.execute("SELECT close_tenure($1::date + 2, $2, 'T2')", s0, USERNAME)
    new_week = s0 + timedelta(days=7)
    assert (await shut(client, auth, new_week)).status_code == 201

    response = await state(client, auth)

    assert response.status_code == 200
    assert [item["week_start"] for item in response.json()] == [new_week.isoformat()]


async def test_state_is_empty_when_nothing_is_shut(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await state(client, auth)

    assert response.status_code == 200
    assert response.json() == []


async def test_state_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    response = await client.get("/api/v1/shutdown-weeks/state")

    assert_problem(response, 401, "invalid_token")
