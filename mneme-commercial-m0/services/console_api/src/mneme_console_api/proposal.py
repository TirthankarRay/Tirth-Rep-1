"""Proposal detail helpers — includes a server-side rendered diff."""

from __future__ import annotations

import difflib
import json
from typing import Any

from .db import get_pool


async def get_detail(proposal_id: str) -> dict[str, Any]:
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

        target = None
        if prop["target_id"]:
            target = await conn.fetchrow(
                "SELECT id, path, type, title, frontmatter, body FROM files WHERE id = $1",
                prop["target_id"],
            )

    diff_blocks = _build_diff(_loads(prop["diff"]))
    fm = None
    if target:
        fm = target["frontmatter"]
        if isinstance(fm, str):
            fm = json.loads(fm)

    return {
        "id": prop["id"],
        "branch": prop["branch"],
        "target_path": prop["target_path"],
        "target_id": prop["target_id"],
        "agent_id": prop["agent_id"],
        "rationale": prop["rationale"],
        "verdict": {
            "label": prop["verdict_label"],
            "rule": prop["verdict_rule"],
            "trace": _loads(prop["verdict_trace"]),
        },
        "sources": _loads(prop["sources"]),
        "diff_blocks": diff_blocks,
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
        "state": prop["state"],
        "created_at": prop["created_at"].isoformat(),
        "decided_at": prop["decided_at"].isoformat() if prop["decided_at"] else None,
        "target": (
            {
                "id": target["id"], "path": target["path"], "type": target["type"],
                "title": target["title"], "frontmatter": fm,
            }
            if target else None
        ),
    }


def _loads(v):
    if v is None:
        return None
    if isinstance(v, str):
        return json.loads(v)
    return v


def _build_diff(diff_records: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in diff_records or []:
        before = (d.get("before") or "").rstrip()
        after = (d.get("after") or "").rstrip()
        unified = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=f"before:{d.get('path','?')}",
                tofile=f"after:{d.get('path','?')}",
                n=2,
                lineterm="",
            )
        )
        out.append({
            "section": d.get("path"),
            "before": before,
            "after": after,
            "unified": unified,
        })
    return out
