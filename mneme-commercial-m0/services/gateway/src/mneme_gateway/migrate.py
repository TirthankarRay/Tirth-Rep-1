"""Idempotent DB migration: runs postgres-init.sql.

Called by `make up` after Postgres reports ready. Splitting CREATE EXTENSION
into its own statement so it works even if pgvector wasn't loaded on first boot.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg


SCHEMA_PATH = Path(
    os.environ.get("MNEME_SCHEMA_SQL", "/app/deploy/docker/postgres-init.sql")
)


async def run() -> None:
    sql = SCHEMA_PATH.read_text()
    conn = await asyncpg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "mneme"),
        password=os.environ.get("POSTGRES_PASSWORD", "mneme"),
        database=os.environ.get("POSTGRES_DB", "mneme"),
    )
    try:
        await conn.execute(sql)
        print("Migration applied.")
    finally:
        await conn.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
