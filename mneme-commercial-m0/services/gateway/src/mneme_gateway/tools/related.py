"""vault.related — neighbor walk over `edges`."""

from __future__ import annotations

from typing import Any

from ..auth import Identity
from ..audit import emit
from ..db import get_pool


async def related(
    identity: Identity,
    id: str,
    depth: int = 1,
    edge_types: list[str] | None = None,
) -> dict[str, Any]:
    depth = max(1, min(depth, 3))
    pool = await get_pool()
    seen: dict[str, int] = {id: 0}
    frontier = [id]
    out_edges: list[dict[str, Any]] = []

    async with pool.acquire() as conn:
        for d in range(depth):
            if not frontier:
                break
            if edge_types:
                rows = await conn.fetch(
                    """SELECT src_id, dst_id, edge_type FROM edges
                       WHERE src_id = ANY($1::text[]) AND edge_type = ANY($2::text[])""",
                    frontier, edge_types,
                )
            else:
                rows = await conn.fetch(
                    """SELECT src_id, dst_id, edge_type FROM edges
                       WHERE src_id = ANY($1::text[])""",
                    frontier,
                )
            next_frontier: list[str] = []
            for r in rows:
                out_edges.append({
                    "src": r["src_id"], "dst": r["dst_id"], "edge_type": r["edge_type"],
                })
                if r["dst_id"] not in seen:
                    seen[r["dst_id"]] = d + 1
                    next_frontier.append(r["dst_id"])
            frontier = next_frontier

        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=id,
            metadata={"tool": "vault.related", "depth": depth, "edges": len(out_edges)},
        )

    return {
        "root": id,
        "depth": depth,
        "nodes": sorted(seen.keys()),
        "edges": out_edges,
    }
