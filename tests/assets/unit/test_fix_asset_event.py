"""The FixAssetEvent use case: one transaction for the reversal + replacement.

Approved step brief answers this session (all the brief's labelled
suggestions): the slice declares its own ports (the D-085 pattern, as every
ledger/member slice did) - a ``FixEventRepository`` with ONE ``fix_event``
method and a ``FixEventUnitOfWork`` exposing it. The use case
- builds the ``AssetEventFix`` value object (so the domain refusals fire
  before any transaction opens),
- opens ONE transaction, passes the JWT actor down as ``recorded_by``,
- commits once, and returns ``(replacement view, reversal_id)``, or ``None``
  when the asset or the event does not exist (the router then answers 404,
  Q4=a) WITHOUT committing - the same shape ``RecordAssetEvent`` has.

The modules are imported lazily (D-069): nothing under test exists yet.
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

DAY = date(2026, 2, 1)


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _use_case() -> Any:
    return vars(_module("mesl_finance.assets.application.fix_event"))["FixAssetEvent"]


def _command() -> Any:
    return vars(_module("mesl_finance.assets.application.fix_event"))["FixEventCommand"]


def _fix_class() -> Any:
    return vars(_module("mesl_finance.assets.domain.asset_event_fix"))["AssetEventFix"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "asset_id": 5,
        "event_id": 42,
        "quantity": 1,
        "occurred_on": DAY,
        "note": "typo, should be 1",
    }
    fields.update(overrides)
    return _command()(**fields)


class FakeFixEvents:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, Any, str]] = []
        self.answer: tuple[int, int, Any] | None = (7, 6, "VIEW")

    async def fix_event(
        self, asset_id: int, event_id: int, fix: Any, recorded_by: str
    ) -> tuple[int, int, Any] | None:
        self.calls.append((asset_id, event_id, fix, recorded_by))
        return self.answer


class FakeUow:
    def __init__(self, actor: str, repo: FakeFixEvents | None = None) -> None:
        self.actor = actor
        self.fix_events = FakeFixEvents() if repo is None else repo
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


def _factory(uows: list[FakeUow], repo: FakeFixEvents | None = None) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, repo))
        return uows[-1]

    return factory


async def test_fix_writes_both_rows_in_one_transaction_and_commits() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows))(command(), actor="treasurer")

    uow = uows[0]
    assert uow.committed
    asset_id, event_id, fix, recorded_by = uow.fix_events.calls[0]
    assert (asset_id, event_id, recorded_by) == (5, 42, "treasurer")
    assert isinstance(fix, _fix_class())
    assert (fix.quantity, fix.occurred_on, fix.note) == (1, DAY, "typo, should be 1")
    assert answer == ("VIEW", 6)


async def test_a_missing_row_answers_none_without_committing() -> None:
    repo = FakeFixEvents()
    repo.answer = None
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows, repo))(command(), actor="treasurer")

    assert answer is None
    assert not uows[0].committed
    assert uows[0].fix_events.calls[0][3] == "treasurer"
