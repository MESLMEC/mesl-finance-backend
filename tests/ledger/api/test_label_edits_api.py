"""POST /api/v1/entries/{entry_id}/edit-labels: the label edit end to end.

Approved contract (step 6.6 brief): Q7 was answered b, every other question was
left unanswered, so the brief's labelled suggestions stand.
- Q1=a ``POST /api/v1/entries/{entry_id}/edit-labels``.
- Q2=a any non-opening entry may be relabelled; PostgreSQL's ``tx_label_edit``
  (db/schema.sql:376-410) owns the tenure, opening and kind rules.
- Q3=a the body is partial: only the fields it names change, an explicit null
  clears ``tag``/``cost_center_id``/``source``, and ``note``/``occurred_on``
  are never null.
- Q4=a an empty body is 422 ``validation_failed``.
- Q5=a the answer is 200 ``{"id", "kind", "note", "tag", "cost_center_id",
  "occurred_on", "source"}`` after the write.
- Q6=a a ``source`` on a non-deposit reaches the server's CHECK and answers
  409 ``rule_violation``.
- Q7=b a blank note on a kind that needs one (transfer/sweep/reversal,
  db/schema.sql:259) is refused by the APP as 422 ``validation_failed`` before
  any SQL runs.
- Q8=a an unknown ``cost_center_id`` is the foreign key -> 422
  ``unknown_reference``.
- Q9=a the history rows are written by the trigger and read later; 6.6 adds no
  read route.

Every edit is ONE transaction; ``ledger_label_edits`` is written by the
database's trigger and names the authenticated treasurer, never ``labapp``.
"""

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS, ADMIN = 1, 2, 3


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def history(db: TestDb) -> list[tuple[str, str | None, str | None, str]]:
    rows = await db.owner.fetch(
        "SELECT field, old_value, new_value, edited_by FROM ledger_label_edits ORDER BY id"
    )
    return [tuple(row) for row in rows]


async def header(db: TestDb, entry_id: int) -> Any:
    return await db.owner.fetchrow(
        "SELECT kind, note, tag, cost_center_id, occurred_on, source"
        " FROM ledger_transactions WHERE id = $1",
        entry_id,
    )


async def add_cost_center(db: TestDb) -> int:
    new_id = await db.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Workshop 1', 'event') RETURNING id"
    )
    return int(new_id)


