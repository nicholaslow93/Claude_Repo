#!/usr/bin/env python3
"""Package repo skills as zip files for upload as claude.ai account skills.

Each zip holds the skill's SKILL.md plus an engine/ folder copied from
work/engine (scripts, blank specs, README; references and their fund data are
left out). Zips go to dist/ (git-ignored).

Usage:  python3 scripts/package-skills.py [skill-name ...]   (default: all)
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "work" / "skills"
ENGINE = ROOT / "work" / "engine"
DIST = ROOT / "dist"
ENGINE_FILES = ["*.py", "*.js", "README.md", "specs/*.json"]


def package(skill: Path) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill.name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill.rglob("*")):
            if f.is_file():
                z.write(f, f"{skill.name}/{f.relative_to(skill)}")
        for pattern in ENGINE_FILES:
            for f in sorted(ENGINE.glob(pattern)):
                z.write(f, f"{skill.name}/engine/{f.relative_to(ENGINE)}")
    return out


def main() -> int:
    names = sys.argv[1:] or [p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists()]
    for name in sorted(names):
        skill = SKILLS / name
        if not (skill / "SKILL.md").exists():
            print(f"skip {name}: no SKILL.md")
            continue
        out = package(skill)
        print(f"{out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
