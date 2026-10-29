"""SQL adapter for the health slice (ROADMAP 12.1)."""

from __future__ import annotations

from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlHealthRepository:
    """Runs the database's own ``verify_all()`` function."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def problems(self) -> list[str]:
        result = await self._uow.execute("SELECT problem FROM verify_all()")
        return [str(problem) for problem in result.scalars().all()]
