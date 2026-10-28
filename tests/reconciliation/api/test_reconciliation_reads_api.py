"""The three reconciliation reads end to end (roadmap step 10.2).

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a the routes are `GET /api/v1/reconciliation-status`,
`GET /api/v1/unverified-entries` and `GET /api/v1/difference-suspects`;
Q2=a the suspects read takes `?difference=<signed int>` plus an optional
`?envelope_id=<int>` and passes both through to `difference_suspects`
(db/schema.sql:1122-1157); Q3=a the status read is a single object with the
view's 7 columns, nullable when nothing has matched yet
(db/schema.sql:1110-1116); Q4=a the unverified list exposes all 14 view
columns as-is, `reverses_id` and `is_voided` included (db/schema.sql:1095-1108).

Database rules these tests rely on (db/schema.sql, read this session):
`unverified_entries` windows by ENTRY ID against `last_match.through_entry_id`
(a late entry for an old date still shows, D-146 (4)); `reconciliation_status`
is a single row even with no match (LEFT JOIN `last_match`); `difference_suspects`
skips zero-net entries unless scoped to one envelope, where a transfer's
single-sided net becomes visible (D-146 (5)). The tenure in the `lab` fixture
opened on 2026-01-01; envelopes pool=1, events=2, admin=3.

Library APIs used, all verified in installed source this session:
- FastAPI int query-param parsing: a non-numeric value answers 422
  `validation_error` (the `?tenure_id=abc` precedent, tests/ledger/api/
  test_entry_list_api.py:280-285; shared/api/problems.py:71-76);
- httpx `AsyncClient.get` with `params=` (0.28.1);
- the real `client` / `lab` / `auth` fixtures from tests/conftest.py.
"""

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb

POOL, EVENTS, ADMIN = 1, 2, 3

STATUS_FIELDS = {
    "last_match_id",
    "last_match_date",
    "last_match_through_entry",
    "days_since_last_match",
    "entries_since_last_match",
    "latest_attempt_matched",
    "latest_difference",
}

ENTRY_FIELDS = {
    "id",
    "tenure_id",
    "kind",
    "occurred_on",
    "recorded_at",
    "recorded_by",
    "note",
    "tag",
    "cost_center_id",
    "member_id",
    "reverses_id",
    "is_voided",
    "net_effect",
    "size",
}

SUSPECT_FIELDS = {"entry_id", "kind", "occurred_on", "effect", "note", "why"}


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
    occurred_on: date | None = None,
) -> int:
    """One ledger entry (header + lines) as `labapp`, in one transaction."""
    async with db.app.transaction():
        tx: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " source, tag, note) VALUES (1, $1, COALESCE($2::date, current_date),"
            " 'treasurer', $3, $4, $5) RETURNING id",
            kind,
            occurred_on,
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


async def reconcile(client: AsyncClient, auth: dict[str, str], counted_total: int) -> Any:
    return await client.post(
        "/api/v1/reconciliations", json={"counted_total": counted_total}, headers=auth
    )


async def status(client: AsyncClient, auth: dict[str, str]) -> Any:
    return await client.get("/api/v1/reconciliation-status", headers=auth)


async def unverified(client: AsyncClient, auth: dict[str, str]) -> Any:
    return await client.get("/api/v1/unverified-entries", headers=auth)


async def suspects(
    client: AsyncClient, auth: dict[str, str], difference: int, envelope_id: int | None = None
) -> Any:
    params: dict[str, Any] = {"difference": difference}
    if envelope_id is not None:
        params["envelope_id"] = envelope_id
    return await client.get("/api/v1/difference-suspects", params=params, headers=auth)


# ---- auth ----------------------------------------------------------------------


async def test_status_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    assert_problem(await client.get("/api/v1/reconciliation-status"), 401, "invalid_token")


async def test_unverified_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    assert_problem(await client.get("/api/v1/unverified-entries"), 401, "invalid_token")


async def test_suspects_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    assert_problem(
        await client.get("/api/v1/difference-suspects", params={"difference": 0}),
        401,
        "invalid_token",
    )


