"""GET /api/v1/entries: the treasurer's list end to end (ROADMAP 6.7).

Approved contract (step 6.7 brief; every question was left unanswered, so the
brief's labelled suggestions stand, same pattern as D-062/D-064/D-066/D-070/
D-076/D-079/D-082/D-086/D-088/D-090):
- Q1=a ``GET /api/v1/entries`` answers 200 with a bare JSON array (Q8=a),
  ordered by ``id`` (Q6=a), with no pagination (Q7=a) and no filter other than
  the optional ``?tenure_id=`` (Q4=a, Q5=a).
- Q2=a each item is ``{"id", "tenure_id", "kind", "occurred_on",
  "recorded_at", "recorded_by", "note", "tag", "cost_center_id", "member_id",
  "source", "corrected_from"}``: the view's ``reverses_id``/``replaces_id``
  stay private and ``corrected_from`` is that ``replaces_id``
  (db/schema.sql:426-430).
- Q3=a the list carries no amounts: ``entries_current`` has none.
  SUPERSEDED by issue #5: each item now also carries ``lines``
  (``[{"envelope_id", "amount"}]``, signed, ordered by ``envelope_id``),
  ``net_effect`` and ``size`` — the exact formula ``unverified_entries`` uses
  (db/schema.sql:1099-1101). Opening entries carry their lines like every
  other kind. Recorded as a new decision at wrapup (origin + blame pointer:
  issue #5).
- Q10=a an unknown ``tenure_id`` is an empty list, not a 404.
- Q9=a 6.7 adds no single-entry read route.

``entries_current`` is the point of the step: it hides reversals and voided
originals, so a fixed amount is one line (db/schema.sql:426-430).
"""

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb, idempotent

ENTRY_KEYS = {
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
    "source",
    "corrected_from",
    # Issue #5: amounts come back per line plus the two totals (db/schema.sql:1099-1101).
    "lines",
    "net_effect",
    "size",
}
POOL, EVENTS, ADMIN = 1, 2, 3


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def entries(client: AsyncClient, auth: dict[str, str], **params: str | int) -> Any:
    response = await client.get("/api/v1/entries", params=params, headers=auth)
    assert response.status_code == 200
    return response.json()


