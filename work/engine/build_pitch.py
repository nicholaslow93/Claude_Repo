#!/usr/bin/env python3
"""Build Nick's ILP pitch one-pager (N-pay regular premium or single top-up).

Usage:  python3 build_pitch.py spec.json out/project/Main.dc.html
Needs common.py next to it, and the fund file named in the spec (from fund_data.py).

Every number is computed here from the fund file + the spec. Nothing is typed.
The build stops (no output) if an input is missing, stale or inconsistent.

Spec keys (see pitch-spec-blank.json)
-------------------------------------
mode          "npay" | "topup"          ("3pay" accepted as an alias of "npay")
client, plan  display strings
date          prepared date, YYYY-MM-DD (must be the fund-fetch day)
fund_file     path to funds_<navdate>.json
premium       npay: annual premium S$ | topup: top-up S$
years         npay only, 2-20, required
bonus_pct     npay only, required (0 only if there really is no bonus); % of Y1 premium
cashback_pct  npay only, required (0 if none); % of Y1 premium, paid once in cash
funds         [{code, weight, role, name?, short?}]  name/short default to common.LABELS
thesis        exactly 4 x {lead, text, source, date YYYY-MM-DD}; each <= 14 days old
volatile_note optional sentence for the footer (e.g. MGSO concentration)
idea          optional override of the navy headline
"""
import json, sys
from common import *

NUMWORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
            12: "twelve", 15: "fifteen", 20: "twenty"}


def kfmt(x):
    k = x / 1000
    return f"S${k:g}k" if abs(k * 10 - round(k * 10)) < 1e-9 else f"S${money(x)}"


# ------------------------------------------------------------------ inputs
def load(spec_path):
    spec = json.load(open(spec_path))
    mode = {"3pay": "npay"}.get(spec.get("mode"), spec.get("mode"))
    if mode not in ("npay", "topup"):
        fail("mode must be 'npay' or 'topup'")
    spec["mode"] = mode
    req = ["client", "plan", "date", "fund_file", "premium", "funds", "thesis"]
    if mode == "npay":
        req += ["years", "bonus_pct", "cashback_pct"]
    for k in req:
        if spec.get(k) in (None, ""):
            fail(f"spec is missing '{k}'")
    if not isinstance(spec["premium"], (int, float)) or spec["premium"] <= 0:
        fail("premium must be a positive number")
    if mode == "npay":
        n = spec["years"]
        if not isinstance(n, int) or not 2 <= n <= 20:
            fail("years must be a whole number from 2 to 20")
        for k in ("bonus_pct", "cashback_pct"):
            if not isinstance(spec[k], (int, float)) or spec[k] < 0:
                fail(f"{k} must be a number (0 if none)")
    reference_mode(spec["client"])
    prepared = pdate(spec["date"])
    codes = [f.get("code") for f in spec["funds"]]
    if len(set(codes)) != len(codes):
        fail(f"duplicate fund codes: {codes}")
    for f in spec["funds"]:
        if not isinstance(f.get("weight"), (int, float)) or f["weight"] <= 0:
            fail(f"fund {f.get('code')} needs a positive numeric weight")
        if not f.get("role"):
            fail(f"fund {f.get('code')} needs a role")
    w = sum(f["weight"] for f in spec["funds"])
    if abs(w - 100) > 1e-6:
        fail(f"weights sum to {w}, not 100")
    ff, fetched = load_fund_file(spec["fund_file"], prepared, codes)
    check_thesis(spec["thesis"], prepared, years=spec.get("years") if mode == "npay" else None)
    funds = []
    for f in spec["funds"]:
        d = dict(ff["funds"][f["code"]])
        name, short = LABELS.get(f["code"], (None, None))
        d.update(weight=f["weight"], role=f["role"], label=f.get("name") or name or d["name"],
                 short=f.get("short") or short or f["code"])
        funds.append(d)
    return spec, prepared, ff, fetched, funds


