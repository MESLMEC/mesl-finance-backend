from typing import Any

from mesl_finance.assets.domain.asset import Asset, AssetView
from mesl_finance.assets.domain.asset_event import AssetEvent, AssetEventView
from mesl_finance.assets.domain.asset_event_fix import AssetEventFix
from mesl_finance.assets.domain.asset_reads import AssetStateRow, WhoHasWhatRow
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


class SqlFixEventRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def fix_event(
        self, asset_id: int, event_id: int, fix: AssetEventFix, recorded_by: str
    ) -> tuple[int, int, AssetEventView] | None:
        """Fix the event: a mirroring reversal plus a replacement, ONE transaction.

        The reversal mirrors the original exactly (`asset_event_guard`,
        db/schema.sql:742-749) and carries the request's note; the
        replacement re-writes the original's kind, member, source and note
        with the corrected quantity and the request's date. Whether the
        original's `ledger_transaction_id` is copied is unpinned (no rule
        decides it; db/schema.sql:673 would allow it on any `acquired` row).
        PostgreSQL owns the "only once" walls (`reverses_id`/`replaces_id`
        UNIQUE, :670-671), the sign rule (:677) and the bucket floors
        (`asset_bucket_check`, :754-775).
        """
        original = (
            (
                await self._uow.execute(
                    """
                    SELECT kind::text AS kind, quantity, member_id,
                           source::text AS source, note
                      FROM asset_events
                     WHERE id = :event_id AND asset_id = :asset_id
                    """,
                    {"event_id": event_id, "asset_id": asset_id},
                )
            )
            .mappings()
            .first()
        )
        if original is None:
            return None
        reversal = await self._uow.execute(
            """
            INSERT INTO asset_events
                   (asset_id, kind, quantity, member_id, occurred_on, recorded_by,
                    note, source, reverses_id)
            VALUES (:asset_id, :kind, :reversal_quantity, :member_id, :occurred_on,
                    :recorded_by, :note, :source, :event_id)
            RETURNING id
            """,
            {
                "asset_id": asset_id,
                "kind": original["kind"],
                "reversal_quantity": -int(original["quantity"]),
                "member_id": original["member_id"],
                "occurred_on": fix.occurred_on,
                "recorded_by": recorded_by,
                "note": fix.note,
                "source": original["source"],
                "event_id": event_id,
            },
        )
        reversal_id = int(reversal.scalar_one())
        replacement = await self._uow.execute(
            """
            INSERT INTO asset_events
                   (asset_id, kind, quantity, member_id, occurred_on, recorded_by,
                    note, source, replaces_id)
            VALUES (:asset_id, :kind, :quantity, :member_id, :occurred_on,
                    :recorded_by, :note, :source, :event_id)
            RETURNING id
            """,
            {
                "asset_id": asset_id,
                "kind": original["kind"],
                "quantity": fix.quantity,
                "member_id": original["member_id"],
                "occurred_on": fix.occurred_on,
                "recorded_by": recorded_by,
                "note": original["note"],
                "source": original["source"],
                "event_id": event_id,
            },
        )
        replacement_id = int(replacement.scalar_one())
        view = AssetEventView(
            id=replacement_id,
            asset_id=asset_id,
            kind=str(original["kind"]),
            quantity=fix.quantity,
            occurred_on=fix.occurred_on,
            note=str(original["note"]),
        )
        return replacement_id, reversal_id, view


class SqlAssetReadRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def asset_state(self) -> list[AssetStateRow]:
        """`asset_overview` (db/schema.sql:844) in its own name order."""
        result = await self._uow.execute(
            """
            SELECT asset_id, asset_name, ownership::text AS ownership,
                   mode::text AS mode, tag, stock, damaged, with_members,
                   lost, scrapped, exchanged
              FROM asset_overview
            """
        )
        return [_state_row(row) for row in result.mappings().all()]

    async def who_has_what(self) -> list[WhoHasWhatRow]:
        """`who_has_what` (db/schema.sql:845) in its own (member, asset) order."""
        result = await self._uow.execute(
            """
            SELECT asset_id, asset_name, member_id, member_name, quantity
              FROM who_has_what
            """
        )
        return [
            WhoHasWhatRow(
                asset_id=int(row["asset_id"]),
                asset_name=str(row["asset_name"]),
                member_id=int(row["member_id"]),
                member_name=str(row["member_name"]),
                quantity=int(row["quantity"]),
            )
            for row in result.mappings().all()
        ]

    async def replacement_queue(self) -> list[AssetStateRow]:
        """`admin_replacement_queue` (db/schema.sql:846-847)."""
        result = await self._uow.execute(
            """
            SELECT asset_id, asset_name, ownership::text AS ownership,
                   mode::text AS mode, tag, stock, damaged, with_members,
                   lost, scrapped, exchanged
              FROM admin_replacement_queue
            """
        )
        return [_state_row(row) for row in result.mappings().all()]


def _state_row(row: Any) -> AssetStateRow:  # RowMapping defeats Mapping[str, Any]
    return AssetStateRow(
        asset_id=int(row["asset_id"]),
        asset_name=str(row["asset_name"]),
        ownership=str(row["ownership"]),
        mode=str(row["mode"]),
        tag=row["tag"],
        stock=int(row["stock"]),
        damaged=int(row["damaged"]),
        with_members=int(row["with_members"]),
        lost=int(row["lost"]),
        scrapped=int(row["scrapped"]),
        exchanged=int(row["exchanged"]),
    )
