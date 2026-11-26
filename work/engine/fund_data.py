#!/usr/bin/env python3
"""Turn a raw iFUNDS fetch (ifunds_fetch.js output) into the shared fund file every
template build reads.

Usage:  python3 fund_data.py raw_<date>.json [out_dir]
Writes  funds_<latest NAV date>.json  and prints the run summary + flags for Nick.

House rules baked in (Nick, 20 Nov 2026):
- Yield = latest iFUNDS payout x payouts per year / latest NAV. Payouts per year come
  from the iFUNDS frequency field, cross-checked against the actual payout spacing.
- Trailing-12M yield is kept only as a cross-check for the flags, never shown as the yield.
- Flags: payout per unit changes, sharp yield moves (split into payout vs price effect),
  latest-vs-12M gap, payout not yet posted, frequency changes, plan tags that don't name
  the plan, NAV date mismatches.
- No figure here is typed by hand; everything is derived from the raw fetch.
"""
import json, sys, os, statistics
from datetime import date, datetime, timedelta

FREQ = {"MONTHLY": 12, "QUARTERLY": 4, "SEMI_ANNUALLY": 2, "SEMIANNUALLY": 2, "HALF_YEARLY": 2,
        "ANNUALLY": 1, "YEARLY": 1, "NO": 0, None: 0}
DPS_STEP = 5.0        # % change in payout per unit (vs previous, or vs 6-payout average) worth flagging
TREND = 10.0          # % change in payout per unit vs a year ago
YIELD_GAP = 0.5       # pp gap between latest-annualised and trailing-12M yields
YIELD_MOVE = 0.75     # pp move in annualised yield vs a year ago
PLAN = "InvestReady (III)"


def d(s):
    return datetime.strptime(s.replace("-", "/")[:10], "%Y/%m/%d").date()


def short(dt):
    return f"{dt.day} {dt.strftime('%b')}"


def observed_freq(divs):
    if len(divs) < 3:
        return None
    gaps = [(d(b["ex"]) - d(a["ex"])).days for a, b in zip(divs[-4:], divs[-3:])]
    g = statistics.median(gaps)
    for per, lo, hi in ((12, 20, 45), (4, 75, 110), (2, 160, 200), (1, 330, 400)):
        if lo <= g <= hi:
            return per
    return None