# ------------------------------------------------------------------ maths
def compute(spec, funds):
    wy = sum(f["weight"] / 100 * (f["yield_pct"] or 0) for f in funds)
    wgap = sum(f["weight"] / 100 * f["gap_pct"] for f in funds)
    maxgap = max(abs(f["gap_pct"]) for f in funds) or 1
    for f in funds:
        f["bar"] = abs(f["gap_pct"]) / maxgap * 100
    c = dict(wy=wy, wgap=wgap, wbar=abs(wgap) / maxgap * 100)
    p = spec["premium"]
    if spec["mode"] == "npay":
        n = spec["years"]
        bonus = p * spec["bonus_pct"] / 100
        cash = p * spec["cashback_pct"] / 100
        cum = [p * (i + 1) + bonus for i in range(n)]
        dist = [x * wy / 100 for x in cum]
        for f in funds:
            f["y1"] = (p + bonus) * f["weight"] / 100
            f["full"] = cum[-1] * f["weight"] / 100
            f["pa"] = f["full"] * (f["yield_pct"] or 0) / 100
        c.update(n=n, bonus=bonus, cash=cash, cum=cum, dist=dist, total_y1=p + bonus, total_full=cum[-1],
                 pa_total=sum(f["pa"] for f in funds), y1_cash=cash + dist[0])
    else:
        for f in funds:
            f["amt"] = p * f["weight"] / 100
            f["pa"] = f["amt"] * (f["yield_pct"] or 0) / 100
        c.update(pa_total=sum(f["pa"] for f in funds))
    return c


def entry_phrase(wgap):
    """Wording for where prices sit vs their 3-month highs, by sign (never 'about 0% below')."""
    n = round(abs(wgap))
    if wgap <= -1.5:
        return f"~{n}% below recent highs", f"~{n}% below", True
    if wgap >= 1.5:
        return f"~{n}% above their 3-month highs", f"~{n}% above", False
    return "close to recent highs", "Near highs", False


# ------------------------------------------------------------------ html bits
def tile(label, value, sub, green=False, pad="11px 14px"):
    bg, lc = ("#e6f2ee", "#3b4a45") if green else ("#f3f5f8", MUTED)
    vc = f"; color: {POS}" if green else ""
    return (f'<div style="background: {bg}; padding: {pad}; display: flex; flex-direction: column; gap: 4px">\n'
            f'<div style="font-size: 10.5px; letter-spacing: 0.8px; text-transform: uppercase; color: {lc}">{label}</div>\n'
            f'<div style="{SERIF}; font-weight: 600; font-size: 22px{vc}">{value}</div>\n'
            f'<div style="font-size: 10.5px; color: {lc}">{sub}</div>\n</div>')


def header(spec, prepared, eyebrow, subline, pb):
    return f"""<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #1a1f2b; padding-bottom: {pb}">
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase; color: {MUTED}">{eyebrow}</div>
<h1 style="margin: 0; {SERIF}; font-weight: 600; font-size: 30px; line-height: 1.1">{e(spec['client'])}</h1>
</div>
<div style="text-align: right; font-size: 11.5px; line-height: 1.5; color: {MUTED}">
<div>{e(spec['plan'])}, {subline}</div>
<div>Prepared {long_date(prepared)}</div>
<div>Prepared by Nicholas Low</div>
</div>
</div>"""


def idea_box(text, pad, gap, fs):
    return f"""<div style="background: #1a1f2b; color: #ffffff; padding: {pad}; display: flex; flex-direction: column; gap: {gap}">
<div style="font-size: 12px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: #d4b46a">The idea</div>
<div style="{SERIF}; font-weight: 500; font-size: {fs}; line-height: 1.4">{e(text)}</div>
</div>"""


def thesis_box(spec, pad, gap, rowgap, lh):
    pts = "\n".join(f'<div><b style="font-weight: 600">{e(t["lead"])}</b> {e(t["text"])}</div>' for t in spec["thesis"])
    return f"""<div style="background: #f3f5f8; padding: {pad}; display: flex; flex-direction: column; gap: {gap}">
<h2 style="margin: 0; font-size: 14px; font-weight: 600">Investment thesis</h2>
<div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: {rowgap} 22px; font-size: 11.5px; line-height: {lh}">
{pts}
</div>
</div>"""


