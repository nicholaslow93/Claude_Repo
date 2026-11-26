---
name: "client-portfolio-snapshot"
description: "Build a one-page A4 client portfolio snapshot (fund-level P&L, dividends, cost basis, welcome-bonus bridge), or a fund switch proposal, from a Manulife Customer Investment Report PDF."
---

# Customer Investment Report → snapshot or fund switch one-pager

Two templates start from the same report: the **Portfolio Snapshot**
(`build_snapshot.py`) and the **Fund Switch Proposal** (`build_switch.py`).
Both need `common.py` beside them. **Never write or edit the page by hand, and
never reuse a previous client's page.** Start from
`specs/snapshot-spec-blank.json` or `specs/switch-spec-blank.json`. Index and
rules: `README.md`.

Engine: `work/engine/` in the repo, or this skill's `engine/` folder when
installed as an account skill.

## 0. Where to run, and the working folder

- **On Nick's PC only** (Cowork, or a local Claude Code session). The
  Customer Investment Report is an identifying document: it stays in AI
  Documents and never goes to Drive, the repo or a cloud session.
- Build in a working folder outside any repo, next to the report. Client specs
  and outputs are never committed.

## 1. Extract (read all pages; render them, the text layer is poor)

- Page 1: total market value, total investment value (premiums), asset mix.
- Per policy, two pages: P&L summary (account value, policy investment value,
  investment cost, total P&L, annualised P&L, partial withdrawal, dividends
  paid out, dividends reinvested, surrender value, issue date) and Fund
  Holdings (fund value, NAV, units, P&L $ and %, dividends paid out /
  reinvested).
- Tie-outs before building: policy account values sum to page-1 market value;
  policy investment values sum to page-1 total investment value; fund values
  per policy sum to the account value. Flag any mismatch.
- Consolidate by fund code across policies. Mask policies as Policy 1..N with
  issue month. No NRIC, no full policy numbers.
- List the fund codes found and confirm them with Nick. Anything unreadable is
  [PENDING]; never invent inputs.

## 2a. Snapshot

Fill the snapshot spec with report figures only: fund lines (code, name,
value, P&L incl. dividends, the report's own % if shown), policy dividends,
capital invested, partial withdrawals and the report's own totals. Run
`python3 build_snapshot.py spec.json project/Main.dc.html`. It stops if the
fund lines don't add up to the report totals, and computes everything else:
- Fund cost = value + dividends paid out + withdrawals − P&L (includes
  welcome-bonus units); fund-level return = P&L ÷ fund cost, not annualised.
- Vs premiums incl. welcome bonuses = value + paid out + withdrawals −
  premiums; it must equal Manulife's policy-level total P&L. Reinvested
  dividends are already in value.
- "What stands out" is computed (top contributors, main detractor, largest
  holding); an optional note may not contain figures.
- Check the implied bonus units it prints against the per-policy bonus gaps
  (policy P&L − sum of its fund P&Ls), proposal sheets in Drive (Catalyst Docs,
  read-only) and the InvestReady brochure; say plainly which gaps are unverified.
- Don't show Manulife's annualised P&L (inflated by bonus on young policies).
  Surrender value is far below account value inside the MIP; the bonus isn't
  realisable early.
- No iFUNDS fetch needed: the snapshot stays as at the report date.

## 2b. Fund switch

1. Fund data for every current and target fund via the
   manulife-ifunds-fund-data skill (reuse today's fund file if complete);
   report its flags.
2. Fill the switch spec: report date, first premium date, premiums paid,
   dividends paid out and reinvested, RPQ/CKA expiry, holdings (code, role,
   value, cost, P&L, units if shown). Target weights default to the model
   CABF 30 / MGMD 15 / NSAD 25 / ASGI 15 / NAJD 15 with `holds_bonds` per fund.
   Idea, tile_lead and tile_note carry Nick's message (we don't dislike the
   current funds; we see better opportunities in equities) and may not contain
   S$, % or numbers. 3 thesis points with dated, checked sources (GDP: BEA;
   global growth: IMF WEO; earnings and forward P/E: FactSet); point 4 is
   computed.
3. Spec `date` = today (SGT). `python3 build_switch.py spec.json project/Main.dc.html`.
   After = report total × target weight (switching is value-neutral); income
   before/after from fund-file yields; value + payouts on premiums, annualised
   only after 12 months; a bridge line explains fund P&L vs return on
   premiums. It stops if the proposal isn't dated today, the fund file is from
   another day, the RPQ/CKA has expired, or the report is more than 7 days
   old, and prints the date and plan-availability checks.
4. No benchmark or backtest sections; no welcome-bonus amount in the
   commentary box.

## 3. Check and deliver

`python3 render_check.py project/Main.dc.html` must say OK. Publish as an
artifact titled `CLIENT · <initials> · Snapshot` or `CLIENT · <initials> · Fund
Switch` (794x1123, A4). Reply punchy, answer first: what ties and what
doesn't, fund-level P&L first then the bonus bridge, fund flags, RPQ/CKA date,
plan availability. Save outputs to the Client Pnl Snapshots folder in AI
Documents only when Nick asks.

## 4. After a script change

Rebuild `ref/ref-snapshot.json` and `ref/ref-switch.json` ("Sample Client",
fictional figures) and compare the renders before client use.
