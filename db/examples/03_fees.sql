-- WORKED EXAMPLE 3 - members, rates, shutdown weeks, payments, waivers, refunds, closing with dues. Fresh database + schema.sql. 'EXPECT FAIL' lines are supposed to ERROR.
SELECT sunday_on_or_before(current_date) AS s0 \gset
\echo '=== setup (owner): tenure opens on this Sunday'
INSERT INTO tenures(name, opened_on) VALUES ('T1', :'s0');
SET ROLE labapp;
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);
INSERT INTO envelopes(name) VALUES ('Events and Workshops');
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0', 20, 'treasurer');
INSERT INTO members(name) VALUES ('A'),('B'),('C'),('D'),('E');
INSERT INTO membership_periods(member_id,start_date,end_date) VALUES
  (1, :'s0', NULL),                              -- A: member from the first Sunday
  (2, :'s0'::date + 3, NULL),                    -- B: joins Wednesday of week 1 -> first owed Sunday is week 2
  (3, :'s0', :'s0'::date + 10),                  -- C: leaves Wednesday of week 2 -> weeks 1 and 2 owed
  (5, :'s0', NULL);                              -- E
SELECT set_shutdown(:'s0'::date + 14, :'s0'::date + 14, true, 'treasurer', 'campus incident') AS weeks_marked;

\echo '=== payments (lump sums) as ledger deposits linked to members'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+1,'treasurer','weekly_fee',1);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,100); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+1,'treasurer','weekly_fee',2);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,30); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+1,'treasurer','weekly_fee',4);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,100); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+1,'treasurer','weekly_fee',5);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,50); COMMIT;

\echo '=== standing at week 5 (as_of s0+28), rate 20. EXPECT A:4wk/80/+20  B:3wk/60/-30 overdue2 oldest=+21  C:2wk/40/-40 overdue2 oldest=0  D:0/0/+100  E:4wk/80/-30'
SELECT who_name, is_member_now AS now, weeks_owed AS wks, owed, credits, balance, weeks_overdue AS od, oldest_unpaid_week - :'s0'::date AS oldest_day FROM member_standing(:'s0'::date+28) ORDER BY 1;

\echo '=== waiver for C (40), refund 60 + credit donation 40 for D'
INSERT INTO member_adjustments(member_id,kind,amount,occurred_on,recorded_by,note) VALUES (3,'waiver',40,:'s0'::date+11,'treasurer','left mid-week, forgiven');
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,member_id,note) VALUES (1,'expense',:'s0'::date+12,'treasurer',4,'refund of credit');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-60); COMMIT;
INSERT INTO member_adjustments(member_id,kind,amount,occurred_on,recorded_by,note) VALUES (4,'credit_donation',-40,:'s0'::date+12,'treasurer','donated to lab');
\echo 'EXPECT C balance 0, D credits 0 balance 0'
SELECT who_name, owed, credits, balance, weeks_overdue AS od FROM member_standing(:'s0'::date+28) WHERE who_name IN ('C','D') ORDER BY 1;

\echo '=== rate change to 30 from week 4 (s0+21). EXPECT A owed 100 bal 0; B owed 80 credits 30 bal -50 overdue 2; past weeks keep 20'
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date+21, 30, 'treasurer');
SELECT who_name, weeks_owed AS wks, owed, credits, balance, weeks_overdue AS od FROM member_standing(:'s0'::date+28) WHERE who_name IN ('A','B') ORDER BY 1;

\echo '=== fix amount for B payment 30 -> 40 (reversal + replacement, same member). EXPECT B credits 40 balance -40'
BEGIN;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,member_id,note)
  SELECT 1,'reversal',:'s0'::date+13,'treasurer',x.id,2,'amount typo' FROM ledger_transactions x WHERE x.member_id=2 AND x.kind='deposit';
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-30);
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id,replaces_id,note)
  SELECT 1,'deposit',:'s0'::date+1,'treasurer','weekly_fee',2,x.id,'corrected to 40' FROM ledger_transactions x WHERE x.member_id=2 AND x.kind='deposit';
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,40);
COMMIT;
SELECT who_name, owed, credits, balance, weeks_overdue AS od FROM member_standing(:'s0'::date+28) WHERE who_name = 'B';
\echo 'treasurer list shows one line for B: '
SELECT id, kind, note, corrected_from FROM entries_current WHERE member_id = 2;