def section_head(title, note, mb):
    return f"""<div style="display: flex; flex-direction: column; gap: 0">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: {mb}">
<h2 style="margin: 0; font-size: 14px; font-weight: 600">{title}</h2>
<div style="font-size: 10.5px; color: {MUTED}">{note}</div>
</div>
"""


def ycell(f):
    if f["yield_pct"] is None:
        return f'<div style="text-align: right; color: {MUTED}">n/a</div>'
    return f'<div style="text-align: right">{f["yield_pct"]:.2f}%</div>'


def pacell(f):
    if f["yield_pct"] is None:
        return f'<div style="text-align: right; color: {MUTED}">0</div>'
    return f'<div style="text-align: right">{money(f["pa"])}</div>'


def ytdcell(f):
    col = POS if f["ytd"] > 0 else (NEG if f["ytd"] < 0 else MUTED)
    return f'<div style="text-align: right; color: {col}">{signed_pct(f["ytd"])}</div>'


def gap_section(funds, c, title, window, hh, rh, fs, barh, th, tfs, mb):
    G = "display: grid; grid-template-columns: 130px 128px 70px minmax(0, 1fr) 50px; column-gap: 12px; align-items: center"
    out = section_head(title, f"Unit price (NAV) change only, {e(window)}", mb)
    out += f"""
<div style="{G}; height: {hh}; border-bottom: 1px solid #1a1f2b; font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">
<div>Fund</div>
<div style="text-align: right">3-month high</div>
<div style="text-align: right">Now</div>
<div>Gap to high</div>
<div style="text-align: right">%</div>
</div>
"""
    for f in funds:
        g = f["gap_pct"]
        bc, tc = (NEGBAR, NEG) if g < 0 else (POS, POS)
        out += f"""<div style="{G}; height: {rh}; border-bottom: 1px solid #e3e7ed; font-size: {fs}">
<div><b style="font-weight: 600">{e(f['code'])}</b> <span style="color: {MUTED}">{e(f['short'])}</span></div>
<div style="text-align: right">{e(f['high_str'])} <span style="color: {MUTED}">({e(f['high_date_short'])})</span></div>
<div style="text-align: right">{e(f['nav_str'])}</div>
<div style="position: relative; height: {barh}; background: #f3f5f8"><div style="position: absolute; left: 0; top: 0; width: {f['bar']:.1f}%; height: {barh}; background: {bc}"></div></div>
<div style="text-align: right; font-weight: 500; color: {tc}">{signed_pct(g)}</div>
</div>
"""
    out += f"""<div style="{G}; height: {th}; border-top: 1px solid #1a1f2b; font-size: {tfs}; font-weight: 600">
<div>Weighted mix</div>
<div></div>
<div></div>
<div style="position: relative; height: {barh}; background: #f3f5f8"><div style="position: absolute; left: 0; top: 0; width: {c['wbar']:.1f}%; height: {barh}; background: #1a1f2b"></div></div>
<div style="text-align: right">{signed_pct(c['wgap'])}</div>
</div>
</div>"""
    return out


def footer(text, pt, fs, lh):
    return f"""<div style="margin-top: auto; border-top: 1px solid #c9d0da; padding-top: {pt}; font-size: {fs}; line-height: {lh}; color: {MUTED}">
{e(text)}
</div>"""


def sources_text(funds, fetched):
    return (f"Sources: Manulife iFUNDS public fund library, fetched {short_date(fetched.date())}: unit prices (NAV, {nav_dates_text(funds)}), "
            f"3-month price history, distributions and official YTD returns (to {ytd_asof(funds)}). Yields annualise each fund's latest "
            f"{freq_text(funds)} payout on its latest NAV.")


