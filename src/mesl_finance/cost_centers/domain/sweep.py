"""The sweep value object (ROADMAP 8.3).

``sweep_leftover`` (db/schema.sql:560-574) owns every rule about the numbers: a
positive leftover, a from-envelope other than the pool, an existing cost center
and envelope, and the tenure-date walls (``tx_guard``). The app validates only
what the treasurer typed: the note is required (db/schema.sql:259 makes it NOT
NULL for a sweep) and non-blank (the D-090 Q7=b pattern, a 422 before any SQL).
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Sweep:
    """The treasurer's end-of-event sweep: leftover moves back to the pool."""

    cost_center_id: int
    from_envelope_id: int
    occurred_on: date
    note: str

    def __post_init__(self) -> None:
        if not self.note.strip():
            raise ValidationFailed("a sweep needs a note")
