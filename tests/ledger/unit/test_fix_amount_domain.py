"""AmountFix value object (ROADMAP 6.5): one entry's amount fixed by a
reversal plus a replacement written in ONE transaction.

Approved step brief (Q2=a naming, Q3=c, Q1=a, Q6=a): the fix carries the
target entry id, the NEW positive whole-BDT amount, an occurred_on date and a
non-blank note. The schema's reversal CHECK (db/schema.sql:259) forbids a
blank note on a reversal anyway, so the domain refuses one early as 422
``validation_failed`` (same pattern as the transfer note, D-086 Q3=a).
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 10, 20)


def _amount_fix_class() -> Any:
    """The module under test does not exist yet (lazy import, see D-069)."""
    try:
        module: ModuleType = import_module("mesl_finance.ledger.domain.fix_amount")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/fix_amount.py does not exist yet")
    return vars(module)["AmountFix"]


def make(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "entry_id": 42,
        "amount": 600,
        "occurred_on": DAY,
        "note": "typo in amount",
    }
    fields.update(overrides)
    return _amount_fix_class().create(**fields)


def test_a_fix_holds_the_target_entry_the_new_amount_and_the_date() -> None:
    fix = make(note="typed 500 instead of 600")

    assert (fix.entry_id, fix.amount, fix.occurred_on, fix.note) == (
        42,
        600,
        DAY,
        "typed 500 instead of 600",
    )


@pytest.mark.parametrize("amount", [0, -1])
def test_a_zero_or_negative_amount_is_refused(amount: int) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


@pytest.mark.parametrize("amount", [10.5, "600", True])
def test_a_non_integer_amount_is_refused(amount: object) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


@pytest.mark.parametrize("entry_id", [3.0, "3", True])
def test_a_non_integer_entry_id_is_refused(entry_id: object) -> None:
    with pytest.raises(ValidationFailed, match="entry"):
        make(entry_id=entry_id)


@pytest.mark.parametrize("note", ["", "   "])
def test_a_blank_note_is_refused(note: str) -> None:
    with pytest.raises(ValidationFailed, match="note"):
        make(note=note)
