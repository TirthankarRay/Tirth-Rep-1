"""Vault seed verifier + git initializer.

The seed *content* lives as actual markdown files under `vault/`. This script:

1. Walks the vault tree
2. Parses each file's frontmatter
3. Validates against the schema for its type
4. Reports per-file status
5. Initializes `vault/.git` if missing and commits the seed state

Idempotent — safe to run multiple times. Designed to be invoked from the
Makefile target `make seed`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import frontmatter

from mneme_schemas import load as load_schemas


VAULT = Path(os.environ.get("VAULT_PATH", "/vault"))
MANIFEST = Path(os.environ.get("MNEME_MANIFEST_PATH", "/manifest"))
SKIP_NAMES = {"README.md"}


def walk_vault_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*.md")):
        if p.name in SKIP_NAMES:
            continue
        yield p


def validate_all() -> tuple[int, int, list[str]]:
    schemas = load_schemas(MANIFEST)
    total = 0
    ok = 0
    errors: list[str] = []
    for path in walk_vault_files(VAULT):
        total += 1
        doc = frontmatter.load(path)
        fm = dict(doc.metadata)
        type_name = fm.get("type")
        if not type_name:
            errors.append(f"{path}: no `type` in frontmatter")
            continue
        problems = schemas.validate(type_name, fm)
        if problems:
            for p in problems:
                errors.append(f"{path}: {p}")
        else:
            ok += 1
    return total, ok, errors


def init_git_repo() -> str:
    if not (VAULT / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=VAULT, check=True)
        subprocess.run(["git", "config", "user.email", "seed@mneme.local"], cwd=VAULT, check=True)
        subprocess.run(["git", "config", "user.name", "Mneme Seed"], cwd=VAULT, check=True)
        subprocess.run(["git", "add", "-A"], cwd=VAULT, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed: initial commercial vault"],
            cwd=VAULT,
            check=True,
        )
        return "initialized"
    # Make sure config is set (no-ops if already set)
    subprocess.run(["git", "config", "user.email", "seed@mneme.local"], cwd=VAULT, check=False)
    subprocess.run(["git", "config", "user.name", "Mneme Seed"], cwd=VAULT, check=False)
    return "already initialized"


def main() -> int:
    print(f"Validating vault content at {VAULT} against schemas in {MANIFEST} ...")
    total, ok, errors = validate_all()
    for e in errors:
        print(f"  ERROR  {e}")
    print(f"  {ok}/{total} files valid")
    if errors:
        print("Seed FAILED — fix errors above before committing.")
        return 1
    state = init_git_repo()
    print(f"Vault git: {state}")
    print("Seed complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
