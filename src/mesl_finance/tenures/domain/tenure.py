"""Pure-Python view of a tenure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TenureView:
    """The fields representing a tenure row."""

    id: int
    name: str
    opened_on: date
    closed_on: date | None = None
    closed_at: datetime | None = None
    closing_checksum: str | None = None
