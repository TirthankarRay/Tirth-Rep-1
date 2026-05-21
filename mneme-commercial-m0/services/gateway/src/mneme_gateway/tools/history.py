"""vault.history — git log for a file (or a section within it)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from git import Repo

from ..auth import Identity
from ..audit import emit
from ..db import get_pool


async def history(
    identity: Identity,
    id: str,
    section: str | None = None,
    since: str | None = None,
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT path FROM files WHERE id = $1", id)
        if not row:
            return {"error": f"file not found: {id}"}
        path = row["path"]
        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=id,
            metadata={"tool": "vault.history", "section": section, "since": since},
        )

    vault = Path(os.environ.get("VAULT_PATH", "/vault"))
    repo = Repo(vault)
    kwargs: dict[str, Any] = {"paths": path}
    if since:
        kwargs["since"] = since
    commits = list(repo.iter_commits(**kwargs))
    changes = []
    for c in commits[:50]:
        changes.append({
            "sha": c.hexsha,
            "author": c.author.name,
            "email": c.author.email,
            "message": c.message.strip(),
            "committed_at": c.committed_datetime.isoformat(),
        })
    return {"id": id, "path": path, "section": section, "changes": changes}
