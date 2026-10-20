-- WORKED EXAMPLE 6 - allocation sessions (draft + confirm), event leftovers, sweeps, envelope rules. Fresh database + schema.sql. 'EXPECT FAIL' lines are supposed to ERROR.
SELECT sunday_on_or_before(current_date) AS s0 \gset
INSERT INTO tenures(name, opened_on) VALUES ('T1', :'s0');
SET ROLE labapp;
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);                 -- 1
INSERT INTO envelopes(name,target_cap,alloc_priority) VALUES ('Admin and Misc',100,1);     -- 2
INSERT INTO envelopes(name,target_cap,alloc_priority) VALUES ('Components and Equipment',500,2); -- 3
INSERT INTO envelopes(name) VALUES ('Member Projects'),('Events and Workshops'),('Research');    -- 4,5,6
INSERT INTO members(name) VALUES ('X');
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit',:'s0','treasurer','other');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,3000); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0','treasurer','weekly_fee',1);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,50); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'transfer',:'s0','treasurer','opening split');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-490),(default,currval('ledger_transactions_id_seq'),2,40),(default,currval('ledger_transactions_id_seq'),3,450); COMMIT;

\echo '=== allocation screen header. EXPECT pool 2560, member credit 50, after credit 2510'
SELECT * FROM allocation_context;
\echo '=== suggestion for 1000 with shares 3:2:1. EXPECT Admin 60 cap_fill, Components 50 cap_fill, Projects 445, Events 297, Research 148 (sum 1000)'
SELECT envelope_name, balance, target_cap AS cap, gap, phase, suggested FROM allocation_suggestion(1000, '{"4":3,"5":2,"6":1}');
SELECT sum(suggested) AS total_suggested FROM allocation_suggestion(1000, '{"4":3,"5":2,"6":1}');
\echo '=== no shares and no history yet. EXPECT only the two cap fills (110); the rest stays in the pool'
SELECT envelope_name, phase, suggested FROM allocation_suggestion(1000);
\echo '=== small amount smaller than the gaps. EXPECT Admin 30, Components 0 (priority order)'
SELECT envelope_name, phase, suggested FROM allocation_suggestion(30) WHERE envelope_name IN ('Admin and Misc','Components and Equipment');

\echo '=== confirm the first session with the drafted numbers'
SELECT jsonb_object_agg(envelope_id::text, suggested) AS amts FROM allocation_suggestion(1000, '{"4":3,"5":2,"6":1}') WHERE suggested > 0 \gset
SELECT allocate('treasurer', :'s0'::date+1, 'first monthly allocation', :'amts'::jsonb) AS session_tx;
\echo 'EXPECT pool 1560, Admin 100, Components 500, Projects 445, Events 297, Research 148'
SELECT name, balance FROM envelope_balances ORDER BY id;

\echo '=== next suggestion reuses the last session proportions for uncapped envelopes. EXPECT Projects 300, Events 200, Research 100, caps 0'
SELECT envelope_name, phase, suggested FROM allocation_suggestion(600) ORDER BY envelope_id;

\echo '=== a second session, then it is voided: suggestion must IGNORE the voided session (EXPECT still 300/200/100)'
SELECT allocate('treasurer', :'s0'::date+2, 'research top-up', '{"6":100}') AS session2;
SELECT max(ledger_transaction_id) AS s2 FROM allocation_sessions \gset
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal',:'s0'::date+2,'treasurer',:s2,'wrong envelope');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,100),(default,currval('ledger_transactions_id_seq'),6,-100);
COMMIT;
SELECT envelope_name, suggested FROM allocation_suggestion(600) WHERE envelope_name IN ('Member Projects','Events and Workshops','Research') ORDER BY envelope_id;

\echo '=== caps are guidance: the committee can override (400 into Admin and Misc, cap 100) EXPECT ok'
SELECT allocate('treasurer', :'s0'::date+3, 'emergency admin spend', '{"2":400}') AS override_tx;
\echo '=== EXPECT FAIL x N: bad allocations'
SELECT allocate('treasurer', :'s0'::date+3, 'too much', '{"4":999999}');
SELECT allocate('treasurer', :'s0'::date+3, 'to itself', '{"1":10}');
SELECT allocate('treasurer', :'s0'::date+3, 'negative', '{"4":-5}');
SELECT allocate('treasurer', :'s0'::date+3, 'zero', '{"4":0}');
SELECT allocate('treasurer', :'s0'::date+3, 'unknown', '{"99":10}');
SELECT allocate('treasurer', :'s0'::date+3, 'text', '{"4":"abc"}');
SELECT allocate('treasurer', :'s0'::date+3, 'array', '[1,2]');
SELECT allocate('treasurer', :'s0'::date+3, 'empty', '{}');
SELECT allocate('treasurer', :'s0'::date+3, '', '{"4":10}');
DELETE FROM allocation_sessions;

