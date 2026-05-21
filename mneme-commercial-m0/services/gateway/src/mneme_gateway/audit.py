"""Append-only audit log writer.

M0: a plain Postgres table. Hash-chained immutability + object-lock are M3.
Any tool that observes or mutates state writes one row here.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg


async def emit(
    conn: asyncpg.Connection,
    *,
    event_type: str,
    subject: str,
    target: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_events (event_type, subject, target, metadata, occurred_at)
        VALUES ($1, $2, $3, $4, NOW())
        """,
        event_type, subject, target, json.dumps(metadata or {}, default=str),
    )
