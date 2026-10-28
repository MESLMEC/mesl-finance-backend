"""The GetCostCenterSummary use case: the event leftover is read in ONE transaction.

ROADMAP 8.3 (approved brief this session, "go with your suggestions", so every
labelled suggestion stands):

- Q2=a ``GET /api/v1/cost-centers/{cost_center_id}/summary``, ONE row: the
  ``cost_center_summary`` view's own 8 columns (db/schema.sql:537-557)
  ``{cost_center_id, name, kind, status, money_in, money_out, swept,
  leftover}``.
- Q1=a the read lives in the ``cost_centers`` feature; the slice declares its
  own port (D-085): ``CostCenterSummaryRepository.get_summary(cost_center_id)``
  reached through ``CostCenterSummaryUnitOfWork.summary``.
- A read: ONE transaction, NO commit and no open-tenure call (the D-093 Q12 /
  D-105 (4) precedent).

The module is imported lazily, so this file collects before /code creates it
(D-069).
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


def _use_case_class() -> Any:
    module = "mesl_finance.cost_centers.application.get_cost_center_summary"
    return vars(_module(module))["GetCostCenterSummary"]


class FakeSummary:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.result: Any = object()

    async def get_summary(self, cost_center_id: int) -> Any:
        self.calls.append(cost_center_id)
        return self.result


class FakeUow:
    def __init__(self, actor: str, summary: FakeSummary | None = None) -> None:
        self.actor = actor
        self.summary = FakeSummary() if summary is None else summary
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


async def test_the_summary_is_read_in_one_transaction_without_commit() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    view = await _use_case_class()(factory)(3, actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert view is uow.summary.result
    assert uow.summary.calls == [3]
    assert uow.actor == "treasurer"
    assert not uow.committed
