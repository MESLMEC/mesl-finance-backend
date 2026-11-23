# Business context (the lab's rules)

Drafted from the user's earlier decisions. **Only lines the user has ticked are authoritative.**
The user ticks (`[x]`) or corrects each line. Agents may propose edits; they never tick.
If a task needs a rule that is not ticked here, not in db/schema.sql, and not in a confirmed
decision: ask the user.

## Users and scope
- [ ] B-01 Only the treasurer uses the system for now. No member logs in; a member-facing view is deferred.
- [ ] B-02 English only. Amounts are whole BDT. Start fresh: no import of old history.
- [ ] B-03 The medium of money (cash, bKash, bank) and receipts are not tracked. Optional basic expense tags are allowed.
- [ ] B-04 Sign-offs are paper-first; the software later generates printable invoices, vouchers and handover reports.

## Member fees
- [ ] B-05 The weekly fee is the same for every member (20 BDT now). The global rate may change later (possibly by batch); a change affects only future weeks, never past ones.
- [ ] B-06 A fee week starts on Sunday. A member owes a week if they were a member on that Sunday: joining on or before it, or having an end date on it, both owe it.
- [ ] B-07 Members pay random lump sums, not a fixed amount per week.
- [ ] B-08 Shutdown weeks (long national vacation, campus incident) are forgiven. The treasurer names each Sunday; a shutdown is never sent as a from-to range.
- [ ] B-09 No automatic "4 missed weeks" trigger and no pending-review state: the system shows raw dues numbers and the admin decides.
- [ ] B-10 Arrears of a leaving member stay until paid or waived. One-week friction is settled with a waiver.
- [ ] B-11 Leftover member credit is refunded, or donated to the lab if the member wants.
- [ ] B-12 Member credit (advance payments) sits in the pool, and the allocation screen shows its total.

## Money and envelopes
- [ ] B-13 Income: member fees, event registration funds, funds from college admin, sponsorships. Most budget is not fixed income.
- [ ] B-14 All income lands first in the Unallocated General pool; the committee allocates manually, with target-cap top-ups for capped envelopes. Split amounts are stored as hard numbers so later changes never alter history.
- [ ] B-15 Envelopes: Unallocated General, Member Projects, Lab Projects, Events and Workshops, Competitions, Components and Equipment, Research, Admin and Misc.
- [ ] B-16 Event registration fees go to the Events envelope. At the end of an event, leftovers are swept back to the pool.
- [ ] B-17 Event money handling is informal and only for record: admin just wants monthly in/out totals; no overspend warnings; no voucher management.

## History and handover
- [ ] B-18 History is immutable. A tenure is hard-closed and balances carry over to the next one. Tenure length is not fixed.
- [ ] B-19 Fixing a typo in an amount is a reversal plus a replacement, and the treasurer's list shows it as one line. Typos in descriptive fields are editable in place, with history.
- [ ] B-20 Reconciliation: when the screen and the treasurer's pocket notes disagree, only entries since the last matching check need review.

## Assets
- [ ] B-21 Assets come from college admin (needs regular reports: new, old, exchange, handover) and from lab money. Consumables such as resistors are not tracked.
- [ ] B-22 Tracking is mostly counts, with a mode per item type; taka value of assets is not needed. Admin report format keeps changing, so the system gives raw CSV-ready numbers and the report is built manually.
- [ ] B-23 Components are lent only to members. For a project or other venture, lend in a member's name with a note. No printed lending slips and no due dates.
- [ ] B-24 Damage and loss counts are tracked, and damaged admin-provided items are reported for replacement. Damage cause is free text. A stock-correction event exists for physical-count differences.
- [ ] B-25 "Handover" of assets means a tenure change (officers handing over to the next committee).

## Deployment
- [ ] B-26 One treasurer login on a server. Earlier plan: Docker on that server; D-008 says Docker is out of scope for now.
