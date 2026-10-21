"""The RecordExpense use case: one transaction, one expense entry.

The use case returns the new entry id AND the envelope's balance after the
write, because the approved expense response body carries both (step 6.3 Q5=b).
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

from mesl_finance.shared.errors import DomainError, NoOpenTenure, ValidationFailed


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _record_expense_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_expense"))["RecordExpense"]


def _command_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_expense"))["RecordExpenseCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "amount": 150,
        "occurred_on": date(2026, 2, 3),
        "envelope_id": 2,
    }
    fields.update(overrides)
    return _command_class()(**fields)


class FakeLedger:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.added: list[tuple[int, Any, str]] = []
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        return 7

    async def add_expense(self, tenure_id: int, expense: Any, recorded_by: str) -> tuple[int, int]:
        if self._fail_with is not None:
            raise self._fail_with
        self.added.append((tenure_id, expense, recorded_by))
        return 42, 350


class FakeUow:
    def __init__(self, actor: str, ledger: FakeLedger | None = None) -> None:
        self.actor = actor
        self.ledger = FakeLedger() if ledger is None else ledger
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


async def test_it_records_the_expense_in_the_open_tenure_and_commits() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    entry_id, balance = await _record_expense_class()(factory)(command(), actor="treasurer")

    assert (entry_id, balance) == (42, 350)
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    tenure_id, expense, recorded_by = uow.ledger.added[0]
    assert (tenure_id, expense.amount, expense.envelope_id, recorded_by) == (
        7,
        150,
        2,
        "treasurer",
    )


async def test_an_invalid_expense_never_opens_a_transaction() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    with pytest.raises(ValidationFailed):
        await _record_expense_class()(factory)(command(amount=0), actor="treasurer")
    assert uows == []


async def test_a_failed_write_is_not_committed() -> None:
    uows: list[FakeUow] = []
    failure = NoOpenTenure("there is no open tenure")

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, FakeLedger(fail_with=failure)))
        return uows[-1]

    with pytest.raises(NoOpenTenure):
        await _record_expense_class()(factory)(command(), actor="treasurer")

    assert not uows[0].committed