\echo '=== shutdown can be undone: week 3 reopened -> A owes 20 more (EXPECT A owed 120), then closed again (100)'
SELECT set_shutdown(:'s0'::date+14, :'s0'::date+14, false, 'treasurer', 'was a mistake');
SELECT owed FROM member_standing(:'s0'::date+28) WHERE who_name='A';
SELECT set_shutdown(:'s0'::date+14, :'s0'::date+14, true, 'treasurer', 'confirmed closed');
SELECT owed FROM member_standing(:'s0'::date+28) WHERE who_name='A';

\echo '=== EXPECT FAIL x N: rejected mistakes'
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date-7, 25, 'treasurer');
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date+1, 25, 'treasurer');
INSERT INTO membership_periods(member_id,start_date) VALUES (1, :'s0'::date+7);
UPDATE membership_periods SET start_date = :'s0'::date - 100 WHERE member_id = 2;
UPDATE membership_periods SET end_date = :'s0'::date + 20 WHERE member_id = 3;
DELETE FROM membership_periods WHERE member_id = 1;
INSERT INTO member_adjustments(member_id,kind,amount,occurred_on,recorded_by,note) VALUES (1,'waiver',-5,:'s0','treasurer','x');
INSERT INTO member_adjustments(member_id,kind,amount,occurred_on,recorded_by) VALUES (1,'waiver',5,:'s0','treasurer');
UPDATE member_adjustments SET amount = 1 WHERE id = 1;
DELETE FROM member_adjustments WHERE id = 1;
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit',:'s0','treasurer','weekly_fee');
INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,member_id,note) VALUES (1,'transfer',:'s0','treasurer',1,'x');
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source,member_id) VALUES (1,'deposit',:'s0'::date+2,'treasurer','weekly_fee',1);
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,20); COMMIT;
SELECT set_shutdown(:'s0'::date+1, :'s0'::date+7, true, 'treasurer');
\echo '--- reversal with the wrong member (reverse A payment but label it member 2)'
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,reverses_id,member_id,note) VALUES (1,'reversal',:'s0'::date+5,'treasurer',(SELECT id FROM ledger_transactions WHERE member_id=1 AND kind='deposit'),2,'oops');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),1,-100); COMMIT;
\echo '--- direct edit of member on a payment / drop a trigger as app role'
UPDATE ledger_transactions SET member_id = 2 WHERE member_id = 1 AND kind = 'deposit';
RESET ROLE;
\echo '=== health: EXPECT 0 rows'
SELECT * FROM verify_integrity();

\echo '=== close tenure at s0+34 (as app role). EXPECT 5 snapshot rows, new tenure T2 opens s0+35'
SET ROLE labapp;
SELECT close_tenure(:'s0'::date+34,'treasurer','T2');
SELECT count(*) AS snapshots FROM tenure_member_snapshots;
SELECT name, opened_on - :'s0'::date AS opened_day, closed_on - :'s0'::date AS closed_day FROM tenures ORDER BY id;
\echo '=== EXPECT FAIL: touching the closed tenure'
SELECT set_shutdown(:'s0'::date+21, :'s0'::date+21, true, 'treasurer');
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date+28, 99, 'treasurer');
UPDATE membership_periods SET end_date = :'s0'::date + 30 WHERE member_id = 1;
INSERT INTO member_adjustments(member_id,kind,amount,occurred_on,recorded_by,note) VALUES (1,'waiver',20,:'s0'::date+30,'treasurer','late');
INSERT INTO members(name) VALUES ('F');
INSERT INTO membership_periods(member_id,start_date) VALUES (6, :'s0'::date+20);
\echo '=== ok: member F joining in the last days of the old tenure starts billing in the new one'
INSERT INTO membership_periods(member_id,start_date) VALUES (6, :'s0'::date+30);
\echo '=== arrears carry over: standing at s0+49. EXPECT A owed 190 credits 100 bal -90 overdue 3'
SELECT who_name, weeks_owed AS wks, owed, credits, balance, weeks_overdue AS od FROM member_standing(:'s0'::date+49) WHERE who_name IN ('A','F') ORDER BY 1;
RESET ROLE;
\echo '=== health after close: EXPECT 0 rows'
SELECT * FROM verify_integrity();
\echo '=== superuser tamper: bypass guard, mark a past week as shutdown -> dues of the closed tenure change'
ALTER TABLE shutdown_events DISABLE TRIGGER shutdown_guard;
INSERT INTO shutdown_events(week_start,is_shutdown,recorded_by) VALUES (:'s0'::date+21, true, 'sneaky');
ALTER TABLE shutdown_events ENABLE TRIGGER shutdown_guard;
SELECT * FROM verify_integrity();
