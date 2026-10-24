"""Member adjustment value objects. Pure Python.

The kind-specific signs (`waiver > 0`, `credit_donation < 0`), the non-zero
amount and the closed-tenure date rule stay in PostgreSQL (db/schema.sql:133-140,
185-191); only the blank-note rule the app refuses first (step 7.3 Q4=c) lives
here.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from mesl_finance.shared.errors import ValidationFailed


class AdjustmentKind(StrEnum):
    """The `adjustment_kind` enum (db/schema.sql:128)."""

    WAIVER = "waiver"
    CREDIT_DONATION = "credit_donation"
    OPENING = "opening"
    CORRECTION = "correction"


@dataclass(frozen=True)
class MemberAdjustment:
    """One adjustment as the treasurer enters it (db/schema.sql:129-141)."""

    member_id: int
    kind: AdjustmentKind
    amount: int
    occurred_on: date
    note: str = ""

    def __post_init__(self) -> None:
        if type(self.member_id) is not int:
            raise ValidationFailed("a member id must be a whole number")
        if type(self.amount) is not int:
            raise ValidationFailed("an adjustment amount must be a whole number of taka")
        if self.kind in (AdjustmentKind.WAIVER, AdjustmentKind.CORRECTION) and not (
            self.note.strip()
        ):
            raise ValidationFailed(f"a {self.kind} needs a note")


@dataclass(frozen=True)
class AdjustmentView:
    """One stored adjustment, for the API's answers (db/schema.sql:129-141)."""

    id: int
    member_id: int
    kind: str
    amount: int
    occurred_on: date
    note: str
    recorded_at: datetime
    recorded_by: str
