"""The ListAssetActivity use case (ROADMAP 9.4): the admin report's raw
numbers, one read-only transaction.

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a `GET /api/v1/assets/activity`; Q2=a the query parameters
are `from_date`/`to_date` (avoiding the Python keyword `from`); Q3=a JSON
rows only - "CSV-ready" means the raw numbers the report is built from
manually (B-22, D-012), no CSV endpoint; Q4=a the function's own six column
names and its own ORDER BY (name, kind enum-ordinal, D-128 (4)); Q5=a a
reversed window passes through - `asset_activity` answers no rows, no
invented 422.

What this test pins (the use case /code must provide): `ListAssetActivity`
in `mesl_finance.assets.application.list_asset_activity` opens ONE
transaction, passes the actor and the window down, answers the repository's
list and NEVER commits (the 7.5 Q9=a / 9.3 read pattern); the slice declares
its own port pair - an `AssetActivityRepository` with ONE `asset_activity`
method and an `AssetActivityUnitOfWork` exposing it as `.asset_activity`
(the D-085 pattern; `SqlAssetUnitOfWork` carries the fourth repository).

The module is imported lazily (D-069): nothing under test exists yet.
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

DAY_FROM = date(2026, 2, 1)
DAY_TO = date(2026, 2, 28)


def _use_case() -> Any:
    try:
        module: ModuleType = import_module("mesl_finance.assets.application.list_asset_activity")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/assets/application/list_asset_activity.py does not exist yet")
    return vars(module)["ListAssetActivity"]


class FakeAssetActivity:
    def __init__(self) -> None:
        self.calls: list[tuple[date, date]] = []
        self.answer: list[Any] = ["ROW"]

    async def asset_activity(self, from_date: date, to_date: date) -> list[Any]:
        self.calls.append((from_date, to_date))
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.asset_activity = FakeAssetActivity()
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


async def test_the_activity_read_never_commits_and_passes_its_window() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows))(DAY_FROM, DAY_TO, actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed  # a read never commits
    assert uow.asset_activity.calls == [(DAY_FROM, DAY_TO)]
    assert answer == ["ROW"]
