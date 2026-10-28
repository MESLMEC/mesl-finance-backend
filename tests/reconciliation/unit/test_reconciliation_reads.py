"""The reconciliation read use cases (ROADMAP 10.2): status, unverified
entries, difference suspects.

Approved step brief answers this session (all the brief's labelled
suggestions): Q5=a the three reads live in the `reconciliation` feature and
share ONE read port pair (D-085) - a `ReconciliationReadRepository` with three
methods and a `ReconciliationReadUnitOfWork` exposing it as
`.reconciliation_reads`; Q1=a the endpoints are
`GET /api/v1/reconciliation-status`, `GET /api/v1/unverified-entries` and
`GET /api/v1/difference-suspects`; Q3=a the status read is a single object.

What these tests pin (the use cases /code must provide), all in
`mesl_finance.reconciliation.application.read_reconciliation`:
- `GetReconciliationStatus(unit_of_work)` -> `__call__(actor)` answering the
  repository's single status row;
- `ListUnverifiedEntries(unit_of_work)` -> `__call__(actor)` answering the
  repository's list;
- `ListDifferenceSuspects(unit_of_work)` ->
  `__call__(difference, envelope_id, actor)` answering the repository's list;
- each opens ONE transaction, passes the JWT actor down and NEVER commits
  (the 7.5 Q9=a read pattern);
- the repository methods are `status()`, `unverified_entries()` and
  `difference_suspects(difference, envelope_id)`.

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


def _use_case(name: str) -> Any:
    return vars(_module("mesl_finance.reconciliation.application.read_reconciliation"))[name]


class FakeReads:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.status_answer: Any = "STATUS"
        self.list_answer: list[Any] = ["ROW"]

    async def status(self) -> Any:
        self.calls.append(("status", ()))
        return self.status_answer

    async def unverified_entries(self) -> list[Any]:
        self.calls.append(("unverified_entries", ()))
        return self.list_answer

    async def difference_suspects(self, difference: int, envelope_id: int | None) -> list[Any]:
        self.calls.append(("difference_suspects", (difference, envelope_id)))
        return self.list_answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.reconciliation_reads = FakeReads()
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


async def test_status_read_opens_one_transaction_and_does_not_commit() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case("GetReconciliationStatus")(_factory(uows))(actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed
    assert answer == "STATUS"
    assert uow.reconciliation_reads.calls == [("status", ())]


async def test_unverified_read_opens_one_transaction_and_does_not_commit() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case("ListUnverifiedEntries")(_factory(uows))(actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed
    assert answer == ["ROW"]
    assert uow.reconciliation_reads.calls == [("unverified_entries", ())]


async def test_suspects_read_passes_difference_and_envelope_and_does_not_commit() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case("ListDifferenceSuspects")(_factory(uows))(
        difference=108, envelope_id=2, actor="treasurer"
    )

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed
    assert answer == ["ROW"]
    assert uow.reconciliation_reads.calls == [("difference_suspects", (108, 2))]
