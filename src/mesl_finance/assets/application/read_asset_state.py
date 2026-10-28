"""The three asset read use cases (ROADMAP 9.3): asset state, who-has-what,
admin replacement queue.

Each read opens ONE transaction, passes the JWT actor down and NEVER commits
(the 7.5 Q9=a pattern); the slice declares its own port pair (D-085).
"""

from collections.abc import Callable

from mesl_finance.assets.application.ports import AssetReadUnitOfWork
from mesl_finance.assets.domain.asset_reads import AssetStateRow, WhoHasWhatRow


class ListAssetState:
    """Every asset with its counts, in the function's name order."""

    def __init__(self, unit_of_work: Callable[[str], AssetReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[AssetStateRow]:
        async with self._unit_of_work(actor) as uow:
            return await uow.asset_reads.asset_state()


class ListWhoHasWhat:
    """What members currently hold, in the view's own order."""

    def __init__(self, unit_of_work: Callable[[str], AssetReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[WhoHasWhatRow]:
        async with self._unit_of_work(actor) as uow:
            return await uow.asset_reads.who_has_what()


class ListReplacementQueue:
    """Admin-owned damaged items awaiting replacement, in name order."""

    def __init__(self, unit_of_work: Callable[[str], AssetReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[AssetStateRow]:
        async with self._unit_of_work(actor) as uow:
            return await uow.asset_reads.replacement_queue()
