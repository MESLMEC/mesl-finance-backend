"""The DraftAllocation use case: the allocation draft is read in ONE transaction.

ROADMAP 8.1 (approved brief this session, "go", so the labelled suggestions stand,
the D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/
D-104/D-106/D-109/D-111 pattern):

- Q5=a the draft lives in the ``envelopes`` feature, like 7.5's
  ``allocation-context``: the pool is an envelope and ``allocation_suggestion``
  reads ``envelope_balances`` (db/schema.sql:413-420,457-503).
- Q6=a no open-tenure call: ``envelope_balances`` only counts the open tenure, so
  with no open tenure every balance is 0 and the draft simply says 0.
- The slice declares its own port (D-085):
  ``DraftAllocationRepository.suggest(query)`` reached through
  ``DraftAllocationUnitOfWork.allocation_suggestion``.
- A read: ONE transaction and NO commit (the D-093 Q12 / D-105 (4) / D-111 Q9
  precedent). Nothing is written; the SQL function is ``STABLE``.

The module is imported lazily, so this file collects before /code creates it (D-069).
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

USE_CASE_MODULE = "mesl_finance.envelopes.application.draft_allocation"
DOMAIN_MODULE = "mesl_finance.envelopes.domain.allocation_suggestion"


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _use_case_class() -> Any:
    return vars(_module(USE_CASE_MODULE))["DraftAllocation"]


def _query(amount: int = 1000, shares: dict[str, int] | None = None) -> Any:
    return vars(_module(DOMAIN_MODULE))["AllocationSuggestionQuery"](amount=amount, shares=shares)


class FakeSuggestion:
    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.result: list[Any] = [object()]

    async def suggest(self, query: Any) -> list[Any]:
        self.calls.append(query)
        return self.result


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.allocation_suggestion = FakeSuggestion()
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


async def test_the_draft_is_read_in_one_transaction_without_commit() -> None:
    uows: list[FakeUow] = []

    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    query = _query(amount=1000, shares={"4": 3, "5": 2})
    views = await _use_case_class()(factory)(query, actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert views == uow.allocation_suggestion.result
    assert uow.allocation_suggestion.calls == [query]
    assert not uow.committed


async def test_the_actor_is_the_transaction_actor() -> None:
    actors: list[str] = []

    def factory(actor: str) -> FakeUow:
        actors.append(actor)
        return FakeUow(actor)

    await _use_case_class()(factory)(_query(), actor="treasurer")

    assert actors == ["treasurer"]
