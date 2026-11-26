#!/usr/bin/env python3
"""Build Nick's ILP Fund Switch Proposal one-pager (rebalance, no new premium).

Usage:  python3 build_switch.py spec.json out/project/Main.dc.html
Needs common.py next to it, and the fund file named in the spec (from fund_data.py).

Every number is computed here from the Customer Investment Report figures in the spec
plus the iFUNDS fund file. Editorial text (idea, tile note) may not contain figures:
any "S$" or "%" in it stops the build, so no typed number can reach the page.

Spec keys (see switch-spec-blank.json)
--------------------------------------
client, plan, date (prepared, YYYY-MM-DD), fund_file
report: {
  date            report date, YYYY-MM-DD
  start_date      first premium date, YYYY-MM-DD
  paid_in         total premiums paid, S$
  dividends_paid_out, dividends_reinvested   S$ to date (from the report)
  rpq_cka_expiry  YYYY-MM-DD
  holdings: [{code, role, value, cost, pnl, units?}]   S$ from the report; pnl includes dividends
}
target:  [{code, weight, role, holds_bonds (true/false)}]    default model: CABF 30 / MGMD 15 / NSAD 25 / ASGI 15 / NAJD 15
idea:       headline text, no figures
tile_lead:  bold opener for the commentary box, no figures (e.g. "Holding up well.")
tile_note:  one sentence for the commentary box, no figures (the dividend sentence is added by the script)
thesis:     exactly 3 x {lead, text, source, date}; each <= 14 days old. Point 4 (balance + entry) is computed.
"""
import json, sys, re
from common import *


def no_figures(label, text):
    if re.search(r"S\$|%|\d{2,}", text or ""):
        fail(f"'{label}' contains a figure. Editorial text can't carry numbers; the script computes them.")


def load(path):
    spec = json.load(open(path))
    for k in ("client", "plan", "date", "fund_file", "report", "target", "idea", "tile_lead", "tile_note", "thesis"):
        if spec.get(k) in (None, "", []):
            fail(f"spec is missing '{k}'")
    r = spec["report"]
    for k in ("date", "start_date", "paid_in", "dividends_paid_out", "dividends_reinvested", "rpq_cka_expiry", "holdings"):
        if r.get(k) in (None, ""):
            fail(f"report is missing '{k}'")
    for h in r["holdings"]:
        for k in ("code", "role", "value", "cost", "pnl"):
            if h.get(k) in (None, ""):
                fail(f"holding {h.get('code')} is missing '{k}'")
    for t in spec["target"]:
        for k in ("code", "weight", "role", "holds_bonds"):
            if t.get(k) in (None, ""):
                fail(f"target fund {t.get('code')} is missing '{k}'")
    if abs(sum(t["weight"] for t in spec["target"]) - 100) > 1e-6:
        fail("target weights don't sum to 100")
    for k in ("idea", "tile_lead", "tile_note"):
        no_figures(k, spec[k])
    reference_mode(spec["client"])
    prepared = pdate(spec["date"])
    rdate = pdate(r["date"])
    if pdate(r["rpq_cka_expiry"]) <= prepared and spec["client"] != REFERENCE_CLIENT:
        fail(f"risk profile / CKA expired on {r['rpq_cka_expiry']}; renew before proposing a switch")
    if (prepared - rdate).days > 7 and spec["client"] != REFERENCE_CLIENT:
        fail(f"report is dated {rdate}, more than 7 days before {prepared}. Use a current report.")
    codes = sorted({h["code"] for h in r["holdings"]} | {t["code"] for t in spec["target"]})
    ff, fetched = load_fund_file(spec["fund_file"], prepared, codes)
    check_thesis(spec["thesis"], prepared, n_points=3)
    return spec, prepared, rdate, ff, fetched


