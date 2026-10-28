from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.assets.application.ports import AssetUnitOfWork
from mesl_finance.assets.domain.asset import Asset, AssetView


@dataclass(frozen=True)
class EditAssetCommand:
    fields: frozenset[str]
    name: str | None = None
    tag: str | None = None
    note: str | None = None
    mode: str | None = None
    ownership: str | None = None


class EditAsset:
    """Business action: change an asset's labels, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], AssetUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, asset_id: int, command: EditAssetCommand, actor: str
    ) -> AssetView | None:
        async with self._unit_of_work(actor) as uow:
            stored = await uow.assets.get(asset_id)
            if stored is None:
                return None
            asset = Asset(
                name=stored.name,
                mode=stored.mode,
                ownership=stored.ownership,
                tag=stored.tag,
                note=stored.note,
            ).edit(
                fields=command.fields,
                name=command.name,
                tag=command.tag,
                note=command.note,
                mode=command.mode,
                ownership=command.ownership,
            )
            view = await uow.assets.save(asset_id, asset)
            await uow.commit()
        return view
