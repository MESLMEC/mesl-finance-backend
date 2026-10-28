"""The CloseTenure use case: close the open tenure, save snapshots, open the next.

Approved brief: Q2=a request `{close_on, next_name}`, response `201
{"id","name","opened_on"}` read back from the new tenure; Q5=a a THIN app -
PostgreSQL's `close_tenure` (db/schema.sql:910-938) owns every rule.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.tenures.application.ports import TenureUnitOfWork
from mesl_finance.tenures.domain.tenure import TenureView


@dataclass(frozen=True)
class CloseTenureCommand:
    """What the treasurer enters to hand over to the next committee."""

    close_on: date
    next_name: str


class CloseTenure:
    """Business action: close one tenure and open the next, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], TenureUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CloseTenureCommand, actor: str) -> TenureView:
        async with self._unit_of_work(actor) as uow:
            view = await uow.tenures.close(
                close_on=command.close_on,
                next_name=command.next_name,
                recorded_by=actor,
            )
            await uow.commit()
        return view
