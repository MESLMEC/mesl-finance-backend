from datetime import date

import pytest

from mesl_finance.ledger.domain.deposit import Deposit, DepositSource
from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 1)


def make(**overrides: object) -> Deposit:
    fields: dict[str, object] = {
        "amount": 500,
        "occurred_on": DAY,
        "source": DepositSource.SPONSORSHIP,
    }
    fields.update(overrides)
    return Deposit.create(**fields)  # type: ignore[arg-type]


def test_a_valid_deposit_is_created() -> None:
    deposit = make(note="sponsor", tag="sponsorship")
    assert deposit.amount == 500
    assert deposit.member_id is None


@pytest.mark.parametrize("amount", [0, -1])
def test_the_amount_must_be_positive(amount: int) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


def test_a_weekly_fee_needs_a_member() -> None:
    with pytest.raises(ValidationFailed, match="member"):
        make(source=DepositSource.WEEKLY_FEE)


def test_a_weekly_fee_always_goes_to_the_pool() -> None:
    with pytest.raises(ValidationFailed, match="pool"):
        make(source=DepositSource.WEEKLY_FEE, member_id=1, envelope_id=2)


def test_only_weekly_fees_are_linked_to_a_member() -> None:
    with pytest.raises(ValidationFailed, match="weekly"):
        make(source=DepositSource.DONATION, member_id=1)
