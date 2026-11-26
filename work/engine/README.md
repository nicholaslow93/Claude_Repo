# One-pager engine — index

Imported from the Cowork project's `claude/` folder on 26 Nov 2026 (index rebuilt there 20 Nov 2026). Client examples removed.

Pinned hub (interactive): [Advisory Template Hub](https://claude.ai/artifact/2DRQQ6nb5hHaUqjzzbJB8X), artifact slug 09d51a60-e4af-44c2-be41-ce6712d63dc4.
Shareable catalogue doc: [Template Catalogue — Financial Advisory Work](https://claude.ai/artifact/PUhLTpaSpkonz4YgNBrbxV) (may lag this index; this file wins).

**Maintenance rule:** when a template is added, changed or retired: (1) update this file, (2) db_write the hub's `templates/<slug>` doc (fields: order, name, purpose, inputs, output, skill, file, exampleLabel, exampleUrl, ask, added, priceCheck, notes[]; status:"archived" to retire), remove it from `backlog/` if listed, bump `meta/info.updated`, (3) update the catalogue doc, (4) rebuild the Sample Client reference for any script change. **Clients:** for pitch templates the Hub saves `clients/<slug>` itself when Nick copies the prompt; the Hub doesn't need to hold refreshed client data.

## Ground rules (all templates)
1. **Every figure is computed by a script.** No page is written or edited by hand. If an output looks wrong, fix the spec or the script and rebuild.
2. **All fund data comes from the Manulife iFUNDS public fund library, no login.** No factsheets, POEMS, manulife.com.sg or YCharts for figures.
3. **Yield = latest payout × payouts per year ÷ latest NAV** (×12 for monthly payers). Trailing 12M is kept only as a cross-check for the flags.
4. **Flags go to Nick every run** (printed by fund_data.py and each build): payout per unit changes (cuts, raises, one-offs), sharp yield moves split into payout vs price effect, latest-vs-12M gaps, payouts not yet posted, frequency changes, plan tags that don't name the plan, NAV date mismatches.
5. **Thesis: external sources are fine, no guessing, nothing stale.** Each point carries its sources with publication date and the date the run checked it is still the latest release; the build stops if any check is older than 14 days.
6. **Same-day reuse:** a fund file fetched today can be reused for any proposal dated today. Re-fetch only if a fund outside the file is added. The build stops on a fund file from another day.
7. **No annualised returns for periods under 12 months.** Returns that include welcome bonuses are labelled as such, with a one-line bridge to fund-level P&L.
8. **References are Sample Client builds**, not client copies. Client pages already published stay as they are.

## Files (`work/engine/`)
| File | What it does |
|---|---|
| `ifunds_fetch.js` | Run in the built-in browser (any iFUNDS fund page, new tab). Set CODES; returns raw JSON (screener fields, last ~2 yrs of payouts, 3-month price series). |
| `fund_data.py` | `python3 fund_data.py raw_<date>.json` → `funds_<latest NAV date>.json` + summary table + flags. Computes 3M high, gap, yields, flags, plan check. |
| `common.py` | Shared helpers and checks (fund-file freshness, thesis sources/age, labels, footers). Must sit next to the build scripts. |
| `build_pitch.py` | Top-up and N-pay (2–20 years) pitches. `python3 build_pitch.py spec.json Main.dc.html` |
| `build_switch.py` | Fund switch proposal from Customer Investment Report figures + fund file. |
| `build_snapshot.py` | Client portfolio snapshot from Customer Investment Report figures (no iFUNDS needed). |
| `render_check.py` | A4 fit check with local IBM Plex fonts; saves a PNG. Needs Plex woff2 (`npm pack @ibm/plex-sans @ibm/plex-serif`, untar in /tmp). |
| `specs/*-spec-blank.json` | Blank specs to fill. No numbers or thesis to copy forward. |
| `ref/ref-*.json` | Sample Client specs: topup, 3pay, 10pay, switch, snapshot. Rebuild after any script change and compare. |
| `data/funds_<date>.json` | Fund files (same-day cache). |

Working folder layout when running: scripts + `data/` + spec in one directory; spec `fund_file` is relative to it (e.g. `data/funds_2026-11-19.json`).

## Run flow
1. **Hub** → prompt (template, client, inputs). For fund templates confirm the fund codes (Hub "Funds (confirmed…; don't re-ask)" counts as confirmed; "Funds to find" means shortlist first).
2. **Fund data** (skip if today's fund file already has every code): built-in browser, new tab on `https://client.asia.manulifeam.com/discovery/en_SG/fund-details/<CODE>`, run `ifunds_fetch.js` with the codes, save the JSON, run `fund_data.py`. Report the summary + flags to Nick.
3. **Thesis** (pitches 4 points, switch 3 + 1 computed): web-search fresh, dated sources; fill `sources` with name, date, checked.
4. **Spec** from the blank; **build**; **render_check.py** (must be OK); read the build's printout for plan-availability and flags.
5. **Publish**: Design artifact, `project/canvas.json` (board Main.dc.html, 794×1123, paper a4, launch focused) + `project/Main.dc.html`.

## Templates
| Template | Ask for it | Build | Inputs |
|---|---|---|---|
| Client Portfolio Snapshot | "Portfolio snapshot for [client]" + report PDF | `build_snapshot.py` | Report figures only: fund lines (value, P&L, report %), policy dividends, capital invested, withdrawals, report totals (build stops if lines don't add up) |
| ILP Top-Up Pitch | Hub → ILP Top-Up Pitch | `build_pitch.py` mode `topup` | Client, plan, top-up S$, fund codes + weights + roles, thesis |
| ILP N-Pay Pitch (3-pay, 10-pay, any 2–20) | Hub → ILP 3-Pay Pitch (set pay years) | `build_pitch.py` mode `npay` | + annual premium, years, bonus % and cashback % of Y1 premium (all required; 0 only if truly none) |
| ILP Fund Switch Proposal | "Fund switch proposal for [client]" + report PDF | `build_switch.py` | Report figures (holdings value/cost/P&L/units, paid in, start date, dividends paid out/reinvested, RPQ/CKA expiry), target weights (default model CABF 30 / MGMD 15 / NSAD 25 / ASGI 15 / NAJD 15), idea + commentary text without figures, 3 thesis points |

### Pitch notes (top-up and N-pay)
- Tiles (N-pay): Total premium | Welcome bonus (% of Y1 premium, in units) | Est. yield (monthly once fully funded) | Y1 cash received (incl. one-off cashback). Never a combined receivables % on premium.
- Funding strip: all years for 2–4 pay, milestone years (1, 2, 3, 5, final) for 5+. "Cash received" row; bonus "subject to policy terms incl. clawback" in footer; strip is before policy charges.
- Entry wording follows the sign of the weighted gap (below / near / above highs). Positive gaps show green.
- Thesis point naming "Years 2–N" must match the pay term (build checks).
- Footer: "Prices can fall further after you invest; later premiums are invested at the prices at that time."
- Plan availability is never claimed on the page; the build prints which funds' iFUNDS tags don't name the plan.

- 10-pay and other long terms: InvestReady III 10-pay welcome bonus is 50% of Y1 premium (Nick, 20 Nov 2026); confirm the cashback campaign rate each run. In the meeting, say plainly that the long-term flat-price, flat-yield view excludes charges and that income after the last premium is illustrative.

### Fund switch notes
- Gold "No additional premium · fund switch only" badge. Message: we don't dislike the current funds; we see better opportunities in equities.
- After = report total × target weight (switching is value-neutral; prices on the switch day set units). If units are given, the build checks units × iFUNDS NAV against report values and flags date gaps.
- Value + payouts tile: value + dividends paid out vs premiums, months held; annualised only after 12 months. Bridge line under the table explains fund P&L (on cost incl. bonus units) vs return on premiums.
- Thesis point 4 is computed: % in funds holding bonds (balanced and multi-asset), weighted gap, how many targets are up YTD.
- RPQ/CKA expiry must be after the proposal date (build stops otherwise); flag the date to Nick.
- Dropped by Nick: benchmark/backtest comparisons; welcome-bonus amount in the commentary box.

### Snapshot notes
- Tiles: Market value (+ premiums invested) | Fund P&L (+ vs premiums incl. welcome bonuses) | Fund-level return (on fund cost incl. bonus units, not annualised) | Dividends to date.
- Fund cost = value + dividends paid out + withdrawals − P&L. Bonus-inclusive = value + paid out + withdrawals − premiums. Build prints implied bonus units: check against the report's policy-level bonuses.
- "What stands out" is computed (top contributors, main detractor, largest holding); optional note without figures.

## Repeated formats not yet saved as templates
- Weekly client market update (WhatsApp/Telegram) — artifacts "Weekly Update …"
- Ad Hoc Note (single-topic market note) — artifacts "Ad Hoc Note — …"
- Today's Pipeline (daily task board) — artifacts "Today's Pipeline"
- Purpose-Driven ILP brief (Aug 2026), SmartRetire dividend-income one-pager (Apr 2026) — past chats only

## House style
A4 794×1123, IBM Plex Sans/Serif, navy #1a1f2b, green #14584a positives, terracotta #a33a0a / #b4410c negatives, panels #f3f5f8 / #e6f2ee, gold #d4b46a on navy, warm commentary panel #f3ede0 (switch). Single disclosure footer.

## iFUNDS reference (captured 19–20 Nov 2026)
- Fund page: https://client.asia.manulifeam.com/discovery/en_SG/fund-details/<CODE>. APIs (header `locale: en_SG`): `/discovery/api/fund-screener` (~4 MB, every fund; fields fundCode, fundName, navpu, priceDate, cumulativePerformance.ytd + asOfDate, distributionFrequency, dividends[{exDate, netDistributionPerShare, nav}], subProduct, fundFacts.isin) and `/discovery/api/fund-prices/<CODE>/three-month` (`data[{date, fund}]`). Filter in JS; `ifunds_fetch.js` does this.
- NAV only (no bid/offer). Amova funds (NAJD, NSAD) price a day behind and post payouts later than the others.
- Share classes on file: ASGI LU2360032135; CABF Bfydmh-SGD LU2521041199; NAJD SG9999010490; NSAD SG9999003826; MGSO LU2931357623 (acc); MGMD LU1935043536; MARH LU1935355344; PGIA IE00B91RQ825.
- The cloud session can't reach Manulife domains from the shell or WebFetch; use the built-in browser on Nick's computer.

## Running in a Claude Code cloud session

- Python Playwright: `pip install playwright` (the browser is already installed; `render_check.py` finds it, or set `CHROME_PATH`).
- Fonts: `npm pack @ibm/plex-sans @ibm/plex-serif`, untar each, and point `PLEX_DIR` at the folder.
- Fund data can't be fetched from the cloud (Manulife blocks data-centre IPs). Fetch on the PC with `ifunds_fetch.js` in the built-in browser, then bring the `funds_<date>.json` file across.
- All `ref/` fixtures are fictional ("Sample Client"); snapshot and switch amounts were scaled and dates shifted.
