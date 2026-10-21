"""Transfer value object (ROADMAP 6.4): money moving between two envelopes.

The schema's per-kind shape (two or more lines summing to zero,
db/schema.sql:353-354), the non-zero line amount (:270), the non-blank note
(:259), the overdraw guard (:319-337) and the inactive-envelope rule (:324)
stay PostgreSQL's. The domain refuses only a non-positive or non-whole amount,
a non-integer envelope reference, the same envelope on both sides and a blank
note (step 6.4 brief, Q3=a/Q5=a).
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Transfer:
    """Money moved from one envelope to another, in whole BDT."""

    amount: int
    occurred_on: date
    from_envelope_id: int
    to_envelope_id: int
    note: str
    tag: str | None = None
    cost_center_id: int | None = None

    @classmethod
    def create(
        cls,
        *,
        amount: int,
        occurred_on: date,
        from_envelope_id: int,
        to_envelope_id: int,
        note: str,
        tag: str | None = None,
        cost_center_id: int | None = None,
    ) -> "Transfer":
        if type(amount) is not int or amount <= 0:
            raise ValidationFailed("a transfer amount must be a positive whole number of taka")
        if type(from_envelope_id) is not int or type(to_envelope_id) is not int:
            raise ValidationFailed("a transfer needs two whole-number envelope ids")
        if from_envelope_id == to_envelope_id:
            raise ValidationFailed("a transfer needs two different envelopes")
        if not note.strip():
            raise ValidationFailed("a transfer needs a note")
        return cls(
            amount,
            occurred_on,
            from_envelope_id,
            to_envelope_id,
            note,
            tag,
            cost_center_id,
        )
