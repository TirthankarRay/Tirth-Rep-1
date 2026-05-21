"""vault.list MCP tool — list frontmatter records by domain/type/entity."""

from __future__ import annotations

import json
from typing import Any

from ..auth import Identity
from ..audit import emit
from ..db import get_pool
from ..retrieval.redact import can_read


async def list_files(
    identity: Identity,
    domain: str | None = None,
    type: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pool = await get_pool()
    where: list[str] = []
    params: list[Any] = []
    if type:
        params.append(type)
        where.append(f"type = ${len(params)}")
    if domain:
        params.append(f"{domain}/%")
        where.append(f"path LIKE ${len(params)}")
    if filters and "entities" in filters and isinstance(filters["entities"], dict):
        for kind, vals in filters["entities"].items():
            if not vals:
                continue
            params.append(json.dumps({kind: list(vals)}))
            where.append(f"frontmatter->'entities' @> ${len(params)}::jsonb")
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT id, path, type, title, frontmatter, updated_at
        FROM files {where_clause}
        ORDER BY path
        LIMIT 200
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        out = []
        for r in rows:
            fm = r["frontmatter"]
            if isinstance(fm, str):
                fm = json.loads(fm)
            if not can_read(identity, fm):
                continue
            out.append({
                "id": r["id"],
                "path": r["path"],
                "type": r["type"],
                "title": r["title"],
                "classification": fm.get("classification"),
                "entities": fm.get("entities") or {},
                "last_verified": fm.get("last_verified"),
                "owners": fm.get("owners") or [],
            })
        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=None,
            metadata={
                "tool": "vault.list",
                "domain": domain,
                "type": type,
                "count": len(out),
            },
        )
    return {"count": len(out), "files": out}
