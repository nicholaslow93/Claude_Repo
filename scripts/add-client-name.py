#!/usr/bin/env python3
"""Add client names to the guard's blocklist, stored as hashes only.

Usage:
  python3 scripts/add-client-name.py "Jane Tan" "J Tan"

Add each form the name might appear in: full name, first name + initial,
initials. Avoid single common words (e.g. "Alice") that would block
unrelated text. Commit .githooks/client-names.sha256 afterwards; it holds
hashes, never the names.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import HASH_FILE, hash_name, load_hashes, normalise  # noqa: E402


def main() -> int:
    names = [n for n in sys.argv[1:] if normalise(n)]
    if not names:
        print(__doc__)
        return 2
    existing = load_hashes()
    new = [h for h in (hash_name(n) for n in names) if h not in existing]
    with HASH_FILE.open("a") as f:
        for h in new:
            f.write(h + "\n")
    print(f"Added {len(new)} new name hash(es); {len(names) - len(new)} already listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
