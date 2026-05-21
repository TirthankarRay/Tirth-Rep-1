"""Sign-off endpoint.

When a reviewer signs off:
  1. Update review_queue (signed_off=true, signed_by, signed_at, comment)
  2. Write an audit_events row (event_type='approve')
  3. If all required co-signers have now signed, mark proposal state=approved
     and merge the branch via mneme_validator.router.merge_proposal
"""

from __future__ import annotations

import json
from typing import Any

from mneme_validator.router import merge_proposal

from .db import get_pool


async def sign_off(
    proposal_id: str,
    role: str,
    signer_user_id: str,
    comment: str | None = None,
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            updated = await conn.fetchrow(
                """
                UPDATE review_queue
                SET signed_off = TRUE, signed_by = $1, signed_at = NOW(), comment = $2
                WHERE proposal_id = $3 AND reviewer_role = $4
                RETURNING reviewer_role
                """,
                signer_user_id, comment, proposal_id, role,
            )
            if not updated:
                return {"ok": False, "error": f"no queue row for {proposal_id}/{role}"}

            await conn.execute(
                """
                INSERT INTO audit_events (event_type, subject, target, metadata)
                VALUES ('approve', $1, $2, $3)
                """,
                signer_user_id, proposal_id,
                json.dumps({"role": role, "comment": comment}),
            )

            outstanding = await conn.fetchval(
                "SELECT count(*) FROM review_queue "
                "WHERE proposal_id = $1 AND signed_off = FALSE",
                proposal_id,
            )
            if outstanding == 0:
                prop = await conn.fetchrow(
                    "SELECT branch, target_path FROM proposals WHERE id = $1",
                    proposal_id,
                )
                await conn.execute(
                    "UPDATE proposals SET state = 'approved', decided_at = NOW() "
                    "WHERE id = $1",
                    proposal_id,
                )

    # If complete, actually merge (outside the transaction; merge is a
    # filesystem op).
    if outstanding == 0 and prop:
        merge_result = await merge_proposal(prop["branch"], proposal_id, prop["target_path"])
        async with pool.acquire() as conn2:
            if merge_result.get("ok"):
                await conn2.execute(
                    "UPDATE proposals SET state = 'merged' WHERE id = $1",
                    proposal_id,
                )
            await conn2.execute(
                """
                INSERT INTO audit_events (event_type, subject, target, metadata)
                VALUES ('merge', $1, $2, $3)
                """,
                signer_user_id, proposal_id,
                json.dumps({"branch": prop["branch"], "result": merge_result}),
            )
        return {"ok": True, "complete": True, "merge": merge_result}

    return {"ok": True, "complete": False}


async def reject(proposal_id: str, role: str, signer_user_id: str, comment: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE proposals SET state = 'rejected', decided_at = NOW() WHERE id = $1",
            proposal_id,
        )
        await conn.execute(
            """
            INSERT INTO audit_events (event_type, subject, target, metadata)
            VALUES ('reject', $1, $2, $3)
            """,
            signer_user_id, proposal_id,
            json.dumps({"role": role, "comment": comment}),
        )
    return {"ok": True}
