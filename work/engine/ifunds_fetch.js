// iFUNDS public fund-library fetch (no login). Run in the built-in browser on any
// https://client.asia.manulifeam.com/discovery/en_SG/... page via javascript_tool.
// Set CODES, run, and save the returned JSON string as raw_<date>.json; then run
//   python3 fund_data.py raw_<date>.json  ->  funds_<navdate>.json
// Pulls only raw data. Every derived figure (3M high, yields, flags) is computed in fund_data.py.
const CODES = ["ASGI", "CABF", "NAJD", "NSAD", "MGSO"];
const H = { headers: { locale: "en_SG" } };
const scr = await fetch("/discovery/api/fund-screener", H).then(r => r.json());
const out = { fetched_at: new Date().toISOString(), source: "Manulife iFUNDS public fund library (fund-screener + fund-prices/three-month)", funds: {} , missing: [] };
for (const code of CODES) {
  const f = scr.find(x => x.fundCode === code);
  if (!f) { out.missing.push(code); continue; }
  const p = await fetch(`/discovery/api/fund-prices/${code}/three-month`, H).then(r => r.json());
  const cut = new Date(); cut.setMonth(cut.getMonth() - 26);  // ~2 years of payouts for trend flags
  out.funds[code] = {
    code, name: f.fundName, isin: f.fundFacts && f.fundFacts.isin, currency: f.currencyCode,
    nav: f.navpu, price_date: (f.priceDate || "").slice(0, 10),
    ytd: f.cumulativePerformance && f.cumulativePerformance.ytd,
    perf_asof: f.cumulativePerformance && f.cumulativePerformance.asOfDate,
    dist_frequency: f.distributionFrequency || null,
    plans: (f.subProduct || []).map(s => s.name),
    dividends: (f.dividends || []).filter(d => new Date(d.exDate.replace(/\//g, "-")) >= cut)
      .map(d => ({ ex: d.exDate, dps: d.netDistributionPerShare, nav: d.nav }))
      .sort((a, b) => a.ex.localeCompare(b.ex)),
    prices: (p.data || []).map(d => [d.date, d.fund]),
  };
}
JSON.stringify(out)
