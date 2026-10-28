"""The SweepLeftover use case: one transaction, one sweep transfer.

ROADMAP 8.3 (approved brief this session, "go with your suggestions", so every
labelled suggestion stands):

- Q3=a the command carries ``cost_center_id``, ``from_envelope_id``,
  ``occurred_on`` and ``note``; ``p_by`` is the JWT actor, never the client.
- Q4=a the use case answers ``(entry_id, from_balance, pool_balance)``; the
  router adds the constant ``kind="sweep"``.
- Q5=a the adapter pre-checks the open tenure, so the port exposes
  ``open_tenure_id()`` beside ``sweep()`` (the 8.2 pattern, D-121 (2));
  ``sweep_leftover``'s own "no open tenure" check stays the backstop.
- Q1=a the slice lives in ``cost_centers`` with its own port (D-085):
  ``SweepRepository`` reached through ``SweepUnitOfWork.sweeps``.
- One transaction and ONE commit (every write slice's rule).

The module is imported lazily, so this file collects before /code creates it
(D-069).

Library APIs used, verified in installed source this session: pytest-asyncio
``auto`` mode (pyproject.toml:25, verified this session), so no
``mark.asyncio`` is needed.
"""

from __future__ import annotations

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

from mesl_finance.shared.errors import ValidationFailed

USE_CASE_MODULE = "mesl_finance.cost_centers.application.sweep_leftover"


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _use_case_class() -> Any:
    return vars(_module(USE_CASE_MODULE))["SweepLeftover"]


def _command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "cost_center_id": 1,
        "from_envelope_id": 2,
        "occurred_on": date(2026, 2, 8),
        "note": "event over; leftover back to pool",
    }
    fields.update(overrides)
    return vars(_module(USE_CASE_MODULE))["SweepCommand"](**fields)


class FakeSweep:
    def __init__(self, fail_with: Exception | None = None) -> None:
        self.events: list[str] = []
        self.command: Any = None
        self.recorded_by: str | None = None
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        self.events.append("open")
        return 7

    async def sweep(self, command: Any, recorded_by: str) -> tuple[int, int, int]:
        self.events.append("sweep")
        self.command = command
        self.recorded_by = recorded_by
        if self._fail_with is not None:
            raise self._fail_with
        return 42, 0, 600


class FakeUow:
    def __init__(self, actor: str, sweep: FakeSweep | None = None) -> None:
        self.actor = actor
        self.sweeps = FakeSweep() if sweep is None else sweep
        self.commits = 0

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
        self.commits += 1


async def test_one_transaction_and_one_commit() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    entry_id, from_balance, pool_balance = await _use_case_class()(factory)(
        _command(), actor="treasurer"
    )

    assert len(uows) == 1
    assert uows[0].commits == 1
    assert (entry_id, from_balance, pool_balance) == (42, 0, 600)


async def test_the_actor_is_the_recorder_and_the_tenure_is_checked_first() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    await _use_case_class()(factory)(_command(), actor="treasurer")

    assert uows[0].actor == "treasurer"
    assert uows[0].sweeps.recorded_by == "treasurer"
    assert uows[0].sweeps.events == ["open", "sweep"]


async def test_the_command_reaches_the_repository_unchanged() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    await _use_case_class()(factory)(
        _command(cost_center_id=5, from_envelope_id=3, occurred_on=date(2026, 3, 4), note="march"),
        actor="treasurer",
    )

    command = uows[0].sweeps.command
    assert command.cost_center_id == 5
    assert command.from_envelope_id == 3
    assert command.occurred_on == date(2026, 3, 4)
    assert command.note == "march"


async def test_a_raised_error_commits_nothing() -> None:
    uows: list[FakeUow] = []
    failing = FakeSweep(fail_with=ValidationFailed("refused"))

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, failing))
        return uows[-1]

    with pytest.raises(ValidationFailed):
        await _use_case_class()(factory)(_command(), actor="treasurer")

    assert uows[0].commits == 0
