from datetime import date
from importlib import import_module
from types import TracebackType
from typing import Any, Self

import pytest

from mesl_finance.ledger.application.record_deposit import RecordDeposit, RecordDepositCommand
from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.shared.errors import DomainError, NoOpenTenure, ValidationFailed


def _income_source() -> Any:
    """The one income-source enum (step 6.1 Q2=a); imported lazily, see D-069."""
    try:
        module = import_module("mesl_finance.ledger.domain.entry")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/entry.py does not exist yet")
    return vars(module)["IncomeSource"]


class FakeLedger:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.added: list[tuple[int, Deposit, str]] = []
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        return 7

    async def add_deposit(self, tenure_id: int, deposit: Deposit, recorded_by: str) -> int:
        if self._fail_with is not None:
            raise self._fail_with
        self.added.append((tenure_id, deposit, recorded_by))
        return 42


class FakeIdempotency:
    """The shared key store, in memory (issue #4)."""

    def __init__(self) -> None:
        self.claimed: list[tuple[str, str]] = []
        self.remembered: list[tuple[str, Any]] = []
        self.replay: Any = None

    async def claim(self, key: str, fingerprint: str) -> Any:
        self.claimed.append((key, fingerprint))
        return self.replay

    async def remember(self, key: str, result: Any) -> None:
        self.remembered.append((key, result))

    async def result_for(self, key: str) -> Any:
        return self.replay


class FakeUow:
    def __init__(
        self,
        actor: str,
        ledger: FakeLedger | None = None,
        idempotency: FakeIdempotency | None = None,
    ) -> None:
        self.actor = actor
        self.ledger = FakeLedger() if ledger is None else ledger
        self.idempotency = FakeIdempotency() if idempotency is None else idempotency
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


def command(**overrides: object) -> RecordDepositCommand:
    fields: dict[str, object] = {
        "amount": 500,
        "occurred_on": date(2026, 2, 1),
        "source": _income_source().SPONSORSHIP,
        "idempotency_key": "key-1",
    }
    fields.update(overrides)
    return RecordDepositCommand(**fields)  # type: ignore[arg-type]


async def test_it_records_the_deposit_in_the_open_tenure_and_commits() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    entry_id = await RecordDeposit(factory)(command(), actor="treasurer")

    assert entry_id == 42
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    tenure_id, deposit, recorded_by = uow.ledger.added[0]
    assert (tenure_id, deposit.amount, recorded_by) == (7, 500, "treasurer")


async def test_it_claims_the_idempotency_key_before_the_write() -> None:
    """The key is claimed FIRST, so a retry finds it before the write runs."""
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    await RecordDeposit(factory)(command(), actor="treasurer")

    uow = uows[0]
    assert uow.idempotency.claimed
    assert uow.idempotency.claimed[0][0] == "key-1"
    assert uow.idempotency.remembered
    assert uow.idempotency.remembered[0][0] == "key-1"


async def test_a_replayed_key_returns_the_stored_result_without_writing() -> None:
    """A key that already succeeded replays its result; no second write."""
    uows: list[FakeUow] = []
    store = FakeIdempotency()
    store.replay = 42

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, idempotency=store))
        return uows[-1]

    entry_id = await RecordDeposit(factory)(command(), actor="treasurer")

    assert entry_id == 42
    assert uows[0].ledger.added == []
    assert not uows[0].committed


async def test_an_invalid_deposit_never_opens_a_transaction() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    with pytest.raises(ValidationFailed):
        await RecordDeposit(factory)(command(amount=0), actor="treasurer")
    assert uows == []


async def test_a_failed_write_is_not_committed() -> None:
    uows: list[FakeUow] = []
    failure = NoOpenTenure("there is no open tenure")

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, FakeLedger(fail_with=failure)))
        return uows[-1]

    with pytest.raises(NoOpenTenure):
        await RecordDeposit(factory)(command(), actor="treasurer")

    assert not uows[0].committed