async def deposit(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> int:
    body: dict[str, Any] = {
        "amount": 500,
        "occurred_on": "2026-02-01",
        "source": "sponsorship",
    }
    body.update(overrides)
    response = await client.post(
        "/api/v1/deposits", json=body, headers=idempotent(auth, "deposit-1-1")
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def spend(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> int:
    body: dict[str, Any] = {
        "amount": 100,
        "occurred_on": "2026-02-02",
        "envelope_id": POOL,
    }
    body.update(overrides)
    response = await client.post("/api/v1/expenses", json=body, headers=auth)
    assert response.status_code == 201
    return int(response.json()["id"])


async def move(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> int:
    body: dict[str, Any] = {
        "amount": 50,
        "occurred_on": "2026-02-03",
        "from_envelope_id": POOL,
        "to_envelope_id": EVENTS,
        "note": "for workshop",
    }
    body.update(overrides)
    response = await client.post("/api/v1/transfers", json=body, headers=auth)
    assert response.status_code == 201
    return int(response.json()["id"])


async def insert_entry(
    db: TestDb,
    tenure_id: int,
    kind: str,
    occurred_on: date,
    *,
    amount: int,
    note: str = "",
    source: str | None = None,
    envelope_id: int = POOL,
) -> int:
    """Write one header + one line in ONE explicit transaction (D-092 item 5)."""
    async with db.app.transaction():
        entry_id = await db.app.fetchval(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, source)
            VALUES ($1, $2::entry_kind, $3::date, $4, $5, $6::income_source)
            RETURNING id
            """,
            tenure_id,
            kind,
            occurred_on,
            USERNAME,
            note,
            source,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines (transaction_id, envelope_id, amount) VALUES ($1, $2, $3)",
            entry_id,
            envelope_id,
            amount,
        )
    return int(entry_id)


async def test_the_list_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.get("/api/v1/entries")

    assert_problem(response, 401, "invalid_token")


async def test_an_empty_lab_lists_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    assert await entries(client, auth) == []


async def test_the_list_returns_entries_in_id_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await deposit(client, auth)
    expense_id = await spend(client, auth)
    transfer_id = await move(client, auth)

    listed = await entries(client, auth)

    assert [item["id"] for item in listed] == [deposit_id, expense_id, transfer_id]
    assert [item["kind"] for item in listed] == ["deposit", "expense", "transfer"]


async def test_a_list_item_carries_the_approved_fields(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/cost-centers", json={"name": "Workshop", "kind": "event"}, headers=auth
    )
    assert created.status_code == 201
    cost_center_id = int(created.json()["id"])
    entry_id = await deposit(
        client,
        auth,
        amount=500,
        occurred_on="2026-02-01",
        source="sponsorship",
        note="sponsor money",
        tag="sponsors",
        cost_center_id=cost_center_id,
    )

    listed = await entries(client, auth)

    assert len(listed) == 1
    item = listed[0]
    assert set(item) == ENTRY_KEYS
    assert item["id"] == entry_id
    assert item["tenure_id"] == 1
    assert item["kind"] == "deposit"
    assert item["occurred_on"] == "2026-02-01"
    assert isinstance(item["recorded_at"], str) and item["recorded_at"]
    assert item["recorded_by"] == USERNAME
    assert item["note"] == "sponsor money"
    assert item["tag"] == "sponsors"
    assert item["cost_center_id"] == cost_center_id
    assert item["member_id"] is None
    assert item["source"] == "sponsorship"
    assert item["corrected_from"] is None


async def test_a_fixed_amount_shows_one_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    original_id = await deposit(client, auth, amount=100)
    fixed = await client.post(
        f"/api/v1/entries/{original_id}/fix-amount",
        json={"amount": 80, "occurred_on": "2026-02-05", "note": "amount typo"},
        headers=auth,
    )
    assert fixed.status_code == 201
    replacement_id = int(fixed.json()["id"])
    reversal_id = int(fixed.json()["reversal_id"])

    listed = await entries(client, auth)

    assert len(listed) == 1
    item = listed[0]
    assert (item["id"], item["kind"], item["corrected_from"]) == (
        replacement_id,
        "deposit",
        original_id,
    )
    assert original_id not in {row["id"] for row in listed}
    assert reversal_id not in {row["id"] for row in listed}


async def test_a_label_edit_shows_in_the_list(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    entry_id = await deposit(client, auth, note="first", tag="old")
    edited = await client.post(
        f"/api/v1/entries/{entry_id}/edit-labels",
        json={"note": "fees wk 27", "tag": "fees"},
        headers=auth,
    )
    assert edited.status_code == 200

    listed = await entries(client, auth)

    assert len(listed) == 1
    assert (listed[0]["id"], listed[0]["note"], listed[0]["tag"]) == (
        entry_id,
        "fees wk 27",
        "fees",
    )


async def test_the_list_can_be_filtered_by_tenure(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    first_tenure_id = await deposit(client, auth)
    # Only ONE tenure may be open at a time (db/schema.sql:40), so hand over through
    # the schema's own close function; it writes the carry-over opening in tenure 2.
    await lab.owner.execute("SELECT close_tenure('2026-12-31', $1, '2027')", USERNAME)
    opening_id = int(
        await lab.owner.fetchval(
            "SELECT id FROM ledger_transactions WHERE tenure_id = 2 AND kind = 'opening'"
        )
    )
    second_tenure_id = await insert_entry(
        lab, 2, "deposit", date(2027, 1, 5), amount=50, source="other"
    )

    everything = await entries(client, auth)
    assert {item["tenure_id"] for item in everything} == {1, 2}
    assert {item["id"] for item in everything} == {first_tenure_id, opening_id, second_tenure_id}

    tenure_one = await entries(client, auth, tenure_id=1)
    assert [(item["id"], item["tenure_id"]) for item in tenure_one] == [(first_tenure_id, 1)]

    tenure_two = await entries(client, auth, tenure_id=2)
    assert [(item["kind"], item["id"]) for item in tenure_two] == [
        ("opening", opening_id),
        ("deposit", second_tenure_id),
    ]


async def test_a_tenure_id_with_no_entries_is_an_empty_list(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await deposit(client, auth)

    assert await entries(client, auth, tenure_id=999) == []


async def test_a_non_numeric_tenure_id_is_a_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get("/api/v1/entries", params={"tenure_id": "abc"}, headers=auth)

    assert_problem(response, 422, "validation_error")


async def test_an_opening_entry_is_listed(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    opening_id = await insert_entry(lab, 1, "opening", date(2026, 1, 1), amount=1000)

    listed = await entries(client, auth)

    assert len(listed) == 1
    item = listed[0]
    assert (item["id"], item["kind"], item["source"]) == (opening_id, "opening", None)
    assert item["corrected_from"] is None


async def allocate(client: AsyncClient, auth: dict[str, str], amounts: dict[str, int]) -> None:
    response = await client.post(
        "/api/v1/allocations",
        json={"occurred_on": "2026-02-04", "note": "monthly allocation", "amounts": amounts},
        headers=auth,
    )
    assert response.status_code == 201


async def test_a_deposit_lists_one_positive_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    entry_id = await deposit(client, auth, amount=500)

    listed = await entries(client, auth)

    item = next(row for row in listed if row["id"] == entry_id)
    assert item["lines"] == [{"envelope_id": POOL, "amount": 500}]
    assert (item["net_effect"], item["size"]) == (500, 500)


async def test_an_expense_lists_one_negative_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await deposit(client, auth)
    entry_id = await spend(client, auth)

    listed = await entries(client, auth)

    item = next(row for row in listed if row["id"] == entry_id)
    assert item["lines"] == [{"envelope_id": POOL, "amount": -100}]
    assert (item["net_effect"], item["size"]) == (-100, 100)


async def test_a_transfer_lists_both_signed_lines_in_envelope_id_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await deposit(client, auth)
    transfer_id = await move(client, auth)

    listed = await entries(client, auth)

    item = next(row for row in listed if row["id"] == transfer_id)
    assert item["lines"] == [
        {"envelope_id": POOL, "amount": -50},
        {"envelope_id": EVENTS, "amount": 50},
    ]
    assert (item["net_effect"], item["size"]) == (0, 50)


async def test_a_multi_line_allocation_lists_every_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await deposit(client, auth, amount=500)
    await allocate(client, auth, {str(EVENTS): 200, str(ADMIN): 300})

    listed = await entries(client, auth)

    item = next(row for row in listed if row["kind"] == "transfer")
    assert item["tag"] == "allocation"
    assert item["lines"] == [
        {"envelope_id": POOL, "amount": -500},
        {"envelope_id": EVENTS, "amount": 200},
        {"envelope_id": ADMIN, "amount": 300},
    ]
    assert (item["net_effect"], item["size"]) == (0, 500)


async def test_a_fixed_amount_lists_only_the_replacement_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    original_id = await deposit(client, auth, amount=100)
    fixed = await client.post(
        f"/api/v1/entries/{original_id}/fix-amount",
        json={"amount": 80, "occurred_on": "2026-02-05", "note": "amount typo"},
        headers=auth,
    )
    assert fixed.status_code == 201

    listed = await entries(client, auth)

    assert len(listed) == 1
    item = listed[0]
    assert item["lines"] == [{"envelope_id": POOL, "amount": 80}]
    assert (item["net_effect"], item["size"]) == (80, 80)


async def test_a_label_edit_leaves_the_lines_untouched(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    entry_id = await deposit(client, auth, amount=250)
    before = await entries(client, auth)
    assert before[0]["lines"] == [{"envelope_id": POOL, "amount": 250}]
    edited = await client.post(
        f"/api/v1/entries/{entry_id}/edit-labels",
        json={"tag": "fees"},
        headers=auth,
    )
    assert edited.status_code == 200

    listed = await entries(client, auth)

    assert len(listed) == 1
    assert listed[0]["lines"] == [{"envelope_id": POOL, "amount": 250}]
    assert (listed[0]["net_effect"], listed[0]["size"]) == (250, 250)


async def test_a_carry_over_opening_lists_its_lines(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Only ONE tenure may be open at a time (db/schema.sql:40); close_tenure carries the
    # closing balances into the next tenure as the opening entry's lines.
    await deposit(client, auth, amount=300)
    await lab.owner.execute("SELECT close_tenure('2026-12-31', $1, '2027')", USERNAME)

    listed = await entries(client, auth, tenure_id=2)

    assert len(listed) == 1
    item = listed[0]
    assert (item["kind"], item["corrected_from"]) == ("opening", None)
    assert item["lines"] == [{"envelope_id": POOL, "amount": 300}]
    assert (item["net_effect"], item["size"]) == (300, 300)


async def test_the_tenure_filter_still_applies_with_lines(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    first_tenure_id = await deposit(client, auth, amount=300)
    await lab.owner.execute("SELECT close_tenure('2026-12-31', $1, '2027')", USERNAME)
    opening_id = int(
        await lab.owner.fetchval(
            "SELECT id FROM ledger_transactions WHERE tenure_id = 2 AND kind = 'opening'"
        )
    )
    second_tenure_id = await insert_entry(
        lab, 2, "deposit", date(2027, 1, 5), amount=50, source="other"
    )

    tenure_one = await entries(client, auth, tenure_id=1)
    assert [(row["id"], row["lines"], row["net_effect"], row["size"]) for row in tenure_one] == [
        (first_tenure_id, [{"envelope_id": POOL, "amount": 300}], 300, 300)
    ]

    tenure_two = await entries(client, auth, tenure_id=2)
    assert [(row["id"], row["kind"], row["lines"]) for row in tenure_two] == [
        (opening_id, "opening", [{"envelope_id": POOL, "amount": 300}]),
        (second_tenure_id, "deposit", [{"envelope_id": POOL, "amount": 50}]),
    ]

    everything = await entries(client, auth)
    assert {row["id"] for row in everything} == {
        first_tenure_id,
        opening_id,
        second_tenure_id,
    }
