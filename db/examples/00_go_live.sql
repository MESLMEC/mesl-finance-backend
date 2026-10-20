-- WORKED EXAMPLE 0 - first day. Fresh database + schema.sql, run as the owner:  psql -d <db> -f 00_go_live.sql
-- =====================================================================================
-- FIRST DAY: how to start the lab on an empty database (run after schema.sql)
-- Step 0 is done ONCE by the database owner; everything after is what the app does as 'labapp'.
-- Run with:  psql -d <db> -f go_live.sql
-- =====================================================================================
SELECT sunday_on_or_before(current_date) AS this_sunday \gset

-- 0. OWNER ONLY: create the first tenure. (labapp cannot; later tenures are created by close_tenure.)
INSERT INTO tenures(name, opened_on) VALUES ('Tenure 2026-27', :'this_sunday');

SET ROLE labapp;                                  -- from here on: what your app does

-- 1. envelopes. The pool first (exactly one). Cap + priority only where you want automatic top-ups.
INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true);                       -- id 1
INSERT INTO envelopes(name, target_cap, alloc_priority) VALUES ('Admin and Misc', 1000, 1);      -- id 2
INSERT INTO envelopes(name) VALUES ('Member Projects'), ('Lab Projects'), ('Events and Workshops'),
                                   ('Competitions'), ('Components and Equipment'), ('Research'); -- ids 3..8

-- 2. starting money: ONE 'opening' entry (allowed once per tenure). Everything starts in the pool.
BEGIN;
INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, note)
VALUES ((SELECT id FROM tenures WHERE closed_on IS NULL), 'opening', :'this_sunday', 'treasurer',
        'balance carried from the old sheet');
INSERT INTO ledger_lines(transaction_id, envelope_id, amount)
VALUES (currval('ledger_transactions_id_seq'), (SELECT id FROM envelopes WHERE is_pool), 4200);
COMMIT;

-- 3. fee rate, effective from this Sunday (billing starts here: no history is billed)
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'this_sunday', 20, 'treasurer');

-- 4. members keep their real join dates; billing still starts at the first rate
INSERT INTO members(name) VALUES ('Member One'), ('Member Two');
INSERT INTO membership_periods(member_id, start_date) VALUES (1, '2024-02-10'), (2, '2025-08-01');
-- optional: carry an old debt (negative) or credit (positive) from the old sheet
INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by, note)
VALUES (2, 'opening', -40, :'this_sunday', 'treasurer', 'owed 2 weeks on the old sheet');

-- 5. a first fee payment: a deposit with source 'weekly_fee' linked to the member, into the pool
BEGIN;
INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source, member_id)
VALUES ((SELECT id FROM tenures WHERE closed_on IS NULL), 'deposit', :'this_sunday', 'treasurer', 'weekly_fee', 1);
INSERT INTO ledger_lines(transaction_id, envelope_id, amount)
VALUES (currval('ledger_transactions_id_seq'), (SELECT id FROM envelopes WHERE is_pool), 100);
COMMIT;

-- 6. assets you decided to track, with what the lab already has
INSERT INTO assets(name, mode, ownership, tag) VALUES ('Oscilloscope', 'individual', 'admin', 'ADM-001'),
                                                      ('ESP32 DevKit', 'counted', 'lab', NULL);
INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source, note) VALUES
  (1, 'acquired',  1, :'this_sunday', 'treasurer', 'admin', 'given by admin'),
  (2, 'acquired', 12, :'this_sunday', 'treasurer', 'other', 'stock at go-live');

-- 7. the first allocation session: look at the draft, then confirm the numbers you agreed
SELECT * FROM allocation_context;
SELECT envelope_name, phase, suggested FROM allocation_suggestion(2000, '{"3":3,"4":2,"5":2,"8":1}');
SELECT allocate('treasurer', :'this_sunday', 'first allocation', '{"2":1000,"3":400,"5":300}') AS session_tx;

-- 8. look around
SELECT name, balance FROM envelope_balances ORDER BY id;
SELECT who_name, weeks_owed, owed, credits, balance FROM member_standing(:'this_sunday'::date + 14);
SELECT asset_name, stock, with_members FROM asset_overview;
RESET ROLE;
SELECT * FROM verify_all();      -- empty = healthy
