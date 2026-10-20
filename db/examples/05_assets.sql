-- WORKED EXAMPLE 5 - assets: acquire, lend, damage, repair, exchange with admin, count corrections, handover register. Fresh database + schema.sql. 'EXPECT FAIL' lines are supposed to ERROR.
SELECT sunday_on_or_before(current_date) AS s0 \gset
INSERT INTO tenures(name, opened_on) VALUES ('T1', :'s0');
SET ROLE labapp;
INSERT INTO envelopes(name,is_pool) VALUES ('Unallocated General', true);
INSERT INTO envelopes(name) VALUES ('Components and Equipment');
INSERT INTO members(name) VALUES ('A'),('B'),('C');
INSERT INTO membership_periods(member_id,start_date,end_date) VALUES (1,:'s0',NULL),(2,:'s0',NULL),(3,:'s0',:'s0'::date+3);
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,source) VALUES (1,'deposit',:'s0','treasurer','other');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,500); COMMIT;
BEGIN; INSERT INTO ledger_transactions(tenure_id,kind,occurred_on,recorded_by,tag) VALUES (1,'expense',:'s0'::date+1,'treasurer','Component purchase');
INSERT INTO ledger_lines VALUES (default,currval('ledger_transactions_id_seq'),2,-300); COMMIT;
INSERT INTO assets(name,mode,ownership,tag) VALUES
  ('Oscilloscope','individual','admin','ADM-001'),   -- 1
  ('Raspberry Pi 5','individual','lab','PI5-01'),     -- 2
  ('ESP32 DevKit','counted','lab',NULL),              -- 3
  ('Multimeter','counted','admin',NULL);              -- 4

\echo '=== acquisitions (ESP32 linked to the purchase entry)'
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source,ledger_transaction_id)
  VALUES (3,'acquired',10,:'s0'::date+1,'treasurer','purchase',(SELECT max(id) FROM ledger_transactions));
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source) VALUES
  (1,'acquired',1,:'s0','treasurer','admin'), (2,'acquired',1,:'s0'::date+1,'treasurer','purchase'),
  (4,'acquired',3,:'s0','treasurer','admin');

\echo '=== lend 4 ESP32 to A for a project (note), A returns 1, 1 burns out while with A'
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,note)
  VALUES (3,'lent',4,1,:'s0'::date+2,'treasurer','for weather-station project');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'returned',1,1,:'s0'::date+3,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,note)
  VALUES (3,'damaged',1,1,:'s0'::date+3,'treasurer','burnt, reverse polarity');
\echo '=== Pi 5 overheats then is repaired; admin multimeter breaks, C borrows another before leaving'
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (2,'damaged',1,:'s0'::date+3,'treasurer','overheated');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by) VALUES (2,'repaired',1,:'s0'::date+4,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (4,'damaged',1,:'s0'::date+3,'treasurer','dead display');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (4,'lent',1,3,:'s0'::date+2,'treasurer');
\echo 'EXPECT ESP32 stock 7 dmg 1 held 2; Pi stock 1; Multimeter stock 1 dmg 1 held 1; queue shows Multimeter'
SELECT asset_name, ownership, stock, damaged, with_members AS held, lost, scrapped, exchanged FROM asset_overview ORDER BY 1;
SELECT asset_name AS awaiting_replacement, damaged FROM admin_replacement_queue;
\echo '=== multimeter sent to admin (exchanged), replacement arrives; ESP32: 1 lost from stock, damaged one scrapped'
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (4,'exchanged',1,:'s0'::date+5,'treasurer','sent to admin for replacement');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source,note) VALUES (4,'acquired',1,:'s0'::date+6,'treasurer','replacement','replacement from admin');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (3,'lost',1,:'s0'::date+6,'treasurer','missing after workshop');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (3,'scrapped',1,:'s0'::date+6,'treasurer','not repairable');
\echo '=== stock correction after a physical count (-1 Pi? no: ESP32 counted 5 not 6)'
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,note) VALUES (3,'correction',-1,:'s0'::date+7,'treasurer','physical count found 5');
\echo 'EXPECT ESP32 stock 5 dmg 0 held 2 lost 1 scrapped 1; Multimeter stock 2 dmg 0 held 1 exch 1'
SELECT asset_name, stock, damaged, with_members AS held, lost, scrapped, exchanged FROM asset_overview WHERE asset_name IN ('ESP32 DevKit','Multimeter') ORDER BY 1;
SELECT member_name, asset_name, quantity FROM who_has_what;

