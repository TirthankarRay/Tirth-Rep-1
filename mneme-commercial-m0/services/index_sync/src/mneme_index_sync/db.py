"""asyncpg pool helper shared across services."""

from __future__ import annotations

import os
import asyncpg


async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "mneme"),
        password=os.environ.get("POSTGRES_PASSWORD", "mneme"),
        database=os.environ.get("POSTGRES_DB", "mneme"),
    )


async def pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "mneme"),
        password=os.environ.get("POSTGRES_PASSWORD", "mneme"),
        database=os.environ.get("POSTGRES_DB", "mneme"),
        min_size=1,
        max_size=8,
    )
