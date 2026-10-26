"""The ListDues use case: the dues overview is read in ONE transaction (ROADMAP 7.5).

Approved brief this session: the user answered "go with your suggestions", so every
labelled suggestion stands (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/
D-082/D-086/D-088/D-090/D-093/D-096/D-101/D-104/D-106/D-109):
- Q1=b TWO routes only: ``GET /api/v1/dues`` (this read) and
  ``GET /api/v1/allocation-context``. ``dues_overview`` is literally
  ``SELECT * FROM member_standing() ORDER BY weeks_overdue DESC, who_name``
  (db/schema.sql:627-628), so a per-member route would expose the same data twice
  and is not part of this step.
- Q4=a the list is every member exactly as the view returns it, in the view's order.
- Q9=a a read: ONE transaction, NO commit and no open-tenure call (the D-093 Q12
  and D-105 (4) precedent).
- Q8=a the read lives in the ``fees`` feature and the slice declares its own port
  (D-085): ``DuesRepository.list_dues()`` reached through
  ``DuesUnitOfWork.dues``. The attribute is ``dues``, not the existing ``fees``,
  following the ``.adjustments`` precedent of D-106 (a second repository in the
  same feature keeps its own name).
- Q3=a the read model is ``StandingView``: ``member_id``/``member_name`` plus the
  other seven columns exactly as ``member_standing()`` returns them
  (db/schema.sql:582-584).

The module is imported lazily: ruff classifies an import of a module that does not
exist yet as third-party, so a module-level import would have to be re-sorted the
moment /code adds it (D-069).
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


def _list_class() -> Any:
    return vars(_module("mesl_finance.fees.application.list_dues"))["ListDues"]


class FakeDues:
    def __init__(self) -> None:
        self.calls = 0
        self.result: list[Any] = [object(), object()]

    async def list_dues(self) -> list[Any]:
        self.calls += 1
        return self.result


class FakeUow:
    def __init__(self, actor: str, dues: FakeDues | None = None) -> None:
        self.actor = actor
        self.dues = FakeDues() if dues is None else dues
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


async def test_the_dues_are_read_in_one_transaction_without_commit() -> None:
    uows: list[FakeUow] = []

    views = await _list_class()(_factory(uows))(actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert views is uow.dues.result
    assert uow.dues.calls == 1
    assert not uow.committed


async def test_the_actor_is_the_transaction_actor() -> None:
    uows: list[FakeUow] = []

    await _list_class()(_factory(uows))(actor="treasurer")

    assert [uow.actor for uow in uows] == ["treasurer"]