def compute(spec, ff, rdate):
    r = spec["report"]
    F = ff["funds"]
    hold = {h["code"]: h for h in r["holdings"]}
    tgt = {t["code"]: t for t in spec["target"]}
    total_now = sum(h["value"] for h in r["holdings"])
    rows = []
    for code in list(hold) + [c for c in tgt if c not in hold]:
        h, t = hold.get(code), tgt.get(code)
        now = h["value"] if h else 0.0
        after = total_now * t["weight"] / 100 if t else 0.0
        if h and not t:
            act = "Switch out"
        elif t and not h:
            act = "Switch in"
        elif after > now * 1.01:
            act = "Top up"
        elif after < now * 0.99:
            act = "Reduce"
        else:
            act = "Hold"
        y = F[code]["yield_pct"] or 0
        name, _ = LABELS.get(code, (F[code]["name"], None))
        rows.append(dict(code=code, name=name, role=(t or h)["role"], now=now, after=after, weight=t["weight"] if t else 0,
                         pnl_pct=(h["pnl"] / h["cost"] * 100) if h else None, act=act, yield_pct=F[code]["yield_pct"],
                         inc_now=now * y / 100, inc_after=after * y / 100, new=not h))
    pnl = sum(h["pnl"] for h in r["holdings"])
    cost = sum(h["cost"] for h in r["holdings"])
    months = (rdate - pdate(r["start_date"])).days / (365.25 / 12)
    paid_out = r["dividends_paid_out"]
    divs = paid_out + r["dividends_reinvested"]
    vp = total_now + paid_out
    ret = (vp / r["paid_in"] - 1) * 100
    c = dict(rows=rows, total_now=total_now, total_after=sum(x["after"] for x in rows), pnl=pnl, cost=cost, pnl_pct=pnl / cost * 100,
             months=months, paid_out=paid_out, divs=divs, vp=vp, ret=ret,
             ann=((vp / r["paid_in"]) ** (12 / months) - 1) * 100 if months >= 12 else None,
             inc_now=sum(x["inc_now"] for x in rows), inc_after=sum(x["inc_after"] for x in rows))
    c["y_now"] = c["inc_now"] / total_now * 100
    c["y_after"] = c["inc_after"] / c["total_after"] * 100
    tf = [dict(F[t["code"]], weight=t["weight"]) for t in spec["target"]]
    c["targets"] = tf
    c["wgap"] = sum(f["weight"] / 100 * f["gap_pct"] for f in tf)
    c["bonds_pct"] = sum(t["weight"] for t in spec["target"] if t["holds_bonds"])
    # revaluation check at iFUNDS NAV (only if units are given): for Nick, not the page
    c["reval"] = [(h["code"], h["units"] * F[h["code"]]["nav"], h["value"], F[h["code"]]["nav_date"]) for h in r["holdings"] if h.get("units")]
    return c


def tile(lab, val, sub, green):
    bg = '#e6f2ee' if green else '#f3f5f8'
    vc = POS if green else '#1a1f2b'
    return (f'<div style="background: {bg}; padding: 10px 13px; display: flex; flex-direction: column; gap: 3px">'
            f'<div style="font-size: 10px; letter-spacing: 0.8px; text-transform: uppercase; color: {MUTED}">{lab}</div>'
            f'<div style="{SERIF}; font-weight: 600; font-size: 19px; color: {vc}; white-space: nowrap">{val}</div>'
            f'<div style="font-size: 10px; color: {MUTED}">{sub}</div></div>')


def b(t):
    return f'<b style="font-weight: 600">{t}</b>'


def h2(t, sub=""):
    return (f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px"><h2 style="margin: 0; font-size: 13.5px; font-weight: 600">{t}</h2>'
            f'<div style="font-size: 10px; color: {MUTED}">{sub}</div></div>')


def pct_cell(v):
    if v is None:
        return f'<div style="text-align: right; color: {MUTED}"></div>'
    col = POS if v > 0 else (NEG if v < 0 else MUTED)
    return f'<div style="text-align: right; color: {col}">{signed_pct(v)}</div>'


TCOLS = "minmax(0, 1fr) 100px 54px 48px 92px 54px 46px 58px"


