"""Audit feed endpoint."""

from __future__ import annotations

import json
from typing import Any

from .db import get_pool


async def list_events(
    event_type: str | None = None,
    subject: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    pool = await get_pool()
    where: list[str] = []
    params: list[Any] = []
    if event_type:
        params.append(event_type)
        where.append(f"event_type = ${len(params)}")
    if subject:
        params.append(subject)
        where.append(f"subject = ${len(params)}")
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    sql = f"""
        SELECT id, event_type, subject, target, metadata, occurred_at
        FROM audit_events
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT ${len(params)}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return {
        "count": len(rows),
        "events": [
            {
                "id": r["id"],
                "event_type": r["event_type"],
                "subject": r["subject"],
                "target": r["target"],
                "metadata": _loads(r["metadata"]),
                "occurred_at": r["occurred_at"].isoformat(),
            }
            for r in rows
        ],
    }


def _loads(v):
    if v is None:
        return None
    if isinstance(v, str):
        return json.loads(v)
    return v
