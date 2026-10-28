"""The three asset read use cases (ROADMAP 9.3): asset state, who-has-what,
admin replacement queue.

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a three GET routes nested under the assets router; Q2=a no
`as_of` parameter - the views call `asset_state()`/`asset_holdings()` with
the default `infinity` (db/schema.sql:844-847), the 7.5 Q2=a pattern; Q3=a
the state row keeps the function's own column names, `with_members`
included; Q4=a all three reads live in `assets`; Q5=a each read in its
view's own order, no adapter ORDER BY (the D-112 (1) lesson).

What these tests pin (the use cases /code must provide):
- `ListAssetState`, `ListWhoHasWhat` and `ListReplacementQueue` in
  `mesl_finance.assets.application.read_asset_state`, each opening ONE
  transaction, passing the JWT actor down, answering the repository's list
  and NEVER committing (the 7.5 Q9=a read pattern);
- the slice declares its own port pair - an `AssetReadRepository` with the
  three methods and an `AssetReadUnitOfWork` exposing it as `.asset_reads`
  (the D-085 pattern; the concrete `SqlAssetUnitOfWork` carries the third
  repository like `SqlMemberUnitOfWork` carries two, D-108 (4)).

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
    return vars(_module("mesl_finance.assets.application.read_asset_state"))[name]


class FakeAssetReads:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.answer: list[Any] = ["ROW"]

    async def asset_state(self) -> list[Any]:
        self.calls.append("asset_state")
        return self.answer

    async def who_has_what(self) -> list[Any]:
        self.calls.append("who_has_what")
        return self.answer

    async def replacement_queue(self) -> list[Any]:
        self.calls.append("replacement_queue")
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.asset_reads = FakeAssetReads()
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


async def test_each_read_runs_one_transaction_and_does_not_commit() -> None:
    for name in ("ListAssetState", "ListWhoHasWhat", "ListReplacementQueue"):
        uows: list[FakeUow] = []

        answer = await _use_case(name)(_factory(uows))(actor="treasurer")

        uow = uows[0]
        assert uow.actor == "treasurer"
        assert not uow.committed  # a read never commits (7.5 Q9=a)
        assert answer == ["ROW"]


async def test_the_three_reads_reach_their_own_repository_method() -> None:
    for name, method in (
        ("ListAssetState", "asset_state"),
        ("ListWhoHasWhat", "who_has_what"),
        ("ListReplacementQueue", "replacement_queue"),
    ):
        uows: list[FakeUow] = []

        await _use_case(name)(_factory(uows))(actor="treasurer")

        assert uows[0].asset_reads.calls == [method]
