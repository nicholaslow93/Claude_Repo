#!/usr/bin/env python3
"""Client-data guard.

Blocks a commit (or fails CI) if any file:
  1. is a document type that tends to hold client data (PDF, Excel, Word, CSV...)
  2. contains something shaped like a Singapore NRIC/FIN number
  3. contains a known client name

Client names are never stored in plain text. They live as salted SHA-256
hashes in .githooks/client-names.sha256. The guard hashes every 1-3 word run
of text in a file and checks it against that list.

Usage:
  python3 scripts/guard.py --staged     # pre-commit hook: staged files only
  python3 scripts/guard.py --all        # CI: every tracked file
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HASH_FILE = ROOT / ".githooks" / "client-names.sha256"
SALT = "nl-guard-v1:"

BLOCKED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".doc", ".pptx", ".ppt",
}
# Files the guard never scans: the hash list itself.
SKIP_PATHS = {".githooks/client-names.sha256"}

NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b")
WORD = re.compile(r"[a-z0-9]+")


def normalise(name: str) -> str:
    return " ".join(WORD.findall(name.lower()))


def hash_name(name: str) -> str:
    return hashlib.sha256((SALT + normalise(name)).encode()).hexdigest()


def load_hashes() -> set:
    if not HASH_FILE.exists():
        return set()
    return {
        line.strip()
        for line in HASH_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    ).stdout


def files_to_check(mode: str):
    """Yield (path, content bytes) pairs."""
    if mode == "--staged":
        names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        for path in filter(None, names.decode().split("\0")):
            yield path, git("show", f":{path}")
    else:
        names = git("ls-files", "-z")
        for path in filter(None, names.decode().split("\0")):
            full = ROOT / path
            if full.is_file():
                yield path, full.read_bytes()


def check(path: str, data: bytes, hashes: set) -> list:
    problems = []
    if Path(path).suffix.lower() in BLOCKED_EXTENSIONS:
        problems.append("document file type is not allowed in the repo")
        return problems
    if path in SKIP_PATHS or b"\0" in data[:8000]:
        return problems  # hash list, or a binary file such as an image or font
    text = data.decode("utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), 1):
        if NRIC.search(line):
            problems.append(f"line {lineno}: looks like an NRIC/FIN number")
        if hashes:
            words = WORD.findall(line.lower())
            for n in (1, 2, 3):
                for i in range(len(words) - n + 1):
                    if hash_name(" ".join(words[i:i + n])) in hashes:
                        problems.append(f"line {lineno}: contains a known client name")
                        break
    return problems


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--staged"
    if mode not in ("--staged", "--all"):
        print(__doc__)
        return 2
    hashes = load_hashes()
    failed = False
    for path, data in files_to_check(mode):
        for problem in check(path, data, hashes):
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
