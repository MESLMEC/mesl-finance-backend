"""Domain tests for the fee value objects (roadmap step 7.2).

Approved brief this session: every question was left unanswered, so the brief's
labelled suggestions stand (same pattern as D-062/D-064/D-066/D-070/D-076/D-079/
D-082/D-086/D-088/D-090/D-093/D-096/D-099/D-101): Q1=a one new `fees` feature with
`domain/fee_rate.py` and `domain/shutdown.py` and ONE repository; Q5=a the amount is
a strict `int` and PostgreSQL owns `amount > 0`; Q8=a domain + API tests only, no
fake unit of work.

What these tests pin (the domain API /code must provide):
- `FeeRate(effective_from=..., amount=...)`: an immutable whole-BDT weekly rate
  (db/schema.sql:106-112), refusing a non-`int` amount with `ValidationFailed`
  (the D-047 strictness, message contains "whole");
- `ShutdownRange(from_week=..., to_week=..., is_shutdown=True, reason="")`: an
  immutable request for `set_shutdown()` (db/schema.sql:220-233), defaulting to a
  shutdown with no reason.

Not tested here, on purpose (AGENTS.md section 5, D-076 Q3=a): the Sunday rule,
`amount > 0`, the tenure floor, "to-week is before from-week" and the closed-tenure
wall all stay PostgreSQL's (`fee_rates_effective_from_check`,
`fee_rates_amount_check`, `rate_guard`, `set_shutdown`, `shutdown_guard`); none of
them is duplicated in Python.

The modules are imported lazily: ruff classifies an import of a module that does not
exist yet as third-party, so a module-level import would have to be re-sorted the
moment /code adds it (D-069); the lazy import also keeps each test's failure
individual ("module does not exist yet") instead of one collection error.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

SUNDAY = date(2026, 10, 18)
NEXT_SUNDAY = date(2026, 10, 25)


def _fee_rate_module() -> ModuleType:
    try:
        return import_module("mesl_finance.fees.domain.fee_rate")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/fees/domain/fee_rate.py does not exist yet")


def _shutdown_module() -> ModuleType:
    try:
        return import_module("mesl_finance.fees.domain.shutdown")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/fees/domain/shutdown.py does not exist yet")


def _fee_rate_class() -> Any:
    return vars(_fee_rate_module())["FeeRate"]


def _shutdown_range_class() -> Any:
    return vars(_shutdown_module())["ShutdownRange"]


def test_fee_rate_holds_the_sunday_and_the_amount() -> None:
    rate = _fee_rate_class()(effective_from=SUNDAY, amount=20)

    assert (rate.effective_from, rate.amount) == (SUNDAY, 20)


@pytest.mark.parametrize("amount", [10.5, "20", True])
def test_fee_rate_refuses_a_non_whole_amount(amount: Any) -> None:
    with pytest.raises(ValidationFailed, match="whole"):
        _fee_rate_class()(effective_from=SUNDAY, amount=amount)


def test_shutdown_range_defaults_to_a_shutdown_with_no_reason() -> None:
    week = _shutdown_range_class()(from_week=SUNDAY, to_week=NEXT_SUNDAY)

    assert (week.from_week, week.to_week) == (SUNDAY, NEXT_SUNDAY)
    assert (week.is_shutdown, week.reason) == (True, "")


def test_shutdown_range_carries_an_undo_and_its_reason() -> None:
    week = _shutdown_range_class()(
        from_week=SUNDAY, to_week=SUNDAY, is_shutdown=False, reason="was a mistake"
    )

    assert (week.is_shutdown, week.reason) == (False, "was a mistake")
