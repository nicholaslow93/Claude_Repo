---
name: "manulife-ifunds-fund-data"
description: "Pull Manulife ILP fund data (NAV, 3-month high, distributions, yield, ISIN, plan availability) from the public iFUNDS funds library, or find a new fund by name or theme."
---

# Manulife iFUNDS fund data

Every fund figure in the top-up, N-pay and switch pages comes from here. The
iFUNDS funds library is public, no login. Never try the adviser sign-in. No
factsheets, POEMS (its Manulife figures were wrong in Nov 2026),
manulife.com.sg or YCharts for figures.

Engine files (`ifunds_fetch.js`, `fund_data.py`): `work/engine/` in the repo,
or this skill's `engine/` folder when installed as an account skill.

## Where it can run

Manulife blocks data-centre IPs (cloud sessions get 403 Access Denied, from
the shell and from a browser). The fetch must run in the **built-in browser on
Nick's PC**: a Cowork session, a local Claude Code session, or a cloud session
linked to the PC through Remote Control. Never try to get round the block from
the cloud.

## Same-day reuse first

Fund files are named `funds_<latest NAV date>.json` and live in Drive:
**AI Assisted Documents / Work AI Files / Fund Data**. If a file fetched today
(SGT) has every code you need, download and use it. Fetch only for a missing
fund or on a new day. The builds refuse a fund file from another day.

## Fetch (read-only, one agent drives the browser at a time)

The work is split so the PC does only what needs its IP (the browser), and
the processing runs where Python is (the cloud; the PC has no Python).

**On the PC** (Claude Bridge session, Cowork, or any session with the
built-in browser):
1. Load the built-in-browser skill, then its tools in one ToolSearch call.
2. Open a NEW tab on any fund page:
   `https://client.asia.manulifeam.com/discovery/en_SG/fund-details/<CODE>`
   (JS-rendered; the APIs below are same-origin from there). If a site-access
   prompt appears, request it and tell Nick to approve.
3. Set `CODES` in `ifunds_fetch.js` and run it with the javascript tool. For
   funds known only by ISIN, first filter the screener in JS by ISIN to get
   their codes. It returns compact raw JSON (screener fields, about two years
   of payouts, 3-month price series). Never dump the screener into context.
4. Upload the raw JSON as `raw_<YYYY-MM-DD>.json` (today, SGT) to Drive
   `Work AI Files / Fund Data` (folder id 1R80Iqy60SBT15ue87QyzQUSwmYbxNprX),
   text/plain content, no conversion. Report any ISIN not found on iFUNDS.
   That's the PC's whole job.

**In the cloud** (or anywhere with Python):
5. Download `raw_<date>.json`, run `python3 fund_data.py raw_<date>.json` →
   `funds_<latest NAV date>.json`, and upload that to the same Drive folder.
6. Tell the Work Desk (https://claude.ai/artifact/HT749EePXdqUcRAwpUHU1p):
   with ArtifactData, set `status/fund` to
   `{navDate: <latest NAV date>, fetchedOn: <fetch date, SGT>, file: <file name>}`.
   Its pitch tiles turn green for the rest of the day.
7. If the browser can't be reached, say so and stop. Don't fall back to other
   sites.

APIs, for reference (both need the header `locale: en_SG`):
- `GET /discovery/api/fund-screener`: every fund (code, name, ISIN, NAV, price
  date, official YTD and as-of date, distribution frequency and history,
  documents, plan tags; about 4 MB).
- `GET /discovery/api/fund-prices/<CODE>/<period>`: one-month, three-month,
  six-month, one-year, three-year, five-year, ten-year, since-inception.

## What fund_data.py computes (never by hand)

- Latest NAV and date, 3-month high and date (from the series fetched), gap to high.
- **Yield = latest payout × payouts per year ÷ latest NAV** (Nick's rule, 20 Nov
  2026). Payouts per year from the iFUNDS frequency field, cross-checked
  against actual payout spacing. Trailing-12M is a cross-check only.
  Accumulating funds: n/a.
- Official YTD and as-of date, ISIN, plan tags, plan check against InvestReady (III).

## Flags: report them to Nick every run

- payout per unit cut or raised (and when), one-off high or low payouts, payout vs a year ago
- sharp yield moves vs a year ago, split into payout effect vs price effect
- latest-payout yield vs trailing-12M gap of 0.5pp or more
- latest payout not yet posted (Amova funds post later), frequency changes
- plan tags that don't name the client's plan (only "InvestReady", or only
  "InvestReady (III) (via DBS/POSB Bank)")
- NAV date mismatches

## Finding a NEW fund (fund swaps)

When Nick names a fund loosely ("the Fidelity global dividend one") or gives a
theme: filter the screener in JS by name keywords / asset class / distribution
flag AND plan tag; fetch the shortlist with `ifunds_fetch.js` and run
`fund_data.py`; return at most 5 with code, full name, ISIN, currency/hedging,
dist vs acc, yield (latest annualised), YTD, 3M gap, plan check, flags. Nick
picks; never pick for him.

## Quirks

- NAV only, no bid/offer. Amova funds (NAJD, NSAD) price a day behind and post payouts later.
- CABF on iFUNDS is the Bfydmh-SGD class (LU2521041199); BFDXM/BFDXMH aren't offered.
- Known ISINs: ASGI LU2360032135, CABF LU2521041199, NAJD SG9999010490,
  NSAD SG9999003826, MGSO LU2931357623, MGMD LU1935043536, MARH LU1935355344,
  PGIA IE00B91RQ825.
