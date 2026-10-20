-- WORKED EXAMPLE 7 - reconciliation: match the screen to your notes, review only entries since the last match, find a typo from the difference. Fresh database + schema.sql. 'EXPECT FAIL' lines are supposed to ERROR.
SELECT sunday_on_or_before(current_date) AS s0 \gset
INSERT INTO tenures(name, opened_on) VALUES ('T1', :'s0');
SET ROLE labapp;
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);        -- 1
INSERT INTO envelopes(name) VALUES ('Events and Workshops');                     -- 2
INSERT INTO members(name) VALUES ('A');

\echo '=== MONTH 1: entries 1-3 (opening 1000, deposit 200, expense 50) -> screen total 1150'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'opening',:'s0','treasurer','go-live');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,1000); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,note) VALUES (1,'deposit',:'s0','treasurer','other','sponsor');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,200); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0','treasurer','stationery');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-50); COMMIT;
\echo 'no check yet: the whole history is unverified (EXPECT 3 entries, last match empty)'
SELECT entries_since_last_match, last_match_date FROM reconciliation_status;
\echo '=== I count 1150 in my pocket notes: EXPECT matched = t'
SELECT reconcile('treasurer', 1150, 'month 1 matched') AS check_no;
SELECT id, through_entry_id, system_total, counted_total, difference, matched FROM reconciliations;
\echo 'EXPECT 0 entries since last match, 0 days'
SELECT entries_since_last_match, days_since_last_match, latest_attempt_matched FROM reconciliation_status;

\echo '=== MONTH 2: entries 4-7. (4) fee 100 from A, (5) expense typed 120 (really 12), (6) transfer 300 to Events, (7) Events expense typed 45 (really 54)'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+7,'treasurer','weekly_fee',1);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,100); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0'::date+8,'treasurer','printing');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-120); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,note) VALUES (1,'transfer',:'s0'::date+9,'treasurer','events money');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-300),(default,currval('ledger_transactions_id_seq'),2,300); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0'::date+10,'treasurer','snacks');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,-45); COMMIT;
\echo 'screen total now 1085. My notes say 1193 (money really there): EXPECT matched = f, difference 108'
SELECT reconcile('treasurer', 1193, 'month 2: does not match') AS check_no;
SELECT id, system_total, counted_total, difference, matched FROM reconciliations ORDER BY id;
\echo '=== the timer: last match is check 1; EXPECT 4 entries to review (ids 4..7), latest attempt f, difference 108'
SELECT last_match_id, last_match_through_entry, entries_since_last_match, latest_attempt_matched, latest_difference FROM reconciliation_status;
SELECT id, kind, occurred_on - :'s0'::date AS day, net_effect, size, tag, note FROM unverified_entries;

\echo '=== suspects. diff +108: EXPECT entry 5 (an extra zero: 120 should be 12)'
SELECT entry_id, kind, effect, why FROM difference_suspects(108);
\echo '=== diff -9: EXPECT entry 7 (swapped digits 45 vs 54)'
SELECT entry_id, kind, effect, why FROM difference_suspects(-9);
\echo '=== diff +120: EXPECT entry 5 (recorded but never happened / typed twice)'
SELECT entry_id, effect, why FROM difference_suspects(120);
\echo '=== diff +240: EXPECT entry 5 (wrong direction)'
SELECT entry_id, effect, why FROM difference_suspects(240);
\echo '=== diff -405: EXPECT entry 7 (a zero left out: 45 should be 450)'
SELECT entry_id, effect, why FROM difference_suspects(-405);
\echo '=== diff -300 limited to the Events envelope: EXPECT entry 6 (the transfer)'
SELECT entry_id, kind, effect, why FROM difference_suspects(-300, 2);
\echo '=== a forgotten entry cannot be found: diff +77 EXPECT 0 rows'
SELECT entry_id, why FROM difference_suspects(77);

