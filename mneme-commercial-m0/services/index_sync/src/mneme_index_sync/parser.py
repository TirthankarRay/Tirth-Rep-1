"""Parse a vault markdown file into a typed record."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter

from mneme_schemas import normalize


@dataclass
class ParsedFile:
    id: str
    path: str               # repo-relative
    type: str
    title: str
    frontmatter: dict[str, Any]
    body: str


def parse_file(repo_root: Path, repo_relative_path: str) -> ParsedFile:
    full = repo_root / repo_relative_path
    doc = frontmatter.load(full)
    fm = normalize(dict(doc.metadata))
    return ParsedFile(
        id=str(fm.get("id") or repo_relative_path),
        path=repo_relative_path,
        type=str(fm.get("type") or "unknown"),
        title=str(fm.get("title") or full.stem),
        frontmatter=fm,
        body=doc.content,
    )
