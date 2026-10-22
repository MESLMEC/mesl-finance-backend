from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import LabelEditUnitOfWork
from mesl_finance.ledger.domain.entry import IncomeSource
from mesl_finance.ledger.domain.label_edit import LabelEdit, LabelView


@dataclass(frozen=True)
class EditLabelsCommand:
    entry_id: int
    fields: frozenset[str]
    note: str | None = None
    tag: str | None = None
    cost_center_id: int | None = None
    occurred_on: date | None = None
    source: IncomeSource | None = None


class EditLabels:
    """Business action: fix one entry's labels in place, in ONE transaction.

    No open tenure is asked for: the database's `tx_label_edit` resolves the
    entry's own tenure and refuses a closed one itself.
    """

    def __init__(self, unit_of_work: Callable[[str], LabelEditUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: EditLabelsCommand, actor: str) -> LabelView:
        edit = LabelEdit.create(
            entry_id=command.entry_id,
            fields=command.fields,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
            occurred_on=command.occurred_on,
            source=command.source,
        )
        async with self._unit_of_work(actor) as uow:
            view = await uow.ledger.edit_labels(edit)
            await uow.commit()
        return view