\echo '=== fix entry 5 (120 -> 12) with reversal + replacement, then count again'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,note) SELECT 1,'reversal',:'s0'::date+11,'treasurer',id,'amount typo' FROM ledger_transactions WHERE tag='printing';
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,120);
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag,replaces_id,note) SELECT 1,'expense',:'s0'::date+8,'treasurer','printing',id,'corrected to 12' FROM ledger_transactions WHERE tag='printing' AND kind='expense' AND reverses_id IS NULL;
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-12);
COMMIT;
\echo 'EXPECT screen total 1193 -> matched = t'
SELECT reconcile('treasurer', 1193, 'month 2 matched after fixing entry 5') AS check_no;
SELECT id, system_total, counted_total, difference, matched FROM reconciliations ORDER BY id;
SELECT entries_since_last_match, latest_attempt_matched FROM reconciliation_status;

\echo '=== per-envelope notes: totals agree but my notes put 10 in the wrong envelope. EXPECT matched = f with difference 0'
SELECT name, balance FROM envelope_balances ORDER BY id;
SELECT reconcile('treasurer', 1193, 'envelope notes', '{"1":948,"2":245}') AS check_no;
SELECT id, difference, matched FROM reconciliations ORDER BY id DESC LIMIT 1;
SELECT envelope_id, system_balance, counted FROM reconciliation_envelopes ORDER BY reconciliation_id DESC, envelope_id LIMIT 2;
\echo 'correct notes: EXPECT matched = t'
SELECT reconcile('treasurer', 1193, 'envelope notes fixed', '{"1":938,"2":255}') AS check_no;
SELECT id, difference, matched FROM reconciliations ORDER BY id DESC LIMIT 1;
SELECT last_match_id, entries_since_last_match FROM reconciliation_status;

\echo '=== EXPECT FAIL x N'
SELECT reconcile('treasurer', -5, 'negative');
SELECT reconcile('treasurer', 100, 'bad envelope', '{"99":10}');
SELECT reconcile('treasurer', 100, 'bad amount', '{"1":"abc"}');
SELECT reconcile('treasurer', 100, 'not an object', '[1,2]');
INSERT INTO reconciliations(tenure_id,through_entry_id,checked_on,system_total,counted_total,difference,matched,recorded_by) VALUES (1,1,current_date,1,1,0,true,'x');
UPDATE reconciliations SET matched = true WHERE id = 2;
DELETE FROM reconciliations WHERE id = 1;

\echo '=== one more entry after the match: the review list shows only it'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0'::date+14,'treasurer','tea');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-30); COMMIT;
SELECT id, kind, net_effect, tag FROM unverified_entries;
\echo '=== a LATE entry for an OLD date is still found (recorded later, dated before the match)'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0'::date+1,'treasurer','forgotten bus fare');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-25); COMMIT;
SELECT id, kind, occurred_on - :'s0'::date AS day, net_effect, tag FROM unverified_entries;
\echo 'EXPECT diff +25+30 = 55 narrowed: suspects for +25 finds the late bus fare'
SELECT entry_id, effect, why FROM difference_suspects(25);
RESET ROLE;
\echo '=== health: EXPECT 0 rows'
SELECT * FROM verify_all();

\echo '=== close the tenure: the carry-over opening must NOT appear as unverified; reconciliations continue in T2'
SET ROLE labapp;
SELECT close_tenure(:'s0'::date+20,'treasurer','T2') AS new_tenure;
\echo 'EXPECT only the 2 entries recorded after the last match (tea, bus fare); opening excluded'
SELECT id, kind, net_effect, tag FROM unverified_entries;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (2,'deposit',:'s0'::date+21,'treasurer','other');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,40); COMMIT;
\echo 'system total in T2 = 1193 - 30 - 25 + 40 = 1178: EXPECT matched = t'
SELECT reconcile('treasurer', 1178, 'first match in the new tenure') AS check_no;
SELECT id, tenure_id, system_total, matched FROM reconciliations ORDER BY id DESC LIMIT 1;
SELECT entries_since_last_match FROM reconciliation_status;
RESET ROLE;
\echo '=== health: EXPECT 0 rows'
SELECT * FROM verify_all();
\echo '=== superuser tamper: rewrite what the screen showed at the failed check (#2). EXPECT 1 problem'
ALTER TABLE reconciliations DISABLE TRIGGER no_change_rec;
UPDATE reconciliations SET system_total = system_total + 5, difference = difference - 5 WHERE id = 2;
ALTER TABLE reconciliations ENABLE TRIGGER no_change_rec;
SELECT * FROM verify_all();
