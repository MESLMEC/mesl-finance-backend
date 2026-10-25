"""The RecordRefund use case: one member-linked expense in ONE transaction.

The approved refund response is `201 {"id", "kind", "balance"}` (step 7.4 brief,
Q4=a), so the use case returns the new entry id AND the pool balance after the
write. The adapter resolves the pool: the body carries no envelope (Q3=a).
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _record_refund_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_refund"))["RecordRefund"]


def _command_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.record_refund"))["RecordRefundCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "member_id": 1,
        "amount": 60,
        "occurred_on": date(2026, 2, 3),
    }
    fields.update(overrides)
    return _command_class()(**fields)


class FakeLedger:
    def __init__(self) -> None:
        self.added: list[tuple[int, Any, str]] = []
        self.open_calls = 0

    async def open_tenure_id(self) -> int:
        self.open_calls += 1
        return 7

    async def add_refund(self, tenure_id: int, refund: Any, recorded_by: str) -> tuple[int, int]:
        self.added.append((tenure_id, refund, recorded_by))
        return 42, 440


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.ledger = FakeLedger()
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


def _factory(uows: list[FakeUow]) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    return factory


async def test_record_refund_uses_one_transaction_and_commits() -> None:
    uows: list[FakeUow] = []

    await _record_refund_class()(_factory(uows))(command(), actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert (uow.actor, uow.committed) == ("treasurer", True)
    tenure_id, refund, recorded_by = uow.ledger.added[0]
    assert (tenure_id, refund.member_id, refund.amount, recorded_by) == (7, 1, 60, "treasurer")


async def test_record_refund_asks_for_the_open_tenure_once() -> None:
    uows: list[FakeUow] = []

    await _record_refund_class()(_factory(uows))(command(), actor="treasurer")

    assert uows[0].ledger.open_calls == 1


async def test_record_refund_returns_the_id_and_the_pool_balance() -> None:
    uows: list[FakeUow] = []

    entry_id, balance = await _record_refund_class()(_factory(uows))(
        command(note="refund of credit", tag="refund", cost_center_id=3), actor="treasurer"
    )

    assert (entry_id, balance) == (42, 440)
    refund = uows[0].ledger.added[0][1]
    assert (refund.note, refund.tag, refund.cost_center_id) == ("refund of credit", "refund", 3)