# ---- status --------------------------------------------------------------------


async def test_status_before_any_match(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await status(client, auth)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == STATUS_FIELDS
    assert body["last_match_id"] is None
    assert body["last_match_date"] is None
    assert body["last_match_through_entry"] is None
    assert body["days_since_last_match"] is None
    assert body["entries_since_last_match"] == 0
    assert body["latest_attempt_matched"] is None
    assert body["latest_difference"] is None


async def test_status_after_a_match(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201

    body = (await status(client, auth)).json()

    assert body["last_match_id"] == 1
    assert body["last_match_date"] is not None
    assert body["last_match_through_entry"] == 3
    assert body["days_since_last_match"] == 0
    assert body["entries_since_last_match"] == 0
    assert body["latest_attempt_matched"] is True
    assert body["latest_difference"] == 0


async def test_status_after_a_mismatch(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1000)).status_code == 201

    body = (await status(client, auth)).json()

    assert body["last_match_id"] is None
    assert body["days_since_last_match"] is None
    assert body["entries_since_last_match"] == 3
    assert body["latest_attempt_matched"] is False
    assert body["latest_difference"] == -150


# ---- unverified entries --------------------------------------------------------


async def test_unverified_lists_all_entries_before_first_match(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)

    response = await unverified(client, auth)

    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body] == [1, 2, 3]
    assert all(set(row) == ENTRY_FIELDS for row in body)
    assert [row["kind"] for row in body] == ["opening", "deposit", "expense"]
    assert [row["net_effect"] for row in body] == [1000, 200, -50]
    assert [row["is_voided"] for row in body] == [False, False, False]
    assert body[0]["note"] == "go-live"
    assert body[1]["note"] == ""
    assert body[2]["tag"] == "stationery"


async def test_unverified_lists_only_entries_since_last_match(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201
    # recorded after the match but dated long before it: still listed (id window, D-146 (4))
    await entry(lab, "expense", [(POOL, -25)], tag="bus fare", occurred_on=date(2026, 1, 2))

    body = (await unverified(client, auth)).json()

    assert [row["id"] for row in body] == [4]
    assert body[0]["net_effect"] == -25
    assert body[0]["occurred_on"] == "2026-01-02"


# ---- difference suspects -------------------------------------------------------


async def test_suspects_finds_an_extra_zero(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201
    await entry(lab, "expense", [(POOL, -120)], tag="printing")

    response = await suspects(client, auth, 108)

    assert response.status_code == 200
    body = response.json()
    assert [row["entry_id"] for row in body] == [4]
    assert set(body[0]) == SUSPECT_FIELDS
    assert body[0]["effect"] == -120
    assert body[0]["kind"] == "expense"
    assert "extra zero" in body[0]["why"]


async def test_suspects_finds_swapped_digits(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201
    await entry(lab, "expense", [(POOL, -45)], tag="snacks")

    body = (await suspects(client, auth, -9)).json()

    assert [row["entry_id"] for row in body] == [4]
    assert body[0]["effect"] == -45
    assert "swapped" in body[0]["why"]


async def test_suspects_scoped_to_one_envelope(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201
    await entry(lab, "transfer", [(POOL, -300), (EVENTS, 300)], note="events money")

    body = (await suspects(client, auth, -300, envelope_id=EVENTS)).json()

    assert [row["entry_id"] for row in body] == [4]
    assert body[0]["effect"] == 300
    assert body[0]["kind"] == "transfer"
    assert "same amount" in body[0]["why"]


async def test_suspects_no_match_returns_empty(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_month1(lab)
    assert (await reconcile(client, auth, 1150)).status_code == 201
    await entry(lab, "deposit", [(POOL, 40)], source="other")

    body = (await suspects(client, auth, 77)).json()

    assert body == []


async def test_suspects_non_integer_difference_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get(
        "/api/v1/difference-suspects", params={"difference": "abc"}, headers=auth
    )

    assert_problem(response, 422, "validation_error")
