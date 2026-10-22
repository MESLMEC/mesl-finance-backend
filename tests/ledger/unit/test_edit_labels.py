"""The EditLabels use case: ONE transaction writes one label edit.

Approved contract (step 6.6 brief; Q7=b, the rest left unanswered so the
brief's labelled suggestions stand): the slice declares its own port (D-085)
and the repository returns the entry's labels after the write (Q5=a). No open
tenure is asked for: ``tx_label_edit`` resolves the entry's own tenure, and the
database refuses a closed one itself (db/schema.sql:387-388).
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest

from mesl_finance.shared.errors import DomainError, UnknownReference, ValidationFailed

DAY = date(2026, 10, 20)


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _edit_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.edit_labels"))["EditLabels"]


def _command_class() -> Any:
    return vars(_module("mesl_finance.ledger.application.edit_labels"))["EditLabelsCommand"]


def command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "entry_id": 42,
        "fields": frozenset({"note"}),
        "note": "fees wk 27",
    }
    fields.update(overrides)
    return _command_class()(**fields)


class FakeLedger:
    def __init__(self, fail_with: DomainError | None = None) -> None:
        self.edits: list[Any] = []
        self.result = object()
        self._fail_with = fail_with

    async def edit_labels(self, label_edit: Any) -> Any:
        if self._fail_with is not None:
            raise self._fail_with
        self.edits.append(label_edit)
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


def _factory(uows: list[FakeUow], failure: DomainError | None = None) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor, FakeLedger(fail_with=failure)))
        return uows[-1]

    return factory


async def test_it_writes_the_edit_and_commits() -> None:
    uows: list[FakeUow] = []

    view = await _edit_class()(_factory(uows))(command(), actor="treasurer")

    uow = uows[0]
    assert view is uow.ledger.result
    assert uow.actor == "treasurer"
    assert uow.committed
    label_edit = uow.ledger.edits[0]
    assert (
        label_edit.entry_id,
        label_edit.fields,
        label_edit.note,
        label_edit.occurred_on,
    ) == (42, frozenset({"note"}), "fees wk 27", None)


async def test_an_invalid_edit_never_opens_a_transaction() -> None:
    uows: list[FakeUow] = []

    with pytest.raises(ValidationFailed):
        await _edit_class()(_factory(uows))(command(fields=frozenset[str]()), actor="treasurer")

    assert uows == []


async def test_a_failed_write_is_not_committed() -> None:
    uows: list[FakeUow] = []

    with pytest.raises(UnknownReference):
        await _edit_class()(_factory(uows, UnknownReference("entry 42 does not exist")))(
            command(), actor="treasurer"
        )

    assert not uows[0].committed
