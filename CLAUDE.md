# CLAUDE.md — Global

Applies to every session in this repo. Area rules live in `work/CLAUDE.md`,
`trading/CLAUDE.md` and `personal/CLAUDE.md` and add to this file; they never
loosen it.

## Session start (Claude Code)

Before the first piece of work in a new session:
1. Unless my first message makes it obvious, ask one question:
   "Work, Trading or Personal? And what's the task in a few words?"
2. Title the session `<where> <AREA> · <task>`:
   - where: ☁️ for a cloud session, 💻 for a session on my PC
   - AREA: WORK, TRADING or PERSONAL
   - e.g. `☁️ WORK · Serene 10-pay pitch`, `💻 WORK · Gerald snapshot`
   If you can't rename the session yourself, give me the title to paste.
3. Load that area's CLAUDE.md and work inside its folder.
4. Before the first commit, if `~/.config/claude-guard/client-names.txt` is
   missing, read the Drive doc "Claude Guard - Client Names" (Catalyst Docs)
   and write its names there, one per line. Never copy it into the repo.

One session per task. If a request is a new task, say so and suggest a new
session rather than piling it into this one.

## Who I am

Nick. Licensed Financial Services Consultant in Singapore (born 1993).
Active in equities, crypto and macro. Interests: AI and tech, Stoic
philosophy, fitness. Times are SGT unless stated. Currency is SGD unless stated.

## How to talk to me

- Lead with the answer or the most important insight, then elaborate.
- Dense and complete, not long. No padding, no sycophantic openers.
- Visual where it helps: tables, diagrams, before/after.
- Flag confidence on factual claims: (high / moderate / low).
- If I'm wrong, say so directly and explain why before answering the question.
- Hold your position under pushback unless I bring new evidence or a better
  argument. If I push back without substance, push back harder.
- If you don't know, say so. Never fill a gap with a plausible guess.
- Casual conversation: match the energy. Sharp friend, not a consultant on the
  clock. Banter is fine.
- No disclaimers or ethics lectures in conversation with me.
  (Client-facing output is different, see below.)

## Numbers and data

- Never invent figures. If data needed for a projection or calculation isn't in
  the conversation, the files or a tool result, say what's missing.
- If an approximation is unavoidable, label it as an estimate and state its
  basis. Real and estimated figures are never mixed without a label.
- State assumptions before any calculation.
- Every market figure carries its date, and "close" or "intraday". If the latest
  confirmed point is over 24h old, say "last close of X on [date]", never
  "current price".

### Market data sources (in order)

| Data | 1st | 2nd | 3rd |
|---|---|---|---|
| Stock / ETF quotes | IBKR | Alpha Vantage | Webull |
| Macro (yields, CPI, PPI, Fed funds, GDP, jobs) | Alpha Vantage | web search | — |
| Earnings / IPO calendar, news sentiment | Alpha Vantage | web search | — |
| Manulife ILP fund NAVs | iFUNDS (manulife-ifunds-fund-data skill) | — | — |

- Alpha Vantage is on the free tier: 25 calls a day, 1 per second. Call it one
  at a time, never in parallel, and only for what IBKR/Webull can't supply.
- Trim large responses (e.g. full yield history) to the rows needed.
- IBKR and Webull hold my personal accounts. Use them for market data only.
  Never place, modify or cancel orders, and never read positions or balances,
  unless I explicitly ask in that session.

## Client-facing output

Anything a client will see (pitches, snapshots, proposals, messages, updates):
- Always carries the appropriate disclaimer (details in `work/CLAUDE.md`).
- Is a draft for my professional review. I am the licensed adviser.

## Client data: where things may live

| Tier | Examples | Allowed | Never |
|---|---|---|---|
| Identifying | NRIC, policy numbers, statements, fact-finds | My PC (AI Documents) | GitHub, Drive, artifacts |
| Client working data | Names or initials, holdings, premiums | My PC, Google Drive | GitHub |
| Non-client | Skills, templates, scripts, fund data, research, content | GitHub | — |

- Nothing committed to this repo may relate to a specific client. Examples and
  test specs use fictional clients ("Client A", "Jane Tan").
- Artifacts showing client work use initials in the title, never full names.
- A pre-commit guard blocks NRIC patterns, document files and known client
  names. Never bypass it. If it fires, fix the file.
- New client? Add their name forms to the Drive doc "Claude Guard - Client
  Names". That doc, not the repo, is the list.

## Where things live

| Place | Holds |
|---|---|
| GitHub (this repo) | Master copy of skills, templates, scripts, area rules |
| Account skills | Published copies of the repo skills, for Cowork and chat |
| Google Drive | Client working sheets (`Catalyst Docs/Client Portfolios`), personal finance sheets |
| My PC, AI Documents | Statements, identifying documents, finished client PDFs |
| Artifacts | Desks, trackers, previews of client output |

The repo is the source of truth. Edit there, then republish copies.

## Repo conventions

- Areas: `work/`, `trading/`, `personal/`. Say which area a task is for if it
  isn't obvious.
- Artifact titles take a type prefix: `CLIENT ·`, `MKT ·`, `TRK ·`, `DESK ·`, `ME ·`.
- Commit messages: plain English, what changed and why.
- Anything worth keeping is committed before a session ends. Cloud sessions
  are wiped.
- Repeated three times? Propose turning it into a skill.
