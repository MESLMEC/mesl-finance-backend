from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.domain.entry import IncomeSource
from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Deposit:
    """Money coming in, in whole BDT.

    A weekly fee belongs to one member and always lands in the pool.
    """

    amount: int
    occurred_on: date
    source: IncomeSource
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None
    member_id: int | None = None
    envelope_id: int | None = None  # None = the Unallocated General pool

    @classmethod
    def create(
        cls,
        *,
        amount: int,
        occurred_on: date,
        source: IncomeSource,
        note: str = "",
        tag: str | None = None,
        cost_center_id: int | None = None,
        member_id: int | None = None,
        envelope_id: int | None = None,
    ) -> "Deposit":
        if amount <= 0:
            raise ValidationFailed("a deposit amount must be a positive whole number of taka")
        if source is IncomeSource.WEEKLY_FEE:
            if member_id is None:
                raise ValidationFailed("a weekly fee must name the member who paid")
            if envelope_id is not None:
                raise ValidationFailed(
                    "a weekly fee always goes to the pool; do not name an envelope"
                )
        elif member_id is not None:
            raise ValidationFailed("only weekly fees are linked to a member")
        return cls(amount, occurred_on, source, note, tag, cost_center_id, member_id, envelope_id)
