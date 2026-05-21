"""Entity resolution.

For M0, resolves frontmatter.entities entries against the ontology CSVs
and returns a list of unresolved (warn-only) tokens. We don't auto-correct
in M0; we surface unknowns so the curator sees them.
"""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


_ONTOLOGY_DIR = Path(os.environ.get("MNEME_MANIFEST_PATH", "/manifest")) / "ontology"


@lru_cache(maxsize=1)
def _ontology() -> dict[str, set[str]]:
    """Map kind -> set of known canonical slugs."""
    out: dict[str, set[str]] = {}
    for csv_path in _ONTOLOGY_DIR.glob("*.csv"):
        kind = csv_path.stem.rstrip("s")  # brands.csv -> brand
        slugs: set[str] = set()
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                slug = row.get("slug")
                if slug:
                    slugs.add(slug)
                aliases = row.get("aliases") or ""
                for a in aliases.split(","):
                    a = a.strip().lower()
                    if a:
                        slugs.add(a)
        out[kind] = slugs
    return out


def resolve(frontmatter: dict[str, Any]) -> list[str]:
    onto = _ontology()
    warnings: list[str] = []
    entities = frontmatter.get("entities") or {}
    if not isinstance(entities, dict):
        return warnings
    for kind, values in entities.items():
        known = onto.get(kind, set())
        if not isinstance(values, (list, tuple)):
            continue
        for v in values:
            if str(v).lower() not in known:
                warnings.append(f"unknown {kind}: '{v}'")
    return warnings
