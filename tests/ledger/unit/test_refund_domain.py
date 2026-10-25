"""Refund value object (ROADMAP 7.4): a member-linked expense, in whole BDT.

Approved contract (step 7.4 brief, Q1-Q7 = a): a refund names the member who
gets the money back and has NO envelope field, because `check_shape`
(db/schema.sql:364-367) forces every member-linked deposit/expense through the
Unallocated General pool; the adapter resolves that pool itself. Note, tag and
cost center are optional. PostgreSQL owns the member link
(`member_link_kinds`, :260) and the pool rule; the domain only refuses an amount
that is not a positive whole number of taka.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 3)


def _refund_class() -> Any:
    """The module under test does not exist yet (lazy import, see D-069)."""
    try:
        module: ModuleType = import_module("mesl_finance.ledger.domain.refund")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/refund.py does not exist yet")
    return vars(module)["Refund"]


def make(**overrides: object) -> Any:
    fields: dict[str, object] = {"member_id": 1, "amount": 60, "occurred_on": DAY}
    fields.update(overrides)
    return _refund_class().create(**fields)


def test_a_refund_keeps_its_values() -> None:
    refund = make(note="refund of credit", tag="refund", cost_center_id=3)

    assert (refund.member_id, refund.amount, refund.occurred_on) == (1, 60, DAY)
    assert (refund.note, refund.tag, refund.cost_center_id) == ("refund of credit", "refund", 3)


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
def test_a_refund_amount_must_be_a_positive_whole_number(amount: object) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)
