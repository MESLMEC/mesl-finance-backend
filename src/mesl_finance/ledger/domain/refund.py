"""A refund: one member-linked expense, in whole BDT (ROADMAP 7.4).

`check_shape` (db/schema.sql:364-367) forces every member-linked deposit or
expense through the Unallocated General pool, and `member_link_kinds` (:260)
allows `member_id` on an `expense`; both rules stay PostgreSQL's, so the
adapter resolves the pool and writes the one negative line. The domain only
refuses an amount that is not a positive whole number of taka.
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Refund:
    """Money returned to one member, out of the pool."""

    member_id: int
    amount: int
    occurred_on: date
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None

    @classmethod
    def create(
        cls,
        *,
        member_id: int,
        amount: int,
        occurred_on: date,
        note: str = "",
        tag: str | None = None,
        cost_center_id: int | None = None,
    ) -> "Refund":
        if type(amount) is not int or amount <= 0:
            raise ValidationFailed("a refund amount must be a positive whole number of taka")
        return cls(member_id, amount, occurred_on, note, tag, cost_center_id)
