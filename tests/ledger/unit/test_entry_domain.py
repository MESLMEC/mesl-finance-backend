"""Domain tests for the ledger value objects (roadmap step 6.1).

Approved brief this session: Q1-Q5 were left unanswered, so the brief's labelled
suggestions stand (same pattern as D-062/D-064/D-066/D-070):
Q1=a exactly three value objects (`EntryKind`, `IncomeSource`, `LedgerLine`) and no
header/aggregate yet; Q2=a `IncomeSource` replaces the old `DepositSource` (one
enum); Q3=a type-only validation, the zero check and every per-kind shape stay
PostgreSQL's; Q4=a one new module `src/mesl_finance/ledger/domain/entry.py`;
Q5=a this single test file, with the lazy import the envelope/cost-center domain
tests use.

What these tests pin (the domain API /code must provide):
- `EntryKind`: the six members, name and value, of `entry_kind`
  (db/schema.sql:240)
- `IncomeSource`: the six members, name and value, of `income_source`
  (db/schema.sql:241)
- `LedgerLine(envelope_id=..., amount=...)`: an immutable signed whole-BDT line
  (db/schema.sql:266-272)
- `LedgerLine` refuses a non-`int` amount (message: "whole") or envelope id
  (message: "envelope") with `ValidationFailed`, i.e. the D-047 strictness
  applied to a signed amount

Not tested here, on purpose (Q3=a, AGENTS.md section 5): `amount <> 0` is the
column CHECK at db/schema.sql:270 and the per-kind shapes are `check_shape()` at
db/schema.sql:340-369; neither rule is duplicated in Python. A zero line is
therefore refused at COMMIT by PostgreSQL, not by this domain object.

The module is imported lazily, like the envelope/cost-center domain objects: ruff
classifies an import of a module that does not exist yet as third-party, so a
module-level import would have to be re-sorted the moment /code adds it (D-069).
The lazy import also keeps each test's failure individual ("module does not
exist yet") instead of one collection error for the whole file.
"""

from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

ENTRY_KIND_MEMBERS = [
    ("DEPOSIT", "deposit"),
    ("EXPENSE", "expense"),
    ("TRANSFER", "transfer"),
    ("SWEEP", "sweep"),
    ("OPENING", "opening"),
    ("REVERSAL", "reversal"),
]

INCOME_SOURCE_MEMBERS = [
    ("WEEKLY_FEE", "weekly_fee"),
    ("REGISTRATION", "registration"),
    ("SPONSORSHIP", "sponsorship"),
    ("ADMIN_GRANT", "admin_grant"),
    ("DONATION", "donation"),
    ("OTHER", "other"),
]


def _entry_module() -> ModuleType:
    try:
        return import_module("mesl_finance.ledger.domain.entry")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/entry.py does not exist yet")


def _entry_kind() -> Any:
    return vars(_entry_module())["EntryKind"]


def _income_source() -> Any:
    return vars(_entry_module())["IncomeSource"]


def _ledger_line_class() -> Any:
    return vars(_entry_module())["LedgerLine"]


def test_entry_kinds_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _entry_kind()] == ENTRY_KIND_MEMBERS


def test_income_sources_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _income_source()] == INCOME_SOURCE_MEMBERS


def test_a_positive_line_keeps_envelope_and_amount() -> None:
    line = _ledger_line_class()(envelope_id=1, amount=500)

    assert (line.envelope_id, line.amount) == (1, 500)


def test_a_negative_line_keeps_its_sign() -> None:
    line = _ledger_line_class()(envelope_id=2, amount=-150)

    assert (line.envelope_id, line.amount) == (2, -150)


@pytest.mark.parametrize("amount", [10.5, "100", True])
def test_a_line_refuses_a_non_integer_amount(amount: Any) -> None:
    with pytest.raises(ValidationFailed, match="whole"):
        _ledger_line_class()(envelope_id=1, amount=amount)


@pytest.mark.parametrize("envelope_id", ["1", 1.0, True])
def test_a_line_refuses_a_non_integer_envelope(envelope_id: Any) -> None:
    with pytest.raises(ValidationFailed, match="envelope"):
        _ledger_line_class()(envelope_id=envelope_id, amount=500)
