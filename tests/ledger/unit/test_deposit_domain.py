from datetime import date
from importlib import import_module
from typing import Any

import pytest

from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 1)


def _income_source() -> Any:
    """The one income-source enum (step 6.1 Q2=a); imported lazily, see D-069."""
    try:
        module = import_module("mesl_finance.ledger.domain.entry")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/entry.py does not exist yet")
    return vars(module)["IncomeSource"]


def make(**overrides: object) -> Deposit:
    fields: dict[str, object] = {
        "amount": 500,
        "occurred_on": DAY,
        "source": _income_source().SPONSORSHIP,
    }
    fields.update(overrides)
    return Deposit.create(**fields)  # type: ignore[arg-type]


def test_a_valid_deposit_is_created() -> None:
    deposit = make(note="sponsor", tag="sponsorship")
    assert deposit.amount == 500
    assert deposit.member_id is None


def test_a_non_weekly_deposit_may_name_an_envelope() -> None:
    deposit = make(source=_income_source().DONATION, envelope_id=2)

    assert deposit.envelope_id == 2
    assert deposit.member_id is None


@pytest.mark.parametrize("amount", [0, -1])
def test_the_amount_must_be_positive(amount: int) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


def test_a_weekly_fee_needs_a_member() -> None:
    with pytest.raises(ValidationFailed, match="member"):
        make(source=_income_source().WEEKLY_FEE)


def test_a_weekly_fee_always_goes_to_the_pool() -> None:
    with pytest.raises(ValidationFailed, match="pool"):
        make(source=_income_source().WEEKLY_FEE, member_id=1, envelope_id=2)


def test_only_weekly_fees_are_linked_to_a_member() -> None:
    with pytest.raises(ValidationFailed, match="weekly"):
        make(source=_income_source().DONATION, member_id=1)
