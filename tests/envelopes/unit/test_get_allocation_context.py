"""The GetAllocationContext use case: the allocation header is read in ONE transaction.

ROADMAP 7.5 (approved brief this session, "go with your suggestions"):
- Q1=b the second of the TWO routes: ``GET /api/v1/allocation-context``.
- Q5=a the payload is the view's three columns
  ``{pool_balance, member_credit_held, pool_after_member_credit}``
  (db/schema.sql:630-634).
- Q8=a the read lives in the ``envelopes`` feature; the slice declares its own port
  (D-085): ``AllocationContextRepository.get_allocation_context()`` reached through
  ``AllocationContextUnitOfWork.allocation_context``.
- Q9=a a read: ONE transaction, NO commit and no open-tenure call (the D-093 Q12
  and D-105 (4) precedent).

The module is imported lazily, so this file collects before /code creates it
(D-069).
"""

from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _use_case_class() -> Any:
    module = "mesl_finance.envelopes.application.get_allocation_context"
    return vars(_module(module))["GetAllocationContext"]


class FakeAllocationContext:
    def __init__(self) -> None:
        self.calls = 0
        self.result: Any = object()

    async def get_allocation_context(self) -> Any:
        self.calls += 1
        return self.result


class FakeUow:
    def __init__(self, actor: str, context: FakeAllocationContext | None = None) -> None:
        self.actor = actor
        self.allocation_context = FakeAllocationContext() if context is None else context
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


async def test_the_context_is_read_in_one_transaction_without_commit() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    view = await _use_case_class()(factory)(actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert view is uow.allocation_context.result
    assert uow.allocation_context.calls == 1
    assert uow.actor == "treasurer"
    assert not uow.committed
