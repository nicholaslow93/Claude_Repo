"""Shared helpers for Nick's one-pager builds (pitch, switch, snapshot).

Nothing in here holds client or fund data. Fund data comes from a funds_<navdate>.json
file made by fund_data.py; client inputs come from the spec file passed to each build.
"""
import json, sys, html, re
from datetime import date, datetime, timedelta

THESIS_MAX_AGE = 14     # days: thesis data older than this blocks the build
FUND_FILE_MAX_AGE = 0   # days between the fund fetch and the prepared date (same day only)
REFERENCE_CLIENT = "Sample Client"   # reference builds only: data-age checks are skipped so references can be rebuilt later
_ref = {"on": False}


def reference_mode(client):
    _ref["on"] = (client == REFERENCE_CLIENT)
    if _ref["on"]:
        print("REFERENCE BUILD (Sample Client): data-age checks skipped. Not for client use.")

# Editorial labels Nick uses for funds on file. Labels only, never data.
LABELS = {
    "ASGI": ("Allspring Global Equity Enhanced Income", "Allspring"),
    "CABF": ("Capital Group American Balanced", "Cap Group"),
    "NAJD": ("Amova Japan Dividend Equity (SGD-H)", "Amova Japan"),
    "NSAD": ("Amova Singapore Dividend Equity", "Amova SG"),
    "MGSO": ("MGF Global Semiconductor Opps (SGD-H, Acc)", "MGF Semis"),
    "MGMD": ("MGF Global Multi-Asset Diversified Income", "MGF Multi-Asset"),
    "PGIA": ("PIMCO GIS Income", "PIMCO Income"),
    "MARH": ("MGF Asia Pac REIT", "MGF APAC REIT"),
}


def fail(msg):
    sys.exit(f"BUILD STOPPED: {msg}")


def e(s):
    return html.escape(str(s), quote=False)


def money(x):
    return f"{round(x):,}"


def r10(x):
    return f"{int(round(x / 10.0) * 10):,}"


def signed_pct(x, dp=1):
    s = f"{abs(x):.{dp}f}%"
    if round(abs(x), dp) == 0:
        return s
    return ("+" if x > 0 else "−") + s


def pdate(s):
    """Accepts '2026-11-20' or '20 November 2026' / '20 Nov 2026'."""
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%Y/%m/%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    fail(f"can't read the date '{s}' (use YYYY-MM-DD)")


def long_date(dt):
    return f"{dt.day} {dt.strftime('%B %Y')}"


def short_date(dt):
    return f"{dt.day} {dt.strftime('%b %Y')}"


def day_mon(dt):
    return f"{dt.day} {dt.strftime('%b')}"


def load_fund_file(path, prepared, codes):
    ff = json.load(open(path))
    fetched = datetime.fromisoformat(ff["fetched_at"].replace("Z", "+00:00")) + timedelta(hours=8)  # SGT
    today_sgt = (datetime.utcnow() + timedelta(hours=8)).date()
    if prepared != today_sgt and not _ref["on"]:
        fail(f"proposal is dated {prepared} but today is {today_sgt} (SGT). Client pages are built on the day, "
             f"with a fund file fetched that day; backdating would let stale prices through.")
    age = (prepared - fetched.date()).days
    if (age > FUND_FILE_MAX_AGE or age < 0) and not _ref["on"]:
        fail(f"fund file was fetched {fetched.date()} but the proposal is dated {prepared}. Re-run the iFUNDS fetch "
             f"(same-day files can be reused).")
    missing = [c for c in codes if c not in ff["funds"]]
    if missing:
        fail(f"fund file has no data for {', '.join(missing)}. Fetch them from iFUNDS first.")
    return ff, fetched


