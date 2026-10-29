"""SQL transaction scope for the health slice."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.health.infrastructure.repository import SqlHealthRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlHealthUnitOfWork(SqlUnitOfWork):
    """One transaction scope carrying the health repository."""

    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.health = SqlHealthRepository(self)