def strip_years(n):
    if n <= 4:
        return list(range(1, n + 1))
    return sorted({y for y in (1, 2, 3, 5, n) if y <= n})


# ------------------------------------------------------------------ N-pay
def build_npay(spec, prepared, fetched, funds, c):
    n, p = c["n"], spec["premium"]
    wy_s = f"~{c['wy']:.1f}%"
    bp, cp = spec["bonus_pct"], spec["cashback_pct"]
    entry_long, _, _ = entry_phrase(c["wgap"])
    idea = spec.get("idea") or (f"An income portfolio built over {NUMWORDS.get(n, n)} years: S${money(c['total_y1'])} invested from day one, "
                                f"entering {entry_long}, aiming for {wy_s} p.a. in distributions.")
    parts = [HEAD.format(title=e(f"ILP {n}-Pay Pitch - {spec['client']}")),
             '<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 26px 44px; background: #ffffff; color: #1a1f2b; font-family: \'IBM Plex Sans\', system-ui, sans-serif; font-variant-numeric: tabular-nums; display: flex; flex-direction: column; gap: 8px">\n',
             header(spec, prepared, f"New ILP Proposal · {n}-Pay", f"{n}-year regular premium", "10px"), "\n"]
    tiles = [tile("Total premium", f"S${money(p * n)}", f"{kfmt(p)} × {n} years, then none")]
    if bp:
        tiles.append(tile("Welcome bonus", f"S${money(c['bonus'])}", f"{bp:g}% of Y1 premium, in units"))
    else:
        tiles.append(tile("Welcome bonus", "None", "No welcome bonus on this policy"))
    tiles.append(tile("Est. yield", f"{wy_s} p.a.", f"~S${r10(c['pa_total'] / 12)}/mo fully funded", green=True))
    tiles.append(tile("Y1 cash received", f"~S${r10(c['y1_cash'])}",
                      "Incl. one-off cashback" if cp else "Est. Y1 distributions", green=True))
    parts.append('\n<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px">\n' + "\n".join(tiles) + "\n</div>\n\n")
    parts.append(idea_box(idea, "12px 22px", "6px", "16px") + "\n\n")
    parts.append(thesis_box(spec, "11px 18px", "7px", "7px", "1.42") + "\n\n")

    G = "display: grid; grid-template-columns: minmax(0, 1fr) 104px 40px 62px 62px 44px 54px 46px; column-gap: 9px; align-items: center"
    a = section_head("Proposed allocation", f"SGD. Same mix for all {n} premiums. Yields: latest payout annualised. YTD official to {ytd_asof(funds)}.", "5px")
    a += f"""
<div style="{G}; height: 22px; border-bottom: 1px solid #1a1f2b; font-size: 9.5px; letter-spacing: 0.5px; line-height: 1.2; text-transform: uppercase; color: {MUTED}">
<div>Fund</div>
<div>Role</div>
<div style="text-align: right">Weight</div>
<div style="text-align: right">Year 1</div>
<div style="text-align: right">Full</div>
<div style="text-align: right">Yield</div>
<div style="text-align: right">Est. p.a.</div>
<div style="text-align: right">YTD</div>
</div>

"""
    for f in funds:
        a += f"""<div style="{G}; height: 22px; border-bottom: 1px solid #e3e7ed; font-size: 11px">
<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><b style="font-weight: 600">{e(f['code'])}</b> <span style="color: {MUTED}">{e(f['label'])}</span></div>
<div style="color: {MUTED}">{e(f['role'])}</div>
<div style="text-align: right">{f['weight']:g}%</div>
<div style="text-align: right">{money(f['y1'])}</div>
<div style="text-align: right">{money(f['full'])}</div>
{ycell(f)}
{pacell(f)}
{ytdcell(f)}
</div>
"""
    a += f"""<div style="{G}; height: 26px; border-top: 1px solid #1a1f2b; font-size: 11.5px; font-weight: 600">
<div>Total</div>
<div></div>
<div style="text-align: right">100%</div>
<div style="text-align: right">{money(c['total_y1'])}</div>
<div style="text-align: right">{money(c['total_full'])}</div>
<div style="text-align: right">{wy_s}</div>
<div style="text-align: right; color: {POS}">~{r10(c['pa_total'])}</div>
<div></div>
</div>
</div>"""
    parts.append(a + "\n\n")

    yrs = strip_years(n)
    long_term = len(yrs) < n
    cw, bw = ("70px", 22) if long_term else ("96px", 50)
    cols = " ".join([cw] * len(yrs)) + (" 100px" if long_term else " 104px")
    G2 = f"display: grid; grid-template-columns: minmax(0, 1fr) {cols}; column-gap: {'10px' if long_term else '12px'}; align-items: center"
    dash = f'<div style="text-align: right; color: {MUTED}">–</div>'
    note = ("Selected years. Flat prices, current yields, before policy charges" if long_term
            else "Illustrative: flat prices, current yields, before policy charges")
    s = section_head("How the portfolio and income build", note, "5px")
    s += f'\n<div style="{G2}; height: 22px; border-bottom: 1px solid #1a1f2b; font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">\n<div>S$</div>\n'
    s += "".join(f'<div style="text-align: right">Year {y}</div>\n' for y in yrs)
    s += f'<div style="text-align: right">Year {n + 1} onward</div>\n</div>\n'
    s += f'<div style="{G2}; height: 20px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n<div>Premium paid</div>\n'
    s += "".join(f'<div style="text-align: right">{money(p)}</div>\n' for _ in yrs)
    s += f'<div style="text-align: right; color: {MUTED}">none due</div>\n</div>\n'
    if bp:
        s += f'<div style="{G2}; height: 20px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n<div>Welcome bonus <span style="color: {MUTED}">({bp:g}% of Y1 premium)</span></div>\n'
        s += f'<div style="text-align: right; color: {POS}">+{money(c["bonus"])}</div>\n' + (dash + "\n") * len(yrs) + "</div>\n"
    mx = c["cum"][-1]
    s += f'<div style="{G2}; height: 24px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n<div><b style="font-weight: 600">Invested</b> <span style="color: {MUTED}">({"cumulative" if long_term else ("premiums + bonus, cumulative" if bp else "cumulative")})</span></div>\n'
    for v in [c["cum"][y - 1] for y in yrs] + [mx]:
        s += f'<div style="display: flex; align-items: center; justify-content: flex-end; gap: {5 if long_term else 6}px"><div style="width: {round(bw * v / mx)}px; height: 8px; background: #1a1f2b"></div><b style="font-weight: 600">{money(v)}</b></div>\n'
    s += "</div>\n"
    s += f'<div style="{G2}; height: 20px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n<div>Est. distributions <span style="color: {MUTED}">({wy_s}{"" if long_term else " on amount invested"})</span></div>\n'
    s += "".join(f'<div style="text-align: right">~{r10(c["dist"][y - 1])}</div>\n' for y in yrs)
    s += f'<div style="text-align: right">~{r10(c["dist"][-1])} a year</div>\n</div>\n'
    if cp:
        cl = f"Cashback <span style=\"color: {MUTED}\">({cp:g}%{', one-off, cash' if long_term else ' of Y1 premium, one-off, in cash'})</span>"
        s += f'<div style="{G2}; height: 20px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n<div>{cl}</div>\n'
        s += f'<div style="text-align: right">{money(c["cash"])}</div>\n' + (dash + "\n") * len(yrs) + "</div>\n"
    got = [c["y1_cash"]] + c["dist"][1:]
    s += f'<div style="{G2}; height: 26px; border-top: 1px solid #1a1f2b; font-size: 12px; font-weight: 600; background: #e6f2ee">\n<div style="padding-left: 6px">Cash received</div>\n'
    s += "".join(f'<div style="text-align: right; color: {POS}">~{r10(got[y - 1])}</div>\n' for y in yrs)
    s += f'<div style="text-align: right; color: {POS}; padding-right: 6px">~{r10(c["dist"][-1])} a year</div>\n</div>\n</div>'
    parts.append(s + "\n\n")

    parts.append(gap_section(funds, c, "Year 1 entry: prices now vs their 3-month high", price_window(funds),
                             "18px", "19px", "11px", "10px", "25px", "11.5px", "5px") + "\n\n")

    extras = []
    if bp or cp:
        extras.append(("Welcome bonus and cashback" if bp and cp else "Welcome bonus" if bp else "Cashback")
                      + " are subject to policy and campaign terms, including any clawback on early surrender.")
    text = (f"{sources_text(funds, fetched)} The 3-month high comparison, weighted figures, funding schedule and estimated distributions are our own calculations; "
            f"they assume premiums at the start of each policy year, the same mix, unchanged prices and current yields, "
            f"and exclude policy charges (see the benefit illustration). {' '.join(extras)} Market views: {market_views(spec['thesis'])}; third-party views do not guarantee returns. "
            f"Distributions are not guaranteed, may be paid out of capital (which reduces the fund's NAV) and are not a forecast of future income. "
            f"Prices can fall further after you invest; later premiums are invested at the prices at that time. {spec.get('volatile_note', '')} "
            f"Past performance is not indicative of future performance. For discussion only; read with the product summary, fund prospectuses and product highlights sheets.").replace("  ", " ")
    parts.append(footer(text, "7px", "8.5px", "1.42") + "\n")
    parts.append(TAIL)
    return "".join(parts)


