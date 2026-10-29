"""The health report value object (ROADMAP 12.1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthReport:
    """The database's integrity problems; none means healthy.

    The problems come from ``verify_all()`` (db/schema.sql:1180-1183), one
    `problem text` row per finding, in the function's own order.
    """

    problems: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return not self.problems