def process(f):
    flags = []
    prices = [(d(a), float(b)) for a, b in f["prices"]]
    nav_date = d(f["price_date"]) if f.get("price_date") else prices[-1][0]
    nav = float(f["nav"])
    if prices[-1][0] != nav_date or abs(prices[-1][1] - nav) > 1e-9:
        flags.append(f"Price series ends {prices[-1][0]} at {prices[-1][1]}, but fund data says NAV {nav} on {nav_date}.")
    hi_date, hi = max(prices, key=lambda x: (x[1], x[0]))
    raw_hi = next(b for a, b in f["prices"] if d(a) == hi_date)
    gap = (nav / hi - 1) * 100

    divs = f.get("dividends") or []
    per_stated = FREQ.get(f.get("dist_frequency"), None)
    if per_stated is None:
        flags.append(f"Unknown distribution frequency '{f.get('dist_frequency')}'.")
        per_stated = 0
    out = dict(code=f["code"], name=f["name"], isin=f.get("isin"), currency=f.get("currency"),
               nav=nav, nav_str=repr(nav) if not str(nav).endswith(".0") else str(nav), nav_date=str(nav_date),
               high=hi, high_str=str(raw_hi), high_date=str(hi_date), high_date_short=short(hi_date),
               gap_pct=gap, window_start=str(prices[0][0]), window_end=str(prices[-1][0]),
               ytd=f.get("ytd"), ytd_asof=f.get("perf_asof"), plans=f.get("plans", []),
               dist_frequency=f.get("dist_frequency"), accumulating=(per_stated == 0 and not divs))

    if out["accumulating"]:
        out.update(yield_pct=None, yield_method="accumulating (no payouts)")
    elif not divs:
        flags.append("Fund is marked as paying distributions but iFUNDS lists none.")
        out.update(yield_pct=None, yield_method="no payout data")
    else:
        per_obs = observed_freq(divs)
        per = per_stated or per_obs
        if per_obs and per_stated and per_obs != per_stated:
            flags.append(f"iFUNDS says {f['dist_frequency']} but recent payouts are spaced like {per_obs}/yr; used {per_obs}/yr.")
            per = per_obs
        last = divs[-1]
        last_ex = d(last["ex"])
        y_latest = last["dps"] * per / nav * 100
        # trailing 12M (cross-check only)
        t12 = [x for x in divs if nav_date - timedelta(days=365) < d(x["ex"]) <= nav_date]
        y_t12 = sum(x["dps"] for x in t12) / nav * 100
        out.update(yield_pct=round(y_latest, 4), yield_method=f"latest payout x {per} / NAV",
                   payouts_per_year=per, latest_dps=last["dps"], latest_ex=str(last_ex),
                   yield_t12m=round(y_t12, 4), t12m_count=len(t12))
        # payout not yet posted
        interval = 365 / per
        days_since = (nav_date - last_ex).days
        if days_since > interval * 1.4:
            flags.append(f"Latest payout on iFUNDS is {short(last_ex)} ({days_since} days before the NAV date); the next one isn't posted yet, so the yield uses the {short(last_ex)} payout.")
        # payout per unit vs previous / recent average (same frequency regime only)
        same = [x for x in divs if x is not last]
        recent = [x for x in same[-6:] if per_obs is None or True]
        if same:
            prev = same[-1]["dps"]
            ch = (last["dps"] / prev - 1) * 100
            if abs(ch) >= DPS_STEP:
                flags.append(f"Payout per unit {'up' if ch > 0 else 'down'} {abs(ch):.1f}% vs the previous payout ({prev:g} -> {last['dps']:g}).")
        # most recent step change in payout per unit within the last 12 months (cuts and raises)
        idx = {id(x): i for i, x in enumerate(divs)}
        skip = False
        for a, b in zip(reversed(divs[:-1]), reversed(divs)):
            if skip:
                skip = False
                continue
            if d(b["ex"]) < nav_date - timedelta(days=365):
                break
            if (d(b["ex"]) - d(a["ex"])).days < interval * 1.6 and abs(b["dps"] / a["dps"] - 1) * 100 >= DPS_STEP:
                i = idx[id(a)]
                before = divs[i - 1] if i > 0 else None
                if before and abs(b["dps"] / before["dps"] - 1) * 100 < DPS_STEP:
                    flags.append(f"One-off {'high' if a['dps'] > b['dps'] else 'low'} payout on {short(d(a['ex']))} ({a['dps']:g} vs {before['dps']:g} before and {b['dps']:g} after); not a lasting change.")
                    skip = True
                    continue
                sc = (b["dps"] / a["dps"] - 1) * 100
                if b is not last:
                    flags.append(f"Payout per unit was {'raised' if sc > 0 else 'cut'} {abs(sc):.1f}% on {short(d(b['ex']))} ({a['dps']:g} -> {b['dps']:g}) and has held since.")
                break
        if len(recent) >= 3:
            avg = statistics.mean(x["dps"] for x in recent)
            ch6 = (last["dps"] / avg - 1) * 100
            if abs(ch6) >= DPS_STEP:
                flags.append(f"Latest payout is {abs(ch6):.1f}% {'above' if ch6 > 0 else 'below'} the average of the previous {len(recent)} ({avg:.6g}).")
        # year-ago comparison: payout effect vs price effect
        ya = [x for x in divs if abs((last_ex - d(x["ex"])).days - 365) <= 20]
        if ya:
            y0 = ya[0]
            per0 = per
            if y0.get("nav"):
                # frequency regime a year ago (e.g. ASGI was quarterly until Apr 2025)
                before = [x for x in divs if d(x["ex"]) <= d(y0["ex"])]
                per0 = observed_freq(before) or per
                y_then = y0["dps"] * per0 / y0["nav"] * 100
                y_now_exnav = last["dps"] * per / last["nav"] * 100 if last.get("nav") else y_latest
                dps_ch = (last["dps"] * per / (y0["dps"] * per0) - 1) * 100
                nav_ch = ((last.get("nav") or nav) / y0["nav"] - 1) * 100
                move = y_latest - y_then
                if per0 != per:
                    flags.append(f"Payout frequency changed in the last year ({per0}/yr -> {per}/yr); compare annual payout, not per-payout amounts.")
                if abs(dps_ch) >= TREND:
                    flags.append(f"Annualised payout per unit {'up' if dps_ch > 0 else 'down'} {abs(dps_ch):.1f}% vs a year ago ({short(d(y0['ex']))} {d(y0['ex']).year}).")
                if abs(move) >= YIELD_MOVE:
                    why = "payout change" if abs(dps_ch) > abs(nav_ch) else "price change"
                    flags.append(f"Yield {'up' if move > 0 else 'down'} {abs(move):.2f}pp vs a year ago ({y_then:.2f}% -> {y_latest:.2f}%), mainly from the {why} (payout {dps_ch:+.1f}%, price {nav_ch:+.1f}%).")
        if abs(y_latest - y_t12) >= YIELD_GAP:
            flags.append(f"Latest-payout yield {y_latest:.2f}% vs trailing-12M {y_t12:.2f}% ({len(t12)} payouts): a gap of {abs(y_latest - y_t12):.2f}pp.")

    # plan availability
    plans = out["plans"]
    if PLAN in plans:
        out["plan_check"] = "named"
    elif any(p.startswith(PLAN) for p in plans):
        out["plan_check"] = "bank channel only"
        flags.append(f"Plan tags name InvestReady (III) only via DBS/POSB Bank: {', '.join(p for p in plans if 'InvestReady' in p)}. Confirm availability for your channel.")
    elif "InvestReady" in plans:
        out["plan_check"] = "InvestReady only"
        flags.append("Plan tags say 'InvestReady' but don't name InvestReady (III). Confirm availability.")
    else:
        out["plan_check"] = "not listed"
        flags.append("Not tagged for any InvestReady plan on iFUNDS.")
    out["flags"] = flags
    return out


