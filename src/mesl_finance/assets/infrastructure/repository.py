from typing import Any

from mesl_finance.assets.domain.asset import Asset, AssetView
from mesl_finance.assets.domain.asset_event import AssetEvent
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _asset_view(row: Any) -> AssetView:
    return AssetView(
        id=int(row[0]),
        name=str(row[1]),
        mode=str(row[2]),
        ownership=str(row[3]),
        tag=row[4],
        note=str(row[5]),
    )


class SqlAssetRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_all(self) -> list[AssetView]:
        result = await self._uow.execute(
            """
            SELECT id, name, mode::text, ownership::text, tag, note
            FROM assets
            ORDER BY id
            """
        )
        return [_asset_view(row) for row in result.all()]

    async def create_asset(self, asset: Asset, recorded_by: str) -> int:
        result = await self._uow.execute(
            """
            INSERT INTO assets (name, mode, ownership, tag, note)
            VALUES (:name, :mode, :ownership, :tag, :note)
            RETURNING id
            """,
            {
                "name": asset.name,
                "mode": asset.mode,
                "ownership": asset.ownership,
                "tag": asset.tag,
                "note": asset.note,
            },
        )
        return int(result.scalar_one())

    async def get(self, asset_id: int) -> AssetView | None:
        result = await self._uow.execute(
            """
            SELECT id, name, mode::text, ownership::text, tag, note
            FROM assets
            WHERE id = :id
            """,
            {"id": asset_id},
        )
        row = result.first()
        return None if row is None else _asset_view(row)

    async def save(self, asset_id: int, asset: Asset) -> AssetView | None:
        result = await self._uow.execute(
            """
            UPDATE assets
            SET name = :name, tag = :tag, note = :note, mode = :mode, ownership = :ownership
            WHERE id = :id
            RETURNING id, name, mode::text, ownership::text, tag, note
            """,
            {
                "id": asset_id,
                "name": asset.name,
                "tag": asset.tag,
                "note": asset.note,
                "mode": asset.mode,
                "ownership": asset.ownership,
            },
        )
        row = result.first()
        return None if row is None else _asset_view(row)

    async def add_event(self, asset_id: int, event: AssetEvent, recorded_by: str) -> int | None:
        exists = await self._uow.execute("SELECT 1 FROM assets WHERE id = :id", {"id": asset_id})
        if exists.first() is None:
            return None
        result = await self._uow.execute(
            """
            INSERT INTO asset_events
                (asset_id, kind, quantity, member_id, occurred_on, recorded_by, note,
                 source, ledger_transaction_id)
            VALUES (:asset_id, :kind, :quantity, :member_id, :occurred_on, :recorded_by,
                    :note, :source, :ledger_transaction_id)
            RETURNING id
            """,
            {
                "asset_id": asset_id,
                "kind": event.kind,
                "quantity": event.quantity,
                "member_id": event.member_id,
                "occurred_on": event.occurred_on,
                "recorded_by": recorded_by,
                "note": event.note,
                "source": event.source,
                "ledger_transaction_id": event.ledger_transaction_id,
            },
        )
        return int(result.scalar_one())
