"""Domain tests for the envelope object (roadmap step 5.1).

Approved brief answers this session: Q3=b (cap/priority are set on create AND
through a separate `settings` action), the rest as the brief's suggestions
(Q4=a no balance in the list, Q6=a PostgreSQL owns the cap check, Q7=a blank
names refused by the app, Q8=a the pool may be renamed).

What these tests pin (the domain API /code must provide):
- `Envelope.create(name=..., target_cap=None, alloc_priority=None)`
- `Envelope.rename(name)` and `Envelope.with_settings(target_cap, alloc_priority)`
  return the updated object (the domain object is treated as immutable)
- omitted cap/priority stay None (D-021: no defaults; caps are data)
- a cap of 0 is data, not "no cap" (db/schema.sql:69 allows target_cap >= 0)
- a blank name is a ValidationFailed (Q7=a; db/schema.sql:68 only says
  NOT NULL, so the blank rule lives in the app and is recorded as such)

Not tested here, on purpose (Q6=a, AGENTS.md section 5): a negative cap is the
database's CHECK, pinned end to end in tests/envelopes/api/test_envelopes_api.py.

The domain class is imported lazily, like the `Unique` helper in
tests/shared/test_error_translator.py: ruff classifies an import of a module
that does not exist yet as third-party, so a module-level import would have to
be re-sorted the moment /code adds the package. The lazy import also keeps
each test's failure individual ("module does not exist yet") instead of one
collection error for the whole file.
"""

from importlib import import_module
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed


def _envelope_class() -> Any:
    try:
        module = import_module("mesl_finance.envelopes.domain.envelope")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/envelopes/domain/envelope.py does not exist yet")
    return vars(module)["Envelope"]


def make(**overrides: Any) -> Any:
    fields: dict[str, Any] = {"name": "Research"}
    fields.update(overrides)
    return _envelope_class().create(**fields)


def test_create_keeps_cap_and_priority_null_when_omitted() -> None:
    envelope = make()

    assert (envelope.name, envelope.target_cap, envelope.alloc_priority) == ("Research", None, None)


def test_create_keeps_a_zero_cap() -> None:
    envelope = make(target_cap=0, alloc_priority=None)

    assert envelope.target_cap == 0


@pytest.mark.parametrize("name", ["", "   ", "\t\n "])
def test_create_rejects_a_blank_name(name: str) -> None:
    with pytest.raises(ValidationFailed, match="name"):
        make(name=name)


def test_rename_rejects_a_blank_name() -> None:
    with pytest.raises(ValidationFailed, match="name"):
        make().rename("  ")


def test_rename_keeps_cap_and_priority() -> None:
    renamed = make(target_cap=500, alloc_priority=2).rename("Research Fund")

    assert (renamed.name, renamed.target_cap, renamed.alloc_priority) == (
        "Research Fund",
        500,
        2,
    )


def test_settings_replace_both_fields_and_keep_the_name() -> None:
    updated = make().with_settings(target_cap=750, alloc_priority=3)

    assert (updated.name, updated.target_cap, updated.alloc_priority) == ("Research", 750, 3)


def test_settings_can_clear_both_fields() -> None:
    cleared = make(target_cap=750, alloc_priority=3).with_settings(
        target_cap=None, alloc_priority=None
    )

    assert (cleared.target_cap, cleared.alloc_priority) == (None, None)
