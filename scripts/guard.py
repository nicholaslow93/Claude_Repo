#!/usr/bin/env python3
"""Client-data guard.

Blocks a commit (or fails CI) if any file:
  1. is a document type that tends to hold client data (PDF, Excel, Word, CSV...)
  2. contains something shaped like a Singapore NRIC/FIN number
  3. contains a known client name

The client-name list never lives in this repo. It is read from a file
outside it: $GUARD_NAMES_FILE, or ~/.config/claude-guard/client-names.txt.
The master list is the Google Doc "Claude Guard - Client Names" in Drive
(AI Assisted Documents / Work AI Files). If the file is missing, checks 1 and 2 still run and the
guard prints a warning that the name check was skipped.

Usage:
  python3 scripts/guard.py --staged     # pre-commit hook: staged files only
  python3 scripts/guard.py --all        # CI or manual: every tracked file
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES_FILE = Path(
    os.environ.get("GUARD_NAMES_FILE")
    or Path.home() / ".config" / "claude-guard" / "client-names.txt"
)

BLOCKED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".doc", ".pptx", ".ppt",
}

NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b")
WORD = re.compile(r"[a-z0-9]+")


def normalise(text: str) -> str:
    return " ".join(WORD.findall(text.lower()))


def load_names() -> set:
    """One name per line. '#' lines are comments (a Google Docs export may
    escape them as '\\#')."""
    if not NAMES_FILE.is_file():
        return set()
    names = set()
    for line in NAMES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("\\").strip()
        if line and not line.startswith("#"):
            name = normalise(line)
            if name:
                names.add(name)
    return names


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    ).stdout


def files_to_check(mode: str):
    """Yield (path, content bytes) pairs."""
    if mode == "--staged":
        out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        for path in filter(None, out.decode().split("\0")):
            yield path, git("show", f":{path}")
    else:
        out = git("ls-files", "-z")
        for path in filter(None, out.decode().split("\0")):
            full = ROOT / path
            if full.is_file():
                yield path, full.read_bytes()


def check(path: str, data: bytes, names: set, longest: int) -> list:
    if Path(path).suffix.lower() in BLOCKED_EXTENSIONS:
        return ["document file type is not allowed in the repo"]
    if b"\0" in data[:8000]:
        return []  # binary file such as an image or font
    problems = []
    text = data.decode("utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), 1):
        if NRIC.search(line):
            problems.append(f"line {lineno}: looks like an NRIC/FIN number")
        if names:
            words = WORD.findall(line.lower())
            hit = any(
                " ".join(words[i:i + n]) in names
                for n in range(1, longest + 1)
                for i in range(len(words) - n + 1)
            )
            if hit:
                # Never echo the name itself into logs.
                problems.append(f"line {lineno}: contains a known client name")
    return problems


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--staged"
    if mode not in ("--staged", "--all"):
        print(__doc__)
        return 2
    names = load_names()
    longest = max((len(n.split()) for n in names), default=0)
    if not names:
        print(
            f"Client-data guard: WARNING, no client-name list at {NAMES_FILE}. "
            "Name check skipped; NRIC and file-type checks still ran."
        )
    failed = False
    for path, data in files_to_check(mode):
        for problem in check(path, data, names, longest):
            failed = True
            print(f"BLOCKED  {path}: {problem}")
    if failed:
        print(
            "\nClient-data guard: this repo holds templates only. Remove the "
            "client details (use a fictional client such as 'Jane Tan') and "
            "try again. Do not bypass this check."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
