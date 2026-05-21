"""vault.proposal_status — read state of a proposal by id."""

from __future__ import annotations

import json
from typing import Any

from ..auth import Identity
from ..audit import emit
from ..db import get_pool


async def proposal_status(identity: Identity, proposal_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        prop = await conn.fetchrow(
            "SELECT * FROM proposals WHERE id = $1", proposal_id,
        )
        if not prop:
            return {"error": f"proposal not found: {proposal_id}"}
        queue = await conn.fetch(
            "SELECT reviewer_role, signed_off, signed_by, signed_at, comment "
            "FROM review_queue WHERE proposal_id = $1 ORDER BY reviewer_role",
            proposal_id,
        )
        await emit(
            conn,
            event_type="read",
            subject=identity.user_id,
            target=proposal_id,
            metadata={"tool": "vault.proposal_status"},
        )
    return {
        "id": prop["id"],
        "branch": prop["branch"],
        "target_id": prop["target_id"],
        "target_path": prop["target_path"],
        "agent_id": prop["agent_id"],
        "rationale": prop["rationale"],
        "state": prop["state"],
        "verdict": {
            "label": prop["verdict_label"],
            "rule": prop["verdict_rule"],
            "trace": _json(prop["verdict_trace"]),
        },
        "diff": _json(prop["diff"]),
        "sources": _json(prop["sources"]),
        "review_queue": [
            {
                "role": q["reviewer_role"],
                "signed_off": q["signed_off"],
                "signed_by": q["signed_by"],
                "signed_at": q["signed_at"].isoformat() if q["signed_at"] else None,
                "comment": q["comment"],
            }
            for q in queue
        ],
        "created_at": prop["created_at"].isoformat(),
        "decided_at": prop["decided_at"].isoformat() if prop["decided_at"] else None,
    }


def _json(v):
    if v is None:
        return None
    if isinstance(v, str):
        return json.loads(v)
    return v
