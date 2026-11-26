# Claude workspace

Nick's Claude Code workspace: rules, skills, templates and scripts.
Templates only. No client data lives here.

## Layout

```
CLAUDE.md                 Global rules, loaded in every session
work/
  CLAUDE.md               Advisory practice rules
  skills/                 Repo copies of advisory skills
  templates/              One-pager layouts and specs (fictional examples only)
  scripts/                Generators and checks (pitch builder, A4 fit check)
  reference/              Archived material
scripts/
  guard.py                Client-data guard
.githooks/                Pre-commit hook
.github/workflows/        The same guard, run on GitHub for every push
.claude/settings.json     Turns the hook on at the start of each session
```

`trading/` and `personal/` get added when they are set up.

## How changes land

1. Each Claude Code session works on its own `claude/...` branch.
2. Nick reviews, then the branch merges into `main` through a pull request.
3. New sessions start from `main`.

## Client-data guard

Every commit is checked. It is blocked if a file:
- is a PDF, Excel, Word, PowerPoint or CSV file
- contains something shaped like an NRIC/FIN number
- contains a known client name

The client-name list is never in the repo. The master copy is the Google Doc
"Claude Guard - Client Names" (Drive, `AI Assisted Documents/Work AI Files`): one name per line, in
every form it appears (full name, first name + initial, initials). Each
session copies it to `~/.config/claude-guard/client-names.txt` (or the path in
`$GUARD_NAMES_FILE`). Without that file the guard still runs the NRIC and
file-type checks and warns that the name check was skipped.

The GitHub check runs without the name list, so it covers NRICs and file
types only.

On a fresh clone outside Claude Code, switch the hook on once with
`git config core.hooksPath .githooks`.
