from datetime import date
from typing import Protocol

from mesl_finance.assets.domain.asset import Asset, AssetView
from mesl_finance.assets.domain.asset_activity import AssetActivityRow
from mesl_finance.assets.domain.asset_event import AssetEvent, AssetEventView
from mesl_finance.assets.domain.asset_event_fix import AssetEventFix
from mesl_finance.assets.domain.asset_reads import AssetStateRow, WhoHasWhatRow
from mesl_finance.shared.ports import UnitOfWork


class AssetRepository(Protocol):
    async def list_all(self) -> list[AssetView]:
        """Every asset, in id order."""
        ...

    async def create_asset(self, asset: Asset, recorded_by: str) -> int:
        """Write a new asset; returns its id."""
        ...

    async def get(self, asset_id: int) -> AssetView | None:
        """One asset; None when the id does not exist."""
        ...

    async def save(self, asset_id: int, asset: Asset) -> AssetView | None:
        """Write an asset's labels; None when the id does not exist."""
        ...

    async def add_event(self, asset_id: int, event: AssetEvent, recorded_by: str) -> int | None:
        """Write one event; None when the asset does not exist."""
        ...


class AssetUnitOfWork(UnitOfWork, Protocol):
    """The assets' transaction scope: the shared scope plus its repository."""

    @property
    def assets(self) -> AssetRepository: ...


class FixEventRepository(Protocol):
    async def fix_event(
        self, asset_id: int, event_id: int, fix: AssetEventFix, recorded_by: str
    ) -> tuple[int, int, AssetEventView] | None:
        """Write a mirroring reversal plus a replacement in the caller's
        transaction; None when the asset or the event does not exist."""
        ...


class FixEventUnitOfWork(UnitOfWork, Protocol):
    """The fix-an-event slice's transaction scope (the D-085 pattern)."""

    @property
    def fix_events(self) -> FixEventRepository: ...


class AssetReadRepository(Protocol):
    async def asset_state(self) -> list[AssetStateRow]:
        """Every asset with its counts, in the function's name order."""
        ...

    async def who_has_what(self) -> list[WhoHasWhatRow]:
        """What members currently hold, in the view's own order."""
        ...

    async def replacement_queue(self) -> list[AssetStateRow]:
        """Admin-owned damaged items, in the function's name order."""
        ...


class AssetReadUnitOfWork(UnitOfWork, Protocol):
    """The asset reads' transaction scope (the D-085 pattern)."""

    @property
    def asset_reads(self) -> AssetReadRepository: ...


class AssetActivityRepository(Protocol):
    async def asset_activity(self, from_date: date, to_date: date) -> list[AssetActivityRow]:
        """The admin report's rows for one window, in the function's own order."""
        ...


class AssetActivityUnitOfWork(UnitOfWork, Protocol):
    """The activity read's transaction scope (the D-085 pattern)."""

    @property
    def asset_activity(self) -> AssetActivityRepository: ...
