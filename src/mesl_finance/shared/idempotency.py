"""The idempotency-key port (issue #4). Pure Python: no SQL, no database.

A write endpoint receives an `Idempotency-Key` from the client. `claim` is the
one call that decides whether this request is new or a replay:

- `claim(key, fingerprint)` returns the stored result when this actor and key
  already succeeded (a replay), or None when the key is free (the caller must
  then do the write and call `remember`). A key that was already used with a
  DIFFERENT fingerprint is a conflict (raised, 409).
- `remember(key, result)` records the result of a write that succeeded in the
  SAME transaction, so the key and the write commit together.
- `result_for(key)` reads a stored result back (None when there is none).

The port is deliberately tiny: the actor comes from the transaction the store
runs in, so the identity is `(actor, key)` (issue #4 Q6=a).
"""

from typing import Any, Protocol


class IdempotencyStore(Protocol):
    async def claim(self, key: str, fingerprint: str) -> Any:
        """The stored result of an earlier success, or None for a free key."""
        ...

    async def remember(self, key: str, result: Any) -> None:
        """Record the result of the write that just succeeded."""
        ...

    async def result_for(self, key: str) -> Any:
        """The stored result, or None when the key was never remembered."""
        ...