def main():
    raw = json.load(open(sys.argv[1]))
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(sys.argv[1]))
    funds = {c: process(f) for c, f in raw["funds"].items()}
    nav_dates = sorted({f["nav_date"] for f in funds.values()})
    res = dict(fetched_at=raw["fetched_at"], source=raw["source"], nav_dates=nav_dates,
               latest_nav_date=nav_dates[-1], missing=raw.get("missing", []), funds=funds)
    path = os.path.join(out_dir, f"funds_{nav_dates[-1]}.json")
    json.dump(res, open(path, "w"), indent=1)
    print(f"Wrote {path}\nFetched {raw['fetched_at']} from {raw['source']}. NAV dates: {', '.join(nav_dates)}.")
    if raw.get("missing"):
        print("NOT FOUND on iFUNDS:", ", ".join(raw["missing"]))
    print(f"\n{'Fund':5} {'NAV':>9} {'date':>10} {'3M high':>9} {'on':>7} {'gap':>7} {'yield':>7} {'12M':>6}  plan")
    for c, f in funds.items():
        y = "acc" if f["yield_pct"] is None else f"{f['yield_pct']:.2f}%"
        t = "" if f.get("yield_t12m") is None else f"{f['yield_t12m']:.2f}"
        print(f"{c:5} {f['nav']:>9g} {f['nav_date']:>10} {f['high']:>9g} {f['high_date_short']:>7} {f['gap_pct']:>6.1f}% {y:>7} {t:>6}  {f['plan_check']}")
    print("\nFlags:")
    for c, f in funds.items():
        for fl in f["flags"]:
            print(f"  {c}: {fl}")


if __name__ == "__main__":
    main()