\echo '=== B gets 2 ESP32 by mistake (should be 1): fix = reversal + replacement; list shows one line'
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,note) VALUES (3,'lent',2,2,:'s0'::date+8,'treasurer','robot arm');
BEGIN;
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,reverses_id,note)
  SELECT 3,'lent',-2,2,:'s0'::date+8,'treasurer',id,'typo, should be 1' FROM asset_events WHERE asset_id=3 AND kind='lent' AND member_id=2 AND reverses_id IS NULL;
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,replaces_id,note)
  SELECT 3,'lent',1,2,:'s0'::date+8,'treasurer',id,'robot arm' FROM asset_events WHERE asset_id=3 AND kind='lent' AND member_id=2 AND reverses_id IS NULL AND quantity=2;
COMMIT;
SELECT id, kind, quantity, note, corrected_from FROM asset_events_current WHERE member_id = 2;
\echo 'note edit in place is logged:'
BEGIN; SET LOCAL app.actor = 'treasurer';
UPDATE asset_events SET note = 'robot arm project' WHERE asset_id=3 AND member_id=2 AND quantity=1 AND reverses_id IS NULL;
COMMIT;
SELECT field, old_value, new_value, edited_by FROM asset_label_edits;

\echo '=== EXPECT FAIL x N: rejected mistakes'
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'lent',20,2,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'returned',5,2,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'lent',1,3,:'s0'::date+5,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by) VALUES (3,'lent',1,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by) VALUES (3,'acquired',1,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source) VALUES (3,'repaired',1,:'s0'::date+9,'treasurer','purchase');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'correction',1,1,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source) VALUES (1,'acquired',1,:'s0'::date+9,'treasurer','admin');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (2,'lent',2,1,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by) VALUES (3,'damaged',1,:'s0'::date+9,'treasurer');
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source) VALUES (3,'acquired',-3,:'s0'::date+9,'treasurer','purchase');
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,reverses_id,note)
  SELECT 3,'lent',-1,2,:'s0'::date+9,'treasurer',id,'again' FROM asset_events WHERE asset_id=3 AND kind='lent' AND member_id=2 AND quantity=2 AND reverses_id IS NULL;
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by,reverses_id,note)
  SELECT 3,'lent',2,2,:'s0'::date+9,'treasurer',id,'undo undo' FROM asset_events WHERE reverses_id IS NOT NULL AND asset_id=3 LIMIT 1;
UPDATE asset_events SET quantity = 99 WHERE id = 1;
DELETE FROM asset_events WHERE id = 1;
UPDATE assets SET mode = 'counted' WHERE id = 1;
UPDATE assets SET name = 'Oscilloscope (Rigol)' WHERE id = 1;
RESET ROLE;
\echo '=== admin report raw numbers for the period (corrections collapsed: the mistaken lend of 2 is not counted)'
SELECT asset_name, ownership, kind, source, units, events FROM asset_activity(:'s0'::date, :'s0'::date+9) ORDER BY 1,3,4;
\echo '=== health: EXPECT 0 rows'
SELECT * FROM verify_all();

\echo '=== close tenure at s0+10; handover register saved automatically'
SET ROLE labapp;
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (4,'lent',1,1,:'s0'::date+9,'treasurer');
SELECT close_tenure(:'s0'::date+10,'treasurer','T2');
SELECT count(*) AS asset_rows FROM tenure_asset_snapshots;
SELECT count(*) AS holding_rows FROM tenure_holding_snapshots;
SELECT m.name AS member, a.name AS asset, h.quantity FROM tenure_holding_snapshots h JOIN members m ON m.id=h.member_id JOIN assets a ON a.id=h.asset_id ORDER BY 1,2;
\echo '=== EXPECT FAIL: touching the closed tenure'
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (3,'returned',1,1,:'s0'::date+9,'treasurer');
UPDATE asset_events SET note = 'sneaky' WHERE asset_id = 3 AND kind = 'acquired';
INSERT INTO asset_events(asset_id,kind,quantity,occurred_on,recorded_by,source,reverses_id,note)
  SELECT 3,'acquired',-10,:'s0'::date+11,'treasurer','purchase',id,'oops' FROM asset_events WHERE asset_id=3 AND kind='acquired';
\echo '=== ok: carries on in the new tenure (A returns multimeter)'
INSERT INTO asset_events(asset_id,kind,quantity,member_id,occurred_on,recorded_by) VALUES (4,'returned',1,1,:'s0'::date+11,'treasurer');
SELECT asset_name, stock, with_members AS held FROM asset_overview WHERE asset_name = 'Multimeter';
RESET ROLE;
\echo '=== health after close: EXPECT 0 rows'
SELECT * FROM verify_all();
\echo '=== superuser tamper: bypass guard and change a quantity inside the closed tenure'
ALTER TABLE asset_events DISABLE TRIGGER asset_event_edit;
UPDATE asset_events SET quantity = 11 WHERE asset_id = 3 AND kind = 'acquired';
ALTER TABLE asset_events ENABLE TRIGGER asset_event_edit;
SELECT * FROM verify_all();
