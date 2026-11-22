-- Issue #4: server-side idempotency for the money-writing endpoints (slice 1:
-- POST /deposits). PostgreSQL owns the rule so every writer is bound by it.
--
-- A key is scoped to the actor (the treasurer login, D-006): the pair
-- (actor, key) is the identity, so two actors may reuse a key independently.
-- `request_hash` detects a key reused with a DIFFERENT request (-> 409).
-- `result` is the use case's result value, replayed verbatim on a retry; it is
-- NULL only between a claim and the same transaction's remember, so a
-- committed row always carries it.
CREATE TABLE idempotency_keys (
  actor        text        NOT NULL,
  key          text        NOT NULL,
  request_hash text        NOT NULL,
  result       jsonb,
  recorded_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (actor, key),
  CHECK (length(btrim(actor)) > 0),
  CHECK (length(btrim(key)) > 0)
);

-- The app role reads, claims (INSERT) and fills in the result (UPDATE).
GRANT SELECT, INSERT, UPDATE ON idempotency_keys TO labapp;
