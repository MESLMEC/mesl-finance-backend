"""The admin report's activity numbers (ROADMAP 9.4): one read-only window.

Opens ONE transaction, passes the JWT actor and the window down and NEVER
commits (the 7.5 Q9=a / 9.3 read pattern); the slice declares its own port
pair (D-085). A reversed window is not refused here - `asset_activity`
answers no rows for it (Q5=a).
"""

from collections.abc import Callable
from datetime import date

from mesl_finance.assets.application.ports import AssetActivityUnitOfWork
from mesl_finance.assets.domain.asset_activity import AssetActivityRow


class ListAssetActivity:
    """The raw numbers for the admin report, in the function's own order."""

    def __init__(self, unit_of_work: Callable[[str], AssetActivityUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, from_date: date, to_date: date, actor: str) -> list[AssetActivityRow]:
        async with self._unit_of_work(actor) as uow:
            return await uow.asset_activity.asset_activity(from_date, to_date)
