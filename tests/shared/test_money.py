"""Tests for src/mesl_finance/shared/money.py (roadmap step 2.1).

Approved in the step 2.1 brief (2026-10-20, user answers 1a/2a/3b/4a):
a whole-BDT `int` value object, never floats. Non-negative, zero allowed.
Construction accepts only a real `int` (bool rejected even though it is an
int subclass). No arithmetic operators: PostgreSQL owns the sums; equality
is dataclass value equality only.
"""

from decimal import Decimal

import pytest

from mesl_finance.shared.errors import ValidationFailed
from mesl_finance.shared.money import Money


def test_money_is_built_from_a_positive_int() -> None:
    assert Money(500).amount == 500


def test_zero_is_a_valid_amount() -> None:
    assert Money(0).amount == 0


def test_a_negative_amount_is_refused() -> None:
    with pytest.raises(ValidationFailed):
        Money(-1)


@pytest.mark.parametrize("value", [1.50, True, False, "500", Decimal("1"), Decimal("1.00")])
def test_only_a_real_int_is_accepted(value: object) -> None:
    with pytest.raises(ValidationFailed):
        Money(value)  # type: ignore[arg-type]


def test_equality_is_value_equality_with_no_ordering_behaviour() -> None:
    assert Money(500) == Money(500)
    assert Money(500) != Money(501)
    assert Money(0) != Money(500)


def test_repr_shows_the_type_and_the_amount() -> None:
    shown = repr(Money(500))
    assert "Money" in shown
    assert "500" in shown
