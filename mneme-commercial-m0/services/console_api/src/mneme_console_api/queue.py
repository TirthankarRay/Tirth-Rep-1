"""Queue endpoint helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .db import get_pool


# SLA (M0): material verdicts get 24h, attention gets 72h. Used for the queue
# "time remaining" column.
SLA_HOURS = {"material": 24, "attention": 72}


async def list_open(role: str | None = None) -> dict[str, Any]:
    """Return proposals in `needs_review` state whose review_queue includes
    the given role and has not yet signed off. If role is None, return all.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if role:
            rows = await conn.fetch(
                """
                SELECT p.id, p.target_path, p.target_id, p.agent_id, p.rationale,
                       p.verdict_label, p.verdict_rule, p.state, p.created_at,
                       array_agg(q.reviewer_role ORDER BY q.reviewer_role) AS roles,
                       bool_or(q.signed_off) AS any_signed,
                       array_agg(q.signed_off ORDER BY q.reviewer_role) AS signed_offs
                FROM proposals p
                JOIN review_queue q ON q.proposal_id = p.id
                WHERE p.state = 'needs_review'
                  AND EXISTS (
                      SELECT 1 FROM review_queue q2
                      WHERE q2.proposal_id = p.id
                        AND q2.reviewer_role = $1
                        AND q2.signed_off = FALSE
                  )
                GROUP BY p.id
                ORDER BY p.created_at ASC
                """,
                role,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT p.id, p.target_path, p.target_id, p.agent_id, p.rationale,
                       p.verdict_label, p.verdict_rule, p.state, p.created_at,
                       array_agg(q.reviewer_role ORDER BY q.reviewer_role) AS roles,
                       array_agg(q.signed_off ORDER BY q.reviewer_role) AS signed_offs
                FROM proposals p
                LEFT JOIN review_queue q ON q.proposal_id = p.id
                WHERE p.state = 'needs_review'
                GROUP BY p.id
                ORDER BY p.created_at ASC
                """,
            )

    out = []
    now = datetime.now(timezone.utc)
    for r in rows:
        created = r["created_at"]
        sla_hours = SLA_HOURS.get(r["verdict_label"], 168)
        age_hours = (now - created).total_seconds() / 3600.0
        remaining = sla_hours - age_hours
        out.append({
            "id": r["id"],
            "target_path": r["target_path"],
            "target_id": r["target_id"],
            "agent_id": r["agent_id"],
            "rationale": r["rationale"],
            "verdict_label": r["verdict_label"],
            "verdict_rule": r["verdict_rule"],
            "state": r["state"],
            "created_at": created.isoformat(),
            "roles": r["roles"] or [],
            "signed_offs": r["signed_offs"] or [],
            "age_hours": round(age_hours, 2),
            "sla_remaining_hours": round(remaining, 2),
        })
    # Sort by SLA remaining ascending (most urgent first)
    out.sort(key=lambda x: x["sla_remaining_hours"])
    return {"count": len(out), "proposals": out}
