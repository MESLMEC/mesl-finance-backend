"""The ListEntries use case: the treasurer's list is read in ONE transaction.

Approved contract (step 6.7 brief; every question was left unanswered, so the
brief's labelled suggestions stand, same pattern as D-062/D-064/D-066/D-070/
D-076/D-079/D-082/D-086/D-088/D-090):
- Q11=a the slice declares its own port (D-085): ``EntryListRepository``
  exposes ``list_entries(query)`` and ``EntryListUnitOfWork`` returns it as
  ``.ledger``.
- Q12=a a read does NOT commit; the transaction just closes, the same shape as
  ``ListCostCenters``.
- Q4=a the query carries an optional ``tenure_id``; Q5=a adds no other filter
  in this step.
- Q3=a the read model carries no amounts: ``entries_current`` has none
  (db/schema.sql:426-430).
  SUPERSEDED by issue #5: the read model also carries ``lines`` (one entry
  per line of the ledger, signed), ``net_effect`` and ``size`` — the use case
  itself stays a passthrough; the amounts come from the repository.
"""

from datetime import date, datetime
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
    return vars(_module("mesl_finance.ledger.application.list_entries"))["ListEntries"]


def _query_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.list_entries"))["ListEntriesQuery"]


def query(**overrides: object) -> Any:
    fields: dict[str, object] = {"tenure_id": None}
    fields.update(overrides)
    return _query_class()(**fields)


class FakeLedger:
    def __init__(self) -> None:
        self.queries: list[Any] = []
        self.result: list[Any] = [object(), object()]

    async def list_entries(self, entry_query: Any) -> list[Any]:
        self.queries.append(entry_query)
        return self.result


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


def _factory(uows: list[FakeUow]) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    return factory


async def test_the_list_is_read_in_one_transaction() -> None:
    uows: list[FakeUow] = []

    views = await _list_class()(_factory(uows))(query(), actor="treasurer")

    uow = uows[0]
    assert views is uow.ledger.result
    assert len(uow.ledger.queries) == 1
    assert not uow.committed


async def test_the_tenure_filter_reaches_the_repository() -> None:
    uows: list[FakeUow] = []

    await _list_class()(_factory(uows))(query(tenure_id=2), actor="treasurer")

    assert [entry_query.tenure_id for entry_query in uows[0].ledger.queries] == [2]

    default_uows: list[FakeUow] = []
    await _list_class()(_factory(default_uows))(query(), actor="treasurer")
    assert default_uows[0].ledger.queries[0].tenure_id is None


async def test_the_actor_is_the_transaction_actor() -> None:
    uows: list[FakeUow] = []

    await _list_class()(_factory(uows))(query(), actor="treasurer")

    assert [uow.actor for uow in uows] == ["treasurer"]


async def test_the_read_model_carries_lines_and_the_two_totals() -> None:
    # Issue #5: the read model gains the signed lines and the two totals; the use
    # case returns the repository's rows unchanged. The lazy `vars(mod)[name]`
    # lookup keeps the whole file importable while `EntryLine` does not exist yet.
    dom: ModuleType = _module("mesl_finance.ledger.domain.entry_list")
    line = vars(dom)["EntryLine"](envelope_id=1, amount=500)
    view = vars(dom)["EntryView"](
        id=1,
        tenure_id=1,
        kind="deposit",
        occurred_on=date(2026, 2, 1),
        recorded_at=datetime(2026, 2, 1, 10, 0),
        recorded_by="treasurer",
        note="",
        tag=None,
        cost_center_id=None,
        member_id=None,
        source=None,
        corrected_from=None,
        lines=(line,),
        net_effect=500,
        size=500,
    )
    ledger = FakeLedger()
    ledger.result = [view]
    uow = FakeUow("treasurer", ledger)

    def factory(_actor: str) -> FakeUow:
        return uow

    views = await _list_class()(factory)(query(), actor="treasurer")

    assert views is ledger.result
    assert len(ledger.queries) == 1
    assert not uow.committed
