"""AmountFix value object (ROADMAP 6.5): one entry's amount fixed by a reversal
plus a replacement written in ONE transaction.

The schema owns the rest: a reversal must exactly mirror the original entry's
lines (db/schema.sql:357-363), carry the same member (:310-312) and sit in the
same tenure (:307); reversal and replacement are both refuse-it-once columns
(:255-256). The fix refuses only what the request itself must know: a
whole-number entry id, a positive whole-BDT new amount and a non-blank note
(a blank reversal note is refused by the CHECK at db/schema.sql:259 anyway).
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class AmountFix:
    """The correction the treasurer asked for, not the correction itself."""

    entry_id: int
    amount: int
    occurred_on: date
    note: str

    @classmethod
    def create(cls, *, entry_id: int, amount: int, occurred_on: date, note: str) -> "AmountFix":
        if type(entry_id) is not int:
            raise ValidationFailed("the entry to fix must be named by a whole-number id")
        if type(amount) is not int or amount <= 0:
            raise ValidationFailed("the corrected amount must be a positive whole number of taka")
        if not note.strip():
            raise ValidationFailed("a fix needs a note")
        return cls(entry_id, amount, occurred_on, note)
