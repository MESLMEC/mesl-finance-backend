"""The FixAmount use case: ONE transaction writes the reversal and the replacement.

The approved response contract (step 6.5 brief, Q4=c) needs the replacement
id, the reversal id, the original entry's kind and the envelope's balance
after the write, so the slice's repository port returns all four (Q2=a; its
own port, the D-085 rule). Like every ledger action, the domain validation
runs before any transaction is opened.
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

from mesl_finance.ledger.domain.entry import EntryKind
from mesl_finance.shared.errors import DomainError, NoOpenTenure, ValidationFailed

DAY = date(2026, 10, 20)


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _record_fix_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.fix_amount"))["FixAmount"]


def _command_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.fix_amount"))["FixAmountCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "entry_id": 42,
        "amount": 600,
        "occurred_on": DAY,
        "note": "typo in amount",
    }
    fields.update(overrides)
    return _command_class()(**fields)


class FakeLedger:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.fixed: list[tuple[int, Any, str]] = []
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        return 7

    async def fix_amount(
        self, tenure_id: int, fix: Any, recorded_by: str
    ) -> tuple[int, int, EntryKind, int]:
        """Returns (replacement_id, reversal_id, kind, balance after the write)."""
        if self._fail_with is not None:
            raise self._fail_with
        self.fixed.append((tenure_id, fix, recorded_by))
        return 99, 98, EntryKind.DEPOSIT, 600


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


def _factory(uows: list[FakeUow], failure: DomainError | None = None) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, FakeLedger(fail_with=failure)))
        return uows[-1]

    return factory


async def test_it_writes_the_fix_in_the_open_tenure_and_commits() -> None:
    uows: list[FakeUow] = []

    replacement_id, reversal_id, kind, balance = await _record_fix_class()(_factory(uows))(
        command(), actor="treasurer"
    )

    assert (replacement_id, reversal_id, kind, balance) == (99, 98, EntryKind.DEPOSIT, 600)
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    tenure_id, fix, recorded_by = uow.ledger.fixed[0]
    assert (tenure_id, fix.entry_id, fix.amount, fix.occurred_on, fix.note, recorded_by) == (
        7,
        42,
        600,
        DAY,
        "typo in amount",
        "treasurer",
    )


async def test_an_invalid_fix_never_opens_a_transaction() -> None:
    uows: list[FakeUow] = []

    with pytest.raises(ValidationFailed):
        await _record_fix_class()(_factory(uows))(command(amount=0), actor="treasurer")

    assert uows == []


async def test_a_failed_write_is_not_committed() -> None:
    uows: list[FakeUow] = []

    with pytest.raises(NoOpenTenure):
        await _record_fix_class()(_factory(uows, NoOpenTenure("there is no open tenure")))(
            command(), actor="treasurer"
        )

    assert not uows[0].committed