def table(c):
    hdr = ''.join(f'<div{" style=\"text-align: right\"" if rgt else (" style=\"padding-left: 4px\"" if i == 0 else "")}>{t}</div>'
                  for i, (t, rgt) in enumerate([("Fund", 0), ("Role", 0), ("Now", 1), ("P&amp;L", 1), ("Action", 0), ("After", 1), ("Weight", 1), ("Yield", 1)]))
    out = (f'<div style="display: grid; grid-template-columns: {TCOLS}; column-gap: 8px; align-items: center; height: 21px; border-bottom: 1px solid #1a1f2b; '
           f'font-size: 9.5px; letter-spacing: 0.5px; text-transform: uppercase; color: {MUTED}">{hdr}</div>')
    for x in c["rows"]:
        actc = POS if x["act"] in ("Top up", "Switch in") else (NEG if x["act"] in ("Reduce", "Switch out") else MUTED)
        y = "n/a" if x["yield_pct"] is None else f"{x['yield_pct']:.2f}%"
        out += (f'<div style="display: grid; grid-template-columns: {TCOLS}; column-gap: 8px; align-items: center; height: 21px; border-bottom: 1px solid #e3e7ed; font-size: 11px;{" background: #e6f2ee;" if x["new"] else ""}">'
                f'<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-left: 4px">{b(e(x["code"]))} <span style="color: {MUTED}">{e(x["name"])}</span></div>'
                f'<div style="color: {MUTED}; white-space: nowrap">{e(x["role"])}</div>'
                f'<div style="text-align: right">{money(x["now"]) if x["now"] else "—"}</div>{pct_cell(x["pnl_pct"])}'
                f'<div style="font-weight: 500; color: {actc}; white-space: nowrap">{x["act"]}</div>'
                f'<div style="text-align: right">{money(x["after"]) if x["after"] else "—"}</div>'
                f'<div style="text-align: right">{x["weight"]:g}%</div><div style="text-align: right">{y}</div></div>')
    plc = POS if c["pnl_pct"] > 0 else NEG
    out += (f'<div style="display: grid; grid-template-columns: {TCOLS}; column-gap: 8px; align-items: center; height: 25px; border-top: 1px solid #1a1f2b; font-size: 11.5px; font-weight: 600">'
            f'<div style="padding-left: 4px">Total</div><div></div><div style="text-align: right">{money(c["total_now"])}</div>'
            f'<div style="text-align: right; color: {plc}">{signed_pct(c["pnl_pct"])}</div><div></div>'
            f'<div style="text-align: right">{money(c["total_after"])}</div><div style="text-align: right">100%</div>'
            f'<div style="text-align: right; white-space: nowrap">{c["y_now"]:.1f}→{c["y_after"]:.1f}%</div></div>')
    return out


def highs(c, window):
    hc = "150px 120px 60px minmax(0, 1fr) 52px"
    mx = max(abs(f["gap_pct"]) for f in c["targets"]) or 1
    out = ('<div style="display: flex; flex-direction: column">' + h2("Proposed funds: price now vs 3-month high", f"Unit price (NAV) only, {e(window)}") +
           f'<div style="display: grid; grid-template-columns: {hc}; column-gap: 12px; align-items: center; height: 20px; border-bottom: 1px solid #1a1f2b; font-size: 9.5px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">'
           '<div>Fund</div><div style="text-align: right">3-month high</div><div style="text-align: right">Now</div><div>Gap to high</div><div style="text-align: right">%</div></div>')
    for f in c["targets"]:
        g = f["gap_pct"]
        bc, tc = (NEGBAR, NEG) if g < 0 else (POS, POS)
        short = LABELS.get(f["code"], (None, f["code"]))[1]
        out += (f'<div style="display: grid; grid-template-columns: {hc}; column-gap: 12px; align-items: center; height: 19px; border-bottom: 1px solid #e3e7ed; font-size: 11px">'
                f'<div>{b(f["code"])} <span style="color: {MUTED}">{e(short)}</span></div><div style="text-align: right">{e(f["high_str"])} ({e(f["high_date_short"])})</div><div style="text-align: right">{e(f["nav_str"])}</div>'
                f'<div style="position: relative; height: 11px; background: #f3f5f8"><div style="position: absolute; left: 0; top: 0; width: {abs(g) / mx * 100:.1f}%; height: 11px; background: {bc}"></div></div>'
                f'<div style="text-align: right; font-weight: 500; color: {tc}">{signed_pct(g)}</div></div>')
    out += (f'<div style="display: grid; grid-template-columns: {hc}; column-gap: 12px; align-items: center; height: 24px; border-top: 1px solid #1a1f2b; font-size: 11.5px; font-weight: 600">'
            f'<div>Weighted mix</div><div></div><div></div><div style="position: relative; height: 11px; background: #f3f5f8"><div style="position: absolute; left: 0; top: 0; width: {abs(c["wgap"]) / mx * 100:.1f}%; height: 11px; background: #1a1f2b"></div></div>'
            f'<div style="text-align: right">{signed_pct(c["wgap"])}</div></div></div>')
    return out


