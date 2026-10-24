"""A shutdown-week range. Pure Python; `set_shutdown` owns the week rules."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ShutdownRange:
    """The range `set_shutdown()` receives (db/schema.sql:220-233)."""

    from_week: date
    to_week: date
    is_shutdown: bool = True
    reason: str = ""


@dataclass(frozen=True)
class ShutdownEventView:
    """One `shutdown_events` row as stored, for the API's answers."""

    id: int
    week_start: date
    is_shutdown: bool
    reason: str
    recorded_at: datetime
    recorded_by: str