# ------------------------------------------------------------------ top-up
def build_topup(spec, prepared, fetched, funds, c):
    p = spec["premium"]
    nf = len(funds)
    wy_s = f"~{c['wy']:.1f}%"
    entry_long, entry_tile, below = entry_phrase(c["wgap"])
    up = sum(1 for f in funds if f["ytd"] > 0)
    asof = ytd_asof(funds)
    ytd_note = (f"All {nf} funds up YTD to {asof}" if up == nf else f"{up} of {nf} funds up YTD to {asof}")
    if spec.get("idea"):
        idea = spec["idea"]
    elif below:
        idea = (f"Opportunistic top-up into equity-income funds on this market pullback: {entry_long}"
                + (" while still up for the year" if up == nf else "")
                + f". Rising equities should support portfolio NAV while generating around {wy_s[1:]} p.a. in distributions.")
    else:
        idea = (f"Top-up into equity-income funds, with prices {entry_long}. "
                f"Rising equities should support portfolio NAV while generating around {wy_s[1:]} p.a. in distributions.")
    parts = [HEAD.format(title=e(f"ILP Top-Up Pitch - {spec['client']}")),
             '<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 34px 44px; background: #ffffff; color: #1a1f2b; font-family: \'IBM Plex Sans\', system-ui, sans-serif; font-variant-numeric: tabular-nums; display: flex; flex-direction: column; gap: 12px">\n',
             header(spec, prepared, "ILP Top-Up Proposal", "equity-income top-up", "12px"), "\n"]
    tiles = [tile("Top-up", f"S${money(p)}", f"{nf} funds, single top-up", pad="12px 14px"),
             tile("Est. distribution yield", f"{wy_s} p.a.", "Weighted, latest payouts annualised", green=True, pad="12px 14px"),
             tile("Est. distributions", f"~S${r10(c['pa_total'] / 12)}/mo", f"About S${r10(c['pa_total'])} a year at current payouts", green=True, pad="12px 14px"),
             tile("Entry point", entry_tile, f"3-month highs, weighted. {ytd_note}", pad="12px 14px")]
    parts.append('\n<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px">\n' + "\n".join(tiles) + "\n</div>\n\n")
    parts.append(idea_box(idea, "16px 22px", "8px", "18px") + "\n\n")
    parts.append(thesis_box(spec, "12px 18px", "8px", "8px", "1.45") + "\n\n")
    G = "display: grid; grid-template-columns: minmax(0, 1fr) 126px 42px 62px 50px 70px 50px; column-gap: 10px; align-items: center"
    a = section_head("Proposed allocation", f"SGD. Yields: latest payout annualised. YTD is the official figure to {asof}.", "6px")
    a += f"""
<div style="{G}; height: 24px; border-bottom: 1px solid #1a1f2b; font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">
<div>Fund</div>
<div>Role</div>
<div style="text-align: right">Weight</div>
<div style="text-align: right">Amount</div>
<div style="text-align: right">Yield</div>
<div style="text-align: right">Est. p.a.</div>
<div style="text-align: right">YTD</div>
</div>

"""
    for f in funds:
        a += f"""<div style="{G}; height: 24px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">
<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><b style="font-weight: 600">{e(f['code'])}</b> <span style="color: {MUTED}">{e(f['label'])}</span></div>
<div style="color: {MUTED}">{e(f['role'])}</div>
<div style="text-align: right">{f['weight']:g}%</div>
<div style="text-align: right">{money(f['amt'])}</div>
{ycell(f)}
{pacell(f)}
{ytdcell(f)}
</div>
"""
    a += f"""<div style="{G}; height: 28px; border-top: 1px solid #1a1f2b; font-size: 12px; font-weight: 600">
<div>Total</div>
<div></div>
<div style="text-align: right">100%</div>
<div style="text-align: right">{money(p)}</div>
<div style="text-align: right">{wy_s}</div>
<div style="text-align: right; color: {POS}">~{r10(c['pa_total'])}</div>
<div></div>
</div>
</div>"""
    parts.append(a + "\n\n")
    parts.append(gap_section(funds, c, "Where prices are now vs their 3-month high", price_window(funds),
                             "22px", "24px", "11.5px", "12px", "28px", "12px", "6px") + "\n\n")
    text = (f"{sources_text(funds, fetched)} The 3-month high comparison, weighted figures and estimated distributions are our own calculations and exclude charges. "
            f"Market views: {market_views(spec['thesis'])}. Distributions are not guaranteed, may be paid out of capital (which reduces the fund's NAV) and are not a forecast of future income. "
            f"Prices can fall further after you invest. {spec.get('volatile_note', '')} Third-party views do not guarantee returns. Past performance is not indicative of future performance. "
            f"For discussion only; read with the product summary, fund prospectuses and product highlights sheets.").replace("  ", " ")
    parts.append(footer(text, "10px", "9.5px", "1.5") + "\n")
    parts.append(TAIL)
    return "".join(parts)