def build(spec, prepared, rdate, fetched, c):
    r = spec["report"]
    start = pdate(r["start_date"])
    months = c["months"]
    mo = f"{months:.0f} months" if months < 23.5 else f"{months / 12:.1f} years"
    ret_sub = (f"S${money(c['total_now'])} value + S${money(c['paid_out'])} paid out<br>{signed_pct(c['ret'])} on premiums, over {mo}"
               + (f" · {signed_pct(c['ann'])} a year" if c["ann"] is not None else ""))
    tiles = [tile("Paid in", f"S${money(r['paid_in'])}", f"Premiums since {start.strftime('%b %Y')}", False),
             tile("Value + payouts", f"S${money(c['vp'])}", ret_sub, True)]
    div_txt = (f"paid out S${money(c['paid_out'])} in dividends" if not r["dividends_reinvested"]
               else f"paid S${money(c['divs'])} in dividends (S${money(c['paid_out'])} paid out, S${money(r['dividends_reinvested'])} reinvested)")
    note = (f"{b(e(spec['tile_lead']))} {e(spec['tile_note'])} Since {start.strftime('%b %Y')} the plan has {div_txt}, "
            f"about S${r10(c['divs'] / months)} a month.")
    funds_t = c["targets"]
    up = [f for f in funds_t if (f["ytd"] or 0) > 0]
    gap_word = (f"about {round(abs(c['wgap']))}% below" if c["wgap"] <= -1.5 else
                (f"about {round(c['wgap'])}% above" if c["wgap"] >= 1.5 else "close to"))
    p4 = (f"{c['bonds_pct']:g}% stays in balanced and multi-asset funds that hold bonds alongside shares. The proposed funds sit {gap_word} their 3-month highs, "
          f"and {'all ' + str(len(funds_t)) if len(up) == len(funds_t) else str(len(up)) + ' of ' + str(len(funds_t))} are up this year (to {ytd_asof(funds_t)}).")
    thesis = [(t["lead"], t["text"]) for t in spec["thesis"]] + [("Balance kept, and the entry.", p4)]
    income = [("Income now", f"S${money(c['inc_now'])} / yr", f"{c['y_now']:.1f}% · ~S${r10(c['inc_now'] / 12)} a month"),
              ("Income after", f"S${money(c['inc_after'])} / yr", f"{c['y_after']:.1f}% · ~S${r10(c['inc_after'] / 12)} a month")]
    d = c["inc_after"] - c["inc_now"]
    income.append(("The trade", f"~S${r10(abs(d))} / yr {'less' if d < 0 else 'more'}",
                   "for more equity growth in your NAV" if d < 0 else "with more equity growth in your NAV"))
    cells = ''.join(f'<div style="display: flex; flex-direction: column; gap: 2px"><div style="font-size: 10px; letter-spacing: 0.8px; text-transform: uppercase; color: #3b4a45">{l}</div>'
                    f'<div style="{SERIF}; font-weight: 600; font-size: 17px">{v}</div><div style="font-size: 10px; color: #3b4a45">{dd}</div></div>' for l, v, dd in income)
    expiry = pdate(r["rpq_cka_expiry"])
    how = (f"A switch within your existing policy: no new premium; charges, if any, per policy terms. Submit before your risk profile and CKA expire on "
           f"{day_mon(expiry)}. After amounts use report values; the switch uses prices on the day.")
    bridge = (f"Fund P&amp;L ({signed_pct(c['pnl_pct'])}) is on fund cost of S${money(c['cost'])}, which includes welcome-bonus units; "
              f"against premiums paid, value + dividends is {signed_pct(c['ret'])}.")
    window = price_window(funds_t)
    all_f = [ffund for ffund in c["all_funds"]]
    footer = (f"Sources: holdings, P&amp;L and dividends from your Manulife Customer Investment Report ({short_date(rdate)}). Fund prices (NAV, {nav_dates_text(all_f)}), 3-month highs, "
              f"distributions and official YTD returns (to {ytd_asof(all_f)}) from the Manulife iFUNDS public fund library, fetched {short_date(fetched.date())}. "
              f"Yields annualise each fund's latest payout ({freq_text(all_f)}) on its latest NAV. Market data: {market_views(spec['thesis'])}. "
              f"Third-party views do not guarantee returns. Distributions are not guaranteed, may be paid out of capital (which reduces NAV) and are not a forecast of future income. "
              f"Past performance is not indicative of future performance. For discussion only; read with the product summary, prospectuses and product highlights sheets.")
    body = f'''<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 22px 42px 12px; background: #ffffff; color: #1a1f2b; font-family: 'IBM Plex Sans', system-ui, sans-serif; font-variant-numeric: tabular-nums; display: flex; flex-direction: column; gap: 6px">

<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #1a1f2b; padding-bottom: 10px">
<div style="display: flex; flex-direction: column; gap: 3px">
<div style="font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase; color: {MUTED}">Portfolio Rebalance Proposal</div>
<h1 style="margin: 0; {SERIF}; font-weight: 600; font-size: 28px; line-height: 1.1">{e(spec['client'])}</h1>
</div>
<div style="display: flex; flex-direction: column; align-items: flex-end; gap: 5px">
<div style="background: #1a1f2b; color: #d4b46a; font-size: 10px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; padding: 4px 9px">No additional premium · fund switch only</div>
<div style="text-align: right; font-size: 10.5px; color: {MUTED}">{e(spec['plan'])} · Prepared {short_date(prepared)} by Nicholas Low</div>
</div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1.4fr 1.8fr; gap: 10px">{''.join(tiles)}<div style="background: #f3ede0; padding: 11px 14px; font-size: 11px; line-height: 1.45; color: #3d3524; display: flex; align-items: center"><div>{note}</div></div></div>

<div style="background: #1a1f2b; color: #ffffff; padding: 12px 20px; display: flex; flex-direction: column; gap: 5px">
<div style="font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: #d4b46a">The idea</div>
<div style="{SERIF}; font-weight: 500; font-size: 14.5px; line-height: 1.42">{e(spec['idea'])}</div>
</div>

<div style="background: #f3f5f8; padding: 9px 16px; display: flex; flex-direction: column; gap: 6px">
<h2 style="margin: 0; font-size: 13.5px; font-weight: 600">Why equity dividends, why now</h2>
<div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px 20px; font-size: 10.6px; line-height: 1.42">{''.join(f'<div>{b(e(x))} {e(t)}</div>' for x, t in thesis)}</div>
</div>

{highs(c, window)}

<div style="display: flex; flex-direction: column">
{h2("Your portfolio: now and after the switch", f"SGD. P&amp;L includes dividends since {day_mon(start)} {start.year}")}
{table(c)}
<div style="font-size: 9.5px; color: {MUTED}; padding: 4px 4px 0">{bridge}</div>
</div>

<div style="background: #e6f2ee; padding: 10px 16px; display: flex; flex-direction: column; gap: 6px"><h2 style="margin: 0; font-size: 13px; font-weight: 600">Your yearly income: before and after</h2><div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px">{cells}</div><div style="font-size: 10px; color: #3b4a45; line-height: 1.4; border-top: 1px solid #c3dcd3; padding-top: 5px">{how}</div></div>

<div style="margin-top: auto; border-top: 1px solid #c9d0da; padding-top: 7px; font-size: 8.5px; line-height: 1.45; color: {MUTED}">{footer}</div>
'''
    return HEAD.format(title=e(f"ILP Fund Switch Proposal - {spec['client']}")) + body + TAIL


