from collections.abc import Callable

from mesl_finance.assets.application.ports import AssetUnitOfWork
from mesl_finance.assets.domain.asset import AssetView


class ListAssets:
    """Business action: the treasurer's asset list (no counts; 9.3 owns reads)."""

    def __init__(self, unit_of_work: Callable[[str], AssetUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[AssetView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.assets.list_all()
