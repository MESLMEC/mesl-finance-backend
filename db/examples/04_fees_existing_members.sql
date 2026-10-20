-- WORKED EXAMPLE 4 - go-live with members who joined years ago; rate dating rules. Fresh database + schema.sql.
SELECT sunday_on_or_before(current_date) AS s0 \gset
\echo '=== go-live in the middle of an existing life: tenure opened 2 weeks before this Sunday, existing member joined in 2023'
INSERT INTO tenures(name, opened_on) VALUES ('T1', :'s0'::date - 14);
SET ROLE labapp;
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);
INSERT INTO members(name) VALUES ('Old member');
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0', 20, 'treasurer');
INSERT INTO membership_periods(member_id,start_date) VALUES (1, '2023-01-01');
\echo 'EXPECT 2 weeks owed at s0+7 (billing starts at first rate, no history), 40'
SELECT who_name, weeks_owed, owed, balance FROM member_standing(:'s0'::date+7);
\echo '=== EXPECT FAIL: rate dated inside the open tenure but before the current week'
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date-7, 25, 'treasurer');
\echo '=== EXPECT ok: this Sunday and a future Sunday'
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0', 22, 'treasurer');
INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES (:'s0'::date+7, 25, 'treasurer');
\echo 'EXPECT latest row for the same week wins: s0 week = 22, next week = 25 -> owed 22+25 = 47'
SELECT who_name, weeks_owed, owed FROM member_standing(:'s0'::date+7);