async def fund(client: AsyncClient, auth: dict[str, str], *, envelope_id: int, amount: int) -> int:
    """Put money in through the deposit action (step 6.2); returns the entry id."""
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "envelope_id": envelope_id,
        },
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def spend(client: AsyncClient, auth: dict[str, str], *, envelope_id: int, amount: int) -> int:
    """Take money out through the expense action (step 6.3); returns the entry id."""
    response = await client.post(
        "/api/v1/expenses",
        json={"amount": amount, "occurred_on": "2026-02-02", "envelope_id": envelope_id},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def move(client: AsyncClient, auth: dict[str, str], *, amount: int = 200) -> int:
    """Move money between two envelopes (step 6.4); returns the entry id."""
    response = await client.post(
        "/api/v1/transfers",
        json={
            "amount": amount,
            "occurred_on": "2026-02-02",
            "from_envelope_id": POOL,
            "to_envelope_id": EVENTS,
            "note": "for workshop",
        },
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def relabel(client: AsyncClient, auth: dict[str, str], entry_id: int, **body: Any) -> Any:
    return await client.post(f"/api/v1/entries/{entry_id}/edit-labels", json=body, headers=auth)


async def test_a_partial_edit_returns_the_labels_and_logs_only_that_field(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, deposit_id, note="fees wk 27")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id",
        "kind",
        "note",
        "tag",
        "cost_center_id",
        "occurred_on",
        "source",
    }
    assert body == {
        "id": deposit_id,
        "kind": "deposit",
        "note": "fees wk 27",
        "tag": None,
        "cost_center_id": None,
        "occurred_on": "2026-02-01",
        "source": "sponsorship",
    }
    assert await history(lab) == [("note", "", "fees wk 27", USERNAME)]


async def test_editing_all_five_labels_at_once_returns_them(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await add_cost_center(lab)
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(
        client,
        auth,
        deposit_id,
        note="sponsor cash",
        tag="sponsor",
        cost_center_id=cost_center,
        occurred_on="2026-02-05",
        source="donation",
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": deposit_id,
        "kind": "deposit",
        "note": "sponsor cash",
        "tag": "sponsor",
        "cost_center_id": cost_center,
        "occurred_on": "2026-02-05",
        "source": "donation",
    }
    rows = await history(lab)
    assert [row[0] for row in rows] == [
        "note",
        "tag",
        "cost_center_id",
        "occurred_on",
        "source",
    ]
    assert rows[2] == ("cost_center_id", None, str(cost_center), USERNAME)
    assert rows[3] == ("occurred_on", "2026-02-01", "2026-02-05", USERNAME)
    assert rows[4] == ("source", "sponsorship", "donation", USERNAME)


async def test_an_explicit_null_clears_the_tag_and_the_cost_center(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await add_cost_center(lab)
    created = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 500,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "tag": "sponsor",
            "cost_center_id": cost_center,
        },
        headers=auth,
    )
    assert created.status_code == 201
    deposit_id = int(created.json()["id"])

    response = await relabel(client, auth, deposit_id, tag=None, cost_center_id=None)

    assert response.status_code == 200
    body = response.json()
    assert (body["tag"], body["cost_center_id"]) == (None, None)
    assert await history(lab) == [
        ("tag", "sponsor", None, USERNAME),
        ("cost_center_id", str(cost_center), None, USERNAME),
    ]


async def test_an_omitted_field_is_left_alone(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await add_cost_center(lab)
    created = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 500,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "tag": "sponsor",
            "cost_center_id": cost_center,
        },
        headers=auth,
    )
    assert created.status_code == 201
    deposit_id = int(created.json()["id"])

    response = await relabel(client, auth, deposit_id, note="fees wk 27")

    assert response.status_code == 200
    body = response.json()
    assert (body["tag"], body["cost_center_id"], body["source"]) == (
        "sponsor",
        cost_center,
        "sponsorship",
    )
    assert [row[0] for row in await history(lab)] == ["note"]


async def test_each_edit_is_logged_against_the_authenticated_treasurer(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, deposit_id, note="fees wk 27", tag="fees")

    assert response.status_code == 200
    editors = await lab.owner.fetch("SELECT DISTINCT edited_by FROM ledger_label_edits")
    assert [row["edited_by"] for row in editors] == [USERNAME]


async def test_an_empty_body_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, deposit_id)

    assert_problem(response, 422, "validation_failed")
    assert await history(lab) == []
    row = await header(lab, deposit_id)
    assert row is not None
    assert row["note"] == ""


async def test_an_unknown_entry_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, 999999, note="nowhere")

    assert_problem(response, 422, "unknown_reference")
    assert "999999" in response.json()["detail"]
    assert await history(lab) == []


async def test_an_unknown_cost_center_is_a_422_unknown_reference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, deposit_id, cost_center_id=999999)

    assert_problem(response, 422, "unknown_reference")
    assert "999999" in response.json()["detail"]
    assert await history(lab) == []
    row = await header(lab, deposit_id)
    assert row is not None
    assert row["cost_center_id"] is None


async def test_a_date_before_the_tenure_opened_is_a_409_date_before_tenure(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await relabel(client, auth, deposit_id, occurred_on="2025-12-31")

    assert_problem(response, 409, "date_before_tenure")
    assert await history(lab) == []
    row = await header(lab, deposit_id)
    assert row is not None
    assert row["occurred_on"] == date(2026, 2, 1)


async def test_an_opening_entry_is_a_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    async with lab.app.transaction():  # one transaction: check_shape fires at COMMIT
        opening_id = int(
            await lab.app.fetchval(
                "INSERT INTO ledger_transactions (tenure_id, kind, occurred_on, recorded_by, note)"
                " VALUES (1, 'opening', '2026-01-01', 'owner', '') RETURNING id"
            )
        )
        await lab.app.execute(
            "INSERT INTO ledger_lines (transaction_id, envelope_id, amount) VALUES ($1, $2, 100)",
            opening_id,
            POOL,
        )

    response = await relabel(client, auth, opening_id, note="renamed")

    assert_problem(response, 409, "rule_violation")
    assert "opening" in response.json()["detail"].lower()
    assert await history(lab) == []


async def test_an_entry_in_a_closed_tenure_is_a_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)
    await lab.app.execute(
        "SELECT close_tenure($1, $2, $3)", date(2026, 12, 31), "treasurer", "2027"
    )

    response = await relabel(client, auth, deposit_id, note="sneaky")

    assert_problem(response, 409, "rule_violation")
    assert "closed" in response.json()["detail"].lower()
    assert await history(lab) == []
    row = await header(lab, deposit_id)
    assert row is not None
    assert row["note"] == ""


