"""API tests for member adjustments (roadmap step 7.3).

Approved brief this session: every question took the brief's labelled suggestion
(same pattern as D-101/D-104): Q1=a `POST /api/v1/members/{member_id}/adjustments`
with `kind` in the body; Q2=a the read is part of the step; Q3=a the amount is
SIGNED and the direction rules stay the table CHECKs'; Q4=c the app refuses a
blank note for `waiver`/`correction` as 422 `validation_failed` while a wrong sign
reaches PostgreSQL and answers 409 `rule_violation`; Q5=a `occurred_on` is
required, with no invented default; Q6=a the answer is the full stored row; Q7=a
an unknown member is 404 `not_found` (adapter pre-check, D-083's pattern); Q8=a
no open tenure is answered by `adj_guard`/`open_tenure_start()` as 409
`rule_violation`.

Contract this file pins:
    POST /api/v1/members/{id}/adjustments   201  AdjustmentOut
    GET  /api/v1/members/{id}/adjustments   200  [AdjustmentOut] in id order

AdjustmentOut = {"id","member_id","kind","amount","occurred_on","note",
"recorded_at","recorded_by"}; `recorded_by` is the JWT actor, never a body field
(AGENTS.md section 5).

Database rules these tests rely on (db/schema.sql, read this session):
- `adjustment_kind` (:128) and `member_adjustments` (:129-141);
- `CHECK (amount <> 0)` (:133) -> 23514 for a zero amount;
- `CHECK (kind <> 'waiver' OR amount > 0)` and
  `CHECK (kind <> 'credit_donation' OR amount < 0)` (:138-139) -> 23514;
- `CHECK (kind NOT IN ('waiver','correction') OR length(btrim(note)) > 0)`
  (:140) is the database BACKSTOP; the app refuses the blank note first (Q4=c);
- `adj_guard` (:185-191) refuses `occurred_on` before `open_tenure_start()`,
  and `open_tenure_start()` (:54-60) raises when no tenure is open;
- `labapp` has INSERT on `member_adjustments` (:1193) and the table is
  append-only (:161), so the app can create but never change a row.

Members are seeded straight through the owner connection, as the 7.0/7.2 tests
seed their rows: this step's behaviour is the adjustment endpoint, so a test that
needs a member must not depend on the members API answering first.

Library APIs used, all verified in installed source or by probe this session:
- pydantic 2.14.1 `Field(strict=True)` refuses `True`, `10.5`, `"20"` and `None`
  for an `int` field, a `StrEnum` field refuses an unknown member, and
  `ConfigDict(extra="forbid")` refuses an extra body field (live probe this
  session; `.venv/lib/python3.15/site-packages/pydantic/fields.py:248,1408`;
  `pydantic/config.py:61-103`);
- the app's validation handler answers 422 `validation_error`
  (`src/mesl_finance/shared/api/problems.py:71-80`);
- `httpx.AsyncClient.post/get` (httpx 0.28.1,
  `.venv/lib/python3.15/site-packages/httpx/_client.py:1751,1838`);
- `asyncpg.Connection.fetchrow/fetchval` (asyncpg-stubs 0.32.0,
  `.venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:236,244`);
- `datetime.date` / `datetime.fromisoformat` are stdlib;
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.

No `db/examples` script is ported here: the database-level adjustment rules were
ported in step 7.0 (`tests/db/test_fees.py`).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

ADJUSTMENT_FIELDS = {
    "id",
    "member_id",
    "kind",
    "amount",
    "occurred_on",
    "note",
    "recorded_at",
    "recorded_by",
}

DEFAULT_BODY: dict[str, Any] = {
    "kind": "waiver",
    "amount": 40,
    "occurred_on": "2026-02-01",
    "note": "left mid-week, forgiven",
}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def seed_member(db: TestDb, name: str = "Ayesha") -> int:
    member_id: int = await db.owner.fetchval(
        "INSERT INTO members(name) VALUES ($1) RETURNING id", name
    )
    return member_id


async def adjust(
    client: AsyncClient, auth: dict[str, str], member_id: int, **overrides: Any
) -> Any:
    body = dict(DEFAULT_BODY)
    body.update(overrides)
    return await client.post(f"/api/v1/members/{member_id}/adjustments", json=body, headers=auth)


async def stored_adjustment(db: TestDb, adjustment_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        """
        SELECT id, member_id, kind, amount, occurred_on, note, recorded_at, recorded_by
        FROM member_adjustments
        WHERE id = $1
        """,
        adjustment_id,
    )
    assert row is not None
    return {
        "id": row["id"],
        "member_id": row["member_id"],
        "kind": row["kind"],
        "amount": row["amount"],
        "occurred_on": row["occurred_on"],
        "note": row["note"],
        "recorded_at": row["recorded_at"],
        "recorded_by": row["recorded_by"],
    }


async def adjustment_count(db: TestDb) -> int:
    count: int = await db.owner.fetchval("SELECT count(*) FROM member_adjustments")
    return count


# ---- create -----------------------------------------------------------------


async def test_create_waiver_returns_201_and_stores_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == ADJUSTMENT_FIELDS
    assert (
        body["member_id"],
        body["kind"],
        body["amount"],
        body["occurred_on"],
        body["note"],
        body["recorded_by"],
    ) == (member_id, "waiver", 40, "2026-02-01", "left mid-week, forgiven", USERNAME)
    stored = await stored_adjustment(lab, body["id"])
    assert (
        stored["member_id"],
        stored["kind"],
        stored["amount"],
        stored["occurred_on"],
        stored["note"],
        stored["recorded_by"],
    ) == (member_id, "waiver", 40, date(2026, 2, 1), "left mid-week, forgiven", USERNAME)
    assert datetime.fromisoformat(body["recorded_at"]) == stored["recorded_at"]


async def test_create_credit_donation_stores_the_negative_amount(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(
        client, auth, member_id, kind="credit_donation", amount=-40, note="donated to lab"
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["amount"]) == ("credit_donation", -40)
    stored = await stored_adjustment(lab, body["id"])
    assert (stored["kind"], stored["amount"], stored["note"]) == (
        "credit_donation",
        -40,
        "donated to lab",
    )


async def test_create_opening_accepts_a_negative_amount(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(
        client,
        auth,
        member_id,
        kind="opening",
        amount=-40,
        note="owed 2 weeks on the old sheet",
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["amount"]) == ("opening", -40)
    stored = await stored_adjustment(lab, body["id"])
    assert (stored["kind"], stored["amount"]) == ("opening", -40)


async def test_create_correction_returns_201(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(
        client, auth, member_id, kind="correction", amount=25, note="fixed typo"
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["amount"], body["note"]) == ("correction", 25, "fixed typo")
    stored = await stored_adjustment(lab, body["id"])
    assert (stored["kind"], stored["amount"], stored["note"]) == ("correction", 25, "fixed typo")


async def test_recorded_by_is_the_token_subject(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id)

    assert response.json()["recorded_by"] == USERNAME
    assert (await stored_adjustment(lab, response.json()["id"]))["recorded_by"] == USERNAME


async def test_unknown_member_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await adjust(client, auth, 9999)

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]
    assert await adjustment_count(lab) == 0


async def test_unknown_kind_is_422(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id, kind="refund")

    assert_problem(response, 422, "validation_error")
    assert await adjustment_count(lab) == 0


async def test_extra_body_field_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)
    body = dict(DEFAULT_BODY)
    body["member_id"] = member_id

    response = await client.post(
        f"/api/v1/members/{member_id}/adjustments", json=body, headers=auth
    )

    assert_problem(response, 422, "validation_error")
    assert await adjustment_count(lab) == 0


async def test_zero_amount_is_409(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id, amount=0)

    assert_problem(response, 409, "rule_violation")
    assert await adjustment_count(lab) == 0


async def test_wrong_sign_for_waiver_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id, amount=-5)

    assert_problem(response, 409, "rule_violation")
    assert await adjustment_count(lab) == 0


async def test_waiver_without_a_note_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)
    body = {"kind": "waiver", "amount": 5, "occurred_on": "2026-02-01"}

    response = await client.post(
        f"/api/v1/members/{member_id}/adjustments", json=body, headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert await adjustment_count(lab) == 0


async def test_occurred_on_before_the_open_tenure_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # `lab` opens the first tenure on 2026-01-01; this date is inside the closed past.
    member_id = await seed_member(lab)

    response = await adjust(client, auth, member_id, occurred_on="2025-12-28")

    assert_problem(response, 409, "rule_violation")
    assert "closed tenure" in response.json()["detail"]
    assert await adjustment_count(lab) == 0


async def test_no_open_tenure_is_409(client: AsyncClient, db: TestDb, auth: dict[str, str]) -> None:
    # No `lab` fixture here: the template clone has no tenure at all.
    member_id = await seed_member(db)

    response = await adjust(client, auth, member_id)

    assert_problem(response, 409, "rule_violation")
    assert "no open tenure" in response.json()["detail"]
    assert await adjustment_count(db) == 0


async def test_create_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    member_id = await seed_member(lab)

    response = await client.post(f"/api/v1/members/{member_id}/adjustments", json=DEFAULT_BODY)

    assert_problem(response, 401, "invalid_token")


# ---- list -------------------------------------------------------------------


async def test_list_returns_the_members_adjustments_in_id_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)
    first = await adjust(client, auth, member_id)
    second = await adjust(client, auth, member_id, kind="opening", amount=-40, note="old sheet")

    response = await client.get(f"/api/v1/members/{member_id}/adjustments", headers=auth)

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [first.json()["id"], second.json()["id"]]
    assert [item["kind"] for item in items] == ["waiver", "opening"]
    assert all(set(item) == ADJUSTMENT_FIELDS for item in items)


async def test_list_for_unknown_member_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get("/api/v1/members/9999/adjustments", headers=auth)

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]


async def test_list_of_a_member_without_adjustments_is_empty(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member_id = await seed_member(lab)

    response = await client.get(f"/api/v1/members/{member_id}/adjustments", headers=auth)

    assert response.status_code == 200
    assert response.json() == []
