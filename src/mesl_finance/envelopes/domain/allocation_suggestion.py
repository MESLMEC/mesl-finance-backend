"""The allocation draft read model (ROADMAP 8.1): ``allocation_suggestion``.

The database function (db/schema.sql:457-503) owns every rule: capped envelopes are
topped up in priority order, the remainder is split by the given shares or by the
proportions of the last non-voided allocation session, and anything not suggested
simply stays in the pool. This module carries the request and the row shape only.
"""

from dataclasses import dataclass

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class AllocationSuggestionQuery:
    """What the treasurer asks to split: whole taka plus optional share weights."""

    amount: int
    shares: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if type(self.amount) is not int:
            raise ValidationFailed("the amount to split must be a whole number of taka")
        if self.amount <= 0:
            raise ValidationFailed("the amount to split must be more than zero")


@dataclass(frozen=True)
class AllocationSuggestionView:
    """One ``allocation_suggestion()`` row, exactly as the function returns it."""

    envelope_id: int
    envelope_name: str
    balance: int
    target_cap: int | None
    alloc_priority: int | None
    gap: int | None
    phase: str
    suggested: int
