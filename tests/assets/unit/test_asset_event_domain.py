"""Domain tests for the asset event value object (roadmap step 9.1).

Approved brief answers this session: Q4=a a strict positive whole `quantity`
for every kind except `correction`, which may be negative or positive; Q5=a
the app refuses the kind-shape rules (source only on `acquired`, member only
on `lent`/`returned`/`damaged`/`lost`, a required non-blank note on
`damaged`/`lost`/`scrapped`/`exchanged`/`correction`) as 422
`validation_failed` before SQL; Q8=a the event response carries no counts.
Reversal/replacement is 9.2 and stays out.

What these tests pin (the domain API /code must provide):
- `AssetEventKind`: the nine members of `asset_event_kind`
  (db/schema.sql:653-654), in the enum's own order
- `AcquireSource`: the six members of `acquire_source` (db/schema.sql:655)
- `AssetEvent.create(kind=..., quantity=..., occurred_on=..., member_id=None,
  source=None, ledger_transaction_id=None, note="")` refuses with
  `ValidationFailed`:
  - a non-`int` quantity (the D-047/D-081 strictness; `bool` refused)
  - a zero quantity (db/schema.sql:661 backstop)
  - a negative quantity on a non-`correction` kind (db/schema.sql:677)
  - a missing `source` on `acquired` and a `source` elsewhere
    (db/schema.sql:672) - the app pre-refusal Q5=a chose
  - a missing `member_id` on `lent`/`returned` and a `member_id` on any other
    kind (db/schema.sql:674-676) - app pre-refusal Q5=a
  - a blank note on the five kinds that require one (db/schema.sql:678-679)
    - app pre-refusal Q5=a
  - a `purchase` with no `ledger_transaction_id` (issue #10, brief Q1=a/Q2=a):
    a lab-money purchase must name the payment that bought it, so the
    acquisition-to-expense link is the only cost trail the lab keeps (the
    database backstop for it is issue #11's CHECK, not in the schema yet)

Not tested here, on purpose: the ledger link only on `acquired`
(db/schema.sql:673) was not part of the approved Q5 enumeration, so the CHECK
stays the backstop and no test pins it; stock/bucket arithmetic is
PostgreSQL's (`asset_event_effects`, db/schema.sql:696-714) and is pinned by
the API tests; `ledger_transaction_id`/`reverses_id`/`replaces_id` shape rules
are 9.2's.

The module is imported lazily (D-069), like the other domain tests.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

KIND_MEMBERS = [
    ("ACQUIRED", "acquired"),
    ("LENT", "lent"),
    ("RETURNED", "returned"),
    ("DAMAGED", "damaged"),
    ("LOST", "lost"),
    ("REPAIRED", "repaired"),
    ("SCRAPPED", "scrapped"),
    ("EXCHANGED", "exchanged"),
    ("CORRECTION", "correction"),
]
SOURCE_MEMBERS = [
    ("PURCHASE", "purchase"),
    ("ADMIN", "admin"),
    ("PROJECT_RETURN", "project_return"),
    ("DONATION", "donation"),
    ("REPLACEMENT", "replacement"),
    ("OTHER", "other"),
]


def _module() -> ModuleType:
    try:
        return import_module("mesl_finance.assets.domain.asset_event")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/assets/domain/asset_event.py does not exist yet")


def _event_class() -> Any:
    return vars(_module())["AssetEvent"]


def _kinds() -> Any:
    return vars(_module())["AssetEventKind"]


def _sources() -> Any:
    return vars(_module())["AcquireSource"]


def test_the_event_kinds_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _kinds()] == KIND_MEMBERS


def test_the_acquire_sources_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _sources()] == SOURCE_MEMBERS


def test_an_event_keeps_its_values() -> None:
    thing = _event_class().create(
        kind="lent",
        quantity=2,
        occurred_on=date(2026, 2, 1),
        member_id=3,
        note="for the weather station",
    )

    assert (thing.kind, thing.quantity, thing.member_id, thing.note) == (
        "lent",
        2,
        3,
        "for the weather station",
    )


@pytest.mark.parametrize("quantity", [10.5, "10", True])
def test_a_non_whole_quantity_is_refused(quantity: Any) -> None:
    with pytest.raises(ValidationFailed, match="whole"):
        _event_class().create(
            kind="acquired",
            quantity=quantity,
            occurred_on=date(2026, 2, 1),
            source="purchase",
        )


def test_a_zero_quantity_is_refused() -> None:
    with pytest.raises(ValidationFailed, match="zero"):
        _event_class().create(
            kind="acquired",
            quantity=0,
            occurred_on=date(2026, 2, 1),
            source="purchase",
        )


@pytest.mark.parametrize("kind", ["acquired", "lent", "returned"])
def test_a_negative_quantity_is_only_for_a_correction(kind: str) -> None:
    body: dict[str, Any] = {
        "kind": kind,
        "quantity": -1,
        "occurred_on": date(2026, 2, 1),
    }
    if kind == "acquired":
        body["source"] = "purchase"
    if kind == "lent":
        body["member_id"] = 1

    with pytest.raises(ValidationFailed, match="negative"):
        _event_class().create(**body)


def test_a_correction_may_be_negative_or_positive() -> None:
    down = _event_class().create(
        kind="correction", quantity=-1, occurred_on=date(2026, 2, 1), note="count 5"
    )
    up = _event_class().create(
        kind="correction", quantity=2, occurred_on=date(2026, 2, 1), note="count 7"
    )

    assert (down.quantity, up.quantity) == (-1, 2)


@pytest.mark.parametrize(
    ("kind", "extra"),
    [
        ("acquired", {}),
        ("repaired", {"source": "purchase"}),
    ],
)
def test_the_source_pairs_only_with_acquired(kind: str, extra: dict[str, Any]) -> None:
    body: dict[str, Any] = {"kind": kind, "quantity": 1, "occurred_on": date(2026, 2, 1), **extra}

    with pytest.raises(ValidationFailed, match="source"):
        _event_class().create(**body)


def test_an_acquired_event_keeps_its_source() -> None:
    thing = _event_class().create(
        kind="acquired",
        quantity=10,
        occurred_on=date(2026, 2, 1),
        source="purchase",
        ledger_transaction_id=9,
    )

    assert thing.source == "purchase"


@pytest.mark.parametrize("kind", ["lent", "returned"])
def test_lending_and_returning_need_a_member(kind: str) -> None:
    with pytest.raises(ValidationFailed, match="member"):
        _event_class().create(kind=kind, quantity=1, occurred_on=date(2026, 2, 1))


@pytest.mark.parametrize(
    ("kind", "extra"),
    [
        ("acquired", {"source": "purchase"}),
        ("repaired", {}),
        ("scrapped", {"note": "not repairable"}),
        ("exchanged", {"note": "sent to admin"}),
        ("correction", {"note": "count 5"}),
    ],
)
def test_the_other_kinds_take_no_member(kind: str, extra: dict[str, Any]) -> None:
    body: dict[str, Any] = {
        "kind": kind,
        "quantity": 1,
        "occurred_on": date(2026, 2, 1),
        "member_id": 3,
        **extra,
    }

    with pytest.raises(ValidationFailed, match="member"):
        _event_class().create(**body)


@pytest.mark.parametrize("kind", ["damaged", "lost"])
def test_damage_and_loss_may_name_the_member_who_had_it(kind: str) -> None:
    thing = _event_class().create(
        kind=kind,
        quantity=1,
        occurred_on=date(2026, 2, 1),
        member_id=3,
        note="burnt, reverse polarity",
    )

    assert thing.member_id == 3


@pytest.mark.parametrize("kind", ["damaged", "lost", "scrapped", "exchanged", "correction"])
@pytest.mark.parametrize("note", ["", "   "])
def test_a_blank_note_is_refused_on_the_kinds_that_need_one(kind: str, note: str) -> None:
    with pytest.raises(ValidationFailed, match="note"):
        _event_class().create(kind=kind, quantity=1, occurred_on=date(2026, 2, 1), note=note)


def test_the_note_defaults_to_empty_where_one_is_not_needed() -> None:
    thing = _event_class().create(
        kind="acquired",
        quantity=10,
        occurred_on=date(2026, 2, 1),
        source="purchase",
        ledger_transaction_id=9,
    )

    assert thing.note == ""


def test_a_purchase_needs_the_payment_that_bought_it() -> None:
    """Issue #10: a lab-money purchase must name its payment.

    The lab keeps no taka value for an item, so the link to the expense is the
    only record of what it cost (brief Q1=a/Q2=a). The rule is the app's own
    pre-refusal; the database backstop (issue #11's CHECK) is not in the
    schema yet.
    """
    with pytest.raises(ValidationFailed, match="purchase"):
        _event_class().create(
            kind="acquired",
            quantity=10,
            occurred_on=date(2026, 2, 1),
            source="purchase",
            ledger_transaction_id=None,
        )


def test_a_purchase_with_a_link_is_accepted() -> None:
    thing = _event_class().create(
        kind="acquired",
        quantity=10,
        occurred_on=date(2026, 2, 1),
        source="purchase",
        ledger_transaction_id=7,
    )

    assert (thing.source, thing.ledger_transaction_id) == ("purchase", 7)


@pytest.mark.parametrize("source", ["admin", "donation", "project_return", "replacement", "other"])
def test_a_non_purchase_may_omit_the_link(source: str) -> None:
    """Only money the lab spends needs a payment; an admin-given or donated
    item has none (brief Q1=a)."""
    thing = _event_class().create(
        kind="acquired",
        quantity=1,
        occurred_on=date(2026, 2, 1),
        source=source,
        ledger_transaction_id=None,
    )

    assert (thing.source, thing.ledger_transaction_id) == (source, None)