\echo '=== envelope guard. EXPECT FAIL: change pool flag, deactivate non-empty envelope, delete; EXPECT ok: deactivate an empty one'
UPDATE envelopes SET is_pool = false WHERE is_pool;
UPDATE envelopes SET active = false WHERE name = 'Research';
UPDATE envelopes SET active = false WHERE is_pool;
INSERT INTO envelopes(name) VALUES ('Old idea');
UPDATE envelopes SET active = false WHERE name = 'Old idea';
SELECT allocate('treasurer', :'s0'::date+3, 'to inactive', jsonb_build_object((SELECT id::text FROM envelopes WHERE name='Old idea'), 10));

\echo '=== event leftovers and the end-of-event sweep'
INSERT INTO cost_centers(name,kind) VALUES ('Robotics Workshop','event');
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,cost_center_id,note) VALUES (1,'deposit',:'s0'::date+4,'treasurer','admin_grant',1,'admin event grant');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),5,1000); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,cost_center_id,tag) VALUES (1,'expense',:'s0'::date+5,'treasurer',1,'catering');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),5,-400); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,cost_center_id,tag) VALUES (1,'expense',:'s0'::date+5,'treasurer',1,'decorations');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),5,-100); COMMIT;
\echo 'EXPECT in 1000, out 500, swept 0, leftover 500'
SELECT name, money_in, money_out, swept, leftover FROM cost_center_summary;
\echo '=== void the decorations expense (reversal carries no event label on purpose). EXPECT out 400, leftover 600'
SELECT id AS dec FROM ledger_transactions WHERE tag = 'decorations' \gset
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal',:'s0'::date+6,'treasurer',:dec,'not bought');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),5,100); COMMIT;
SELECT name, money_in, money_out, swept, leftover FROM cost_center_summary;
\echo '=== sweep the leftover to the pool. EXPECT swept 600, leftover 0, Events envelope 297 (297+1000-400-600), pool +600'
SELECT pool_balance AS pool_before FROM allocation_context \gset
SELECT sweep_leftover(1, 5, 'treasurer', :'s0'::date+7, 'event over; leftover back to pool') AS sweep_tx;
SELECT name, money_in, money_out, swept, leftover FROM cost_center_summary;
SELECT name, balance FROM envelope_balances WHERE name = 'Events and Workshops';
SELECT pool_balance - :pool_before AS pool_gain FROM allocation_context;
\echo '=== EXPECT FAIL: nothing left to sweep; sweep without an event; sweep out of the pool'
SELECT sweep_leftover(1, 5, 'treasurer', :'s0'::date+7, 'again');
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'sweep',:'s0'::date+7,'treasurer','no event named'); COMMIT;
SELECT sweep_leftover(1, 1, 'treasurer', :'s0'::date+7, 'from pool');
\echo '=== undo the sweep with a reversal. EXPECT swept 0, leftover 600 again; then sweeping works a second time'
SELECT id AS sw FROM ledger_transactions WHERE kind = 'sweep' \gset
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal',:'s0'::date+8,'treasurer',:sw,'swept too early');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),5,600),(default,currval('ledger_transactions_id_seq'),1,-600); COMMIT;
SELECT name, swept, leftover FROM cost_center_summary;
SELECT sweep_leftover(1, 5, 'treasurer', :'s0'::date+9, 'event really over') AS sweep_tx2;
SELECT name, swept, leftover FROM cost_center_summary;
RESET ROLE;
\echo '=== health: EXPECT 0 rows'
SELECT * FROM verify_all();
\echo '=== close tenure and check again: EXPECT 0 rows; sessions survive'
SET ROLE labapp;
SELECT close_tenure(:'s0'::date+20,'treasurer','T2') AS new_tenure;
RESET ROLE;
SELECT * FROM verify_all();
SELECT count(*) AS allocation_sessions_kept FROM allocation_sessions;
SELECT name, balance FROM envelope_balances ORDER BY id;
