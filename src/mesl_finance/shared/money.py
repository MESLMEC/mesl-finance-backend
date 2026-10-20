"""Money as a whole-BDT ``int`` value object. Never floats.

Non-negative: zero is valid (a balance or leftover can be zero), negative
money does not exist — direction (income/expense) belongs to the entry, not
the amount. No arithmetic operators: PostgreSQL owns the sums; if a step ever
needs one in Python, it is added in that step together with its test.
"""

from dataclasses import dataclass

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Money:
    """A whole number of BDT."""

    amount: int

    def __post_init__(self) -> None:
        if type(self.amount) is not int:
            raise ValidationFailed("money must be a whole number of taka")
        if self.amount < 0:
            raise ValidationFailed("money cannot be negative")
