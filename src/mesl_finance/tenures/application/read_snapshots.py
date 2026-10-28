"""The three snapshot read use cases (ROADMAP 11.1)."""

from __future__ import annotations

from collections.abc import Callable

from mesl_finance.tenures.application.ports import SnapshotUnitOfWork
from mesl_finance.tenures.domain.snapshots import (
    AssetSnapshotView,
    HoldingSnapshotView,
    MemberSnapshotView,
)


class ListMemberSnapshots:
    """Read the saved member standing at close time."""

    def __init__(self, unit_of_work: Callable[[str], SnapshotUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, tenure_id: int, actor: str) -> list[MemberSnapshotView] | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.snapshots.member_snapshots(tenure_id)


class ListAssetSnapshots:
    """Read the saved asset counts at close time."""

    def __init__(self, unit_of_work: Callable[[str], SnapshotUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, tenure_id: int, actor: str) -> list[AssetSnapshotView] | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.snapshots.asset_snapshots(tenure_id)


class ListHoldingSnapshots:
    """Read the saved who-holds-what register at close time."""

    def __init__(self, unit_of_work: Callable[[str], SnapshotUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, tenure_id: int, actor: str) -> list[HoldingSnapshotView] | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.snapshots.holding_snapshots(tenure_id)