def main():
    spec, prepared, rdate, ff, fetched = load(sys.argv[1])
    c = compute(spec, ff, rdate)
    codes = [x["code"] for x in c["rows"]]
    c["all_funds"] = [ff["funds"][k] for k in codes]
    out = build(spec, prepared, rdate, fetched, c)
    open(sys.argv[2], "w").write(out)
    print(f"Built {sys.argv[2]} from report {rdate} + {spec['fund_file']}.")
    print(f"Now S${c['total_now']:,.0f} -> after S${c['total_after']:,.0f} | income S${c['inc_now']:,.0f} -> S${c['inc_after']:,.0f} "
          f"({c['y_now']:.2f}% -> {c['y_after']:.2f}%) | fund P&L {c['pnl_pct']:+.2f}% on S${c['cost']:,.0f} | "
          f"value+payouts {c['ret']:+.2f}% on premiums over {c['months']:.1f} months | weighted gap {c['wgap']:+.2f}%")
    for code, rv, v, nd in c["reval"]:
        gap = (rv / v - 1) * 100
        if abs(gap) > 0.25:
            print(f"DATE CHECK: {code} units x iFUNDS NAV ({nd}) = S${rv:,.0f} vs report S${v:,.0f} ({gap:+.2f}%). Report and NAV dates differ.")
    plan_warn = [f["code"] for f in c["targets"] if f["plan_check"] != "named"]
    if plan_warn:
        print(f"CHECK BEFORE PRESENTING: iFUNDS plan tags don't name {spec['plan']} for {', '.join(plan_warn)}.")
    print(f"Risk profile / CKA expires {spec['report']['rpq_cka_expiry']}: submit before then.")
    print_flags(c["all_funds"], spec["plan"])


if __name__ == "__main__":
    main()
