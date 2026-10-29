"""The health read use case (ROADMAP 12.1)."""

from __future__ import annotations

from collections.abc import Callable

from mesl_finance.health.application.ports import HealthUnitOfWork


class CheckHealth:
    """Read `verify_all()` in ONE transaction, passing the actor and never committing."""

    def __init__(self, unit_of_work: Callable[[str], HealthUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[str]:
        async with self._unit_of_work(actor) as uow:
            return await uow.health.problems()
