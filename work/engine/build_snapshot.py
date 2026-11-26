#!/usr/bin/env python3
"""Build Nick's Client Portfolio Snapshot one-pager from Customer Investment Report figures.

Usage:  python3 build_snapshot.py spec.json out/project/Main.dc.html
Needs common.py next to it. No iFUNDS data is needed (the report is the price source).

The spec holds only figures read off the report. Every total, %, bar and comment figure
is computed here, and the totals are checked against the report's own page-1 totals.

Spec keys (see snapshot-spec-blank.json)
----------------------------------------
client, report_date (YYYY-MM-DD)
capital_invested      total investment cost on the report (premiums), S$
partial_withdrawals   S$ withdrawn to date (0 if none)
report_totals         {value, pnl} as printed on the report (used to check the fund lines add up)
policies   [{label, start ("May 2024"), paid_out, reinvested}]
funds      [{code, name, value, pnl, pnl_pct?}]  pnl includes dividends (Manulife definition);
           pnl_pct: the report's own % if shown, otherwise the script uses pnl / (value - pnl)
note       optional extra comment for "What stands out" (no figures allowed)
"""
import json, sys, re
from common import *

TOL = 2.5   # S$ rounding tolerance when checking against the report's own totals


def load(path):
    s = json.load(open(path))
    for k in ("client", "report_date", "capital_invested", "partial_withdrawals", "report_totals", "policies", "funds"):
        if s.get(k) in (None, "", []):
            fail(f"spec is missing '{k}'")
    for f in s["funds"]:
        for k in ("code", "name", "value", "pnl"):
            if f.get(k) is None:
                fail(f"fund {f.get('code')} is missing '{k}'")
    for p in s["policies"]:
        for k in ("label", "start", "paid_out", "reinvested"):
            if p.get(k) is None:
                fail(f"policy {p.get('label')} is missing '{k}'")
    if s.get("note") and re.search(r"S\$|%|\d{2,}", s["note"]):
        fail("'note' contains a figure; comment figures are computed by the script")
    return s


def compute(s):
    funds = sorted(s["funds"], key=lambda f: -f["pnl"])
    for f in funds:
        f["pct"] = f["pnl_pct"] if f.get("pnl_pct") is not None else f["pnl"] / (f["value"] - f["pnl"]) * 100
        f["pct_src"] = "report" if f.get("pnl_pct") is not None else "computed"
    value = sum(f["value"] for f in funds)
    pnl = sum(f["pnl"] for f in funds)
    paid_out = sum(p["paid_out"] for p in s["policies"])
    reinv = sum(p["reinvested"] for p in s["policies"])
    rt = s["report_totals"]
    issues = []
    if abs(value - rt["value"]) > TOL:
        issues.append(f"fund values add to S${value:,.0f} but the report total is S${rt['value']:,.0f}")
    if abs(pnl - rt["pnl"]) > TOL:
        issues.append(f"fund P&L adds to S${pnl:,.0f} but the report total is S${rt['pnl']:,.0f}")
    if issues:
        fail("; ".join(issues) + ". Re-read the report lines before building.")
    fund_cost = value + paid_out + s["partial_withdrawals"] - pnl      # cost basis behind Manulife's P&L (incl. bonus units)
    incl_bonus = value + paid_out + s["partial_withdrawals"] - s["capital_invested"]
    c = dict(funds=funds, value=value, pnl=pnl, paid_out=paid_out, reinv=reinv, divs=paid_out + reinv,
             fund_cost=fund_cost, fund_ret=pnl / fund_cost * 100, incl_bonus=incl_bonus,
             bonus_implied=fund_cost - s["capital_invested"], n_pol=len(s["policies"]), n_funds=len(funds))
    return c


def bars(c):
    W = 220
    pos = max([f["pnl"] for f in c["funds"] if f["pnl"] > 0] or [0])
    neg = max([-f["pnl"] for f in c["funds"] if f["pnl"] < 0] or [0])
    scale = W / (pos + neg) if pos + neg else 0
    zero = neg * scale
    return zero, scale


