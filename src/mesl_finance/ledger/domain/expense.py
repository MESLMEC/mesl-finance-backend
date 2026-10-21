from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Expense:
    """Money going out, in whole BDT.

    The entry's shape (one negative amount, db/schema.sql:351-352), the
    non-zero line amount (db/schema.sql:270) and the overdraw guard
    (db/schema.sql:319-337) stay PostgreSQL's.
    """

    amount: int
    occurred_on: date
    envelope_id: int
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None

    @classmethod
    def create(
        cls,
        *,
        amount: int,
        occurred_on: date,
        envelope_id: int,
        note: str = "",
        tag: str | None = None,
        cost_center_id: int | None = None,
    ) -> "Expense":
        if type(amount) is not int or amount <= 0:
            raise ValidationFailed("an expense amount must be a positive whole number of taka")
        return cls(amount, occurred_on, envelope_id, note, tag, cost_center_id)
