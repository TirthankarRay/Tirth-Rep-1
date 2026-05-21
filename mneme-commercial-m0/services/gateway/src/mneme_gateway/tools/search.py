"""vault.search MCP tool."""

from __future__ import annotations

from typing import Any, Literal

from ..auth import Identity
from ..db import get_pool
from ..retrieval.hybrid import search as do_search
from ..retrieval.redact import can_read
from ..audit import emit


async def search(
    identity: Identity,
    query: str,
    filters: dict[str, Any] | None = None,
    mode: Literal["hybrid", "semantic", "lexical"] = "hybrid",
    top_k: int = 10,
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        hits = await do_search(conn, query, filters=filters, mode=mode, top_k=top_k)
        # Drop hits the caller can't read at the file level
        hits = [h for h in hits if can_read(identity, h.frontmatter)]
        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=None,
            metadata={
                "tool": "vault.search",
                "query": query,
                "mode": mode,
                "top_k": top_k,
                "filters": filters or {},
                "hits": len(hits),
            },
        )
    return {
        "query": query,
        "mode": mode,
        "results": [
            {
                "file_id": h.file_id,
                "path": h.path,
                "type": h.type,
                "title": h.title,
                "section_path": h.section_path,
                "snippet": h.snippet,
                "score": h.score,
                "entities": h.frontmatter.get("entities") or {},
                "classification": h.frontmatter.get("classification"),
                "last_verified": h.frontmatter.get("last_verified"),
            }
            for h in hits
        ],
    }
