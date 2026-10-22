from datetime import date
from typing import Any

from mesl_finance.members.domain.member import (
    Member,
    MembershipPeriod,
    MembershipPeriodView,
    MemberView,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _member_view(row: Any) -> MemberView:
    return MemberView(
        id=int(row[0]),
        name=str(row[1]),
        batch=row[2],
        note=str(row[3]),
    )


def _period_view(row: Any) -> MembershipPeriodView:
    return MembershipPeriodView(
        id=int(row[0]),
        member_id=int(row[1]),
        start_date=row[2],
        end_date=row[3],
    )


class SqlMemberRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_all(self) -> list[MemberView]:
        result = await self._uow.execute("SELECT id, name, batch, note FROM members ORDER BY id")
        return [_member_view(row) for row in result.all()]

    async def add(self, member: Member) -> MemberView:
        result = await self._uow.execute(
            """
            INSERT INTO members (name, batch, note)
            VALUES (:name, :batch, :note)
            RETURNING id, name, batch, note
            """,
            {"name": member.name, "batch": member.batch, "note": member.note},
        )
        return _member_view(result.one())

    async def get(self, member_id: int) -> MemberView | None:
        result = await self._uow.execute(
            "SELECT id, name, batch, note FROM members WHERE id = :id",
            {"id": member_id},
        )
        row = result.first()
        return None if row is None else _member_view(row)

    async def save(self, member_id: int, member: Member) -> MemberView | None:
        result = await self._uow.execute(
            """
            UPDATE members SET name = :name, batch = :batch, note = :note
            WHERE id = :id
            RETURNING id, name, batch, note
            """,
            {"id": member_id, "name": member.name, "batch": member.batch, "note": member.note},
        )
        row = result.first()
        return None if row is None else _member_view(row)

    async def start(self, period: MembershipPeriod) -> MembershipPeriodView | None:
        exists = await self._uow.execute(
            "SELECT 1 FROM members WHERE id = :id", {"id": period.member_id}
        )
        if exists.first() is None:
            return None
        result = await self._uow.execute(
            """
            INSERT INTO membership_periods (member_id, start_date)
            VALUES (:member_id, :start_date)
            RETURNING id, member_id, start_date, end_date
            """,
            {"member_id": period.member_id, "start_date": period.start_date},
        )
        return _period_view(result.one())

    async def end(self, member_id: int, end_date: date) -> MembershipPeriodView | None:
        # The DB owns "ended once" (period_guard, db/schema.sql:210-212): address
        # the member's latest period and let PostgreSQL refuse a second end.
        latest = await self._uow.execute(
            """
            SELECT id FROM membership_periods
            WHERE member_id = :member_id
            ORDER BY id DESC
            LIMIT 1
            """,
            {"member_id": member_id},
        )
        row = latest.first()
        if row is None:
            return None
        result = await self._uow.execute(
            """
            UPDATE membership_periods SET end_date = :end_date
            WHERE id = :period_id
            RETURNING id, member_id, start_date, end_date
            """,
            {"period_id": int(row[0]), "end_date": end_date},
        )
        return _period_view(result.one())

    async def periods_for(self, member_id: int) -> list[MembershipPeriodView] | None:
        exists = await self._uow.execute("SELECT 1 FROM members WHERE id = :id", {"id": member_id})
        if exists.first() is None:
            return None
        result = await self._uow.execute(
            """
            SELECT id, member_id, start_date, end_date
            FROM membership_periods
            WHERE member_id = :member_id
            ORDER BY id
            """,
            {"member_id": member_id},
        )
        return [_period_view(row) for row in result.all()]
