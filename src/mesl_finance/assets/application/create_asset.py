from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.assets.application.ports import AssetUnitOfWork
from mesl_finance.assets.domain.asset import Asset, AssetView


@dataclass(frozen=True)
class CreateAssetCommand:
    name: str
    mode: str
    ownership: str
    tag: str | None = None
    note: str = ""


class CreateAsset:
    """Business action: add an asset record, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], AssetUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CreateAssetCommand, actor: str) -> AssetView:
        asset = Asset.create(
            name=command.name,
            mode=command.mode,
            ownership=command.ownership,
            tag=command.tag,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            asset_id = await uow.assets.create_asset(asset, actor)
            await uow.commit()
        return AssetView(
            id=asset_id,
            name=asset.name,
            mode=asset.mode,
            ownership=asset.ownership,
            tag=asset.tag,
            note=asset.note,
        )
