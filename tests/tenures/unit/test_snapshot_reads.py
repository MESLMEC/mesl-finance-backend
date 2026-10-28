"""The three snapshot read use cases (ROADMAP 11.1): member, asset and holding
handover snapshots.

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a the reads are `GET /api/v1/tenures/{tenure_id}/
member-snapshots`, `/asset-snapshots` and `/holding-snapshots`; Q3=a bare
arrays with every stored table column, `tenure_id` included; Q4=a an unknown
tenure answers 404 (the read returns None and the router raises it).

What these tests pin (the use cases /code must provide):
- `ListMemberSnapshots`, `ListAssetSnapshots` and `ListHoldingSnapshots` in
  `mesl_finance.tenures.application.read_snapshots`, each opening ONE
  transaction, passing the JWT actor down, answering the repository's list and
  NEVER committing (the read pattern);
- the slice declares its own port pair - a `SnapshotRepository` with the three
  methods and a `SnapshotUnitOfWork` exposing it as `.snapshots` (the D-085
  pattern).

The modules are imported lazily (D-069): nothing under test exists yet.
"""

from __future__ import annotations

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
    return vars(_module("mesl_finance.tenures.application.read_snapshots"))[name]


class FakeSnapshots:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.answer: Any = ["ROW"]

    async def member_snapshots(self, tenure_id: int) -> Any:
        self.calls.append(("member_snapshots", tenure_id))
        return self.answer

    async def asset_snapshots(self, tenure_id: int) -> Any:
        self.calls.append(("asset_snapshots", tenure_id))
        return self.answer

    async def holding_snapshots(self, tenure_id: int) -> Any:
        self.calls.append(("holding_snapshots", tenure_id))
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.snapshots = FakeSnapshots()
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


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("ListMemberSnapshots", "member_snapshots"),
        ("ListAssetSnapshots", "asset_snapshots"),
        ("ListHoldingSnapshots", "holding_snapshots"),
    ],
)
async def test_snapshot_reads_use_one_transaction_without_commit(name: str, method: str) -> None:
    uows: list[FakeUow] = []

    answer = await _use_case(name)(_factory(uows))(tenure_id=1, actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed  # a read never commits
    assert uow.snapshots.calls == [(method, 1)]
    assert answer == ["ROW"]
