"""The allocation confirmation value object (ROADMAP 8.2).

The database function ``allocate`` (db/schema.sql:505-534) owns every rule about
the numbers: an object of positive whole taka, no pool target, no zero entry, an
active envelope, enough money in the pool and a non-blank note. The app validates
only that the JSON amounts are whole numbers (step 8.2 Q4=a: a thin app), so this
module carries the request and nothing else.
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class AllocationDecision:
    """The treasurer's confirmed split: whole taka per envelope id, as JSON keys."""

    occurred_on: date
    note: str
    amounts: dict[str, int]

    def __post_init__(self) -> None:
        for amount in self.amounts.values():
            if type(amount) is not int:
                raise ValidationFailed("an allocation amount must be a whole number of taka")
