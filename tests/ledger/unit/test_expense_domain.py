"""Expense value object (ROADMAP 6.3): money going out, in whole BDT.

The per-kind shape ("an expense is one negative amount", db/schema.sql:351-352),
the non-zero line amount (db/schema.sql:270) and the overdraw guard
(db/schema.sql:319-337) stay PostgreSQL's; the domain only refuses an amount
that is not a positive whole number of taka.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 3)


def _expense_class() -> Any:
    """The module under test does not exist yet (lazy import, see D-069)."""
    try:
        module: ModuleType = import_module("mesl_finance.ledger.domain.expense")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/expense.py does not exist yet")
    return vars(module)["Expense"]


def make(**overrides: object) -> Any:
    fields: dict[str, object] = {"amount": 150, "occurred_on": DAY, "envelope_id": 2}
    fields.update(overrides)
    return _expense_class().create(**fields)


def test_a_valid_expense_is_created() -> None:
    expense = make(note="catering", tag="catering")

    assert expense.amount == 150
    assert expense.occurred_on == DAY
    assert expense.envelope_id == 2
    assert (expense.note, expense.tag) == ("catering", "catering")


@pytest.mark.parametrize("amount", [0, -1])
def test_the_amount_must_be_positive(amount: int) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


@pytest.mark.parametrize("amount", [10.5, "100", True])
def test_a_non_int_amount_is_refused(amount: object) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)
