"""vault.read MCP tool."""

from __future__ import annotations

import json
from typing import Any

from ..auth import Identity
from ..audit import emit
from ..db import get_pool
from ..retrieval.redact import can_read, redact_body


async def read(
    identity: Identity,
    id: str,
    sections: list[str] | None = None,
    include: list[str] | None = None,
) -> dict[str, Any]:
    include = include or []
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, path, type, title, frontmatter, body, last_commit, updated_at "
            "FROM files WHERE id = $1",
            id,
        )
        if not row:
            return {"error": f"file not found: {id}"}
        fm = row["frontmatter"]
        if isinstance(fm, str):
            fm = json.loads(fm)
        body = redact_body(identity, fm, row["body"])

        # Section slicing on H2 headings
        if sections and can_read(identity, fm):
            body = _slice_sections(body, sections)

        result: dict[str, Any] = {
            "id": row["id"],
            "path": row["path"],
            "type": row["type"],
            "title": row["title"],
            "frontmatter": fm,
            "body": body,
            "last_commit": row["last_commit"],
            "updated_at": row["updated_at"].isoformat(),
        }

        if "provenance" in include:
            result["provenance"] = {
                "sources": fm.get("sources") or [],
                "owners": fm.get("owners") or [],
                "last_verified": fm.get("last_verified"),
            }
        if "history" in include:
            # Simple: at M0 we expose last_commit only; deeper git history via tools/history.py
            result["history"] = {"last_commit": row["last_commit"]}
        if "related" in include:
            related = await conn.fetch(
                """SELECT dst_id FROM edges WHERE src_id = $1 LIMIT 20""",
                row["id"],
            )
            result["related"] = [r["dst_id"] for r in related]

        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=id,
            metadata={"tool": "vault.read", "sections": sections or [], "include": include},
        )
    return result


def _slice_sections(body: str, sections: list[str]) -> str:
    """Return only the requested H2 sections (by exact heading match)."""
    import re
    out: list[str] = []
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        if title not in sections:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append(body[start:end].rstrip())
    return "\n\n".join(out) if out else body
