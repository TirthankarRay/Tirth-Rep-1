"""Thin wrapper around the vault git repo.

Exposes the operations the index-sync and gateway services need: head
commit, list files at HEAD, diff between commits, last commit for a path.
"""

from __future__ import annotations

import os
from pathlib import Path

from git import Repo


def get_repo(path: str | Path | None = None) -> Repo:
    p = Path(path or os.environ.get("VAULT_PATH", "/vault"))
    return Repo(p)


def head_sha(repo: Repo) -> str:
    return repo.head.commit.hexsha


def list_tracked_md(repo: Repo) -> list[str]:
    """Paths (relative to repo root) of all tracked .md files at HEAD."""
    return sorted(
        item.path
        for item in repo.head.commit.tree.traverse()
        if item.type == "blob" and item.path.endswith(".md")
    )


def last_commit_for_path(repo: Repo, path: str) -> str:
    """Return the SHA of the most recent commit that touched `path`."""
    commits = list(repo.iter_commits(paths=path, max_count=1))
    if not commits:
        return head_sha(repo)
    return commits[0].hexsha
