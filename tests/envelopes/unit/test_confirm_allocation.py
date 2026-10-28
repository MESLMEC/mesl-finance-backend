"""The ConfirmAllocation use case: one transaction, one allocation transfer.

ROADMAP 8.2 (approved brief this session, "go with your suggestions", so every
labelled suggestion stands):

- Q2=a the decision carries exactly what ``allocate`` needs besides the actor:
  ``occurred_on``, ``note`` and ``amounts`` (string envelope ids -> whole taka).
- Q3=b the use case answers ``(entry_id, pool_balance)``; the router adds the
  constant ``kind="transfer"``.
- Q4=a a THIN app: the value object refuses only a non-whole amount, because
  zero, negative, empty and blank values are PostgreSQL's rules and reach
  ``allocate`` as 409 (AGENTS.md section 5). That is pinned by the third test.
- Q5=a the adapter pre-checks the open tenure, so the port exposes
  ``open_tenure_id()`` beside ``confirm()``; ``allocate``'s own check stays the
  backstop.
- Q6=a the slice lives in ``envelopes`` with its own port (D-085):
  ``ConfirmAllocationRepository`` reached through
  ``ConfirmAllocationUnitOfWork.allocations``.
- One transaction and ONE commit (every write slice's rule).

The module is imported lazily, so this file collects before /code creates it (D-069).

Library APIs used, verified in installed source this session: ``pytest.raises`` and
``pytest.mark.parametrize`` (pytest 9.1.1, ``.venv/lib/python3.15/site-packages/_pytest``),
and pytest-asyncio ``auto`` mode (pyproject.toml:25), so no ``mark.asyncio`` is needed.
"""

from __future__ import annotations

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

from mesl_finance.shared.errors import DomainError, ValidationFailed

DOMAIN_MODULE = "mesl_finance.envelopes.domain.allocation_decision"
USE_CASE_MODULE = "mesl_finance.envelopes.application.confirm_allocation"


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _decision(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "occurred_on": date(2026, 2, 2),
        "note": "first monthly allocation",
        "amounts": {"2": 100},
    }
    fields.update(overrides)
    return vars(_module(DOMAIN_MODULE))["AllocationDecision"](**fields)


def _command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "occurred_on": date(2026, 2, 2),
        "note": "first monthly allocation",
        "amounts": {"2": 100},
    }
    fields.update(overrides)
    return vars(_module(USE_CASE_MODULE))["ConfirmAllocationCommand"](**fields)


def _use_case_class() -> Any:
    return vars(_module(USE_CASE_MODULE))["ConfirmAllocation"]


def test_a_decision_keeps_its_amounts_date_and_note() -> None:
    decision = _decision()

    assert decision.occurred_on == date(2026, 2, 2)
    assert decision.note == "first monthly allocation"
    assert decision.amounts == {"2": 100}


@pytest.mark.parametrize("amount", [10.5, True, "20"])
def test_a_non_whole_amount_is_refused(amount: Any) -> None:
    with pytest.raises(ValidationFailed):
        _decision(amounts={"2": amount})


def test_the_value_object_leaves_the_amount_rules_to_the_database() -> None:
    """Q4=a: zero, a negative entry and a blank note are ``allocate``'s business."""
    decision = _decision(amounts={"2": 0, "3": -5}, note="")

    assert decision.amounts == {"2": 0, "3": -5}
    assert decision.note == ""


class FakeAllocation:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.events: list[str] = []
        self.decision: Any = None
        self.recorded_by: str | None = None
        self._fail_with = fail_with

    async def open_tenure_id(self) -> int:
        self.events.append("open")
        return 7

    async def confirm(self, decision: Any, recorded_by: str) -> tuple[int, int]:
        self.events.append("confirm")
        self.decision = decision
        self.recorded_by = recorded_by
        if self._fail_with is not None:
            raise self._fail_with
        return 42, 2460


class FakeUow:
    def __init__(self, actor: str, allocation: FakeAllocation | None = None) -> None:
        self.actor = actor
        self.allocations = FakeAllocation() if allocation is None else allocation
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

    entry_id, pool_balance = await _use_case_class()(factory)(_command(), actor="treasurer")

    assert len(uows) == 1
    assert uows[0].commits == 1
    assert (entry_id, pool_balance) == (42, 2460)


async def test_the_actor_is_the_recorder_and_the_tenure_is_checked_first() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    await _use_case_class()(factory)(_command(), actor="treasurer")

    assert uows[0].actor == "treasurer"
    assert uows[0].allocations.recorded_by == "treasurer"
    assert uows[0].allocations.events == ["open", "confirm"]


async def test_the_decision_reaches_the_repository_unchanged() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    await _use_case_class()(factory)(
        _command(occurred_on=date(2026, 3, 4), note="march", amounts={"2": 60, "5": 40}),
        actor="treasurer",
    )

    decision = uows[0].allocations.decision
    assert decision.occurred_on == date(2026, 3, 4)
    assert decision.note == "march"
    assert decision.amounts == {"2": 60, "5": 40}


async def test_a_raised_error_commits_nothing() -> None:
    uows: list[FakeUow] = []
    failing = FakeAllocation(fail_with=ValidationFailed("refused"))

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, failing))
        return uows[-1]

    with pytest.raises(ValidationFailed):
        await _use_case_class()(factory)(_command(), actor="treasurer")

    assert uows[0].commits == 0
