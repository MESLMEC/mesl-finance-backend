from typing import Any

from mesl_finance.fees.domain.dues import StandingView
from mesl_finance.fees.domain.fee_rate import FeeRate, FeeRateView
from mesl_finance.fees.domain.shutdown import (
    ShutdownEventView,
    ShutdownStateView,
    ShutdownWeeks,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _rate_view(row: Any) -> FeeRateView:
    return FeeRateView(
        id=int(row[0]),
        effective_from=row[1],
        amount=int(row[2]),
        recorded_at=row[3],
        recorded_by=str(row[4]),
    )


def _event_view(row: Any) -> ShutdownEventView:
    return ShutdownEventView(
        id=int(row[0]),
        week_start=row[1],
        is_shutdown=bool(row[2]),
        reason=str(row[3]),
        recorded_at=row[4],
        recorded_by=str(row[5]),
    )


def _state_view(row: Any) -> ShutdownStateView:
    return ShutdownStateView(
        week_start=row[0],
        event_id=int(row[1]),
        reason=str(row[2]),
        recorded_at=row[3],
        recorded_by=str(row[4]),
    )


class SqlFeeRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def add_rate(self, rate: FeeRate, recorded_by: str) -> FeeRateView:
        result = await self._uow.execute(
            """
            INSERT INTO fee_rates (effective_from, amount, recorded_by)
            VALUES (:effective_from, :amount, :recorded_by)
            RETURNING id, effective_from, amount, recorded_at, recorded_by
            """,
            {
                "effective_from": rate.effective_from,
                "amount": rate.amount,
                "recorded_by": recorded_by,
            },
        )
        return _rate_view(result.one())

    async def list_rates(self) -> list[FeeRateView]:
        result = await self._uow.execute(
            """
            SELECT id, effective_from, amount, recorded_at, recorded_by
            FROM fee_rates
            ORDER BY effective_from, id
            """
        )
        return [_rate_view(row) for row in result.all()]

    async def set_shutdown(self, shutdown: ShutdownWeeks, recorded_by: str) -> int:
        # One schema call per named Sunday, all in the caller's transaction; the Sunday
        # and tenure rules stay PostgreSQL's (db/schema.sql:220-233, 177-183).
        weeks = 0
        for week in shutdown.weeks:
            result = await self._uow.execute(
                """
                SELECT set_shutdown(:week, :week, :is_shutdown, :recorded_by, :reason) AS weeks
                """,
                {
                    "week": week,
                    "is_shutdown": shutdown.is_shutdown,
                    "recorded_by": recorded_by,
                    "reason": shutdown.reason,
                },
            )
            weeks += int(result.one()[0])
        return weeks

    async def list_shutdown_events(self) -> list[ShutdownEventView]:
        result = await self._uow.execute(
            """
            SELECT id, week_start, is_shutdown, reason, recorded_at, recorded_by
            FROM shutdown_events
            ORDER BY week_start, id
            """
        )
        return [_event_view(row) for row in result.all()]


class SqlShutdownStateRepository:
    """The current shutdown state (issue #15 step 2): latest row per week, open tenure.

    The latest-wins subquery is the schema's own rule (db/schema.sql:594-595), and
    ``open_tenure_start()`` (:54-60) is the same wall ``shutdown_guard`` (:177-183)
    uses, so a closed tenure's weeks can never appear.
    """

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_current(self) -> list[ShutdownStateView]:
        result = await self._uow.execute(
            """
            SELECT s.week_start, s.id, s.reason, s.recorded_at, s.recorded_by
            FROM shutdown_events s
            WHERE s.week_start >= open_tenure_start()
              AND s.is_shutdown
              AND s.id = (
                  SELECT latest.id FROM shutdown_events latest
                  WHERE latest.week_start = s.week_start
                  ORDER BY latest.id DESC
                  LIMIT 1
              )
            ORDER BY s.week_start
            """
        )
        return [_state_view(row) for row in result.all()]


def _standing_view(row: Any) -> StandingView:
    return StandingView(
        member_id=int(row[0]),
        member_name=str(row[1]),
        is_member_now=bool(row[2]),
        weeks_owed=int(row[3]),
        owed=int(row[4]),
        credits=int(row[5]),
        balance=int(row[6]),
        weeks_overdue=int(row[7]),
        oldest_unpaid_week=row[8],
    )


class SqlDuesRepository:
    """The dues read: ``dues_overview`` as it stands (step 7.5 Q4=a)."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_dues(self) -> list[StandingView]:
        # The view owns the order (weeks_overdue DESC, who_name; db/schema.sql:627-628).
        result = await self._uow.execute(
            """
            SELECT who_id, who_name, is_member_now, weeks_owed, owed, credits,
                   balance, weeks_overdue, oldest_unpaid_week
            FROM dues_overview
            """
        )
        return [_standing_view(row) for row in result.all()]
