-- WORKED EXAMPLE 1 - ledger basics, rejected mistakes, reversals, closing a tenure. Fresh database + schema.sql. Lines marked 'EXPECT FAIL' are SUPPOSED to print an ERROR.
\set ON_ERROR_STOP off
INSERT INTO tenures(name, opened_on) VALUES ('2026', '2026-01-01');
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);
INSERT INTO envelopes(name) VALUES ('Events and Workshops'),('Admin and Misc');
INSERT INTO cost_centers(name,kind) VALUES ('Workshop 1','event');

\echo '--- 1 deposit 500 to pool'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,note) VALUES (1,'deposit','2026-02-01','tres','other','fees');
INSERT INTO ledger_lines(transaction_id,envelope_id,amount) VALUES (1,1,500);
COMMIT;
\echo '--- 2 transfer 200 pool->events'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'transfer','2026-02-02','tres','for workshop');
INSERT INTO ledger_lines(transaction_id,envelope_id,amount) VALUES (2,1,-200),(2,2,200);
COMMIT;
\echo '--- 3 expense 150 events'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,cost_center_id,tag) VALUES (1,'expense','2026-02-03','tres',1,'catering');
INSERT INTO ledger_lines(transaction_id,envelope_id,amount) VALUES (3,2,-150);
COMMIT;
SELECT name,balance FROM envelope_balances ORDER BY id;

\echo '--- 4 EXPECT FAIL overdraw: expense 100 from events (balance 50)'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by) VALUES (1,'expense','2026-02-04','tres');
INSERT INTO ledger_lines(transaction_id,envelope_id,amount) VALUES (currval('ledger_transactions_id_seq'),2,-100);
COMMIT;
\echo '--- 5 EXPECT FAIL update / delete / truncate'
UPDATE ledger_lines SET amount = 999 WHERE id = 1;
DELETE FROM ledger_transactions WHERE id = 1;
TRUNCATE ledger_lines CASCADE;
\echo '--- 6 EXPECT FAIL bad shapes'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit','2026-02-05','tres','other'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-5); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'transfer','2026-02-05','tres','x'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-5),(default,currval('ledger_transactions_id_seq'),2,4); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit','2026-02-05','tres','other'); COMMIT;
\echo '--- 7 undo the catering expense via reversal (EXPECT balance events back to 200)'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,cost_center_id,reverses_id,note) VALUES (1,'reversal','2026-02-06','tres',1,3,'typo in amount');
INSERT INTO ledger_lines(transaction_id,envelope_id,amount) VALUES (currval('ledger_transactions_id_seq'),2,150);
COMMIT;
SELECT name,balance FROM envelope_balances ORDER BY id;
SELECT id,kind,is_voided FROM entries ORDER BY id;
\echo '--- 8 EXPECT FAIL reverse the same entry twice / reverse a reversal / wrong mirror'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal','2026-02-06','tres',3,'again'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,150); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal','2026-02-06','tres',4,'undo undo'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,-150); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal','2026-02-06','tres',1,'wrong amount'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-499); COMMIT;
\echo '--- 9 EXPECT FAIL reversing deposit 1 would push pool negative? pool has 300 so reversing 500 must fail'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (1,'reversal','2026-02-07','tres',1,'void'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-500); COMMIT;

\echo '--- 10 close tenure on 2026-06-30'
SELECT close_tenure('2026-06-30','tres','2026-27');
SELECT id,name,opened_on,closed_on,left(closing_checksum,12) chk FROM tenures ORDER BY id;
SELECT name,balance FROM envelope_balances ORDER BY id;
\echo '--- 11 EXPECT FAIL entry into closed tenure 1, and backdated entry in tenure 2'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit','2026-03-01','tres','other'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,10); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (2,'deposit','2026-03-01','tres','other'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,10); COMMIT;
\echo '--- 12 EXPECT FAIL reversing an entry of the closed tenure, editing a closed tenure row'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (2,'reversal','2026-07-02','tres',1,'old'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-500); COMMIT;
UPDATE tenures SET closed_on = '2026-12-31' WHERE id = 1;
\echo '--- 13 ok: new-tenure deposit works'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (2,'deposit','2026-07-05','tres','other'); INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,60); COMMIT;
SELECT name,balance FROM envelope_balances ORDER BY id;
