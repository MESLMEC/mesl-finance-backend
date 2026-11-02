-- Issue #11: a lab-money purchase is one expense + one acquisition + a link
-- between them (D-163). PostgreSQL owns the rule so every writer is bound by it
-- (direct SQL, the future Go backend), not only the app.
ALTER TABLE asset_events
  ADD CONSTRAINT asset_purchase_needs_link
  CHECK (source IS DISTINCT FROM 'purchase' OR ledger_transaction_id IS NOT NULL);
