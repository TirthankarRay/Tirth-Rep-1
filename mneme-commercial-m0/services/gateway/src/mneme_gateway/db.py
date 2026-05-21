"""Gateway DB pool. Process-wide singleton."""

from __future__ import annotations

import os
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            user=os.environ.get("POSTGRES_USER", "mneme"),
            password=os.environ.get("POSTGRES_PASSWORD", "mneme"),
            database=os.environ.get("POSTGRES_DB", "mneme"),
            min_size=1,
            max_size=8,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
