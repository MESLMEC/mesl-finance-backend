"""AssetEventFix value object (ROADMAP 9.2): one asset event fixed by a
reversal plus a replacement written in ONE transaction.

The schema owns the rest: the reversal must mirror the original (same
asset/kind/member/source, negated quantity - ``asset_event_guard``,
db/schema.sql:742-749), the reversal may not carry a blank note
(db/schema.sql:680) and both rows are refuse-it-once columns (:670-671). The
fix refuses only what the request itself must know: a whole-number event id,
a whole non-zero quantity (db/schema.sql:677 keeps the sign - only a
``correction`` replacement may be negative, so the sign is not duplicated
here) and a non-blank note.
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class AssetEventFix:
    """The correction the treasurer asked for, not the correction itself."""

    event_id: int
    quantity: int
    occurred_on: date
    note: str

    @classmethod
    def create(
        cls, *, event_id: int, quantity: int, occurred_on: date, note: str
    ) -> "AssetEventFix":
        if type(event_id) is not int:
            raise ValidationFailed("the event to fix must be named by a whole-number id")
        if type(quantity) is not int:
            raise ValidationFailed("the corrected quantity must be a whole number")
        if quantity == 0:
            raise ValidationFailed("a quantity cannot be zero")
        if not note.strip():
            raise ValidationFailed("a fix needs a note")
        return cls(event_id, quantity, occurred_on, note)
