"""Use cases for reading tenure records."""

from __future__ import annotations

from collections.abc import Callable

from mesl_finance.tenures.application.ports import TenureUnitOfWork
from mesl_finance.tenures.domain.tenure import TenureView


class GetOpenTenure:
    """Read the single open tenure, or None if no tenure is open."""

    def __init__(self, unit_of_work: Callable[[str], TenureUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> TenureView | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.tenures.get_open()


class ListTenures:
    """Read all tenures ordered by id."""

    def __init__(self, unit_of_work: Callable[[str], TenureUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[TenureView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.tenures.list_all()
