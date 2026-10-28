"""The CloseTenure use case (ROADMAP 11.1): close the open tenure, save the
snapshots and open the next tenure.

Approved step brief answers this session (all the brief's labelled
suggestions): Q2=a the request is `{close_on, next_name}` and the response is
`201 {"id","name","opened_on"}` read back from the new tenure row; Q5=a a THIN
app - the use case passes the close date, next name and the JWT actor down and
PostgreSQL's `close_tenure` (db/schema.sql:910-938) owns every rule.

What these tests pin (the modules /code must provide):
- `CloseTenureCommand(close_on=..., next_name=...)`
- `CloseTenure.__call__(command, actor)` returning the new tenure's view
- the slice declares its own port pair - a `TenureRepository` with ONE `close`
  method and a `TenureUnitOfWork` exposing it as `.tenures` (the D-085
  pattern). The use case opens ONE transaction, passes the JWT actor down as
  `recorded_by` and commits once.

The modules are imported lazily (D-069): nothing under test exists yet.
"""

from __future__ import annotations

from datetime import date
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
    return vars(_module("mesl_finance.tenures.application.close_tenure"))["CloseTenure"]


def _command() -> Any:
    return vars(_module("mesl_finance.tenures.application.close_tenure"))["CloseTenureCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {"close_on": date(2026, 1, 31), "next_name": "2026"}
    fields.update(overrides)
    return _command()(**fields)


class FakeTenures:
    def __init__(self) -> None:
        self.calls: list[tuple[date, str, str]] = []
        self.answer: Any = "VIEW"

    async def close(self, *, close_on: date, next_name: str, recorded_by: str) -> Any:
        self.calls.append((close_on, next_name, recorded_by))
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.tenures = FakeTenures()
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


async def test_close_tenure_uses_one_transaction_and_commits_once() -> None:
    uows: list[FakeUow] = []

    answer = await _use_case()(_factory(uows))(
        command(close_on=date(2026, 1, 31), next_name="2026B"), actor="treasurer"
    )

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    assert uow.tenures.calls == [(date(2026, 1, 31), "2026B", "treasurer")]
    assert answer == "VIEW"
