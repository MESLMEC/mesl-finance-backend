"""POST /api/v1/reconciliations: record one screen-vs-notes check end to end
(roadmap step 10.1).

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a the route is `POST /api/v1/reconciliations`; Q2=a the body
is `{counted_total, note="", counted={"<envelope_id>": int} | null}`; Q3=a the
response is `201 {"id","through_entry_id","system_total","counted_total",
"difference","matched"}` read back from the stored row; Q4=a a THIN app - a
negative `counted_total` reaches the table CHECK `counted_total >= 0`
(db/schema.sql:1024) and answers 409 `rule_violation`; Q5=a `counted` is
pydantic-typed `dict[str, int] | null`, so a non-object or non-integer value
answers 422 `validation_error` (mirroring D-120 Q4=a) while an unknown
envelope that survives typing reaches `reconcile` as 409; Q6=a the action
lives in a new `reconciliation` feature.

Database rules these tests rely on (db/schema.sql:1047-1087, read this
session): `reconcile` is SECURITY DEFINER, callable by `labapp`; it raises
'nothing to reconcile yet' when the open tenure has no entries, 'no open
tenure' when none is open, 'envelope % does not exist' for an unknown counted
key, and the INSERT's `counted_total >= 0` CHECK is 23514. The tenure in the
`lab` fixture opened on 2026-01-01; envelopes pool=1, events=2, admin=3.

Out of scope on purpose: 'no open tenure' is unreachable through the API
(`close_tenure` always opens the next tenure), so no test pins it.

Library APIs used, all verified in installed source this session:
- pydantic 2.14.1 `Field(strict=True)` refuses 10.5/True/"100" and a
  `dict[str, int] | None` field rejects `[1,2]` and `{"1": "abc"}` (probed);
- httpx `AsyncClient.post` (0.28.1, _client.py:1838);
- pytest.mark.parametrize (9.1.1, _pytest/python.py:1231);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

POOL, EVENTS = 1, 2
FIELDS = {"id", "through_entry_id", "system_total", "counted_total", "difference", "matched"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def entry(
    db: TestDb,
    kind: str,
    lines: list[tuple[int, int]],
    *,
    source: str | None = None,
    tag: str | None = None,
    note: str = "",
) -> int:
    """One ledger entry (header + lines) as `labapp`, in one transaction."""
    async with db.app.transaction():
        tx: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " source, tag, note) VALUES (1, $1, current_date, 'treasurer', $2, $3, $4)"
            " RETURNING id",
            kind,
            source,
            tag,
            note,
        )
        for envelope_id, amount in lines:
            await db.app.execute(
                "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
                tx,
                envelope_id,
                amount,
            )
    return tx


async def seed_month1(db: TestDb) -> None:
    """opening 1000 + deposit 200 + expense -50 -> screen total 1150, 3 entries."""
    await entry(db, "opening", [(POOL, 1000)], note="go-live")
    await entry(db, "deposit", [(POOL, 200)], source="other")
    await entry(db, "expense", [(POOL, -50)], tag="stationery")


async def seed_envelopes(db: TestDb) -> None:
    """opening 1000 to the pool, then a 300 transfer to Events -> pool 700, events 300."""
    await entry(db, "opening", [(POOL, 1000)], note="go-live")
    await entry(db, "transfer", [(POOL, -300), (EVENTS, 300)], note="events money")


async def reconcile(
    client: AsyncClient, auth: dict[str, str], counted_total: int, **overrides: Any
) -> Any:
    body: dict[str, Any] = {"counted_total": counted_total}
    body.update(overrides)
    return await client.post("/api/v1/reconciliations", json=body, headers=auth)


# ---- 201 ---------------------------------------------------------------------


async def test_a_total_match_is_201_matched(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, 1150, note="month 1 matched")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["through_entry_id"], body["system_total"], body["counted_total"]) == (
        3,
        1150,
        1150,
    )
    assert (body["difference"], body["matched"]) == (0, True)
    row = await lab.app.fetchrow("SELECT * FROM reconciliations WHERE id = $1", body["id"])
    assert row is not None
    assert (row["system_total"], row["matched"], row["note"]) == (1150, True, "month 1 matched")


async def test_a_total_mismatch_is_201_not_matched(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, 1000)

    assert response.status_code == 201
    body = response.json()
    assert (body["system_total"], body["counted_total"]) == (1150, 1000)
    assert (body["difference"], body["matched"]) == (-150, False)


async def test_per_envelope_counts_can_mismatch_on_zero_difference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_envelopes(lab)

    wrong = await reconcile(client, auth, 1000, counted={"1": 690, "2": 300})
    assert wrong.status_code == 201
    assert (wrong.json()["difference"], wrong.json()["matched"]) == (0, False)

    right = await reconcile(client, auth, 1000, counted={"1": 700, "2": 300})
    assert right.status_code == 201
    assert (right.json()["difference"], right.json()["matched"]) == (0, True)


# ---- 409: the function and the CHECK own the rest -----------------------------


async def test_a_negative_counted_total_reaches_the_check(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, -5)

    assert_problem(response, 409, "rule_violation")
    assert "counted_total" in response.json()["detail"]


async def test_an_unknown_envelope_in_counted_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, 1150, counted={"99": 10})

    assert_problem(response, 409, "rule_violation")
    assert "envelope 99 does not exist" in response.json()["detail"]


async def test_nothing_to_reconcile_yet_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # the lab fixture opens a tenure and envelopes but writes no ledger entries

    response = await reconcile(client, auth, 0)

    assert_problem(response, 409, "rule_violation")
    assert "nothing to reconcile yet" in response.json()["detail"]


# ---- 422: framework validation ------------------------------------------------


async def test_a_bad_counted_value_is_a_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, 1150, counted={"1": "abc"})

    assert_problem(response, 422, "validation_error")


async def test_a_non_object_counted_is_a_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, 1150, counted=[1, 2])

    assert_problem(response, 422, "validation_error")


@pytest.mark.parametrize("counted_total", [10.5, True, "100"])
async def test_a_non_whole_counted_total_is_a_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], counted_total: Any
) -> None:
    await seed_month1(lab)

    response = await reconcile(client, auth, counted_total)

    assert_problem(response, 422, "validation_error")


# ---- auth ----------------------------------------------------------------------


async def test_reconciling_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/reconciliations", json={"counted_total": 0})

    assert_problem(response, 401, "invalid_token")
