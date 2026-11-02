from datetime import date
from typing import Any

from mesl_finance.assets.domain.asset import Asset, AssetView
from mesl_finance.assets.domain.asset_activity import AssetActivityRow
from mesl_finance.assets.domain.asset_event import AssetEvent, AssetEventView
from mesl_finance.assets.domain.asset_event_fix import AssetEventFix
from mesl_finance.assets.domain.asset_reads import AssetStateRow, WhoHasWhatRow
from mesl_finance.shared.errors import UnknownReference, ValidationFailed
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

    async def _check_purchase_link(self, link: int) -> None:
        """Name the error before the FK can (see `add_event`'s docstring)."""
        row = (
            (
                await self._uow.execute(
                    """
                SELECT x.kind::text AS kind, x.tenure_id,
                       EXISTS (SELECT 1 FROM ledger_transactions r
                                WHERE r.reverses_id = x.id) AS voided
                  FROM ledger_transactions x
                 WHERE x.id = :link
                """,
                    {"link": link},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise UnknownReference(f"ledger entry {link} does not exist")
        kind = str(row["kind"])
        if kind != "expense":
            raise ValidationFailed(
                f"the payment must be an expense; ledger entry {link} is a {kind}"
            )
        if bool(row["voided"]):
            raise ValidationFailed(
                f"ledger entry {link} has been corrected away; name the entry that replaced it"
            )
        tenure = (await self._uow.execute("SELECT id FROM tenures WHERE closed_on IS NULL")).first()
        if tenure is not None and int(row["tenure_id"]) != int(tenure[0]):
            raise ValidationFailed(
                f"the payment must belong to the open tenure; ledger entry {link} does not"
            )

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
        """Write one event; None when the asset does not exist.

        Issue #10: a payment named by a purchase is validated first, so the
        app can answer by the error's real name before PostgreSQL's FK
        (db/schema.sql:669) is reached. The named entry must EXIST
        (`unknown_reference`), be an EXPENSE of the open tenure and not have
        been corrected away (both `validation_failed`; `entries.is_voided`,
        db/schema.sql:423, is the definition). With no link there is nothing
        to check, so no extra query runs.
        """
        exists = await self._uow.execute("SELECT 1 FROM assets WHERE id = :id", {"id": asset_id})
        if exists.first() is None:
            return None
        if event.ledger_transaction_id is not None:
            await self._check_purchase_link(event.ledger_transaction_id)
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
                           source::text AS source, note, ledger_transaction_id
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
        event_link = (
            None
            if original["ledger_transaction_id"] is None
            else int(original["ledger_transaction_id"])
        )
        reversal = await self._uow.execute(
            """
            INSERT INTO asset_events
                   (asset_id, kind, quantity, member_id, occurred_on, recorded_by,
                    note, source, ledger_transaction_id, reverses_id)
            VALUES (:asset_id, :kind, :reversal_quantity, :member_id, :occurred_on,
                    :recorded_by, :note, :source, :ledger_transaction_id, :event_id)
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
                "ledger_transaction_id": event_link,
                "event_id": event_id,
            },
        )
        reversal_id = int(reversal.scalar_one())
        replacement = await self._uow.execute(
            """
            INSERT INTO asset_events
                   (asset_id, kind, quantity, member_id, occurred_on, recorded_by,
                    note, source, ledger_transaction_id, replaces_id)
            VALUES (:asset_id, :kind, :quantity, :member_id, :occurred_on,
                    :recorded_by, :note, :source, :ledger_transaction_id, :event_id)
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
                "ledger_transaction_id": event_link,
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
            ledger_transaction_id=event_link,
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


class SqlAssetActivityRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def asset_activity(self, from_date: date, to_date: date) -> list[AssetActivityRow]:
        """`asset_activity(p_from, p_to)` (db/schema.sql:849-858), its own order."""
        result = await self._uow.execute(
            """
            SELECT asset_name, ownership::text AS ownership, kind::text AS kind,
                   source::text AS source, units, events
              FROM asset_activity(CAST(:from_date AS date), CAST(:to_date AS date))
            """,
            {"from_date": from_date, "to_date": to_date},
        )
        return [
            AssetActivityRow(
                asset_name=str(row["asset_name"]),
                ownership=str(row["ownership"]),
                kind=str(row["kind"]),
                source=None if row["source"] is None else str(row["source"]),
                units=int(row["units"]),
                events=int(row["events"]),
            )
            for row in result.mappings().all()
        ]
