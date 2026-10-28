"""Pure-Python view of a tenure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TenureView:
    """The fields returned by `close_tenure`, read back from the new row."""

    id: int
    name: str
    opened_on: date
