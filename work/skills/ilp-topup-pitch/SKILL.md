---
name: "ilp-topup-pitch"
description: "Build Nick's one-page A4 ILP pitch: a single top-up, or a new 2-20 year regular-premium N-pay policy (3-pay, 10-pay...), from fresh iFUNDS fund data, using build_pitch.py."
---

# ILP pitch one-pager (top-up and N-pay)

One script builds both: `build_pitch.py` (needs `common.py` beside it).
Mode `topup` = single top-up into an ILP. Mode `npay` = new regular-premium
policy for 2-20 years. **Never write or edit the page by hand, and never copy
figures or thesis text from an old pitch or example.** Start from
`specs/pitch-spec-blank.json`. Index and rules: `README.md`.

Engine: `work/engine/` in the repo, or this skill's `engine/` folder when
installed as an account skill.

## 0. Where to run, and the working folder

- Runs in the cloud or on the PC. Fund data must come from the PC (see the
  manulife-ifunds-fund-data skill); the build itself runs anywhere.
- Build in a working folder **outside the repo** (e.g. `~/runs/<date>-<initials>/`):
  copy the engine scripts in, put the spec and `data/funds_<date>.json` beside
  them. Client specs and outputs never go into the repo.
- Cloud setup, once per session: `pip install playwright`; Plex fonts via
  `npm pack @ibm/plex-sans @ibm/plex-serif`, untar, set `PLEX_DIR`.

## 1. Inputs (ask only for what's missing)

- Client display name (no NRIC, no policy number), plan (e.g. Manulife InvestReady III).
- topup: top-up S$. npay: annual premium S$, pay years (2-20), welcome bonus %
  and cashback % of Y1 premium. All required; 0 only if there really is none.
  InvestReady III 10-pay welcome bonus is 50% (Nick, 20 Nov 2026); confirm the
  cashback campaign rate every run.
- Funds: codes + weights (sum 100) + roles. **Confirm the fund list with Nick
  before fetching** (show the mix on file; he sends codes only if different),
  unless the prompt says "Funds (confirmed…; don't re-ask)". "Funds to find" =
  run the manulife-ifunds-fund-data shortlist and get his pick first.
- Client working inputs may come from his Drive client sheet
  (`Catalyst Docs/Client Portfolios`). Anything that can't be found is
  [PENDING]; never invent figures.

## 2. Fund data

Follow the manulife-ifunds-fund-data skill: use today's `funds_<date>.json`
from Drive `Work AI Files / Fund Data` if it has every code, else fetch on the
PC. Report its summary and flags to Nick (payout changes, yield moves,
latest-vs-12M gaps, missing payouts, plan tags).

## 3. Thesis (4 points)

Web-search fresh, real sources for each point (e.g. FactSet Earnings Insight,
bank strategy calls). In the spec each point has `lead`, `text` (1-2
sentences) and `sources: [{name, date (publication; YYYY-MM if only the month
is known), checked (the day you confirmed it's the latest release)}]`.
Push back if a point argues against itself ("rates higher for longer" is a
general equity headwind; frame it through a concrete holding effect such as
bank margins). Keep each point to about two lines so the page fits.

## 4. Build and check

1. Spec `date` = today (SGT). `fund_file` is relative, e.g. `data/funds_2026-11-19.json`.
2. `python3 build_pitch.py spec.json project/Main.dc.html`. It computes every
   figure (amounts, weighted yield, distributions, funding schedule, gaps,
   bars, tiles, idea line, sources and market-views lines) and stops on missing
   or inconsistent inputs. It also stops if:
   - the proposal date isn't today, or the fund file wasn't fetched that day
   - a thesis source was checked more than 14 days ago
   - a "Years 2–N" thesis point doesn't match the pay term
3. `python3 render_check.py project/Main.dc.html` must say OK. If it fails,
   shorten the thesis or idea text.
4. From the build printout, pass plan-availability warnings (the page never
   claims availability) and fund flags to Nick.

## 5. What the page shows (fixed by the script; house style A4 794x1123, IBM Plex)

- Header, four tiles, THE IDEA (navy), Investment thesis (2x2), Proposed
  allocation table, prices now vs 3-month high chart, one footer. No key-risks,
  next-steps or NAV-scenario sections (Nick removed them).
- Top-up tiles: Top-up | Est. distribution yield (latest payouts annualised) |
  Est. distributions /mo | Entry point (wording follows the sign of the weighted
  gap: below / near / above highs).
- N-pay tiles: Total premium | Welcome bonus (% of Y1, in units) | Est. yield
  (/mo once fully funded) | Y1 cash received (incl. one-off cashback). Funding
  strip shows every year for 2-4 pay, milestone years (1, 2, 3, 5, final) for
  5+, before policy charges, ending in a Cash received row. Chart labelled
  "Year 1 entry". Never a combined receivables % on premium.

## 6. Compliance wording (non-negotiable)

"should" / "expected to", never "will", for future performance;
"distributions" not "dividends" for payouts that may come from capital; name
any concentrated or volatile fund in `volatile_note`; no annualised returns
under 12 months. The footer (script) carries: sources with dates, own
calculations and assumptions, exclusion of policy charges (see BI),
bonus/cashback terms incl. clawback, distributions not guaranteed and may come
from capital, prices can fall further after you invest, third-party views
don't guarantee returns, past performance, read with product summary,
prospectuses and PHS.

## 7. Deliver

- Artifact titled `CLIENT · <initials> · ILP Top-Up` or
  `CLIENT · <initials> · ILP <n>-Pay`, from `project/Main.dc.html`
  (794x1123, A4).
- Final PDF to the client's folder in Drive (`Catalyst Docs/Client Portfolios/`)
  or AI Documents on the PC, only when Nick asks.
- Reply with the key figures from the build printout, fund flags,
  plan-availability warnings and any [PENDING] item.

## 8. After a script change

Rebuild the references in `ref/` (`ref-topup.json`, `ref-3pay.json`,
`ref-10pay.json`, "Sample Client", against `ref/data/funds_2026-11-19.json`;
data-age checks are skipped only for that name) and compare the renders before
using the script for a client.