def check_thesis(thesis, prepared, n_points=4, years=None):
    """Each point: {lead, text, sources: [{name, date, checked}]}.
    date = the source's publication date (as printed in the footer).
    checked = the day this run confirmed it is still the latest release; must be within THESIS_MAX_AGE days.
    """
    if len(thesis) != n_points:
        fail(f"need exactly {n_points} thesis points, got {len(thesis)}")
    for i, t in enumerate(thesis, 1):
        for k in ("lead", "text", "sources"):
            if not t.get(k):
                fail(f"thesis point {i} is missing '{k}' (every point needs named, dated sources)")
        for s in t["sources"]:
            for k in ("name", "date", "checked"):
                if not s.get(k):
                    fail(f"thesis point {i}: a source is missing '{k}'")
            age = (prepared - pdate(s["checked"])).days
            if (age > THESIS_MAX_AGE or age < 0) and not _ref["on"]:
                fail(f"thesis point {i}: '{s['name']}' was last checked {s['checked']} ({age} days before the proposal date); "
                     f"limit is {THESIS_MAX_AGE}. Re-check it's still the latest release.")
            if pdate(s["date"]) > pdate(s["checked"]):
                fail(f"thesis point {i}: '{s['name']}' is dated after it was checked")
        if years is not None:
            for m in re.finditer(r"Years? 2\s*[–-]\s*(\d+)", t["lead"] + " " + t["text"]):
                if int(m.group(1)) != years:
                    fail(f"thesis point {i} says 'Years 2–{m.group(1)}' but this is a {years}-pay plan")


def market_views(thesis):
    """One entry per named source, with its publication date (latest if cited twice)."""
    latest = {}
    for t in thesis:
        for s in t["sources"]:
            dt = pdate(s["date"])
            if s["name"] not in latest or dt > latest[s["name"]]:
                latest[s["name"]] = dt
    shown = {}
    for t in thesis:
        for s in t["sources"]:
            if pdate(s["date"]) == latest[s["name"]]:
                shown[s["name"]] = s["date"]
    fmt = lambda raw: pdate(raw).strftime("%b %Y") if len(raw) == 7 else short_date(pdate(raw))
    return "; ".join(f"{s} ({fmt(shown[s])})" for s in latest)


def price_window(funds):
    starts = sorted({pdate(f["window_start"]) for f in funds})
    ends = sorted({pdate(f["window_end"]) for f in funds})

    def fmt(ds, year):
        days = "/".join(str(x.day) for x in ds)
        return f"{days} {ds[-1].strftime('%b')}" + (f" {ds[-1].year}" if year else "")
    if len({x.month for x in starts}) > 1 or len({x.month for x in ends}) > 1:
        return f"{short_date(starts[0])} to {short_date(ends[-1])}"
    return f"{fmt(starts, False)} to {fmt(ends, True)}"


def nav_dates_text(funds):
    by = {}
    for f in funds:
        by.setdefault(f["nav_date"], []).append(f["code"])
    if len(by) == 1:
        return short_date(pdate(next(iter(by))))
    latest = max(by)
    parts = [short_date(pdate(latest))]
    for dt, codes in sorted(by.items()):
        if dt != latest:
            parts.append(f"{', '.join(codes)} {day_mon(pdate(dt))}")
    return "; ".join(parts)


def ytd_asof(funds):
    s = {f["ytd_asof"] for f in funds}
    if len(s) != 1:
        fail(f"funds have different YTD dates on iFUNDS: {s}")
    return short_date(pdate(s.pop()))


def freq_text(funds):
    per = {f.get("payouts_per_year") for f in funds if f.get("yield_pct") is not None}
    names = {12: "monthly", 4: "quarterly", 2: "half-yearly", 1: "yearly"}
    return "/".join(names.get(p, f"{p}x a year") for p in sorted(per, reverse=True)) or "n/a"


def print_flags(funds, plan_name):
    print("\nFund flags (for Nick, not printed on the page):")
    any_ = False
    for f in funds:
        for fl in f["flags"]:
            any_ = True
            print(f"  {f['code']}: {fl}")
    if not any_:
        print("  none")


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&amp;family=IBM+Plex+Serif:wght@500;600&amp;display=swap" rel="stylesheet">
<style>
body{{margin:0}}
</style>
</helmet>
"""
TAIL = """
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
  renderVals() { return {}; }
}
</script>
</body>
</html>
"""
SERIF = "font-family: 'IBM Plex Serif', Georgia, serif"
MUTED = "#5b6472"
POS, NEG, NEGBAR = "#14584a", "#a33a0a", "#b4410c"
