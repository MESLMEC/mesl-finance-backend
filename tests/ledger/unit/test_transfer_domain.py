"""Transfer value object (ROADMAP 6.4): money moving between two envelopes.

The schema's per-kind shape ("a transfer needs two or more lines that sum to
zero", db/schema.sql:353-354), the non-zero line amount (:270), the non-blank
note (:259), the overdraw guard (:319-337) and the inactive-envelope rule
(:324) stay PostgreSQL's. The domain refuses only a non-positive or non-whole
amount, a non-integer envelope reference, and the same envelope on both sides
(step 6.4 brief, Q5=a).
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 2, 2)
POOL, EVENTS = 1, 2


def _transfer_class() -> Any:
    """The module under test does not exist yet (lazy import, see D-069)."""
    try:
        module: ModuleType = import_module("mesl_finance.ledger.domain.transfer")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/ledger/domain/transfer.py does not exist yet")
    return vars(module)["Transfer"]


def make(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "amount": 200,
        "occurred_on": DAY,
        "from_envelope_id": POOL,
        "to_envelope_id": EVENTS,
        "note": "for workshop",
    }
    fields.update(overrides)
    return _transfer_class().create(**fields)


def test_a_transfer_holds_its_amount_date_and_two_envelopes() -> None:
    transfer = make(tag="workshop", cost_center_id=3)

    assert transfer.amount == 200
    assert transfer.occurred_on == DAY
    assert (transfer.from_envelope_id, transfer.to_envelope_id) == (POOL, EVENTS)
    assert transfer.note == "for workshop"
    assert (transfer.tag, transfer.cost_center_id) == ("workshop", 3)


@pytest.mark.parametrize("amount", [0, -1])
def test_a_zero_or_negative_amount_is_refused(amount: int) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


@pytest.mark.parametrize("amount", [10.5, "200", True])
def test_a_non_integer_amount_is_refused(amount: object) -> None:
    with pytest.raises(ValidationFailed):
        make(amount=amount)


@pytest.mark.parametrize("field", ["from_envelope_id", "to_envelope_id"])
@pytest.mark.parametrize("value", [1.0, "1", True])
def test_a_non_integer_envelope_id_is_refused(field: str, value: object) -> None:
    with pytest.raises(ValidationFailed, match="envelope"):
        make(**{field: value})


def test_the_two_envelopes_must_differ() -> None:
    with pytest.raises(ValidationFailed):
        make(to_envelope_id=POOL)
