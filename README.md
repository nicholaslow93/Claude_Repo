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
  add-client-name.py      Add a name to the guard's hashed blocklist
.githooks/                Pre-commit hook and the hashed name list
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
- contains a known client name (stored only as salted hashes)

The same check runs on GitHub, so web uploads are covered too. To add a client:

```
python3 scripts/add-client-name.py "Full Name" "First L" "INITIALS"
```

Then commit `.githooks/client-names.sha256`. On a fresh clone outside Claude
Code, switch the hook on once with `git config core.hooksPath .githooks`.