async def test_source_on_a_non_deposit_is_a_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=300)
    expense_id = await spend(client, auth, envelope_id=EVENTS, amount=150)

    response = await relabel(client, auth, expense_id, source="donation")

    assert_problem(response, 409, "rule_violation")
    assert await history(lab) == []
    row = await header(lab, expense_id)
    assert row is not None
    assert row["source"] is None


async def test_changing_a_weekly_fee_deposit_to_another_source_while_a_member_is_attached_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members (name) VALUES ('A') RETURNING id")
    sunday = await lab.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await lab.app.execute(
        "INSERT INTO fee_rates (effective_from, amount, recorded_by) VALUES ($1, 20, 'treasurer')",
        sunday,
    )
    await lab.app.execute(
        "INSERT INTO membership_periods (member_id, start_date) VALUES ($1, $2)", member, sunday
    )
    payment = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 100,
            "occurred_on": sunday.isoformat(),
            "source": "weekly_fee",
            "member_id": member,
        },
        headers=auth,
    )
    assert payment.status_code == 201
    deposit_id = int(payment.json()["id"])

    response = await relabel(client, auth, deposit_id, source="donation")

    assert_problem(response, 409, "rule_violation")
    assert "fee_needs_member" in response.json()["detail"]
    assert await history(lab) == []
    row = await header(lab, deposit_id)
    assert row is not None
    assert row["source"] == "weekly_fee"


async def test_a_blank_note_on_a_transfer_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)
    transfer_id = await move(client, auth)

    response = await relabel(client, auth, transfer_id, note="   ")

    assert_problem(response, 422, "validation_failed")
    assert await history(lab) == []
    row = await header(lab, transfer_id)
    assert row is not None
    assert row["note"] == "for workshop"


async def test_a_voided_original_and_a_reversal_are_editable(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)
    fixed = await client.post(
        f"/api/v1/entries/{deposit_id}/fix-amount",
        json={"amount": 600, "occurred_on": "2026-10-20", "note": "typo in amount"},
        headers=auth,
    )
    assert fixed.status_code == 201
    reversal_id = int(fixed.json()["reversal_id"])

    original = await relabel(client, auth, deposit_id, note="original relabel")
    reversal = await relabel(client, auth, reversal_id, tag="correction")

    assert original.status_code == 200
    assert original.json()["note"] == "original relabel"
    assert reversal.status_code == 200
    assert reversal.json()["tag"] == "correction"
    current = await lab.owner.fetch("SELECT id FROM entries_current")
    assert [row["id"] for row in current] == [int(fixed.json()["id"])]


async def test_a_label_edit_leaves_balances_and_the_checksum_unchanged(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)
    before = await lab.owner.fetch("SELECT id, balance FROM envelope_balances ORDER BY id")
    checksum = await lab.owner.fetchval("SELECT ledger_checksum(1)")

    response = await relabel(client, auth, deposit_id, note="fees wk 27", tag="fees")

    assert response.status_code == 200
    after = await lab.owner.fetch("SELECT id, balance FROM envelope_balances ORDER BY id")
    assert [(r["id"], int(r["balance"])) for r in after] == [
        (r["id"], int(r["balance"])) for r in before
    ]
    assert await lab.owner.fetchval("SELECT ledger_checksum(1)") == checksum


async def test_the_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/entries/1/edit-labels", json={"note": "x"})

    assert_problem(response, 401, "invalid_token")
    assert await history(lab) == []
