-- WORKED EXAMPLE 2 - label edits, the limited app role, tamper detection. Run in the SAME database right after example 1.
SELECT id AS e FROM ledger_transactions WHERE tenure_id = 2 AND kind = 'deposit' ORDER BY id LIMIT 1 \gset
\echo '--- healthy DB: EXPECT 0 rows'
SELECT * FROM verify_integrity();
SELECT ledger_checksum(2) AS chk_before \gset
SET ROLE labapp;
\echo '--- A. label edit as app role, logged automatically'
BEGIN; SET LOCAL app.actor = 'treasurer';
UPDATE ledger_transactions SET note = 'fees wk 27', tag = 'fees' WHERE id = :e;
COMMIT;
SELECT field, old_value, new_value, edited_by FROM ledger_label_edits ORDER BY id;
RESET ROLE;
SELECT (ledger_checksum(2) = :'chk_before') AS checksum_unchanged_by_label_edit;
SET ROLE labapp;
\echo '--- EXPECT FAIL: change recorded_by / kind / amount / delete / disable triggers / replica mode'
UPDATE ledger_transactions SET recorded_by = 'someone else' WHERE id = :e;
UPDATE ledger_transactions SET kind = 'expense' WHERE id = :e;
UPDATE ledger_lines SET amount = 1 WHERE id = 1;
DELETE FROM ledger_lines WHERE id = 1;
ALTER TABLE ledger_lines DISABLE TRIGGER ALL;
SET session_replication_role = replica;
\echo '--- EXPECT FAIL: label edit inside a closed tenure'
UPDATE ledger_transactions SET note = 'sneaky' WHERE id = 1;
\echo '--- fix amount = reversal + replacement in one DB transaction, as app role'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) VALUES (2,'reversal','2026-07-08','treasurer',:e,'amount typo');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-60);
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,replaces_id,note) VALUES (2,'deposit','2026-07-05','treasurer','other',:e,'fees wk 27');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,80);
COMMIT;
\echo '--- treasurer view (entries_current): one line, pointing at what it corrected'
SELECT id, kind, note, corrected_from FROM entries_current WHERE tenure_id = 2 ORDER BY id;
SELECT name, balance FROM envelope_balances ORDER BY id;
\echo '--- app role may close tenure via function'
RESET ROLE;
\echo '--- healthy again: EXPECT 0 rows'
SELECT * FROM verify_integrity();
\echo '--- superuser tamper: bypass trigger, change a closed-tenure amount'
ALTER TABLE ledger_lines DISABLE TRIGGER no_change_ln;
UPDATE ledger_lines SET amount = amount + 1 WHERE id = 1;
ALTER TABLE ledger_lines ENABLE TRIGGER no_change_ln;
SELECT * FROM verify_integrity();
\echo '--- restore the tampered amount, then close tenure as app role (EXPECT ok, 0 problems)'
ALTER TABLE ledger_lines DISABLE TRIGGER no_change_ln;
UPDATE ledger_lines SET amount = amount - 1 WHERE id = 1;
ALTER TABLE ledger_lines ENABLE TRIGGER no_change_ln;
SET ROLE labapp;
SELECT close_tenure('2026-12-31','treasurer','2027');
RESET ROLE;
SELECT name, balance FROM envelope_balances ORDER BY id;
SELECT * FROM verify_integrity();
