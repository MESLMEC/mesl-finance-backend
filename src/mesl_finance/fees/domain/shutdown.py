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


@dataclass(frozen=True)
class ShutdownStateView:
    """One currently shut week: the latest `shutdown_events` row of the open tenure.

    The latest-wins rule and the open-tenure scope are PostgreSQL's
    (db/schema.sql:117,177-183,594-595); this holds the API's answer only.
    """

    week_start: date
    event_id: int
    reason: str
    recorded_at: datetime
    recorded_by: str
