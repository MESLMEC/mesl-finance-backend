"""The weeks a shutdown call names. Pure Python; `set_shutdown` owns the week rules."""

from dataclasses import dataclass
from datetime import date, datetime

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class ShutdownWeeks:
    """The Sundays `set_shutdown()` is called for, one row each (db/schema.sql:220-233)."""

    weeks: tuple[date, ...]
    is_shutdown: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.weeks:
            raise ValidationFailed("a shutdown call must name at least one Sunday")


@dataclass(frozen=True)
class ShutdownEventView:
    """One `shutdown_events` row as stored, for the API's answers."""

    id: int
    week_start: date
    is_shutdown: bool
    reason: str
    recorded_at: datetime
    recorded_by: str
