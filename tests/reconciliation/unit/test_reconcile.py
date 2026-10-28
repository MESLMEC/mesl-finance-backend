"""The Reconcile use case (ROADMAP 10.1): record one screen-vs-notes check.

Approved step brief answers this session (all the brief's labelled
suggestions): Q6=a the action lives in a new `reconciliation` feature; the
slice declares its own port pair (D-085) - a `ReconciliationRepository` with
ONE `reconcile` method and a `ReconciliationUnitOfWork` exposing it as
`.reconciliation`. The use case opens ONE transaction, passes the JWT actor
down as `recorded_by`, commits once and returns the stored row as a
`ReconciliationView`.

What these tests pin (the modules /code must provide):
- `ReconcileCommand(counted_total=..., note="", counted=None)`
- `Reconcile.__call__(command, actor)` returning `ReconciliationView`

The modules are imported lazily (D-069): nothing under test exists yet.
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


def _use_case() -> Any:
    return vars(_module("mesl_finance.reconciliation.application.reconcile"))["Reconcile"]


def _command() -> Any:
    return vars(_module("mesl_finance.reconciliation.application.reconcile"))["ReconcileCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {"counted_total": 1150, "note": "", "counted": None}
    fields.update(overrides)
    return _command()(**fields)


class FakeReconciliation:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, object, str]] = []
        self.answer: Any = "VIEW"

    async def reconcile(
        self,
        *,
        counted_total: int,
        note: str,
        counted: dict[str, int] | None,
        recorded_by: str,
    ) -> Any:
        self.calls.append((counted_total, note, counted, recorded_by))
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.reconciliation = FakeReconciliation()
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


async def test_reconcile_opens_one_transaction_and_commits_once() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows))(
        command(counted_total=1150, note="month 1", counted={"1": 900}), actor="treasurer"
    )

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    assert uow.reconciliation.calls == [(1150, "month 1", {"1": 900}, "treasurer")]
    assert answer == "VIEW"


async def test_reconcile_returns_the_stored_row() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows))(command(), actor="treasurer")

    assert answer == "VIEW"
