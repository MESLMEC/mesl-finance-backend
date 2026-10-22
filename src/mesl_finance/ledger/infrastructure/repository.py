from typing import Any

from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource
from mesl_finance.ledger.domain.expense import Expense
from mesl_finance.ledger.domain.fix_amount import AmountFix
from mesl_finance.ledger.domain.label_edit import LabelEdit, LabelView
from mesl_finance.ledger.domain.transfer import Transfer
from mesl_finance.shared.errors import (
    NoOpenTenure,
    UnknownReference,
    ValidationFailed,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlLedgerRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def open_tenure_id(self) -> int:
        row = (await self._uow.execute("SELECT id FROM tenures WHERE closed_on IS NULL")).first()
        if row is None:
            raise NoOpenTenure("there is no open tenure; the owner must create one first")
        return int(row[0])

    async def add_deposit(self, tenure_id: int, deposit: Deposit, recorded_by: str) -> int:
        header = await self._uow.execute(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, tag,
                    cost_center_id, source, member_id)
            VALUES (:tenure_id, 'deposit', :occurred_on, :recorded_by, :note, :tag,
                    :cost_center_id, :source, :member_id)
            RETURNING id
            """,
            {
                "tenure_id": tenure_id,
                "occurred_on": deposit.occurred_on,
                "recorded_by": recorded_by,
                "note": deposit.note,
                "tag": deposit.tag,
                "cost_center_id": deposit.cost_center_id,
                "source": deposit.source.value,
                "member_id": deposit.member_id,
            },
        )
        entry_id = int(header.scalar_one())
        await self._uow.execute(
            """
            INSERT INTO ledger_lines (transaction_id, envelope_id, amount)
            SELECT CAST(:entry_id AS bigint),
                   COALESCE(CAST(:envelope_id AS bigint), (SELECT id FROM envelopes WHERE is_pool)),
                   CAST(:amount AS integer)
            """,
            {"entry_id": entry_id, "envelope_id": deposit.envelope_id, "amount": deposit.amount},
        )
        return entry_id

    async def add_expense(
        self, tenure_id: int, expense: Expense, recorded_by: str
    ) -> tuple[int, int]:
        # The schema's `line_guard` (BEFORE INSERT) runs before the foreign key, so a
        # missing envelope would surface as P0001 "would drop below zero"; name it
        # correctly as an unknown reference (step 6.3 Q, approved 2026-10-21).
        envelope = await self._uow.execute(
            "SELECT id FROM envelopes WHERE id = :envelope_id",
            {"envelope_id": expense.envelope_id},
        )
        if envelope.first() is None:
            raise UnknownReference(f"envelope {expense.envelope_id} does not exist")
        header = await self._uow.execute(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, tag, cost_center_id)
            VALUES (:tenure_id, 'expense', :occurred_on, :recorded_by, :note, :tag,
                    :cost_center_id)
            RETURNING id
            """,
            {
                "tenure_id": tenure_id,
                "occurred_on": expense.occurred_on,
                "recorded_by": recorded_by,
                "note": expense.note,
                "tag": expense.tag,
                "cost_center_id": expense.cost_center_id,
            },
        )
        entry_id = int(header.scalar_one())
        await self._uow.execute(
            """
            INSERT INTO ledger_lines (transaction_id, envelope_id, amount)
            VALUES (CAST(:entry_id AS bigint), CAST(:envelope_id AS bigint),
                    CAST(:amount AS integer))
            """,
            {"entry_id": entry_id, "envelope_id": expense.envelope_id, "amount": -expense.amount},
        )
        balance = await self._uow.execute(
            "SELECT balance FROM envelope_balances WHERE id = :envelope_id",
            {"envelope_id": expense.envelope_id},
        )
        return entry_id, int(balance.scalar_one())

    async def add_transfer(
        self, tenure_id: int, transfer: Transfer, recorded_by: str
    ) -> tuple[int, int, int]:
        # `line_guard` is BEFORE INSERT and preempts the FK: a missing source would
        # say "would drop below zero" (D-084). Name an unknown envelope correctly.
        for envelope_id in (transfer.from_envelope_id, transfer.to_envelope_id):
            row = await self._uow.execute(
                "SELECT id FROM envelopes WHERE id = :envelope_id",
                {"envelope_id": envelope_id},
            )
            if row.first() is None:
                raise UnknownReference(f"envelope {envelope_id} does not exist")
        header = await self._uow.execute(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, tag, cost_center_id)
            VALUES (:tenure_id, 'transfer', :occurred_on, :recorded_by, :note, :tag,
                    :cost_center_id)
            RETURNING id
            """,
            {
                "tenure_id": tenure_id,
                "occurred_on": transfer.occurred_on,
                "recorded_by": recorded_by,
                "note": transfer.note,
                "tag": transfer.tag,
                "cost_center_id": transfer.cost_center_id,
            },
        )
        entry_id = int(header.scalar_one())
        await self._uow.execute(
            """
            INSERT INTO ledger_lines (transaction_id, envelope_id, amount)
            VALUES (CAST(:entry_id AS bigint), CAST(:from_envelope_id AS bigint),
                    CAST(:out_amount AS integer)),
                   (CAST(:entry_id AS bigint), CAST(:to_envelope_id AS bigint),
                    CAST(:in_amount AS integer))
            """,
            {
                "entry_id": entry_id,
                "from_envelope_id": transfer.from_envelope_id,
                "to_envelope_id": transfer.to_envelope_id,
                "out_amount": -transfer.amount,
                "in_amount": transfer.amount,
            },
        )
        from_balance = await self._uow.execute(
            "SELECT balance FROM envelope_balances WHERE id = :envelope_id",
            {"envelope_id": transfer.from_envelope_id},
        )
        to_balance = await self._uow.execute(
            "SELECT balance FROM envelope_balances WHERE id = :envelope_id",
            {"envelope_id": transfer.to_envelope_id},
        )
        return entry_id, int(from_balance.scalar_one()), int(to_balance.scalar_one())

    async def fix_amount(
        self, tenure_id: int, fix: AmountFix, recorded_by: str
    ) -> tuple[int, int, EntryKind, int]:
        """Fix the amount: a mirroring reversal plus a replacement, ONE transaction.

        The reversal mirrors the original's lines exactly (`check_shape`,
        db/schema.sql:357-363) and carries the same member (`tx_guard`,
        :310-312). The replacement re-writes the original's labels with the
        corrected amount signed by the kind; its note and date follow the
        approved contract (step 6.5 brief, Q3=c, Q6=a). PostgreSQL owns the
        "only once" walls (`reverses_id`/`replaces_id` UNIQUE, :255-256),
        the tenure checks (`tx_guard`, :293-315) and the overdraw guard
        (`line_guard`, :319-337).
        """
        original = (
            (
                await self._uow.execute(
                    """
                SELECT kind, note, tag, cost_center_id, source, member_id
                  FROM ledger_transactions WHERE id = :entry_id
                """,
                    {"entry_id": fix.entry_id},
                )
            )
            .mappings()
            .first()
        )
        if original is None:
            raise UnknownReference(f"entry {fix.entry_id} does not exist")
        kind = EntryKind(original["kind"])
        if kind not in (EntryKind.DEPOSIT, EntryKind.EXPENSE):
            # step 6.5 Q1=a: a fix replaces the one line the kind owns; a
            # multi-line entry needs its own step, so refuse it by name.
            raise ValidationFailed(
                f"entry {fix.entry_id} is a {kind.value}; only deposits and expenses"
                " can have their amount fixed"
            )
        reversal = await self._uow.execute(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, tag,
                    cost_center_id, member_id, reverses_id)
            VALUES (:tenure_id, 'reversal', :occurred_on, :recorded_by, :note, :tag,
                    :cost_center_id, :member_id, :entry_id)
            RETURNING id
            """,
            {
                "tenure_id": tenure_id,
                "occurred_on": fix.occurred_on,
                "recorded_by": recorded_by,
                "note": fix.note,
                "tag": original["tag"],
                "cost_center_id": original["cost_center_id"],
                "member_id": original["member_id"],
                "entry_id": fix.entry_id,
            },
        )
        reversal_id = int(reversal.scalar_one())
        await self._uow.execute(
            """
            INSERT INTO ledger_lines (transaction_id, envelope_id, amount)
            SELECT CAST(:reversal_id AS bigint), envelope_id, -amount
              FROM ledger_lines WHERE transaction_id = :entry_id
            """,
            {"reversal_id": reversal_id, "entry_id": fix.entry_id},
        )
        replacement = await self._uow.execute(
            """
            INSERT INTO ledger_transactions
                   (tenure_id, kind, occurred_on, recorded_by, note, tag,
                    cost_center_id, source, member_id, replaces_id)
            VALUES (:tenure_id, :kind, :occurred_on, :recorded_by, :note, :tag,
                    :cost_center_id, :source, :member_id, :entry_id)
            RETURNING id
            """,
            {
                "tenure_id": tenure_id,
                "kind": kind.value,
                "occurred_on": fix.occurred_on,
                "recorded_by": recorded_by,
                "note": original["note"],
                "tag": original["tag"],
                "cost_center_id": original["cost_center_id"],
                "source": original["source"],
                "member_id": original["member_id"],
                "entry_id": fix.entry_id,
            },
        )
        replacement_id = int(replacement.scalar_one())
        amount = fix.amount if kind is EntryKind.DEPOSIT else -fix.amount
        new_line = await self._uow.execute(
            """
            INSERT INTO ledger_lines (transaction_id, envelope_id, amount)
            SELECT CAST(:replacement_id AS bigint), envelope_id, CAST(:amount AS integer)
              FROM ledger_lines WHERE transaction_id = :entry_id
            RETURNING envelope_id
            """,
            {"replacement_id": replacement_id, "amount": amount, "entry_id": fix.entry_id},
        )
        balance = await self._uow.execute(
            "SELECT balance FROM envelope_balances WHERE id = :envelope_id",
            {"envelope_id": int(new_line.scalar_one())},
        )
        return replacement_id, reversal_id, kind, int(balance.scalar_one())

    async def edit_labels(self, edit: LabelEdit) -> LabelView:
        """Fix one entry's labels in one UPDATE; history is the schema's job.

        The row is read FOR UPDATE so the merge of the request's fields onto
        the current labels cannot race another edit. `tx_label_edit`
        (db/schema.sql:376-410) refuses opening entries, closed tenures, a date
        before the tenure opened, and writes `ledger_label_edits` naming
        `app.actor`; the app refuses only a blank note that a kind needs
        (step 6.6 Q7=b).
        """
        current = (
            (
                await self._uow.execute(
                    """
                SELECT kind, note, tag, cost_center_id, occurred_on, source
                  FROM ledger_transactions WHERE id = :entry_id FOR UPDATE
                """,
                    {"entry_id": edit.entry_id},
                )
            )
            .mappings()
            .first()
        )
        if current is None:
            raise UnknownReference(f"entry {edit.entry_id} does not exist")
        kind = EntryKind(current["kind"])
        edit.validate_for(kind)
        labels: dict[str, Any] = {
            "note": current["note"],
            "tag": current["tag"],
            "cost_center_id": current["cost_center_id"],
            "occurred_on": current["occurred_on"],
            "source": current["source"],
        }
        for field in edit.fields:
            labels[field] = getattr(edit, field)
        source = labels["source"]
        if isinstance(source, IncomeSource):
            source = source.value
        await self._uow.execute(
            """
            UPDATE ledger_transactions
               SET note = :note, tag = :tag, cost_center_id = :cost_center_id,
                   occurred_on = :occurred_on, source = :source
             WHERE id = :entry_id
            """,
            {
                "note": labels["note"],
                "tag": labels["tag"],
                "cost_center_id": labels["cost_center_id"],
                "occurred_on": labels["occurred_on"],
                "source": source,
                "entry_id": edit.entry_id,
            },
        )
        return LabelView(
            id=edit.entry_id,
            kind=kind,
            note=labels["note"],
            tag=labels["tag"],
            cost_center_id=labels["cost_center_id"],
            occurred_on=labels["occurred_on"],
            source=IncomeSource(source) if source is not None else None,
        )
