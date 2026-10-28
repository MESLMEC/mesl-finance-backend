from typing import Protocol

from mesl_finance.assets.domain.asset import Asset, AssetView
from mesl_finance.assets.domain.asset_event import AssetEvent
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
