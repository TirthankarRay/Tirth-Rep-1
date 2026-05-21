"""Merge-after-signoff router.

Called by the console-api when the last required reviewer signs off on a
material proposal. Performs the actual `git merge proposal/...` into main
and triggers index-sync.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import httpx
from git import Repo


VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
INDEX_SYNC_URL = os.environ.get("INDEX_SYNC_URL", "http://index-sync:8003")

# Same justification as the gateway's _GIT_LOCK — serialize against any
# concurrent caller touching the shared working tree.
_GIT_LOCK = asyncio.Lock()


async def merge_proposal(branch: str, proposal_id: str, target_path: str) -> dict:
    async with _GIT_LOCK:
        repo = Repo(VAULT_PATH)
        if repo.active_branch.name != "main":
            repo.git.checkout("main")
        try:
            repo.git.merge(
                branch, "--no-ff",
                "-m", f"merge {proposal_id}: material (signed off)",
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

    asyncio.create_task(_trigger_sync(target_path))
    return {"ok": True, "branch": branch, "merged_into": "main"}


async def _trigger_sync(path: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(f"{INDEX_SYNC_URL}/sync", json={"path": path})
    except Exception as e:
        print(f"warn: post-merge sync failed for {path}: {e}")
