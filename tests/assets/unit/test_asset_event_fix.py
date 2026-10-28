"""AssetEventFix value object (ROADMAP 9.2): one asset event fixed by a
reversal plus a replacement written in ONE transaction.

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a the route is ``POST
/api/v1/assets/{asset_id}/events/{event_id}/fix``; Q2=a the body is
``{quantity, occurred_on, note}`` - the reversal mirrors the original (same
asset/kind/member/source, negated quantity; the mirror rule is
``asset_event_guard``'s, db/schema.sql:742-749) and carries the request's
note, while the replacement copies the original's note and takes the new
quantity and the request's ``occurred_on`` (6.5's approved shape, D-088 Q3);
Q3=a all nine kinds are fixable; Q4=a an unknown event is 404 ``not_found``;
Q5=a ``201 {"id","asset_id","kind","quantity","occurred_on","note",
"reversal_id"}``.

What the DOMAIN pins (the value object /code must provide):
- ``AssetEventFix.create(event_id=..., quantity=..., occurred_on=...,
  note=...)`` refuses with ``ValidationFailed``:
  - a non-``int`` quantity (the D-047/D-081 strictness; ``bool`` refused)
  - a zero quantity (db/schema.sql:661 backstop)
  - a blank note: the schema CHECK (db/schema.sql:680) forbids one on the
    reversal, so the domain refuses it early (the D-086 Q3=a pattern)
  - a non-``int`` event_id
- the replacement's SIGN is not the domain's business: the command carries no
  kind, and db/schema.sql:677 allows a negative quantity only on a
  ``correction`` - so a negative value passes through and the API test pins
  that a negative replacement on a non-correction kind reaches that CHECK as
  409 ``rule_violation``. This reading keeps 9.1's approved rule ("a strict
  positive whole quantity for every kind except correction") without
  duplicating the kind-dependent sign in Python (AGENTS.md section 5).

The module is imported lazily (D-069), like the other domain tests.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 1)


def _fix_class() -> Any:
    """The module under test does not exist yet (lazy import, see D-069)."""
    try:
        module: ModuleType = import_module("mesl_finance.assets.domain.asset_event_fix")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/assets/domain/asset_event_fix.py does not exist yet")
    return vars(module)["AssetEventFix"]


def make(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "event_id": 42,
        "quantity": 1,
        "occurred_on": DAY,
        "note": "typo, should be 1",
    }
    fields.update(overrides)
    return _fix_class().create(**fields)


def test_a_fix_holds_the_target_event_the_new_quantity_and_the_date() -> None:
    fix = make(note="typed 2 instead of 1")

    assert (fix.event_id, fix.quantity, fix.occurred_on, fix.note) == (
        42,
        1,
        DAY,
        "typed 2 instead of 1",
    )


@pytest.mark.parametrize("quantity", [10.5, "10", True])
def test_a_non_whole_quantity_is_refused(quantity: Any) -> None:
    with pytest.raises(ValidationFailed, match="whole"):
        make(quantity=quantity)


def test_a_zero_quantity_is_refused() -> None:
    with pytest.raises(ValidationFailed, match="zero"):
        make(quantity=0)


def test_a_negative_quantity_is_not_the_domains_business() -> None:
    """db/schema.sql:677 owns the sign (a correction replacement may be
    negative); the domain refuses only non-whole and zero quantities."""
    fix = make(quantity=-1)

    assert fix.quantity == -1


@pytest.mark.parametrize("note", ["", "   "])
def test_a_blank_note_is_refused(note: str) -> None:
    with pytest.raises(ValidationFailed, match="note"):
        make(note=note)


@pytest.mark.parametrize("event_id", [3.0, "3", True])
def test_a_non_integer_event_id_is_refused(event_id: object) -> None:
    with pytest.raises(ValidationFailed, match="event"):
        make(event_id=event_id)
