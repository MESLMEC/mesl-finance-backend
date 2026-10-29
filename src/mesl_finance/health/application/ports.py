"""Application ports for the health slice (ROADMAP 12.1)."""

from __future__ import annotations

from typing import Protocol

from mesl_finance.shared.ports import UnitOfWork


class HealthRepository(Protocol):
    """The database's own ``verify_all()`` problems."""

    async def problems(self) -> list[str]:
        """Every integrity problem, in the function's own order; empty = healthy."""
        ...


class HealthUnitOfWork(UnitOfWork, Protocol):
    """One transaction scope, exposing the health repository as ``.health``."""

    @property
    def health(self) -> HealthRepository: ...
