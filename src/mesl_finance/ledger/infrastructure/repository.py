from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.ledger.domain.expense import Expense
from mesl_finance.shared.errors import NoOpenTenure, UnknownReference
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