def build(s, c):
    rd = pdate(s["report_date"])
    zero, scale = bars(c)
    G = "display: grid; grid-template-columns: minmax(0, 1fr) 66px 220px 66px 48px; column-gap: 12px; align-items: center"
    rows = ""
    for f in c["funds"]:
        w = abs(f["pnl"]) * scale
        if f["pnl"] >= 0:
            bar = f'<div style="position: absolute; left: {zero:.0f}px; top: 0; width: {max(w, 1):.0f}px; height: 12px; background: #1f6f5c"></div>'
            col, sgn = POS, "+"
        else:
            bar = f'<div style="position: absolute; left: {zero - max(w, 1):.0f}px; top: 0; width: {max(w, 1):.0f}px; height: 12px; background: {NEGBAR}"></div>'
            col, sgn = NEG, "−"
        rows += (f'<div style="{G}; height: 24px; border-bottom: 1px solid #e3e7ed; font-size: 11.5px">\n'
                 f'<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><b style="font-weight: 600">{e(f["code"])}</b> <span style="color: {MUTED}">{e(f["name"])}</span></div>\n'
                 f'<div style="text-align: right">{money(f["value"])}</div>\n'
                 f'<div style="position: relative; height: 12px; background: #f3f5f8">{bar}</div>\n'
                 f'<div style="text-align: right; font-weight: 500; color: {col}">{sgn}{money(abs(f["pnl"]))}</div>\n'
                 f'<div style="text-align: right; color: {MUTED}">{signed_pct(f["pct"])}</div>\n</div>\n')
    pols = ""
    PG = "display: grid; grid-template-columns: minmax(0, 1fr) 54px 70px 48px; column-gap: 8px; align-items: center"
    for p in s["policies"]:
        pols += (f'<div style="{PG}; height: 22px; border-bottom: 1px solid #e3e7ed; font-size: 11px">\n<div>{e(p["label"])} <span style="color: {MUTED}">({e(p["start"])})</span></div>\n'
                 f'<div style="text-align: right">{money(p["paid_out"])}</div>\n<div style="text-align: right">{money(p["reinvested"])}</div>\n'
                 f'<div style="text-align: right">{money(p["paid_out"] + p["reinvested"])}</div>\n</div>\n')
    # What stands out: computed from the lines
    gains = [f for f in c["funds"] if f["pnl"] > 0]
    top = gains[:3]
    top_sum = sum(f["pnl"] for f in top)
    pts = []
    if top and c["pnl"] > 0:
        pts.append(f'<div><b style="font-weight: 600">{"Three funds drive" if len(top) == 3 else "The top funds drive"} the result.</b> '
                   f'{", ".join(f["code"] for f in top[:-1])} and {top[-1]["code"]} account for about S${top_sum / 1000:.1f}k of the S${c["pnl"] / 1000:.1f}k net gain.</div>')
    worst = c["funds"][-1]
    if worst["pnl"] < 0:
        pts.append(f'<div><b style="font-weight: 600">{e(worst["name"])} ({e(worst["code"])}) is the main detractor</b> at −S${abs(worst["pnl"]) / 1000:.1f}k, '
                   f'a {worst["value"] / c["value"] * 100:.1f}% holding.</div>')
    big = max(c["funds"], key=lambda f: f["value"])
    if big is not worst and big not in top:
        pts.append(f'<div><b style="font-weight: 600">Largest holding: {e(big["name"])} ({e(big["code"])})</b>, {big["value"] / c["value"] * 100:.1f}% of the portfolio, '
                   f'at {signed_pct(big["pct"])} including dividends.</div>')
    if s.get("note"):
        pts.append(f"<div>{e(s['note'])}</div>")
    computed = [f["code"] for f in c["funds"] if f["pct_src"] == "computed"]
    pct_note = ("Fund percentages are the report's own." if not computed else
                "Fund percentages are P&amp;L ÷ (value − P&amp;L)" + ("" if len(computed) == c["n_funds"] else f" for {', '.join(computed)}; the rest are the report's own") + ".")
    tile = lambda lab, val, sub, extra="", green=False: (
        f'<div style="background: {"#e6f2ee" if green else "#f3f5f8"}; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px">\n'
        f'<div style="font-size: 10.5px; letter-spacing: 0.8px; text-transform: uppercase; color: {"#3b4a45" if green else MUTED}">{lab}</div>\n'
        f'<div style="{SERIF}; font-weight: 600; font-size: 22px{"; color: " + POS if green else ""}">{val}</div>\n'
        f'<div style="font-size: 10.5px; color: {"#3b4a45" if green else MUTED}">{sub}</div>\n'
        + (f'<div style="font-size: 10.5px; color: #1a1f2b; font-weight: 500">{extra}</div>\n' if extra else "") + '</div>')
    sgn = lambda x: ("+" if x >= 0 else "−") + f"S${money(abs(x))}"
    html_ = HEAD.format(title=e(f"Portfolio Snapshot - {s['client']}")) + f"""<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 34px 44px; background: #ffffff; color: #1a1f2b; font-family: 'IBM Plex Sans', system-ui, sans-serif; font-variant-numeric: tabular-nums; display: flex; flex-direction: column; gap: 14px">

<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #1a1f2b; padding-bottom: 12px">
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase; color: {MUTED}">Portfolio Snapshot</div>
<h1 style="margin: 0; {SERIF}; font-weight: 600; font-size: 30px; line-height: 1.1">{e(s['client'])}</h1>
</div>
<div style="text-align: right; font-size: 11.5px; line-height: 1.5; color: {MUTED}">
<div>Investment-linked policies, fund-level view</div>
<div>As of {long_date(rd)}</div>
<div>Prepared by Nicholas Low</div>
</div>
</div>

<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px">
{tile("Market value", f"S${money(c['value'])}", f"{c['n_pol']} policies, {c['n_funds']} funds", f"Premiums invested: S${money(s['capital_invested'])}")}
{tile("Fund P&amp;L", sgn(c['pnl']), "Dividends included", f"Vs premiums, incl. welcome bonuses: {sgn(c['incl_bonus'])}", green=c['pnl'] >= 0)}
{tile("Fund-level return", f"{signed_pct(c['fund_ret'])}", f"On fund cost of ~S${c['fund_cost'] / 1000:,.1f}k (incl. bonus units). Not annualised", green=c['fund_ret'] >= 0)}
{tile("Dividends to date", f"S${money(c['divs'])}", "Paid out + reinvested")}
</div>

<div style="display: flex; flex-direction: column; gap: 0">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px">
<h2 style="margin: 0; font-size: 14px; font-weight: 600">Profit &amp; loss by fund</h2>
<div style="font-size: 10.5px; color: {MUTED}">Funds held across all policies, combined. SGD.</div>
</div>
<div style="{G}; height: 24px; border-bottom: 1px solid #1a1f2b; font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">
<div>Fund</div><div style="text-align: right">Value</div><div style="text-align: center">Loss / gain</div><div style="text-align: right">P&amp;L</div><div style="text-align: right">%</div>
</div>
{rows}<div style="{G}; height: 28px; border-top: 1px solid #1a1f2b; font-size: 12px; font-weight: 600">
<div>Total</div><div style="text-align: right">{money(c['value'])}</div><div></div>
<div style="text-align: right; color: {POS if c['pnl'] >= 0 else NEG}">{sgn(c['pnl'])[0]}{money(abs(c['pnl']))}</div>
<div style="text-align: right">{signed_pct(c['fund_ret'])}</div>
</div>
</div>

<div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; align-items: start">
<div style="display: flex; flex-direction: column; gap: 0">
<h2 style="margin: 0 0 6px 0; font-size: 14px; font-weight: 600">Dividends by policy</h2>
<div style="{PG}; height: 22px; border-bottom: 1px solid #1a1f2b; font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: {MUTED}">
<div>Policy</div><div style="text-align: right">Paid out</div><div style="text-align: right">Reinvested</div><div style="text-align: right">Total</div>
</div>
{pols}<div style="{PG}; height: 26px; border-top: 1px solid #1a1f2b; font-size: 11.5px; font-weight: 600">
<div>Total (S$)</div><div style="text-align: right">{money(c['paid_out'])}</div><div style="text-align: right">{money(c['reinv'])}</div><div style="text-align: right">{money(c['divs'])}</div>
</div>
</div>
<div style="display: flex; flex-direction: column; gap: 6px">
<h2 style="margin: 0; font-size: 14px; font-weight: 600">What stands out</h2>
<div style="display: flex; flex-direction: column; gap: 9px; font-size: 11.5px; line-height: 1.5; padding-top: 4px">
{''.join(pts)}
</div>
</div>
</div>

<div style="margin-top: auto; border-top: 1px solid #c9d0da; padding-top: 10px; font-size: 9.5px; line-height: 1.5; color: {MUTED}">
How the figures fit: fund P&amp;L (as defined by Manulife, dividends included) is measured on fund cost of S${money(c['fund_cost'])}, which includes welcome-bonus units. Against premiums invested (S${money(s['capital_invested'])}), market value + dividends paid out{f" + partial withdrawals (S${money(s['partial_withdrawals'])})" if s['partial_withdrawals'] else ""} = {sgn(c['incl_bonus'])}. Reinvested dividends are already inside market value and are not added again. {pct_note} Source: Manulife Customer Investment Report dated {short_date(rd)}. Prices are indicative and not guaranteed. Percentages are not annualised. Past performance is not indicative of future performance. Investments are subject to risk, and you may lose the principal amount invested. This snapshot is for information only and is not a recommendation; it should be read together with the insurer's policy documents and your adviser's advice.
</div>
"""
    return html_ + TAIL


def main():
    s = load(sys.argv[1])
    c = compute(s)
    open(sys.argv[2], "w").write(build(s, c))
    print(f"Built {sys.argv[2]}. Value S${c['value']:,.0f} | fund P&L S${c['pnl']:,.0f} on fund cost S${c['fund_cost']:,.0f} "
          f"({c['fund_ret']:+.2f}%) | vs premiums incl. bonuses S${c['incl_bonus']:,.0f} | implied bonus units S${c['bonus_implied']:,.0f} | dividends S${c['divs']:,.0f}")
    print("Check the implied bonus units against the policy-level welcome bonuses on the report before sending.")


if __name__ == "__main__":
    main()
