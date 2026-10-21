"""The RecordTransfer use case: one transaction, one transfer entry.

The use case returns the new entry id AND both envelopes' balances after the
write, because the approved response body carries all three (step 6.4 brief,
Q2=a). Step 6.4 Q7=a gives this slice its own port, the D-085 rule.
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


def _record_transfer_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_transfer"))["RecordTransfer"]


def _command_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_transfer"))["RecordTransferCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "amount": 200,
        "occurred_on": date(2026, 2, 2),
        "from_envelope_id": 1,
        "to_envelope_id": 2,
        "note": "for workshop",
    }
    fields.update(overrides)
    return _command_class()(**fields)


class FakeLedger:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.added: list[tuple[int, Any, str]] = []
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        return 7

    async def add_transfer(
        self, tenure_id: int, transfer: Any, recorded_by: str
    ) -> tuple[int, int, int]:
        if self._fail_with is not None:
            raise self._fail_with
        self.added.append((tenure_id, transfer, recorded_by))
        return 42, 300, 200


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


async def test_it_records_the_transfer_in_the_open_tenure_and_commits() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    entry_id, from_balance, to_balance = await _record_transfer_class()(factory)(
        command(), actor="treasurer"
    )

    assert (entry_id, from_balance, to_balance) == (42, 300, 200)
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    tenure_id, transfer, recorded_by = uow.ledger.added[0]
    assert (
        tenure_id,
        transfer.amount,
        transfer.from_envelope_id,
        transfer.to_envelope_id,
        recorded_by,
    ) == (7, 200, 1, 2, "treasurer")


async def test_an_invalid_transfer_never_opens_a_transaction() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    with pytest.raises(ValidationFailed):
        await _record_transfer_class()(factory)(command(amount=0), actor="treasurer")
    assert uows == []


async def test_a_failed_write_is_not_committed() -> None:
    uows: list[FakeUow] = []
    failure = NoOpenTenure("there is no open tenure")

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, FakeLedger(fail_with=failure)))
        return uows[-1]

    with pytest.raises(NoOpenTenure):
        await _record_transfer_class()(factory)(command(), actor="treasurer")

    assert not uows[0].committed
