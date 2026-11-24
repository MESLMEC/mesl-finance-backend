"""The ListShutdownState use case: the current state is read in ONE transaction (issue #15).

Approved brief this session ("go with your suggestions"), so every labelled
suggestion stands:
- Q4=a the step-2 slice declares its OWN port pair (the D-085/D-093/D-150
  convention): ``ShutdownStateRepository.list_current()`` reached through
  ``ShutdownStateUnitOfWork.shutdown_state``. The attribute is
  ``shutdown_state``, not ``fees`` or ``dues``, following the ``.adjustments`` /
  ``.dues`` / ``.reconciliation_reads`` precedent.
- The read opens ONE transaction, passes the JWT actor down and NEVER commits
  (the 7.5 Q9=a / D-093 Q12 pattern).
- The route that answers it (``GET /api/v1/shutdown-weeks/state``) returns the
  latest ``shutdown_events`` row per week, open tenure only; the ordering and
  the latest-wins rule are the adapter's SQL's (db/schema.sql:117,594-595),
  pinned end to end by the API tests in ``tests/fees/api/test_shutdown_weeks_api.py``.

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
    return vars(_module("mesl_finance.fees.application.list_shutdown_state"))["ListShutdownState"]


class FakeShutdownState:
    def __init__(self) -> None:
        self.calls = 0
        self.result: list[Any] = [object(), object()]

    async def list_current(self) -> list[Any]:
        self.calls += 1
        return self.result


class FakeUow:
    def __init__(self, actor: str, shutdown_state: FakeShutdownState | None = None) -> None:
        self.actor = actor
        self.shutdown_state = FakeShutdownState() if shutdown_state is None else shutdown_state
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


async def test_the_state_is_read_in_one_transaction_without_commit() -> None:
    uows: list[FakeUow] = []

    views = await _list_class()(_factory(uows))(actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert views is uow.shutdown_state.result
    assert uow.shutdown_state.calls == 1
    assert not uow.committed


async def test_the_actor_is_the_transaction_actor() -> None:
    uows: list[FakeUow] = []

    await _list_class()(_factory(uows))(actor="treasurer")

    assert [uow.actor for uow in uows] == ["treasurer"]