def main():
    spec, prepared, ff, fetched, funds = load(sys.argv[1])
    c = compute(spec, funds)
    out = build_npay(spec, prepared, fetched, funds, c) if spec["mode"] == "npay" else build_topup(spec, prepared, fetched, funds, c)
    open(sys.argv[2], "w").write(out)
    print(f"Built {sys.argv[2]} ({spec['mode']}) from {spec['fund_file']} (NAV dates {', '.join(sorted({f['nav_date'] for f in funds}))}).")
    print(f"Weighted yield {c['wy']:.3f}% | weighted gap to 3M high {c['wgap']:+.2f}% | est. p.a. S${c['pa_total']:,.0f}")
    if spec["mode"] == "npay":
        print(f"Y1 invested S${c['total_y1']:,.0f} | fully funded S${c['total_full']:,.0f} | Y1 cash received S${c['y1_cash']:,.0f}")
    print(f"Yield per fund: " + ", ".join(f"{f['code']} {'acc' if f['yield_pct'] is None else format(f['yield_pct'], '.2f') + '%'}" for f in funds))
    plan_warn = [f["code"] for f in funds if f["plan_check"] != "named"]
    if plan_warn:
        print(f"CHECK BEFORE PRESENTING: iFUNDS plan tags don't name {spec['plan']} for {', '.join(plan_warn)} "
              f"(see flags). The page makes no availability claim.")
    print_flags(funds, spec["plan"])


if __name__ == "__main__":
    main()
